"""Prepara o modelo de terreno usado para estimar a água por nível do Guaíba.

Ideia (modelo "híbrido" calibrado com a enchente de 2024):

1. O relevo aberto (Terrain Tiles/Mapzen, ~30 m) é uma superfície que inclui prédios e
   vegetação; no centro ele fica metros acima do chão. Por isso não usamos o relevo puro.
2. Onde o Copernicus EMSN194 mapeou água em 06/05 e 08/05/2024, o chão é estimado por
   ``nível do Guaíba naquele dia (ANA) - profundidade modelada``.
3. Nas demais células, o chão é ``relevo - viés``, em que o viés é a mediana da diferença
   entre relevo e chão nas células molhadas; nunca abaixo do nível de 06/05 (estavam secas).
4. A água entra a partir do lago (``priority flood``): para cada célula guardamos a menor cota
   da água capaz de alcançá-la por células conectadas. Uma célula fica alagada no nível L
   se essa cota for menor que L; a profundidade é ``L - chão``.
5. A mancha observada pelo Copernicus em 04, 06, 08 e 10/05/2024 é comparada com o modelo
   no nível medido pela ANA em cada dia (validação).

Os níveis internos estão em metros acima do nível médio do mar (referencial corrigido da
estação ANA 87450020). Para a régua do Cais Mauá (5,35 m no recorde) soma-se 1,18 m,
diferença documentada pela ANA/SGB para o pico de 05/05/2024 (5,35 m ↔ 4,17 m).

Uso: python3 -m scripts.preparar_modelo_agua
"""

from __future__ import annotations

import heapq
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import tifffile
from PIL import Image
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.transform import Affine
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "dados" / "cache"
ZIP_PATH = CACHE / "EMSN194_GeospatialData.zip"
OUTPUT = ROOT / "dados" / "processados" / "modelo_agua_poa.npz"
REPORT = ROOT / "dados" / "processados" / "modelo_agua_validacao.json"
COPERNICUS_URL = "https://riskandrecovery.emergency.copernicus.eu/download/EMSN194/EMSN194_GeospatialData.zip/"
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
HEADERS = {"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica)"}
ANA_DATA = ROOT / "dados" / "processados" / "ana_guaiba_2024_limpo.csv"
BAIRROS = ROOT / "dados" / "processados" / "bairros_poa.geojson"

DEPTH_RASTERS = {
    "2024-05-06": "GeospatialData/Raster_data/P04FLDEL/EMSN194_STD_AOI01_P04FLDEL01_WaterDepth_v01.tif",
    "2024-05-08": "GeospatialData/Raster_data/P04FLDEL/EMSN194_STD_AOI01_P04FLDEL02_WaterDepth_v01.tif",
}
EXTENTS = {
    "2024-05-04": "GeospatialData/Geojson/P06/EMSN194_STD_AOI01_P06TMFL_FloodTempEvolution_04052024_v01.geojson",
    "2024-05-06": "GeospatialData/Geojson/P06/EMSN194_STD_AOI01_P06TMFL_FloodTempEvolution_06052024_v01.geojson",
    "2024-05-08": "GeospatialData/Geojson/P06/EMSN194_STD_AOI01_P06TMFL_FloodTempEvolution_08052024_v01.geojson",
    "2024-05-10": "GeospatialData/Geojson/P06/EMSN194_STD_AOI01_P06TMFL_FloodTempEvolution_10052024_v01.geojson",
}
CALIBRATION_EXTENT = "2024-05-06"
BIAS_RADIUS_CELLS = 50    # 1 km: viés local do relevo, estimado com as células molhadas próximas
MIN_WET_CELLS = 200
CELL = 20.0              # metros, igual ao raster do Copernicus
LAKE_MAX_ELEV = 0.5      # células do relevo nesta cota ou abaixo são tratadas como lago (sementes)
LAND_MIN_MSL = 2.50 - 1.18  # cota de alerta da régua convertida para o referencial da ANA
REGUA_OFFSET = 1.18      # régua do Cais Mauá = referencial corrigido + 1,18 m


def download_sources() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not ZIP_PATH.exists():
        response = requests.get(COPERNICUS_URL, headers=HEADERS, timeout=300)
        response.raise_for_status()
        ZIP_PATH.write_bytes(response.content)


def daily_level(date: str) -> float:
    ana = pd.read_csv(ANA_DATA)
    values = ana[ana.data_hora.str.startswith(date)].nivel_m.dropna()
    return float(values.mean())


def terrain_mosaic(lat: np.ndarray, lon: np.ndarray, zoom: int = 13) -> np.ndarray:
    """Amostra bilinear do relevo Terrarium para arrays de lat/lon."""
    n = 2 ** zoom
    fx = (lon + 180) / 360 * n
    fy = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n
    x0, x1 = int(np.floor(fx.min())), int(np.floor(fx.max()))
    y0, y1 = int(np.floor(fy.min())), int(np.floor(fy.max()))
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256))
    tile_dir = CACHE / "terrarium" / str(zoom)
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            path = tile_dir / str(tx) / f"{ty}.png"
            if not path.exists():
                response = requests.get(TERRAIN_URL.format(z=zoom, x=tx, y=ty), headers=HEADERS, timeout=30)
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
            rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
            mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = \
                rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768
    px = (fx - x0) * 256 - 0.5
    py = (fy - y0) * 256 - 0.5
    ix, iy = np.clip(np.floor(px).astype(int), 0, mosaic.shape[1] - 2), np.clip(np.floor(py).astype(int), 0, mosaic.shape[0] - 2)
    tx, ty = px - ix, py - iy
    top = mosaic[iy, ix] * (1 - tx) + mosaic[iy, ix + 1] * tx
    bottom = mosaic[iy + 1, ix] * (1 - tx) + mosaic[iy + 1, ix + 1] * tx
    return top * (1 - ty) + bottom * ty


def read_depth(archive: zipfile.ZipFile, member: str, transform: Affine, shape_: tuple[int, int]) -> np.ndarray:
    with tifffile.TiffFile(io.BytesIO(archive.read(member))) as tif:
        page = tif.pages[0]
        depth = page.asarray().astype(np.float64)
        scale = page.tags["ModelPixelScaleTag"].value
        tie = page.tags["ModelTiepointTag"].value
    out = np.full(shape_, np.nan)
    col_off = int(round((transform.c - tie[3]) / scale[0]))
    row_off = int(round((tie[4] - transform.f) / scale[1]))
    rows, cols = shape_
    src = depth[max(0, row_off):row_off + rows, max(0, col_off):col_off + cols]
    out[max(0, -row_off):max(0, -row_off) + src.shape[0], max(0, -col_off):max(0, -col_off) + src.shape[1]] = src
    out[~np.isfinite(out) | (out < 0) | (out > 50)] = np.nan
    return out


def local_mean(values: np.ndarray, weights: np.ndarray, radius: int) -> np.ndarray:
    """Média ponderada em janela quadrada (2r+1)², via somas acumuladas."""
    def box(a: np.ndarray) -> np.ndarray:
        padded = np.pad(a, radius + 1)
        c = padded.cumsum(0).cumsum(1)
        k = 2 * radius + 1
        return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])[:a.shape[0], :a.shape[1]]
    total = box(values * weights)
    weight = box(weights)
    with np.errstate(all="ignore"):
        return np.where(weight > 0, total / weight, 0.0)


def priority_flood(ground: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    """Menor cota de água que alcança cada célula a partir das sementes (lago)."""
    rows, cols = ground.shape
    spill = np.full(ground.shape, np.inf)
    heap = []
    for r, c in zip(*np.nonzero(seeds)):
        spill[r, c] = ground[r, c]
        heap.append((ground[r, c], r, c))
    heapq.heapify(heap)
    while heap:
        level, r, c = heapq.heappop(heap)
        if level > spill[r, c]:
            continue
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols:
                candidate = max(level, ground[nr, nc])
                if candidate < spill[nr, nc]:
                    spill[nr, nc] = candidate
                    heapq.heappush(heap, (candidate, nr, nc))
    return spill


def main() -> None:
    download_sources()
    archive = zipfile.ZipFile(ZIP_PATH)

    to_utm = Transformer.from_crs(4326, 32722, always_xy=True)
    to_geo = Transformer.from_crs(32722, 4326, always_xy=True)
    west, south, east, north = -51.31, -30.28, -51.0, -29.92
    xs, ys = to_utm.transform([west, east, west, east], [south, south, north, north])
    x_min, x_max = math.floor(min(xs) / CELL) * CELL, math.ceil(max(xs) / CELL) * CELL
    y_min, y_max = math.floor(min(ys) / CELL) * CELL, math.ceil(max(ys) / CELL) * CELL
    cols, rows = int((x_max - x_min) / CELL), int((y_max - y_min) / CELL)
    transform = Affine(CELL, 0, x_min, 0, -CELL, y_max)
    cx = x_min + (np.arange(cols) + 0.5) * CELL
    cy = y_max - (np.arange(rows) + 0.5) * CELL
    gx, gy = np.meshgrid(cx, cy)
    lon, lat = to_geo.transform(gx, gy)
    print(f"Grade {rows} x {cols} células de {CELL:.0f} m")

    dem = terrain_mosaic(lat, lon)
    levels = {date: daily_level(date) for date in EXTENTS}
    estimates = []
    for date, member in DEPTH_RASTERS.items():
        depth = read_depth(archive, member, transform, dem.shape)
        estimates.append(np.where(depth > 0.01, levels[date] - depth, np.nan))
    with np.errstate(all="ignore"):
        ground_obs = np.nanmean(np.stack(estimates), axis=0)
    has_depth = np.isfinite(ground_obs)
    bias = float(np.nanmedian(dem[has_depth] - ground_obs[has_depth]))
    local_bias = local_mean(np.where(has_depth, dem - ground_obs, 0.0), has_depth.astype(float), BIAS_RADIUS_CELLS)
    count = local_mean(has_depth.astype(float), np.ones_like(dem), BIAS_RADIUS_CELLS) * (2 * BIAS_RADIUS_CELLS + 1) ** 2
    bias_map = np.clip(np.where(count >= MIN_WET_CELLS, local_bias, bias), 0, 15)
    reference = levels[CALIBRATION_EXTENT]
    wet_reference = extent_mask(archive, EXTENTS[CALIBRATION_EXTENT], to_utm, transform, dem.shape) | has_depth
    lake = dem <= LAKE_MAX_ELEV
    # Chão: profundidade observada quando existe; senão relevo sem viés, limitado pela
    # condição observada em 06/05 (abaixo da água se molhado, acima se seco).
    ground = np.where(has_depth, ground_obs,
                      np.where(wet_reference, np.minimum(dem - bias_map, reference - 0.1),
                               np.maximum(dem - bias_map, reference + 0.05)))
    # Terra firme não fica abaixo da cota de alerta (2,50 m na régua): evita ruas "alagadas" com o rio normal
    # onde a profundidade modelada junto ao cais exagera a altura da água.
    ground = np.where(lake, ground, np.maximum(ground, LAND_MIN_MSL))
    ground = np.where(lake & ~wet_reference, np.minimum(dem, 0.0), ground)
    poa = rasterize(((_to_utm(f["geometry"], to_utm), 1)
                     for f in json.loads(BAIRROS.read_text(encoding="utf-8"))["features"]),
                    out_shape=dem.shape, transform=transform, fill=0).astype(bool)
    spill = priority_flood(ground, lake)
    print(f"Viés do relevo (relevo - chão nas células molhadas): {bias:.2f} m")

    validation = []
    for date, member in EXTENTS.items():
        observed = extent_mask(archive, member, to_utm, transform, dem.shape)
        predicted = spill < levels[date]
        valid = poa & ~lake
        tp = int((observed & predicted & valid).sum())
        fp = int((~observed & predicted & valid).sum())
        fn = int((observed & ~predicted & valid).sum())
        validation.append({
            "date": date, "ana_level_msl_m": round(levels[date], 2),
            "regua_equivalent_m": round(levels[date] + REGUA_OFFSET, 2),
            "used_in_calibration": date in DEPTH_RASTERS or date == CALIBRATION_EXTENT,
            "observed_km2": round((observed & valid).sum() * CELL * CELL / 1e6, 2),
            "predicted_km2": round((predicted & valid).sum() * CELL * CELL / 1e6, 2),
            "iou": round(tp / max(1, tp + fp + fn), 3),
            "recall": round(tp / max(1, tp + fn), 3),
            "precision": round(tp / max(1, tp + fp), 3),
        })
        print(validation[-1])

    np.savez_compressed(
        OUTPUT,
        ground_cm=np.round(ground * 100).astype(np.int16),
        spill_cm=np.round(np.where(np.isfinite(spill), spill, 9999) * 100).clip(-32000, 32000).astype(np.int16),
        lake=lake,
        poa=poa,
        transform=np.array([CELL, x_min, y_max]),
    )
    REPORT.write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grid": {"rows": rows, "cols": cols, "cell_m": CELL, "crs": "EPSG:32722", "x_min": x_min, "y_max": y_max},
        "terrain_bias_m": round(bias, 2),
        "terrain_bias_local": {"radius_m": BIAS_RADIUS_CELLS * CELL, "min_wet_cells": MIN_WET_CELLS,
                               "p50_m": round(float(np.median(bias_map[poa])), 2),
                               "p90_m": round(float(np.percentile(bias_map[poa], 90)), 2)},
        "regua_offset_m": REGUA_OFFSET,
        "land_min_msl_m": LAND_MIN_MSL,
        "calibration_levels_msl_m": {d: round(levels[d], 2) for d in DEPTH_RASTERS},
        "validation": validation,
        "sources": {
            "copernicus": COPERNICUS_URL,
            "terrain": "https://registry.opendata.aws/terrain-tiles/",
            "ana": "https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL",
        },
        "note": ("Modelo simplificado de enchimento a partir do lago. Considera o sistema de proteção como em 2024 "
                 "(com passagem de água), não simula vazão, chuva local, drenagem nem correnteza."),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")


def extent_mask(archive, member, to_utm, transform, shape_) -> np.ndarray:
    features = json.loads(archive.read(member))["features"]
    return rasterize(((_to_utm(f["geometry"], to_utm), 1) for f in features),
                     out_shape=shape_, transform=transform, fill=0).astype(bool)


def _to_utm(geometry: dict, transformer: Transformer):
    from shapely.ops import transform as shp_transform
    return shp_transform(lambda x, y, z=None: transformer.transform(x, y), shape(geometry))


if __name__ == "__main__":
    main()

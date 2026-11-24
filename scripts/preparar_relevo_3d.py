"""Prepara uma malha leve de relevo e profundidade histórica para visualização 3D."""

from __future__ import annotations

import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import rasterio
import requests
import tifffile
from pyproj import Transformer
from rasterio.io import MemoryFile
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

from scripts.preparar_rotas_2024 import COPERNICUS_URL, ZIP_FLOOD, ZIP_RASTER

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dados/processados/relevo_3d_2024_05_06.json"
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff/12/1465/2406.tif"
TERRAIN_PAGE = "https://registry.opendata.aws/terrain-tiles/"
REGIONS = {
    "cais": {"label": "Cais Mauá", "bbox": [-51.2345, -30.0295, -51.2295, -30.025]},
    "usina": {"label": "Usina do Gasômetro", "bbox": [-51.237, -30.035, -51.232, -30.03]},
}
GRID = 48


def main() -> None:
    headers = {"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica)"}
    source_zip = Path("/tmp/EMSN194_GeospatialData.zip")
    if not source_zip.exists():
        response = requests.get(COPERNICUS_URL, headers=headers, timeout=120)
        response.raise_for_status()
        source_zip.write_bytes(response.content)
    terrain_response = requests.get(TERRAIN_URL, headers=headers, timeout=40)
    terrain_response.raise_for_status()
    with zipfile.ZipFile(source_zip) as archive:
        flood = prep(unary_union([shape(f["geometry"]) for f in json.loads(archive.read(ZIP_FLOOD))["features"]]))
        with tifffile.TiffFile(io.BytesIO(archive.read(ZIP_RASTER))) as tif:
            page = tif.pages[0]
            depth = page.asarray()
            scale = page.tags["ModelPixelScaleTag"].value
            tie = page.tags["ModelTiepointTag"].value
        water_projection = Transformer.from_crs(4326, 32722, always_xy=True)
        with MemoryFile(terrain_response.content) as memory, memory.open() as terrain:
            terrain_projection = Transformer.from_crs(4326, terrain.crs, always_xy=True)
            regions = {}
            for key, region in REGIONS.items():
                west, south, east, north = region["bbox"]
                elevations, depths = [], []
                for row in range(GRID):
                    lat = north + (south - north) * row / (GRID - 1)
                    elevation_row, depth_row = [], []
                    for col in range(GRID):
                        lon = west + (east - west) * col / (GRID - 1)
                        tx, ty = terrain_projection.transform(lon, lat)
                        elev = float(next(terrain.sample([(tx, ty)]))[0])
                        elevation_row.append(None if elev == terrain.nodata else round(elev, 1))
                        wet = 0.0
                        if flood.covers(Point(lon, lat)):
                            wx, wy = water_projection.transform(lon, lat)
                            c = math.floor((wx - tie[3]) / scale[0])
                            r = math.floor((tie[4] - wy) / scale[1])
                            if 0 <= r < depth.shape[0] and 0 <= c < depth.shape[1]:
                                value = float(depth[r, c])
                                wet = round(value, 2) if math.isfinite(value) and value > 0 else 0.0
                        depth_row.append(wet)
                    elevations.append(elevation_row)
                    depths.append(depth_row)
                if not any(value > 0 for row in depths for value in row):
                    raise RuntimeError(f"Região sem profundidade modelada: {key}")
                regions[key] = {**region, "elevation_m": elevations, "water_depth_m": depths}
    output = {"metadata": {"scenario_date": "2024-05-06",
                            "collected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "terrain_source": TERRAIN_URL, "terrain_source_page": TERRAIN_PAGE,
                            "water_source": COPERNICUS_URL,
                            "grid_size": GRID, "unit": "m",
                            "note": "Sobreposição visual exploratória: DEM regional e profundidade modelada de fontes diferentes. Não representa uma superfície hidráulica validada, não usa a cota da régua e não serve para decisão de segurança."},
              "regions": regions}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUTPUT}: {len(regions)} regiões, {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()

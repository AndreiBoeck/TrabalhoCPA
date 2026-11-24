"""Gera uma pequena rede pedonal com profundidade estimada em 06/05/2024.

Fonte da profundidade: Copernicus EMSN194, produto P04 FLDEL01 (modelo HAND).
Ruas: OpenStreetMap API 0.6. A rede resultante é histórica e experimental.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import tifffile
from pyproj import Transformer
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dados" / "processados" / "rotas_centro_2024_05_06.json"
COPERNICUS_URL = "https://riskandrecovery.emergency.copernicus.eu/download/EMSN194/EMSN194_GeospatialData.zip/"
OSM_URL = "https://api.openstreetmap.org/api/0.6/map"
BBOX = (-51.235, -30.035, -51.225, -30.025)
ZIP_RASTER = "GeospatialData/Raster_data/P04FLDEL/EMSN194_STD_AOI01_P04FLDEL01_WaterDepth_v01.tif"
ZIP_FLOOD = "GeospatialData/Geojson/P04/EMSN194_STD_AOI01_P04FLDEL01_FloodExtent_v01.geojson"
ZIP_AOI = "GeospatialData/Geojson/EMSN194_STD_AOI01_P00_aoi_v01.geojson"
WALKABLE = {"residential", "tertiary", "secondary", "primary", "living_street", "pedestrian", "footway", "service", "steps", "path", "unclassified", "track"}


def obtain_sources(source_zip: Path | None, osm_xml: Path | None):
    headers = {"User-Agent": "TrabalhoCPA/0.1 (https://github.com/AndreiBoeck/TrabalhoCPA)"}
    if source_zip is None:
        response = requests.get(COPERNICUS_URL, headers=headers, timeout=120)
        response.raise_for_status()
        source_zip = Path(tempfile.gettempdir()) / "cpa_EMSN194_GeospatialData.zip"
        source_zip.write_bytes(response.content)
    if osm_xml is None:
        response = requests.get(OSM_URL, params={"bbox": ",".join(map(str, BBOX))}, headers=headers, timeout=90)
        response.raise_for_status()
        osm_xml = Path(tempfile.gettempdir()) / "cpa_osm_centro.xml"
        osm_xml.write_bytes(response.content)
    return source_zip, osm_xml


def build(source_zip: Path, osm_xml: Path) -> dict:
    with zipfile.ZipFile(source_zip) as bundle:
        flooded = unary_union([shape(f["geometry"]) for f in json.loads(bundle.read(ZIP_FLOOD))["features"]])
        aoi = unary_union([shape(f["geometry"]) for f in json.loads(bundle.read(ZIP_AOI))["features"]])
        with tifffile.TiffFile(io.BytesIO(bundle.read(ZIP_RASTER))) as tiff:
            page = tiff.pages[0]
            raster = page.asarray()
            scale = page.tags["ModelPixelScaleTag"].value
            tie = page.tags["ModelTiepointTag"].value

    flood_area, study_area = prep(flooded), prep(aoi)
    transformer = Transformer.from_crs(4326, 32722, always_xy=True)

    def depth(lon: float, lat: float):
        point = Point(lon, lat)
        if not study_area.covers(point):
            return None
        if not flood_area.covers(point):
            return 0.0
        x, y = transformer.transform(lon, lat)
        column = math.floor((x - tie[3]) / scale[0])
        row = math.floor((tie[4] - y) / scale[1])
        if not (0 <= row < raster.shape[0] and 0 <= column < raster.shape[1]):
            return None
        value = float(raster[row, column])
        if not math.isfinite(value) or value < 0:
            return None
        return max(0.001, round(value, 3)) if value > 0 else 0.0

    osm = ET.parse(osm_xml).getroot()
    coordinates = {}
    for element in osm.findall("node"):
        lon, lat = float(element.get("lon")), float(element.get("lat"))
        if BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]:
            coordinates[element.get("id")] = (lon, lat)

    nodes = {}
    edges = []
    for way in osm.findall("way"):
        tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
        if tags.get("highway") not in WALKABLE or tags.get("access") in {"no", "private"} or tags.get("foot") in {"no", "private"}:
            continue
        refs = [nd.get("ref") for nd in way.findall("nd")]
        for source, target in zip(refs, refs[1:]):
            if source not in coordinates or target not in coordinates:
                continue
            lon1, lat1 = coordinates[source]
            lon2, lat2 = coordinates[target]
            first, last = depth(lon1, lat1), depth(lon2, lat2)
            if first is None or last is None:
                continue
            x1, y1 = transformer.transform(lon1, lat1)
            x2, y2 = transformer.transform(lon2, lat2)
            length = math.hypot(x2 - x1, y2 - y1)
            if length <= 0:
                continue
            samples = [depth(lon1 + (lon2 - lon1) * i / n, lat1 + (lat2 - lat1) * i / n)
                       for n in [max(1, math.ceil(length / 10))] for i in range(n + 1)]
            # Pontes e passagens elevadas exigem cota da via, ausente no raster.
            water = None if tags.get("bridge") == "yes" or any(v is None for v in samples) else max(samples)
            nodes[source] = {"id": source, "lon": lon1, "lat": lat1, "depth_m": first}
            nodes[target] = {"id": target, "lon": lon2, "lat": lat2, "depth_m": last}
            edges.append({"source": source, "target": target, "length_m": round(length, 2),
                          "depth_m": water, "bidirectional": tags.get("oneway:foot") != "yes"})

    visible_flood = flooded.intersection(box(*BBOX)).simplify(0.00001, preserve_topology=True)
    return {
        "metadata": {
            "scenario": "Profundidade estimada para 06/05/2024 (Copernicus EMSN194 P04 FLDEL01)",
            "scenario_date": "2024-05-06",
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "flood_source": COPERNICUS_URL,
            "roads_source": f"{OSM_URL}?bbox={','.join(map(str, BBOX))}",
            "bbox": BBOX,
            "mode": "a_pe",
            "raster_resolution_m": 20,
            "raster_crs": "EPSG:32722 (WGS 84 / UTM 22S)",
            "depth_unit": "m",
            "depth_reference": "profundidade local estimada; não é cota da régua do Guaíba",
            "note": "Cenário histórico experimental; profundidade modelada, sem bloqueios atuais ou validação de vias.",
        },
        "nodes": list(nodes.values()),
        "edges": edges,
        "flood_extent": {"type": "Feature", "properties": {"date": "2024-05-06", "source": "Copernicus EMSN194 P04 FLDEL01"},
                         "geometry": mapping(visible_flood)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--osm-xml", type=Path)
    args = parser.parse_args()
    source_zip, osm_xml = obtain_sources(args.source_zip, args.osm_xml)
    result = build(source_zip, osm_xml)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUTPUT}: {len(result['nodes'])} nós, {len(result['edges'])} trechos")


if __name__ == "__main__":
    main()

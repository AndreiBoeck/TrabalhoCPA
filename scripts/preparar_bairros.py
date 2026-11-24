"""Baixa os limites oficiais e prepara um GeoJSON leve para o mapa temático INCT."""

from __future__ import annotations

import json
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://drive.google.com/uc?export=download&id=17gLbmV3DNjdu6Df9uMwogtnJxmbRhOqI"
SOURCE_PAGE = "https://prefeitura.poa.br/smpg/observapoa/mapas"
DEST = ROOT / "dados/processados/bairros_poa.geojson"
INCT = ROOT / "dados/processados/inct_simai_limpo.json"
NS = {"k": "http://www.opengis.net/kml/2.2"}


def normalized(name: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", name.upper())
                   if unicodedata.category(char) != "Mn" and char.isalnum())


def ring(element: ET.Element) -> list[tuple[float, float]]:
    value = element.findtext("k:LinearRing/k:coordinates", namespaces=NS) or ""
    return [(float(parts[0]), float(parts[1])) for point in value.split()
            if len(parts := point.split(",")) >= 2]


def main() -> None:
    response = requests.get(SOURCE, timeout=60, headers={"User-Agent": "TrabalhoCPA/1.0"})
    response.raise_for_status()
    if not response.content.lstrip().startswith(b"<?xml"):
        raise RuntimeError("A fonte não retornou o KML esperado")
    root = ET.fromstring(response.content)
    official_names = {normalized(row["bairro"]): row["bairro"]
                      for row in json.loads(INCT.read_text(encoding="utf-8"))}
    aliases = {"CELAPARICIOBORGES": "CORONELAPARICIOBORGES",
               "PASSODAAREIA": "PASSODAREIA"}
    grouped: dict[str, list[Polygon]] = {}
    for place in root.findall(".//k:Placemark", NS):
        raw = place.findtext(".//k:SimpleData", namespaces=NS)
        if not raw:
            continue
        key = aliases.get(normalized(raw), normalized(raw))
        if key not in official_names:
            raise RuntimeError(f"Bairro sem correspondente no INCT: {raw}")
        name = official_names[key]
        for element in place.findall(".//k:Polygon", NS):
            outer = element.find("k:outerBoundaryIs", NS)
            if outer is None:
                continue
            holes = [ring(hole) for hole in element.findall("k:innerBoundaryIs", NS)]
            polygon = Polygon(ring(outer), holes)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            if not polygon.is_empty:
                grouped.setdefault(name, []).append(polygon)
    if set(grouped) != set(official_names.values()):
        raise RuntimeError("Os bairros da Prefeitura e do INCT não coincidem")
    features = []
    for name, polygons in sorted(grouped.items()):
        geometry = unary_union(polygons).simplify(0.00004, preserve_topology=True)
        features.append({"type": "Feature", "properties": {"bairro": name},
                         "geometry": mapping(geometry)})
    result = {"type": "FeatureCollection", "features": features,
              "metadata": {"source": "Prefeitura de Porto Alegre — Bairros Oficiais",
                           "source_page": SOURCE_PAGE, "source_url": SOURCE,
                           "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                           "crs": "WGS84 (lon/lat) do KML", "feature_count": len(features),
                           "note": "Limites dos bairros; não são manchas de inundação."}}
    DEST.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{DEST}: {len(features)} bairros, {DEST.stat().st_size} bytes")


if __name__ == "__main__":
    main()

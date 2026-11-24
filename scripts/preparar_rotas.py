"""Gera a rede de ruas a pé da área que alagou em 2024 (Centro, 4º Distrito, Menino Deus, Cidade Baixa).

Ruas: API 0.6 do OpenStreetMap, baixada em blocos (cache em dados/cache/osm_tiles).
Mancha observada em 06/05/2024: Copernicus EMSN194 (zip em dados/cache).
A profundidade de cada trecho não é gravada aqui: o backend a calcula para cada nível
com o modelo de água (backend/water.py).

Uso: python3 -m scripts.preparar_rotas
"""

from __future__ import annotations

import json
import math
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dados" / "processados" / "rotas_poa.json"
TILES = ROOT / "dados" / "cache" / "osm_tiles"
COPERNICUS_ZIP = ROOT / "dados" / "cache" / "EMSN194_GeospatialData.zip"
ZIP_FLOOD = "GeospatialData/Geojson/P04/EMSN194_STD_AOI01_P04FLDEL01_FloodExtent_v01.geojson"
OSM_URL = "https://api.openstreetmap.org/api/0.6/map"
BBOX = (-51.245, -30.065, -51.165, -29.975)  # oeste, sul, leste, norte
WALKABLE = {"primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "residential",
            "living_street", "pedestrian", "unclassified", "footway", "steps", "path", "service"}
SKIP_SERVICE = {"parking_aisle", "driveway", "drive-through"}
_TO_UTM = Transformer.from_crs(4326, 32722, always_xy=True)


def download_tiles(rows: int = 4, cols: int = 4):
    """Baixa os blocos que faltam no cache; divide o bloco quando a API recusa por excesso de nós."""
    TILES.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "educational-flood-dashboard/1.0"}

    def get(s, w, n, e, depth=0):
        path = TILES / f"{s:.4f}_{w:.4f}_{n:.4f}_{e:.4f}.xml"
        if path.exists():
            return
        response = requests.get(OSM_URL, params={"bbox": f"{w},{s},{e},{n}"}, headers=headers, timeout=120)
        if response.status_code == 400 and depth < 3:
            ms, me = (s + n) / 2, (w + e) / 2
            for part in [(s, w, ms, me), (s, me, ms, e), (ms, w, n, me), (ms, me, n, e)]:
                get(*part, depth + 1)
            return
        response.raise_for_status()
        path.write_bytes(response.content)
        time.sleep(1)

    w, s, e, n = BBOX
    for i in range(rows):
        for j in range(cols):
            get(s + (n - s) * i / rows, w + (e - w) * j / cols, s + (n - s) * (i + 1) / rows, w + (e - w) * (j + 1) / cols)


def walkable(tags: dict) -> bool:
    if tags.get("highway") not in WALKABLE or tags.get("area") == "yes":
        return False
    if tags.get("access") in {"no", "private"} or tags.get("foot") in {"no", "private"}:
        return False
    return not (tags.get("highway") == "service" and tags.get("service") in SKIP_SERVICE)


def read_osm():
    coords, ways = {}, {}
    for path in sorted(TILES.glob("*.xml")):
        root = ET.parse(path).getroot()
        for node in root.iter("node"):
            coords[node.get("id")] = (float(node.get("lon")), float(node.get("lat")))
        for way in root.iter("way"):
            tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
            if walkable(tags):
                ways[way.get("id")] = ([nd.get("ref") for nd in way.findall("nd")], tags)
    return coords, ways


def build(coords: dict, ways: dict) -> dict:
    w, s, e, n = BBOX
    inside = lambda ref: ref in coords and w <= coords[ref][0] <= e and s <= coords[ref][1] <= n
    pieces = []  # cada via vira trechos contínuos dentro do recorte
    for refs, tags in ways.values():
        current = []
        for ref in refs:
            if inside(ref):
                current.append(ref)
            else:
                if len(current) > 1:
                    pieces.append((current, tags))
                current = []
        if len(current) > 1:
            pieces.append((current, tags))

    use = defaultdict(int)
    for refs, _ in pieces:
        for i, ref in enumerate(refs):
            use[ref] += 2 if i in (0, len(refs) - 1) else 1

    node_index, nodes, edges = {}, [], []

    def node_id(ref):
        if ref not in node_index:
            node_index[ref] = len(nodes)
            nodes.append([round(coords[ref][1], 6), round(coords[ref][0], 6)])
        return node_index[ref]

    for refs, tags in pieces:
        start = 0
        for i in range(1, len(refs)):
            if use[refs[i]] < 2 and i < len(refs) - 1:
                continue
            chain = refs[start:i + 1]
            start = i
            xy = [_TO_UTM.transform(*coords[ref]) for ref in chain]
            length = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
            if length < 0.5:
                continue
            edges.append({
                "u": node_id(chain[0]), "v": node_id(chain[-1]), "length_m": round(length, 1),
                "oneway": tags.get("oneway:foot") == "yes" or (tags.get("highway") == "steps" and tags.get("oneway") == "yes"),
                "bridge": tags.get("bridge") not in (None, "no"),
                "name": tags.get("name", ""),
                "coords": [[round(coords[ref][1], 6), round(coords[ref][0], 6)] for ref in chain],
            })

    # Mantém só o maior componente conectado (descarta pedaços soltos na borda do recorte).
    parent = list(range(len(nodes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for edge in edges:
        parent[find(edge["u"])] = find(edge["v"])
    sizes = defaultdict(int)
    for edge in edges:
        sizes[find(edge["u"])] += 1
    main = max(sizes, key=sizes.get)
    edges = [edge for edge in edges if find(edge["u"]) == main]
    used = sorted({i for edge in edges for i in (edge["u"], edge["v"])})
    remap = {old: new for new, old in enumerate(used)}
    nodes = [nodes[i] for i in used]
    for edge in edges:
        edge["u"], edge["v"] = remap[edge["u"]], remap[edge["v"]]
    return {"nodes": nodes, "edges": edges}


def observed_extent():
    with zipfile.ZipFile(COPERNICUS_ZIP) as bundle:
        flooded = unary_union([shape(f["geometry"]) for f in json.loads(bundle.read(ZIP_FLOOD))["features"]])
    clipped = flooded.intersection(box(*BBOX)).simplify(0.00003, preserve_topology=True)
    return {"type": "Feature", "properties": {"date": "2024-05-06", "source": "Copernicus EMSN194 P04 FLDEL01"},
            "geometry": mapping(clipped)}


def main():
    download_tiles()
    network = build(*read_osm())
    network["metadata"] = {
        "area": "Centro Histórico, 4º Distrito, Menino Deus e Cidade Baixa (Porto Alegre)",
        "bbox": list(BBOX),
        "collected_at_utc": datetime.fromtimestamp(min(p.stat().st_mtime for p in TILES.glob("*.xml")), timezone.utc).isoformat(),
        "roads_source": OSM_URL,
        "mode": "a_pe",
        "note": "Profundidade por trecho calculada no backend com o modelo de água, para o nível escolhido.",
    }
    network["flood_extent"] = observed_extent()
    OUTPUT.write_text(json.dumps(network, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUTPUT}: {len(network['nodes'])} nós, {len(network['edges'])} trechos, {OUTPUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

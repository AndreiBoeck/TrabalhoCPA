"""Rotas a pé na área que alagou em 2024, com a profundidade do modelo de água no nível escolhido.

A rede vem de ``scripts/preparar_rotas.py`` (OpenStreetMap). Para cada nível da régua, cada trecho
recebe a maior profundidade do modelo ao longo dele (amostras a cada ~10 m). A saída a pé procura o
ponto seco mais próximo com folga: o rio teria de subir pelo menos ``SAFE_MARGIN_M`` a mais para
chegar lá.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from pyproj import Transformer

from backend import water
from backend.routing import best_exit

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "dados" / "processados" / "rotas_poa.json"
SAMPLE_STEP_M = 10
SAFE_MARGIN_M = 1.0
SNAP_LIMIT_M = 60
MIN_DRY_AREA_M = 3000  # o ponto seco precisa estar ligado a pelo menos 3 km de ruas secas (descarta ilhotas)
WALK_M_PER_MIN = 75  # 4,5 km/h em área seca
_TO_UTM = Transformer.from_crs(4326, 32722, always_xy=True)


@lru_cache(maxsize=1)
def network() -> dict:
    data = json.loads(NETWORK.read_text(encoding="utf-8"))
    nodes = np.array(data["nodes"], dtype=float)  # [lat, lon]
    edges = data["edges"]
    m = water.model()
    rows, cols = m["ground"].shape

    def cells(lats, lons):
        x, y = _TO_UTM.transform(lons, lats)
        c = ((np.asarray(x) - m["x_min"]) // m["cell"]).astype(int)
        r = ((m["y_max"] - np.asarray(y)) // m["cell"]).astype(int)
        ok = (r >= 0) & (r < rows) & (c >= 0) & (c < cols)
        return np.clip(r, 0, rows - 1), np.clip(c, 0, cols - 1), ok

    # Amostras ao longo de cada trecho, em ordem, com o índice do trecho de cada amostra.
    lats, lons, owner = [], [], []
    for index, edge in enumerate(edges):
        pts = edge["coords"]
        for (la1, lo1), (la2, lo2) in zip(pts, pts[1:]):
            n = max(1, math.ceil(math.dist((la1 * 111_200, lo1 * 96_400), (la2 * 111_200, lo2 * 96_400)) / SAMPLE_STEP_M))
            for i in range(n):
                lats.append(la1 + (la2 - la1) * i / n)
                lons.append(lo1 + (lo2 - lo1) * i / n)
                owner.append(index)
        lats.append(pts[-1][0])
        lons.append(pts[-1][1])
        owner.append(index)
    r, c, ok = cells(lats, lons)
    owner = np.array(owner)
    # Amostras que caem em célula do lago (borda da orla na grade de 20 m) não contam como rua alagada.
    lake = ok & m["lake"][r, c]
    sample_ground = np.where(ok & ~lake, m["ground"][r, c], np.nan)
    sample_spill = np.where(ok & ~lake, m["spill"][r, c], 99.0)
    starts = np.flatnonzero(np.r_[True, owner[1:] != owner[:-1]])
    unknown = np.zeros(len(edges), bool)
    np.logical_or.at(unknown, owner, ~ok)

    nr, nc, nok = cells(nodes[:, 0], nodes[:, 1])
    node_lake = nok & m["lake"][nr, nc]
    node_ground = np.where(nok, m["ground"][nr, nc], np.nan)
    node_spill = np.where(nok & ~node_lake, m["spill"][nr, nc], np.where(nok, 99.0, np.nan))

    # Segmentos em metros (aproximação local) para encaixar cliques na rua mais próxima.
    seg_a, seg_b, seg_edge, seg_offset = [], [], [], []
    for index, edge in enumerate(edges):
        along = 0.0
        pts = [(lo * 96_400, la * 111_200) for la, lo in edge["coords"]]
        for a, b in zip(pts, pts[1:]):
            seg_a.append(a)
            seg_b.append(b)
            seg_edge.append(index)
            seg_offset.append(along)
            along += math.dist(a, b)
    return {
        "raw": data, "nodes": nodes, "edges": edges,
        "u": np.array([e["u"] for e in edges]), "v": np.array([e["v"] for e in edges]),
        "length": np.array([e["length_m"] for e in edges]), "bridge": np.array([e["bridge"] for e in edges]),
        "sample_ground": sample_ground, "sample_spill": sample_spill, "starts": starts, "unknown": unknown,
        "node_ground": node_ground, "node_spill": node_spill,
        "seg_a": np.array(seg_a), "seg_b": np.array(seg_b), "seg_edge": np.array(seg_edge), "seg_offset": np.array(seg_offset),
    }


def _level_key(level_regua: float) -> float:
    return round(min(12.0, max(0.0, level_regua)), 2)


@lru_cache(maxsize=64)
def depths(level_regua: float) -> dict:
    """Profundidade por trecho e por nó no nível da régua (None = desconhecida)."""
    net = network()
    level = water.regua_to_msl(level_regua)
    sample = np.where(net["sample_spill"] < level, level - net["sample_ground"], 0.0)
    edge = np.maximum.reduceat(np.nan_to_num(sample, nan=0.0), net["starts"])
    node = np.where(np.isnan(net["node_spill"]), np.nan,
                    np.where(net["node_spill"] < level, np.maximum(level - net["node_ground"], 0.01), 0.0))
    # Pontes e viadutos ficam acima da água: valem as cabeceiras.
    edge = np.where(net["bridge"], np.fmax(node[net["u"]], node[net["v"]]), edge)
    edge = np.where(net["unknown"] & ~net["bridge"], np.nan, np.round(edge, 2))
    safe = (node == 0) & ((net["node_spill"] >= level + SAFE_MARGIN_M) | (net["node_spill"] >= 99))
    # Ilhotas secas (viadutos, plataformas, quarteirões altos cercados de água) não servem de destino:
    # o ponto seco precisa pertencer a um conjunto de ruas secas ligadas entre si com MIN_DRY_AREA_M.
    parent = np.arange(len(net["nodes"]))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    dry_edges = np.flatnonzero(np.nan_to_num(edge, nan=1.0) == 0)
    for i in dry_edges.tolist():
        a, b = find(int(net["u"][i])), find(int(net["v"][i]))
        if a != b:
            parent[a] = b
    roots = np.array([find(i) for i in range(len(parent))])
    area = np.zeros(len(parent))
    np.add.at(area, roots[net["u"][dry_edges]], net["length"][dry_edges])
    safe &= area[roots] >= MIN_DRY_AREA_M
    adjacency = [[] for _ in range(len(net["nodes"]))]
    for i, (u, v, length, d) in enumerate(zip(net["u"].tolist(), net["v"].tolist(), net["length"].tolist(), edge.tolist())):
        d = None if math.isnan(d) else d
        adjacency[u].append((v, length, d, (i, True)))
        if not net["edges"][i]["oneway"]:
            adjacency[v].append((u, length, d, (i, False)))
    node_list = [None if math.isnan(x) else float(x) for x in node.tolist()]
    return {"level": level, "edge": edge, "node": node_list, "safe": set(np.flatnonzero(safe).tolist()), "adjacency": adjacency}


def streets() -> dict:
    """Geometria fixa da rede (o navegador guarda e só pede as profundidades por nível)."""
    net = network()
    raw = net["raw"]
    _, _, bounds = water.grid_window(tuple(raw["metadata"]["bbox"]))
    return {"metadata": raw["metadata"], "overlay_bounds": bounds, "flood_extent": raw["flood_extent"],
            "edges": [{"coords": e["coords"], "name": e["name"], "bridge": e["bridge"]} for e in net["edges"]],
            "total_length_m": round(float(net["length"].sum()))}


def depths_public(level_regua: float) -> dict:
    level_regua = _level_key(level_regua)
    d = depths(level_regua)
    net = network()
    wet = np.nan_to_num(d["edge"], nan=0) > 0
    return {"level_regua_m": level_regua,
            "edge_depth_m": [None if math.isnan(x) else round(x, 2) for x in d["edge"].astype(float).tolist()],
            "wet_length_m": round(float(net["length"][wet].sum())), "wet_edges": int(wet.sum()),
            "total_length_m": round(float(net["length"].sum())), "total_edges": len(net["edges"])}


def snap(lat: float, lon: float) -> dict:
    net = network()
    p = np.array([lon * 96_400, lat * 111_200])
    a, b = net["seg_a"], net["seg_b"]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-9), 0, 1)
    q = a + ab * t[:, None]
    dist = np.hypot(*(q - p).T)
    i = int(dist.argmin())
    edge = int(net["seg_edge"][i])
    along = float(net["seg_offset"][i] + t[i] * math.dist(a[i], b[i]))
    seg_index = i - int(np.searchsorted(net["seg_edge"], edge))
    return {"edge": edge, "segment": seg_index, "t": float(t[i]), "distance_m": round(float(dist[i]), 1),
            "along_m": along, "lat": float(q[i][1] / 111_200), "lon": float(q[i][0] / 96_400)}


def _cut(coords: list, snapped: dict, toward_end: bool) -> list:
    """Pedaço da geometria do trecho entre o ponto encaixado e uma das pontas."""
    point = [snapped["lat"], snapped["lon"]]
    k = snapped["segment"]
    return [point] + coords[k + 1:] if toward_end else [point] + coords[:k + 1][::-1]


def plan(origin: tuple[float, float], destination: Optional[tuple[float, float]], level_regua: float) -> dict:
    """Rota a pé da origem ao destino ou, sem destino, até o ponto seco com folga mais próximo."""
    level_regua = _level_key(level_regua)
    net, d = network(), depths(level_regua)
    o = snap(*origin)
    t = snap(*destination) if destination else None
    for name, s in (("origin", o), ("destination", t)):
        if s and s["distance_m"] > SNAP_LIMIT_M:
            return {"status": "no_route", "reason": "point_too_far_from_network", "which": name, "max_snap_distance_m": SNAP_LIMIT_M}
    n = len(net["nodes"])
    ORIGIN, DEST = n, n + 1
    extra: dict[int, list] = {}
    node_depth = list(d["node"]) + [None, None]

    def attach(virtual: int, s: dict):
        i = s["edge"]
        e = net["edges"][i]
        depth = None if math.isnan(d["edge"][i]) else float(d["edge"][i])
        node_depth[virtual] = depth
        first, last = max(.1, s["along_m"]), max(.1, e["length_m"] - s["along_m"])
        # Ligações do ponto virtual às pontas do trecho (respeitando mão única a pé).
        extra.setdefault(virtual, []).append((e["v"], last, depth, ("cut", virtual, True)))
        extra.setdefault(e["u"], []).append((virtual, first, depth, ("cut", virtual, False, "in")))
        if not e["oneway"]:
            extra[virtual].append((e["u"], first, depth, ("cut", virtual, False)))
            extra.setdefault(e["v"], []).append((virtual, last, depth, ("cut", virtual, True, "in")))

    attach(ORIGIN, o)
    if t:
        attach(DEST, t)
        if o["edge"] == t["edge"]:
            e = net["edges"][o["edge"]]
            if not e["oneway"] or o["along_m"] <= t["along_m"]:
                extra[ORIGIN].append((DEST, max(.1, abs(t["along_m"] - o["along_m"])), node_depth[ORIGIN], ("same",)))
    if node_depth[ORIGIN] is None:
        return {"status": "no_route", "reason": "unknown_depth_at_point"}
    if t and node_depth[DEST] is None:
        return {"status": "no_route", "reason": "unknown_depth_at_point"}
    if t and node_depth[DEST] > 0:
        return {"status": "no_route", "reason": "destination_flooded"}

    if t:
        goals = {DEST}
    else:
        goals = d["safe"]
        edge = net["edges"][o["edge"]]
        level = d["level"]
        spill_here = min(net["node_spill"][edge["u"]], net["node_spill"][edge["v"]])
        if node_depth[ORIGIN] == 0 and (spill_here >= level + SAFE_MARGIN_M):
            return {"status": "already_safe", "snapped": {"origin": o}, "margin_m": _margin(spill_here, level)}

    adjacency = d["adjacency"]
    neighbors = lambda node: (adjacency[node] if node < n else []) + extra.get(node, [])
    result = best_exit(node_depth, neighbors, ORIGIN, goals)
    if result["status"] != "ok":
        return result
    result["coordinates"] = _geometry(result, net, o, t)
    end = result["node_ids"][-1]
    result.pop("edge_refs")
    result.pop("node_ids")
    result["walk_min"] = math.ceil(result["length_m"] / WALK_M_PER_MIN)
    result["snapped"] = {"origin": o, "destination": t}
    if not t:
        lat, lon = net["nodes"][end]
        result["safe_point"] = {"lat": float(lat), "lon": float(lon), "street": _street_at(end, net),
                                "margin_m": _margin(float(net["node_spill"][end]), d["level"])}
    else:
        dry = plan_dry(o, t, net)
        if dry:
            result["normal_route"] = dry
    return result


def _margin(spill: float, level: float) -> Optional[float]:
    spill = float(spill)
    return None if spill >= 99 or math.isnan(spill) else round(spill - float(level), 1)


def _street_at(node: int, net: dict) -> str:
    names = [e["name"] for e in net["edges"] if (e["u"] == node or e["v"] == node) and e["name"]]
    return names[0] if names else ""


def _geometry(result: dict, net: dict, o: dict, t: Optional[dict]) -> list:
    points: list = []
    for ref in result["edge_refs"]:
        if ref[0] == "same":
            piece = [[o["lat"], o["lon"]], [t["lat"], t["lon"]]]
        elif ref[0] == "cut":
            virtual, toward_end = ref[1], ref[2]
            s = o if virtual == len(net["nodes"]) else t
            coords = net["edges"][s["edge"]]["coords"]
            piece = _cut(coords, s, toward_end)
            if len(ref) > 3:  # chegando ao ponto virtual: percorre ao contrário
                piece = piece[::-1]
        else:
            index, forward = ref
            coords = net["edges"][index]["coords"]
            piece = coords if forward else coords[::-1]
        points.extend(piece if not points else piece[1:])
    return [[round(a, 6), round(b, 6)] for a, b in points]


def plan_dry(o: dict, t: dict, net: dict) -> Optional[dict]:
    """Mesma origem e destino sem alagamento, para comparar o desvio."""
    n = len(net["nodes"])
    zero = depths(0.0)
    extra: dict[int, list] = {}
    for virtual, s in ((n, o), (n + 1, t)):
        e = net["edges"][s["edge"]]
        first, last = max(.1, s["along_m"]), max(.1, e["length_m"] - s["along_m"])
        extra.setdefault(virtual, []).append((e["v"], last, 0.0, ("cut", virtual, True)))
        extra.setdefault(e["u"], []).append((virtual, first, 0.0, ("cut", virtual, False, "in")))
        if not e["oneway"]:
            extra[virtual].append((e["u"], first, 0.0, ("cut", virtual, False)))
            extra.setdefault(e["v"], []).append((virtual, last, 0.0, ("cut", virtual, True, "in")))
    if o["edge"] == t["edge"]:
        extra[n].append((n + 1, max(.1, abs(t["along_m"] - o["along_m"])), 0.0, ("same",)))
    depth0 = [0.0] * (n + 2)
    adjacency = zero["adjacency"]
    neighbors = lambda node: [(a, b, 0.0 if c is not None else None, r) for a, b, c, r in (adjacency[node] if node < n else [])] + extra.get(node, [])
    result = best_exit(depth0, neighbors, n, {n + 1})
    if result["status"] != "ok":
        return None
    return {"length_m": result["length_m"], "coordinates": _geometry(result, net, o, t)}

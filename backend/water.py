"""Modelo de água por nível do Guaíba e previsão estatística, usados pela Tela 2.

Níveis "régua" seguem a régua do Cais Mauá (recorde 5,35 m, mesma escala da Tela 1).
Níveis "msl" seguem o referencial corrigido da estação ANA 87450020 (nível médio do mar).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "dados" / "processados" / "modelo_agua_poa.npz"
VALIDATION = ROOT / "dados" / "processados" / "modelo_agua_validacao.json"
FORECAST_MODEL = ROOT / "dados" / "processados" / "modelo_previsao.json"
REGUA_OFFSET = 1.18
_TO_UTM = Transformer.from_crs(4326, 32722, always_xy=True)
_TO_GEO = Transformer.from_crs(32722, 4326, always_xy=True)


def regua_to_msl(level: float) -> float:
    return level - REGUA_OFFSET


def msl_to_regua(level: float) -> float:
    return level + REGUA_OFFSET


@lru_cache(maxsize=1)
def model() -> dict:
    data = np.load(MODEL)
    cell, x_min, y_max = data["transform"]
    return {"ground": data["ground_cm"].astype(np.float32) / 100,
            "spill": data["spill_cm"].astype(np.float32) / 100,
            "poa": data["poa"], "cell": float(cell), "x_min": float(x_min), "y_max": float(y_max)}


@lru_cache(maxsize=1)
def validation() -> dict:
    return json.loads(VALIDATION.read_text(encoding="utf-8"))


def cell_of(lat: float, lon: float) -> tuple[int, int] | None:
    m = model()
    x, y = _TO_UTM.transform(lon, lat)
    col = int((x - m["x_min"]) // m["cell"])
    row = int((m["y_max"] - y) // m["cell"])
    rows, cols = m["ground"].shape
    return (row, col) if 0 <= row < rows and 0 <= col < cols else None


def depth_at(ground: float, spill: float, level_msl: float) -> float:
    return round(level_msl - ground, 2) if spill < level_msl else 0.0


def point_window(lat: float, lon: float, half_cells: int = 30) -> dict | None:
    """Recorte do modelo em volta do ponto (60 x 60 células de 20 m = 1,2 km)."""
    m = model()
    center = cell_of(lat, lon)
    if center is None:
        return None
    rows, cols = m["ground"].shape
    r0 = max(0, min(rows - 2 * half_cells, center[0] - half_cells))
    c0 = max(0, min(cols - 2 * half_cells, center[1] - half_cells))
    ground = m["ground"][r0:r0 + 2 * half_cells, c0:c0 + 2 * half_cells]
    spill = m["spill"][r0:r0 + 2 * half_cells, c0:c0 + 2 * half_cells]
    x0 = m["x_min"] + c0 * m["cell"]
    y0 = m["y_max"] - r0 * m["cell"]
    x1, y1 = x0 + 2 * half_cells * m["cell"], y0 - 2 * half_cells * m["cell"]
    (west, east), (north, south) = _TO_GEO.transform([x0, x1], [y0, y1])
    r, c = center
    return {
        "cell_m": m["cell"],
        "bbox": [round(min(west, east), 6), round(min(north, south), 6), round(max(west, east), 6), round(max(north, south), 6)],
        "point": {"lat": lat, "lon": lon, "row": r - r0, "col": c - c0,
                  "ground_msl_m": round(float(m["ground"][r, c]), 2),
                  "spill_msl_m": round(float(m["spill"][r, c]), 2) if m["spill"][r, c] < 99 else None,
                  "inside_poa": bool(m["poa"][r, c])},
        "ground_msl_m": np.round(ground, 2).tolist(),
        "spill_msl_m": np.where(spill < 99, np.round(spill, 2), None).tolist(),
    }


_EDGE_SAMPLES: dict[int, list] = {}


def edge_samples(network: dict) -> list[list[tuple[float, float]] | None]:
    """Amostras (chão, cota de entrada da água) a cada ~10 m ao longo de cada trecho."""
    if id(network) in _EDGE_SAMPLES:
        return _EDGE_SAMPLES[id(network)]
    m = model()
    nodes = {node["id"]: node for node in network["nodes"]}
    samples = []
    for edge in network["edges"]:
        if edge["depth_m"] is None:  # pontes e trechos sem cota conhecida continuam desconhecidos
            samples.append(None)
            continue
        a, b = nodes[edge["source"]], nodes[edge["target"]]
        n = max(1, math.ceil(edge["length_m"] / 10))
        points = []
        for i in range(n + 1):
            cell = cell_of(a["lat"] + (b["lat"] - a["lat"]) * i / n, a["lon"] + (b["lon"] - a["lon"]) * i / n)
            if cell is None:
                points = None
                break
            points.append((float(m["ground"][cell]), float(m["spill"][cell])))
        samples.append(points)
    _EDGE_SAMPLES[id(network)] = samples
    return samples


def network_at_level(network: dict, level_regua: float) -> dict:
    """Copia a rede trocando a profundidade de 06/05/2024 pela do modelo no nível escolhido."""
    level_msl = regua_to_msl(level_regua)
    samples = edge_samples(network)
    m = model()
    edges = []
    for edge, points in zip(network["edges"], samples):
        depth = None if points is None else max(depth_at(g, s, level_msl) for g, s in points)
        edges.append({**edge, "depth_m": depth})
    nodes = []
    for node in network["nodes"]:
        cell = cell_of(node["lat"], node["lon"])
        depth = None if cell is None else depth_at(float(m["ground"][cell]), float(m["spill"][cell]), level_msl)
        nodes.append({**node, "depth_m": depth})
    return {**network, "nodes": nodes, "edges": edges}


@lru_cache(maxsize=1)
def forecast_model() -> dict:
    return json.loads(FORECAST_MODEL.read_text(encoding="utf-8"))


def forecast(hourly: list[tuple[datetime, float]]) -> dict:
    """Aplica o modelo estatístico à série horária recente (referencial msl)."""
    spec = forecast_model()
    if len(hourly) < 24 * 20:
        return {"status": "unavailable", "reason": "insufficient_recent_data"}
    by_time = dict(hourly)
    last_time, last_level = hourly[-1]

    def level_before(hours: int) -> float | None:
        target = last_time - timedelta(hours=hours)
        for offset in range(0, 3):
            for candidate in (target - timedelta(hours=offset), target + timedelta(hours=offset)):
                if candidate in by_time:
                    return by_time[candidate]
        return None

    window = [v for t, v in hourly if t > last_time - timedelta(days=30)]
    values = {"d6": level_before(6), "d24": level_before(24), "d72": level_before(72)}
    if any(v is None for v in values.values()):
        return {"status": "unavailable", "reason": "gaps_in_recent_data"}
    x = {k: last_level - v for k, v in values.items()}
    x["anom30"] = last_level - sum(window) / len(window)
    points = []
    for h in spec["horizons"]:
        coef = h["coef"]
        delta = coef[0] + sum(coef[i + 1] * x[f] for i, f in enumerate(spec["features"]))
        level = last_level + delta
        points.append({"time": (last_time + timedelta(hours=h["hours"])).isoformat(timespec="minutes"),
                       "hours": h["hours"],
                       "msl_m": round(level, 2), "low_msl_m": round(level + h["p10_error_m"], 2),
                       "high_msl_m": round(level + h["p90_error_m"], 2),
                       "regua_m": round(msl_to_regua(level), 2),
                       "low_regua_m": round(msl_to_regua(level + h["p10_error_m"]), 2),
                       "high_regua_m": round(msl_to_regua(level + h["p90_error_m"]), 2),
                       "mae_m": h["mae_model_m"], "mae_persistence_m": h["mae_persistence_m"]})
    return {"status": "ok", "issued_from": last_time.isoformat(timespec="minutes"), "points": points,
            "method": "Regressão linear por horizonte sobre a tendência recente do nível (ANA 87450020).",
            "training": spec["training"], "note": spec["note"], "generated_at_utc": spec["generated_at_utc"]}

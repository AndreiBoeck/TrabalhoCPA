"""API e servidor local da primeira tela do projeto."""

from __future__ import annotations

import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import requests

from backend.routing import RouteRequest, calculate_route

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados" / "processados" / "inct_simai_limpo.json"
FRONTEND = ROOT / "frontend"
ROUTING_DATA = ROOT / "dados" / "processados" / "rotas_centro_2024_05_06.json"
BAIRROS_DATA = ROOT / "dados" / "processados" / "bairros_poa.geojson"
TERRAIN_DATA = ROOT / "dados" / "processados" / "relevo_3d_2024_05_06.json"
ANA_DATA = ROOT / "dados" / "processados" / "ana_guaiba_2024_limpo.csv"
ANA_METADATA = ROOT / "dados" / "originais" / "ana_metadados_coleta.csv"

app = FastAPI(title="TrabalhoCPA — INCT SiMAI", version="0.1.0")
app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@lru_cache(maxsize=1)
def dataset() -> dict[str, dict[str, dict]]:
    if not DATA.exists():
        raise RuntimeError("JSON limpo não encontrado. Execute python -c 'from scripts.preparar_dados import clean_inct; clean_inct()'.")
    by_level: dict[str, dict[str, dict]] = {}
    for row in json.loads(DATA.read_text(encoding="utf-8")):
        level = f"{Decimal(str(row['nivel_m'])):.1f}"
        bairro = row["bairro"]
        by_level.setdefault(level, {})[bairro] = {
            "bairro": bairro,
            "total_buildings": int(row["total_buildings"]),
            "affected_buildings": int(row["affected_buildings"]),
            "percentage": int(row["percentage"]),
            "percentage_exact": float(row["percentage_exact"]),
            "population": int(row["population"]),
            "affected_population": int(row["affected_population"]),
        }
    if len(by_level) != 71 or any(len(rows) != 94 for rows in by_level.values()):
        raise RuntimeError("A grade INCT não contém 71 níveis × 94 bairros.")
    return by_level


def parse_level(value: str) -> str:
    try:
        number = Decimal(value.replace(",", "."))
    except InvalidOperation as error:
        raise HTTPException(422, "Nível inválido") from error
    if not number.is_finite():
        raise HTTPException(422, "Nível inválido")
    if not (Decimal("3.0") <= number <= Decimal("10.0")) or number * 10 != (number * 10).to_integral_value():
        raise HTTPException(422, "Use um nível entre 3,0 e 10,0 m em passos de 0,1 m")
    return f"{number:.1f}"


def aggregate(rows: list[dict]) -> dict:
    buildings = sum(row["total_buildings"] for row in rows)
    affected_buildings = sum(row["affected_buildings"] for row in rows)
    return {
        "total_buildings": buildings,
        "affected_buildings": affected_buildings,
        "percentage": rows[0]["percentage"] if len(rows) == 1 else (round(100 * affected_buildings / buildings, 1) if buildings else 0),
        "population": sum(row["population"] for row in rows),
        "affected_population": sum(row["affected_population"] for row in rows),
        "bairros_atingidos": sum(row["affected_buildings"] > 0 for row in rows),
    }


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/tela2")
def screen_two():
    return FileResponse(FRONTEND / "tela2.html")


@app.get("/mockup")
def mockup():
    return FileResponse(FRONTEND / "mockup.html")


@app.get("/api/metadata")
def metadata():
    data = dataset()
    return {
        "levels": sorted(map(float, data)),
        "bairros": sorted(next(iter(data.values()))),
        "source": "INCT SiMAI — JSON fornecido no projeto, após limpeza documentada",
        "notice": "Simulação de exposição: valores estimados, não previsão nem contagem oficial de pessoas atingidas.",
    }


@app.get("/api/scenario")
def scenario(level: str = Query(default="5.3"), bairro: Optional[str] = None):
    key = parse_level(level)
    rows_by_name = dataset()[key]
    if bairro and bairro not in rows_by_name:
        raise HTTPException(404, "Bairro não encontrado")
    all_rows = list(rows_by_name.values())
    selected_rows = [rows_by_name[bairro]] if bairro else all_rows
    ranking = sorted(all_rows, key=lambda row: (-row["affected_population"], row["bairro"]))[:10]
    return {
        "level": float(key),
        "selected_bairro": bairro,
        "totals": aggregate(selected_rows),
        "city_totals": aggregate(all_rows),
        "neighborhoods": all_rows,
        "ranking": ranking,
    }


@app.get("/api/curve")
def curve():
    return [
        {"level": float(level), **aggregate(list(dataset()[level].values()))}
        for level in sorted(dataset(), key=float)
    ]


@app.get("/api/bairros/geometry")
def bairros_geometry():
    if not BAIRROS_DATA.exists():
        raise HTTPException(503, "Limites dos bairros não preparados")
    return FileResponse(BAIRROS_DATA, media_type="application/geo+json")


@app.get("/api/terrain/historical")
def historical_terrain():
    if not TERRAIN_DATA.exists():
        raise HTTPException(503, "Relevo histórico não preparado")
    return FileResponse(TERRAIN_DATA, media_type="application/json")


@lru_cache(maxsize=1)
def ana_history() -> dict:
    if not ANA_DATA.exists() or not ANA_METADATA.exists():
        raise HTTPException(503, "Série ANA preparada não encontrada")
    with ANA_METADATA.open(encoding="utf-8", newline="") as file:
        source = next(csv.DictReader(file))
    observations = []
    daily = {}
    with ANA_DATA.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            date = row["data_hora"][:10]
            level = float(row["nivel_m"]) if row["nivel_m"] else None
            observations.append([row["data_hora"].replace(" ", "T"), level])
            day = daily.setdefault(date, {"date": date, "min": None, "max": None,
                                          "available": 0, "expected": 0})
            day["expected"] += 1
            if level is not None:
                day["available"] += 1
                day["min"] = min(level, day["min"]) if day["min"] is not None else level
                day["max"] = max(level, day["max"]) if day["max"] is not None else level
    return {
        "observations": observations,
        "daily": list(daily.values()),
        "metadata": {
            "station_code": source["estacao_codigo"],
            "station_name": source["estacao_nome"],
            "vertical_reference": "Marco IBGE 1788A; nível médio do mar",
            "unit": "m",
            "collected_at": source["coletado_ou_cache_em"],
            "source_url": source["url"],
            "first_date": observations[0][0][:10],
            "last_date": observations[-1][0][:10],
            "time_note": "Horários como fornecidos pelo XML da ANA; fuso não explícito na origem.",
        },
    }


@app.get("/api/ana/history")
def ana_history_public():
    return ana_history()


@lru_cache(maxsize=2)
def _fetch_ana_latest(time_bucket: int) -> dict:
    now = datetime.now().astimezone()
    source = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
    base = {"station_code": "87450020", "station_name": "Usina do Gasômetro",
            "vertical_reference": "Marco IBGE 1788A; nível médio do mar",
            "source_url": source, "queried_at": now.isoformat(timespec="seconds"),
            "time_note": "Horário da medição informado pela ANA sem fuso explícito; avaliação de recência usa o horário local do servidor."}
    try:
        response = requests.get(source, params={
            "codEstacao": "87450020",
            "dataInicio": (now.date() - timedelta(days=3)).strftime("%d/%m/%Y"),
            "dataFim": now.date().strftime("%d/%m/%Y"),
        }, headers={"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica)"}, timeout=15)
        response.raise_for_status()
        readings = []
        for item in ET.fromstring(response.content).iter():
            if item.tag.split("}")[-1] != "DadosHidrometereologicos":
                continue
            row = {child.tag.split("}")[-1]: child.text for child in item}
            if row.get("CodEstacao") != "87450020" or not row.get("Nivel") or not row.get("DataHora"):
                continue
            try:
                measured = datetime.fromisoformat(row["DataHora"].strip())
                level = float(row["Nivel"]) / 100
            except (ValueError, TypeError):
                continue
            if measured and 0 <= level < 20:
                readings.append((measured, level))
        if not readings:
            return {**base, "status": "unavailable", "reason": "no_measurement"}
        measured, level = max(readings, key=lambda item: item[0])
        age_minutes = (now.replace(tzinfo=None) - measured).total_seconds() / 60
        return {**base, "status": "recent" if 0 <= age_minutes <= 120 else "stale",
                "measurement_at": measured.isoformat(timespec="seconds"),
                "level_m": level, "age_minutes": round(age_minutes, 1)}
    except (requests.RequestException, ET.ParseError):
        return {**base, "status": "unavailable", "reason": "source_unavailable"}


@app.get("/api/ana/latest")
def ana_latest():
    return _fetch_ana_latest(int(datetime.now().timestamp() // 300))


@app.post("/api/routing/calculate")
def routing_calculate(request: RouteRequest):
    """Protótipo do motor de rotas; requer rede e profundidades por trecho."""
    try:
        return calculate_route(request)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@lru_cache(maxsize=1)
def routing_network() -> dict:
    if not ROUTING_DATA.exists():
        raise HTTPException(503, "Rede de rotas não preparada")
    return json.loads(ROUTING_DATA.read_text(encoding="utf-8"))


class MapPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class MapRouteRequest(BaseModel):
    origin: MapPoint
    destination: MapPoint


def nearest_edge(point: MapPoint, network: dict) -> dict:
    """Projeta um clique sobre o trecho de rua mais próximo no recorte local."""
    nodes = {node["id"]: node for node in network["nodes"]}
    px, py = point.lon * 96_400, point.lat * 111_200
    best = None
    for index, edge in enumerate(network["edges"]):
        a, b = nodes[edge["source"]], nodes[edge["target"]]
        ax, ay = a["lon"] * 96_400, a["lat"] * 111_200
        bx, by = b["lon"] * 96_400, b["lat"] * 111_200
        dx, dy = bx - ax, by - ay
        fraction = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        qx, qy = ax + fraction * dx, ay + fraction * dy
        distance = ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
        if best is None or distance < best["distance_m"]:
            best = {"edge_index": index, "fraction": fraction, "distance_m": distance,
                    "lat": a["lat"] + fraction * (b["lat"] - a["lat"]),
                    "lon": a["lon"] + fraction * (b["lon"] - a["lon"]),
                    "depth_m": edge["depth_m"]}
    best["distance_m"] = round(best["distance_m"], 1)
    return best


def attach_point(name: str, snapped: dict, network: dict, nodes: list, edges: list):
    edge = network["edges"][snapped["edge_index"]]
    nodes.append({"id": name, "depth_m": snapped["depth_m"]})
    fraction = snapped["fraction"]
    # Trechos de comprimento zero surgem quando o clique coincide com um nó.
    # Uma ligação pequena preserva o nó virtual sem alterar a escolha da rota.
    first = max(0.001, edge["length_m"] * fraction)
    last = max(0.001, edge["length_m"] * (1 - fraction))
    edges.extend([
        {"source": edge["source"], "target": name, "length_m": first,
         "depth_m": edge["depth_m"], "bidirectional": edge["bidirectional"]},
        {"source": name, "target": edge["target"], "length_m": last,
         "depth_m": edge["depth_m"], "bidirectional": edge["bidirectional"]},
    ])


@app.get("/api/routing/network")
def routing_network_public():
    return routing_network()


@app.post("/api/routing/plan")
def routing_plan(request: MapRouteRequest):
    network = routing_network()
    origin = nearest_edge(request.origin, network)
    destination = nearest_edge(request.destination, network)
    if max(origin["distance_m"], destination["distance_m"]) > 25:
        return {"status": "no_route", "reason": "point_too_far_from_network",
                "max_snap_distance_m": 25, "metadata": network["metadata"]}
    if origin["depth_m"] is None or destination["depth_m"] is None:
        return {"status": "no_route", "reason": "unknown_depth_at_point",
                "metadata": network["metadata"]}
    nodes = list(network["nodes"])
    edges = list(network["edges"])
    attach_point("__origin__", origin, network, nodes, edges)
    attach_point("__destination__", destination, network, nodes, edges)
    if origin["edge_index"] == destination["edge_index"]:
        edge = network["edges"][origin["edge_index"]]
        if edge["bidirectional"] or origin["fraction"] <= destination["fraction"]:
            edges.append({"source": "__origin__", "target": "__destination__",
                          "length_m": max(.001, edge["length_m"] * abs(destination["fraction"] - origin["fraction"])),
                          "depth_m": edge["depth_m"], "bidirectional": edge["bidirectional"]})
    graph = RouteRequest(nodes=nodes, edges=edges, origin="__origin__", destination="__destination__")
    result = calculate_route(graph)
    nodes_by_id = {node["id"]: node for node in network["nodes"]}
    nodes_by_id["__origin__"] = origin
    nodes_by_id["__destination__"] = destination
    if result["status"] == "ok":
        result["coordinates"] = [[nodes_by_id[node_id]["lat"], nodes_by_id[node_id]["lon"]]
                                 for node_id in result["node_ids"]]
        normal_graph = RouteRequest(
            nodes=[{"id": node.id, "depth_m": 0} for node in graph.nodes],
            edges=[{"source": edge.source, "target": edge.target,
                    "length_m": edge.length_m, "depth_m": 0 if edge.depth_m is not None else None,
                    "bidirectional": edge.bidirectional} for edge in graph.edges],
            origin=graph.origin, destination=graph.destination,
        )
        normal = calculate_route(normal_graph)
        if normal["status"] == "ok":
            result["normal_route"] = {
                "length_m": normal["length_m"],
                "coordinates": [[nodes_by_id[node_id]["lat"], nodes_by_id[node_id]["lon"]]
                                for node_id in normal["node_ids"]],
            }
    result["snapped"] = {"origin": origin, "destination": destination}
    result["metadata"] = network["metadata"]
    return result

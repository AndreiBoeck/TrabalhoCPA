"""API e servidor local das duas telas do projeto."""

from __future__ import annotations

import json
import time
import csv
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import requests

from backend.routing import RouteRequest, calculate_route
from backend import rotas, water

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados" / "processados" / "inct_simai_limpo.json"
FRONTEND = ROOT / "frontend"
BAIRROS_DATA = ROOT / "dados" / "processados" / "bairros_poa.geojson"
ANA_DATA = ROOT / "dados" / "processados" / "ana_guaiba_2024_limpo.csv"
ANA_METADATA = ROOT / "dados" / "originais" / "ana_metadados_coleta.csv"

app = FastAPI(title="TrabalhoCPA — INCT SiMAI", version="0.1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)
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


ANA_SOURCE = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"


BRT = timezone(timedelta(hours=-3))  # horário de Brasília (sem horário de verão desde 2019); a ANA informa nesse horário
_ANA_DAYS: dict = {}  # dia -> leituras; dias encerrados não mudam e ficam guardados


def _ana_day(day) -> list[tuple[datetime, float]]:
    """Leituras de um único dia. A ANA passou a falhar (erro 500 após 30 s) em consultas de vários dias."""
    response = requests.get(ANA_SOURCE, params={
        "codEstacao": "87450020", "dataInicio": day.strftime("%d/%m/%Y"), "dataFim": day.strftime("%d/%m/%Y"),
    }, headers={"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica)"}, timeout=25)
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
        if -1 < level < 20:
            readings.append((measured, level))
    return readings


def _ana_readings(start, end) -> list[tuple[datetime, float]]:
    """Junta as leituras dia a dia, em paralelo. Hoje e ontem são sempre consultados de novo; dias
    anteriores vêm do cache. Falha em um dia não derruba os outros; sem nenhum dia, propaga o erro."""
    today = datetime.now(BRT).date()
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    pending = [d for d in days if d not in _ANA_DAYS or d >= today - timedelta(days=1)]
    errors = []
    for attempt in range(3):  # a ANA recusa parte das consultas simultâneas; tenta de novo os dias que falharam
        failed = []
        with ThreadPoolExecutor(max_workers=4 if attempt == 0 else 1) as pool:
            for day, future in [(d, pool.submit(_ana_day, d)) for d in pending]:
                try:
                    _ANA_DAYS[day] = future.result()
                except (requests.RequestException, ET.ParseError) as error:
                    failed.append(day)
                    errors.append(error)
        if not failed:
            break
        pending = failed
        time.sleep(1)
    if errors and not any(d in _ANA_DAYS for d in days):
        raise errors[0]
    return sorted(r for d in days for r in _ANA_DAYS.get(d, []))


def _hourly(readings: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    buckets: dict[datetime, list[float]] = {}
    for measured, level in readings:
        buckets.setdefault(measured.replace(minute=0, second=0), []).append(level)
    return [(hour, sum(v) / len(v)) for hour, v in sorted(buckets.items())]


@lru_cache(maxsize=2)
def _fetch_live(time_bucket: int) -> dict:
    now = datetime.now(BRT)
    base = {"station_code": "87450020", "station_name": "Usina do Gasômetro",
            "vertical_reference": "Marco IBGE 1788A; nível médio do mar",
            "regua_offset_m": water.REGUA_OFFSET,
            "source_url": ANA_SOURCE, "queried_at": now.isoformat(timespec="seconds"),
            "time_note": "Horário da medição informado pela ANA sem fuso explícito, tratado como horário de Brasília (UTC−3)."}
    try:
        readings = _ana_readings(now.date() - timedelta(days=32), now.date())
    except (requests.RequestException, ET.ParseError):
        if _LAST_LIVE:  # ANA fora do ar: mantém a última resposta boa, marcada pela idade da medição
            return {**_LAST_LIVE[0], "queried_at": base["queried_at"], "status": "stale", "source_error": True}
        return {**base, "status": "unavailable", "reason": "source_unavailable", "recent": [],
                "forecast": {"status": "unavailable", "reason": "source_unavailable"}}
    if not readings:
        return {**base, "status": "unavailable", "reason": "no_measurement", "recent": [],
                "forecast": {"status": "unavailable", "reason": "no_measurement"}}
    measured, level = readings[-1]
    age_minutes = (now.replace(tzinfo=None) - measured).total_seconds() / 60
    hourly = _hourly(readings)
    week_start = hourly[-1][0] - timedelta(days=7)
    result = {**base, "status": "recent" if 0 <= age_minutes <= 120 else "stale",
            "measurement_at": measured.isoformat(timespec="seconds"),
            "level_m": level, "level_regua_m": round(water.msl_to_regua(level), 2),
            "age_minutes": round(age_minutes, 1),
            "recent": [[t.isoformat(timespec="minutes"), round(v, 3)] for t, v in hourly if t >= week_start],
            "forecast": water.forecast(hourly)}
    _LAST_LIVE[:] = [result]
    return result


_LAST_LIVE: list = []


@app.on_event("startup")
def _warm_live():
    """Busca a série da ANA em segundo plano ao subir o servidor, para a primeira visita não esperar."""
    import threading
    threading.Thread(target=live, daemon=True).start()


@app.get("/api/live")
def live():
    """Leitura atual, últimos 7 dias (horário) e previsão de 72 h."""
    return _fetch_live(int(datetime.now().timestamp() // 300))


@app.get("/api/ana/latest")
def ana_latest():
    data = live()
    return {k: v for k, v in data.items() if k not in {"recent", "forecast"}}


@app.get("/api/forecast/model")
def forecast_model():
    return water.forecast_model()


@app.get("/api/water/point")
def water_point(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
                half_cells: int = Query(default=30, ge=10, le=60)):
    """Chão e cota de entrada da água em volta do ponto (2 × half_cells células de 20 m de lado)."""
    window = water.point_window(lat, lon, half_cells)
    if window is None:
        raise HTTPException(422, "Ponto fora da área do modelo (Porto Alegre)")
    return {**window, "regua_offset_m": water.REGUA_OFFSET, "validation": water.validation()}


@app.get("/api/water/validation")
def water_validation():
    return water.validation()


@app.post("/api/routing/calculate")
def routing_calculate(request: RouteRequest):
    """Protótipo do motor de rotas; requer rede e profundidades por trecho."""
    try:
        return calculate_route(request)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


class MapPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class MapRouteRequest(BaseModel):
    origin: MapPoint
    destination: Optional[MapPoint] = None  # sem destino: saída até o ponto seco mais próximo
    level_regua_m: float = Field(ge=0, le=12)


@app.get("/api/routing/streets")
def routing_streets(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600"
    return rotas.streets()


@app.get("/api/routing/depths")
def routing_depths(level: float = Query(ge=0, le=12)):
    return rotas.depths_public(level)


@app.get("/api/water/overlay.png")
def water_overlay(level: float = Query(ge=0, le=12)):
    bbox = tuple(rotas.network()["raw"]["metadata"]["bbox"])
    png = water.overlay_png(bbox, round(level, 2))
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/routing/plan")
def routing_plan(request: MapRouteRequest):
    destination = (request.destination.lat, request.destination.lon) if request.destination else None
    result = rotas.plan((request.origin.lat, request.origin.lon), destination, request.level_regua_m)
    for key in ("length_m", "flooded_length_m"):
        if key in result:
            result[key] = round(result[key])
    if "max_depth_m" in result:
        result["max_depth_m"] = round(result["max_depth_m"], 2)
    return result

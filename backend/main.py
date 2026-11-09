"""API e servidor local da primeira tela do projeto."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados" / "processados" / "inct_simai_limpo.json"
FRONTEND = ROOT / "frontend"

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

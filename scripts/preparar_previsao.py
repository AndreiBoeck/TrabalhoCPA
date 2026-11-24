"""Treina e valida o modelo estatístico de previsão do nível do Guaíba (estação ANA 87450020).

Modelo: para cada horizonte h (6 a 72 h), uma regressão linear prevê a variação
``nível(t + h) - nível(t)`` a partir de:

* variação nas últimas 6, 24 e 72 horas (tendência recente);
* diferença entre o nível atual e a média dos últimos 30 dias (volta à média).

A incerteza é a faixa entre os percentis 10 e 90 dos erros no período de teste.
Validação: treino até 12 meses antes da última leitura; teste nos últimos 12 meses,
comparado com a persistência (repetir o último nível).

A série é baixada mês a mês do WebService da ANA e guardada em dados/cache/.

Uso: python3 -m scripts.preparar_previsao
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "dados" / "cache" / "ana_mensal"
OUTPUT = ROOT / "dados" / "processados" / "modelo_previsao.json"
SOURCE = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
STATION = "87450020"
START = date(2023, 1, 1)
HORIZONS = list(range(6, 73, 6))
FEATURES = ["d6", "d24", "d72", "anom30"]
HEADERS = {"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica)"}


def parse(content: bytes) -> list[tuple[str, float]]:
    rows = []
    for item in ET.fromstring(content).iter():
        if item.tag.split("}")[-1] != "DadosHidrometereologicos":
            continue
        row = {child.tag.split("}")[-1]: child.text for child in item}
        if row.get("Nivel") and row.get("DataHora"):
            try:
                rows.append((row["DataHora"].strip(), float(row["Nivel"]) / 100))
            except ValueError:
                pass
    return rows


def download() -> pd.Series:
    CACHE.mkdir(parents=True, exist_ok=True)
    today = date.today()
    month = START
    frames = []
    while month <= today:
        nxt = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = min(nxt - timedelta(days=1), today)
        path = CACHE / f"{month:%Y-%m}.csv"
        complete = end < today - timedelta(days=1)
        if not path.exists() or not complete:
            response = requests.get(SOURCE, params={"codEstacao": STATION, "dataInicio": f"{month:%d/%m/%Y}",
                                                    "dataFim": f"{end:%d/%m/%Y}"}, headers=HEADERS, timeout=90)
            response.raise_for_status()
            pd.DataFrame(parse(response.content), columns=["data_hora", "nivel_m"]).to_csv(path, index=False)
        frames.append(pd.read_csv(path))
        month = nxt
    data = pd.concat(frames)
    data["data_hora"] = pd.to_datetime(data.data_hora)
    series = data.drop_duplicates("data_hora").set_index("data_hora").nivel_m.sort_index()
    series = series[(series > -1) & (series < 8)]
    return series.resample("1h").mean().interpolate(limit=3)


def features(hourly: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"y": hourly})
    frame["d6"] = hourly - hourly.shift(6)
    frame["d24"] = hourly - hourly.shift(24)
    frame["d72"] = hourly - hourly.shift(72)
    frame["anom30"] = hourly - hourly.rolling(24 * 30, min_periods=24 * 20).mean()
    for h in HORIZONS:
        frame[f"t{h}"] = hourly.shift(-h) - hourly
    return frame


def fit(train: pd.DataFrame, h: int) -> np.ndarray:
    rows = train.dropna(subset=FEATURES + [f"t{h}"])
    x = np.column_stack([np.ones(len(rows))] + [rows[c].to_numpy() for c in FEATURES])
    coef, *_ = np.linalg.lstsq(x, rows[f"t{h}"].to_numpy(), rcond=None)
    return coef


def predict(coef: np.ndarray, rows: pd.DataFrame) -> np.ndarray:
    return coef[0] + sum(coef[i + 1] * rows[c].to_numpy() for i, c in enumerate(FEATURES))


def main() -> None:
    hourly = download()
    frame = features(hourly)
    split = hourly.index.max() - pd.Timedelta(days=365)
    train, test = frame[frame.index < split], frame[frame.index >= split]
    horizons = []
    for h in HORIZONS:
        coef = fit(train, h)
        rows = test.dropna(subset=FEATURES + [f"t{h}"])
        error = rows[f"t{h}"].to_numpy() - predict(coef, rows)
        persistence = rows[f"t{h}"].to_numpy()
        final = fit(frame, h)  # coeficientes finais usam toda a série
        horizons.append({
            "hours": h,
            "coef": [round(float(v), 6) for v in final],
            "mae_model_m": round(float(np.mean(np.abs(error))), 3),
            "mae_persistence_m": round(float(np.mean(np.abs(persistence))), 3),
            "p10_error_m": round(float(np.percentile(error, 10)), 3),
            "p90_error_m": round(float(np.percentile(error, 90)), 3),
            "test_points": int(len(rows)),
        })
        print(horizons[-1])
    OUTPUT.write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "station_code": STATION, "source_url": SOURCE,
        "vertical_reference": "referencial corrigido da estação (nível médio do mar)",
        "features": FEATURES,
        "feature_description": {"d6": "nível atual - nível 6 h antes", "d24": "nível atual - nível 24 h antes",
                                "d72": "nível atual - nível 72 h antes",
                                "anom30": "nível atual - média dos últimos 30 dias"},
        "training": {"first_hour": str(hourly.index.min()), "last_hour": str(hourly.index.max()),
                     "test_from": str(split), "hourly_points": int(hourly.notna().sum())},
        "horizons": horizons,
        "note": ("Modelo estatístico experimental baseado apenas no histórico do nível. Não usa chuva prevista, "
                 "vento nem vazão dos afluentes; não substitui os boletins oficiais do SGB."),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()

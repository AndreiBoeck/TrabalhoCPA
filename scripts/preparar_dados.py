"""Pipeline reproduzível para os dados do INCT SiMAI e da ANA.

Execute a partir da raiz do repositório: python -m scripts.preparar_dados
As correções do INCT são registradas linha a linha no CSV de auditoria.
"""

from __future__ import annotations

import json
import math
import shutil
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "dados" / "originais"
PROCESSED = ROOT / "dados" / "processados"
SOURCE_INCT = ROOT.parent / "data.json"
ANA_URL = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
ANA_STATIONS = {
    "87450020": ("Usina do Gasômetro, referencial corrigido", "2024-05-03", "2024-06-30"),
}


def load_inct() -> pd.DataFrame:
    ORIGINAL.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    if not (ORIGINAL / "inct_simai_data.json").exists():
        if not SOURCE_INCT.exists():
            raise FileNotFoundError(
                "Coloque data.json ao lado da pasta TrabalhoCPA antes de executar o pipeline."
            )
        shutil.copy2(SOURCE_INCT, ORIGINAL / "inct_simai_data.json")
    with (ORIGINAL / "inct_simai_data.json").open(encoding="utf-8") as f:
        raw = json.load(f)
    records = []
    for level_key, neighborhoods in raw.items():
        level = float(level_key.removesuffix("m").replace("_", "."))
        for neighborhood, values in neighborhoods.items():
            records.append({"nivel_m": level, "bairro": neighborhood, **values})
    df = pd.DataFrame.from_records(records).sort_values(["bairro", "nivel_m"]).reset_index(drop=True)
    required = {
        "nivel_m", "bairro", "affected_buildings", "total_buildings", "percentage",
        "population", "affected_population",
    }
    if set(df.columns) != required:
        raise ValueError(f"Estrutura inesperada: {set(df.columns) ^ required}")
    if len(df) != 71 * 94 or df.duplicated(["nivel_m", "bairro"]).any():
        raise ValueError("Quantidade de linhas ou chaves nível/bairro inesperada")
    expected_levels = {round(3 + i / 10, 1) for i in range(71)}
    if set(df.nivel_m) != expected_levels or df.groupby("nivel_m").bairro.nunique().ne(94).any():
        raise ValueError("Grade de níveis/bairros incompleta")
    numeric = list(required - {"nivel_m", "bairro"})
    if df[numeric].isna().any().any() or (df[numeric] < 0).any().any():
        raise ValueError("Dados numéricos nulos ou negativos")
    for col in ("total_buildings", "population"):
        if df.groupby("bairro")[col].nunique().ne(1).any():
            raise ValueError(f"{col} muda entre níveis")
    if (df.affected_buildings > df.total_buildings).any():
        raise ValueError("Prédios atingidos excedem o total")
    return df


def clean_inct() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = load_inct()
    audit = []
    original = df.set_index(["bairro", "nivel_m"])

    def fix_count(bairro: str, nivel: float, new_value: int, reason: str, method: str) -> None:
        mask = (df.bairro == bairro) & (df.nivel_m == round(nivel, 1))
        old = int(df.loc[mask, "affected_buildings"].iloc[0])
        new_value = int(new_value)
        if old != new_value:
            audit.append({
                "bairro": bairro, "nivel_m": round(nivel, 1), "campo": "affected_buildings",
                "valor_original": old, "valor_corrigido": new_value,
                "problema": reason, "tratamento": method,
            })
            df.loc[mask, "affected_buildings"] = new_value

    # 64/71 registros são 4680. Os sete desvios isolados não formam uma curva crescente.
    arq = df[df.bairro == "Arquipélago"]
    arq_mode = int(arq.affected_buildings.mode().iloc[0])
    for row in arq.itertuples():
        if row.affected_buildings != arq_mode:
            fix_count("Arquipélago", row.nivel_m, arq_mode,
                      "Oscilação isolada em série quase constante; nível maior reduz o total atingido",
                      "Substituir pela moda observada em 64 dos 71 níveis")

    # Os primeiros cinco pontos destoam da continuação (25 em 3,5/3,6 m).
    for level in (3.0, 3.1, 3.2, 3.3, 3.4):
        fix_count("Espírito Santo", level, 25,
                  "Patamar inicial 633–637 cai abruptamente para 25 em 3,5 m",
                  "Imputação pelo primeiro valor plausível (3,5 m); estimativa incerta")
    fix_count("Espírito Santo", 4.7, 47,
              "Pico isolado de 2101 entre 46 e 47 prédios",
              "Interpolação linear entre 4,6 e 4,8 m, arredondada")

    # Zeros isolados ou consecutivos em séries com valores positivos nos dois lados.
    for bairro, levels in {
        "Centro Histórico": (9.7, 9.8),
        "Lageado": (8.1,),
        "Rubem Berta": (8.8,),
    }.items():
        series = original.loc[bairro, "affected_buildings"].sort_index()
        first, last = levels[0], levels[-1]
        before = round(first - 0.1, 1)
        after = round(last + 0.1, 1)
        left, right = int(series.loc[before]), int(series.loc[after])
        for i, level in enumerate(levels, 1):
            estimate = math.floor(left + (right - left) * i / (len(levels) + 1) + 0.5)
            fix_count(bairro, level, estimate,
                      "Zero entre níveis com prédios atingidos positivos",
                      f"Interpolação linear entre {before:.1f} e {after:.1f} m")

    # A fonte usa arredondamento para cima nos dois campos derivados; preservamos essa convenção.
    for row in df.itertuples():
        pct_expected = math.ceil(100 * row.affected_buildings / row.total_buildings)
        pop_expected = math.ceil(row.population * pct_expected / 100)
        for field, new_value in (("percentage", pct_expected), ("affected_population", pop_expected)):
            mask = (df.bairro == row.bairro) & (df.nivel_m == row.nivel_m)
            old = int(df.loc[mask, field].iloc[0])
            if old != new_value:
                audit.append({
                    "bairro": row.bairro, "nivel_m": row.nivel_m, "campo": field,
                    "valor_original": old, "valor_corrigido": new_value,
                    "problema": "Campo derivado incompatível com a contagem corrigida",
                    "tratamento": "Recalcular com arredondamento para cima usado pela fonte",
                })
                df.loc[mask, field] = new_value

    df["percentage_exact"] = (100 * df.affected_buildings / df.total_buildings).round(4)
    df["bairro_atingido"] = df.affected_buildings.gt(0)
    df = df.sort_values(["nivel_m", "bairro"]).reset_index(drop=True)
    changes = pd.DataFrame(audit).sort_values(["bairro", "nivel_m", "campo"])
    remaining = df.groupby("bairro").affected_buildings.diff().lt(0)
    if remaining.any():
        raise AssertionError(f"Restaram {remaining.sum()} quedas na contagem corrigida")
    if (df.percentage != (100 * df.affected_buildings / df.total_buildings).apply(math.ceil)).any():
        raise AssertionError("Percentuais inconsistentes")
    df.to_csv(PROCESSED / "inct_simai_limpo.csv", index=False)
    changes.to_csv(PROCESSED / "auditoria_inct.csv", index=False)
    summary = df.groupby("nivel_m", as_index=False).agg(
        pessoas_afetadas=("affected_population", "sum"),
        predios_afetados=("affected_buildings", "sum"),
        bairros_atingidos=("bairro_atingido", "sum"),
    )
    summary.to_csv(PROCESSED / "inct_resumo_por_nivel.csv", index=False)
    return df, changes, summary


def fetch_ana(force: bool = False) -> pd.DataFrame:
    ORIGINAL.mkdir(parents=True, exist_ok=True)
    records = []
    collection_metadata = []
    session = requests.Session()
    session.headers.update({"User-Agent": "TrabalhoCPA/1.0 (pesquisa academica; cache local)"})
    for code, (name, start, end) in ANA_STATIONS.items():
        target = ORIGINAL / f"ana_{code}_{start}_{end}.xml"
        if force or not target.exists():
            response = session.get(ANA_URL, params={
                "codEstacao": code,
                "dataInicio": date.fromisoformat(start).strftime("%d/%m/%Y"),
                "dataFim": date.fromisoformat(end).strftime("%d/%m/%Y"),
            }, timeout=90)
            response.raise_for_status()
            ET.fromstring(response.content)  # Só salva XML válido.
            target.write_bytes(response.content)
        root = ET.fromstring(target.read_bytes())
        station_rows = 0
        for item in root.iter():
            if item.tag.split("}")[-1] != "DadosHidrometereologicos":
                continue
            fields = {child.tag.split("}")[-1]: child.text for child in item}
            if fields.get("CodEstacao") != code:
                raise ValueError(f"Resposta inesperada para estação {code}")
            station_rows += 1
            records.append({
                "estacao_codigo": code,
                "estacao_nome": name,
                "data_hora": fields.get("DataHora", "").strip(),
                "nivel_cm": fields.get("Nivel"),
                "chuva_mm": fields.get("Chuva"),
            })
        collection_metadata.append({
            "estacao_codigo": code, "estacao_nome": name,
            "inicio_solicitado": start, "fim_solicitado": end,
            "linhas_xml": station_rows, "arquivo_bruto": target.name,
            "coletado_ou_cache_em": datetime.fromtimestamp(target.stat().st_mtime).isoformat(timespec="seconds"),
            "url": ANA_URL,
            "licenca": "Consultar termos da ANA; fonte pública oficial, crédito obrigatório",
        })
    pd.DataFrame(collection_metadata).to_csv(ORIGINAL / "ana_metadados_coleta.csv", index=False)
    return pd.DataFrame(records)


def clean_ana(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = fetch_ana(force)
    df["data_hora"] = pd.to_datetime(df.data_hora, errors="coerce")
    df["nivel_cm"] = pd.to_numeric(df.nivel_cm, errors="coerce")
    df["chuva_mm"] = pd.to_numeric(df.chuva_mm, errors="coerce")
    audit = []
    for row in df[df.data_hora.isna()].itertuples():
        audit.append({"estacao_codigo": row.estacao_codigo, "data_hora": "", "problema": "data inválida", "tratamento": "descartar"})
    df = df.dropna(subset=["data_hora"])
    dupes = df.duplicated(["estacao_codigo", "data_hora"], keep="first")
    for row in df[dupes].itertuples():
        audit.append({"estacao_codigo": row.estacao_codigo, "data_hora": str(row.data_hora), "problema": "duplicata", "tratamento": "manter primeira"})
    df = df[~dupes].copy()
    missing = df.nivel_cm.isna()
    for row in df[missing].itertuples():
        audit.append({"estacao_codigo": row.estacao_codigo, "data_hora": str(row.data_hora), "problema": "nível ausente", "tratamento": "manter lacuna; sem interpolação"})
    # Reconstruir a grade temporal revela intervalos ausentes do XML.
    frames = []
    for code, (name, start, end) in ANA_STATIONS.items():
        station = df[df.estacao_codigo.eq(code)].copy()
        expected = pd.DataFrame({"data_hora": pd.date_range(
            f"{start} 00:00", f"{end} 23:45", freq="15min"
        )})
        station = expected.merge(station, on="data_hora", how="left", indicator=True)
        for row in station[station["_merge"].eq("left_only")].itertuples():
            audit.append({"estacao_codigo": code, "data_hora": str(row.data_hora),
                          "problema": "horário sem registro no XML", "tratamento": "inserir lacuna; sem interpolação"})
        station["estacao_codigo"] = code
        station["estacao_nome"] = name
        frames.append(station.drop(columns="_merge"))
    df = pd.concat(frames, ignore_index=True)
    df["nivel_m"] = df.nivel_cm / 100
    df["referencial"] = "Marco IBGE 1788A; nível médio do mar"
    df = df.sort_values(["estacao_codigo", "data_hora"]).reset_index(drop=True)
    df.to_csv(PROCESSED / "ana_guaiba_2024_limpo.csv", index=False)
    pd.DataFrame(audit, columns=["estacao_codigo", "data_hora", "problema", "tratamento"]).to_csv(
        PROCESSED / "auditoria_ana.csv", index=False
    )
    return df, pd.DataFrame(audit)


if __name__ == "__main__":
    inct, corrections, summary = clean_inct()
    ana, ana_audit = clean_ana()
    print(f"INCT: {len(inct)} linhas, {len(corrections)} correções; {len(summary)} níveis")
    print(f"ANA: {len(ana)} horários, {ana.nivel_cm.notna().sum()} níveis válidos; {len(ana_audit)} lacunas auditadas")

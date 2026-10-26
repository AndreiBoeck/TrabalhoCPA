"""Gera os dois relatórios em PDF exigidos nas fases 1 e 2."""

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "relatorios"
REPORTS.mkdir(exist_ok=True)
P = ROOT / "dados" / "processados"
METADATA = ROOT / "dados" / "originais" / "ana_metadados_coleta.csv"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold",
                          fontSize=17, leading=21, textColor=colors.HexColor("#173b52"), spaceAfter=10))
styles.add(ParagraphStyle(name="SectionCustom", parent=styles["Heading2"], fontName="Helvetica-Bold",
                          fontSize=11.5, leading=14, textColor=colors.HexColor("#285d73"), spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.3, leading=13, spaceAfter=7))
styles.add(ParagraphStyle(name="SmallCustom", parent=styles["BodyText"], fontSize=7.6, leading=10, spaceAfter=4,
                          wordWrap="CJK"))
styles.add(ParagraphStyle(name="FooterCustom", parent=styles["Normal"], fontSize=8, leading=10,
                          textColor=colors.grey, alignment=TA_CENTER))


def para(s: str, small: bool = False):
    return Paragraph(escape(s), styles["SmallCustom" if small else "BodyCustom"])


def section(title: str):
    return Paragraph(escape(title), styles["SectionCustom"])


def table(headers: list[str], rows: list[list[str]], widths=None):
    cells = [[para(h, True) for h in headers]] + [[para(str(v), True) for v in row] for row in rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceaf0")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c5d1d8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def pdf(path: Path, title: str, story):
    doc = BaseDocTemplate(str(path), pagesize=(21 * cm, 29.7 * cm),
                          leftMargin=2 * cm, rightMargin=2 * cm,
                          topMargin=1.8 * cm, bottomMargin=1.7 * cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0,
                  rightPadding=0, topPadding=0, bottomPadding=0)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(10.5 * cm, 1 * cm, f"Trabalho CPA | {title} | página {d.page}")
        canvas.restoreState()

    doc.addPageTemplates(PageTemplate(id="normal", frames=frame, onPage=footer))
    doc.build(story)


meta = pd.read_csv(METADATA).iloc[0]
ana = pd.read_csv(P / "ana_guaiba_2024_limpo.csv")
inct = pd.read_csv(P / "inct_simai_limpo.csv")
audit = pd.read_csv(P / "auditoria_inct.csv")
ana_audit = pd.read_csv(P / "auditoria_ana.csv")
summary = pd.read_csv(P / "inct_resumo_por_nivel.csv")

story = [
    Paragraph("Fase 1 — levantamento e escolha de bases", styles["TitleCustom"]),
    para("Projeto extensionista: análise de enchentes do INCT SiMAI. Preparado em 26/10/2026. Integrantes da equipe: preencher no README."),
    section("Pergunta proposta para a Tela 2"),
    para("Como o nível medido do Guaíba variou em Porto Alegre durante maio e junho de 2024, e quão completa é a série disponível? A Tela 2 apresentará a evolução observada, a faixa diária e a completude das medições. A ligação com a Tela 1 será o evento de 2024, sem tratar as duas bases como uma validação mútua."),
    section("Bases levantadas"),
    table(["Base", "Origem e conteúdo", "Recorte e formato", "Coleta / licença"], [
        ["INCT SiMAI", "Simulação de prédios e população afetados por bairro e nível; população IBGE 2022 e prédios OSM conforme enunciado.",
         "94 bairros de Porto Alegre; 71 cenários de 3,0 a 10,0 m; JSON local.",
         "Arquivo fornecido pela disciplina. Licença de redistribuição não informada no enunciado; confirmar com o INCT."],
        ["ANA / SGB", "Nível medido do Guaíba na estação Usina do Gasômetro, código 87450020, referencial Marco IBGE 1788A.",
         "Porto Alegre; 03/05 a 30/06/2024; XML original e CSV processado; intervalo predominante de 15 min.",
         "Download automatizado por código e período no WebService público da ANA, com cache local. Política geral de dados abertos da ANA; citar fonte."],
    ], [2.4 * cm, 5.0 * cm, 4.3 * cm, 5.3 * cm]),
    section("Por que usar a série da ANA"),
    para("A estação 87450020 cobre o pico da enchente e fornece medições datadas, com origem institucional clara e coleta por código reproduzível. A série corrigida tem referencial altimétrico documentado. Sua informação temporal acrescenta ao projeto uma descrição da evolução real do nível, enquanto o INCT responde à exposição estimada em cenários. Cada análise permanece separada."),
    section("Limitações e licença"),
    para("A estação representa um ponto em Porto Alegre e não mede impactos por bairro. Há lacunas de nível e o horário do XML não traz fuso explícito. O recorte começa em 03/05/2024. A licença específica do JSON do INCT precisa ser confirmada antes de redistribuição pública. A ANA informa que seus dados abertos são disponibilizados para uso livre; manter crédito à ANA e ao SGB."),
    section("Fonte e coleta"),
    para("ANA, documentação da série: https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs", True),
    para("Serviço de coleta: https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL", True),
    para("Política de dados abertos: https://www.gov.br/ana/pt-br/acesso-a-informacao/dados-abertos", True),
    para(f"XML obtido ou recuperado do cache em {meta['coletado_ou_cache_em']}; arquivo bruto: {meta['arquivo_bruto']}.", True),
    section("Avaliação da ferramenta atual"),
    para("O link do enunciado (http://vhlab.com.br/INCT/floods/) retornou HTTP 406 ao acesso automatizado nesta etapa. Por isso, não atribuímos problemas de interface ou desempenho sem observação direta. O grupo deve abrir a ferramenta no navegador durante o acompanhamento e registrar o que funciona, o que demora e o que não fica claro."),
]
pdf(REPORTS / "base_dados.pdf", "Levantamento de bases", story)

counts = audit[audit.campo.eq("affected_buildings")]
snap = summary[summary.nivel_m.eq(5.3)].iloc[0]
story = [
    Paragraph("Fase 2 — limpeza de dados e análise exploratória", styles["TitleCustom"]),
    para("Projeto extensionista: INCT SiMAI e nível do Guaíba. Preparado em 26/10/2026. Os procedimentos completos estão nos notebooks 01, 02 e 03."),
    section("1. Preparação do JSON do INCT"),
    para(f"O JSON original foi preservado e transformado em {len(inct):,} linhas (71 níveis × 94 bairros), com uma linha por nível e bairro. Nenhum nível ou bairro está ausente. O total de prédios e a população de cada bairro permanecem constantes entre níveis. O arquivo limpo está em dados/processados/inct_simai_limpo.csv.".replace(",", ".")),
    para("A fonte arredonda para cima o percentual de prédios afetados e a população estimada. Essa regra foi identificada antes das correções e mantida; uma coluna adicional registra o percentual exato. A população afetada é estimada sob a hipótese de distribuição uniforme de moradores entre prédios, inclusive não residenciais."),
    section("2. Inconsistências encontradas e decisões"),
    table(["Onde aparece", "Problema observado", "Tratamento e justificativa"], [
        ["Arquipélago; 3,0, 3,5, 4,0, 4,1, 4,5, 5,0 e 5,3 m", "Sete valores isolados desviam da contagem 4680, presente em 64 dos 71 níveis; surgem quedas quando o nível sobe.", "Substituídos pela moda 4680; preservar valores originais na auditoria."],
        ["Espírito Santo; 3,0–3,4 m", "Contagens 633–637 caem para 25 em 3,5 m.", "Imputação pelo primeiro valor plausível (25); trecho marcado como incerto."],
        ["Espírito Santo; 4,7 m", "Pico isolado de 2101 entre 46 e 47.", "Interpolação linear entre níveis adjacentes: 47."],
        ["Centro Histórico; 9,7–9,8 m", "Zeros entre 2050 (9,6 m) e 2130 (9,9 m).", "Interpolação linear: 2077 e 2103."],
        ["Lageado; 8,1 m; Rubem Berta; 8,8 m", "Zero isolado entre valores positivos.", "Interpolação linear: 109 e 269, respectivamente."],
        ["Boa Vista do Sul; 7,2–7,3 m", "Percentual 29, mas 686/2450 exige 28 pela regra da fonte.", "Recalcular percentual e população afetada a partir das contagens."],
    ], [4.1 * cm, 6.2 * cm, 6.7 * cm]),
    Spacer(1, 0.15 * cm),
    para(f"Foram alteradas {len(counts)} contagens de prédios e {len(audit) - len(counts)} campos derivados, totalizando {len(audit)} alterações rastreadas em dados/processados/auditoria_inct.csv. Depois do tratamento não restam quedas de prédios afetados dentro de cada bairro."),
    section("3. Série ANA"),
    para(f"O XML da estação 87450020 foi preservado com {int(meta['linhas_xml']):,} registros. A grade de 15 minutos entre 03/05 e 30/06/2024 tem {len(ana):,} horários: {ana.nivel_m.notna().sum():,} com nível válido, {ana_audit.problema.eq('nível ausente').sum()} registros com nível vazio e {ana_audit.problema.eq('horário sem registro no XML').sum()} horários ausentes do XML. Valores em centímetros foram convertidos para metros. Lacunas foram mantidas, sem interpolação. Nenhuma medição foi removida como outlier sem evidência suficiente.".replace(",", ".")),
    para("Pico observado no recorte: 4,17 m em 05/05/2024 às 05h30. Trata-se da série da estação 87450020 no referencial corrigido. A base ANA foi auditada em separado, sem classificar diferenças com a simulação do INCT como erros."),
    section("4. EDA e resultado salvo"),
    para(f"O notebook 03 contém oito gráficos comentados e exportados em resultados/figuras: cinco da simulação INCT e três da série ANA. No cenário 5,3 m, o JSON limpo estima {int(snap.pessoas_afetadas):,} pessoas, {int(snap.predios_afetados):,} prédios e {int(snap.bairros_atingidos)} bairros atingidos. Esses números são estimativas da simulação.".replace(",", ".")),
    para("O esboço das duas telas está em relatorios/wireframe.md. A Tela 1 usa exclusivamente o JSON limpo; a Tela 2 usa a série ANA. A ligação temática é o evento de 2024, com fontes e data de coleta visíveis."),
    section("5. Reprodutibilidade e limites"),
    para("Execute python -m scripts.preparar_dados na raiz do repositório. O XML bruto permite repetir a limpeza sem nova coleta caso o serviço legado da ANA seja descontinuado. Data e URL estão no CSV de metadados. O uso de IA está registrado no README."),
]
pdf(REPORTS / "limpeza_dados.pdf", "Limpeza e EDA", story)
print("Relatórios criados em", REPORTS)

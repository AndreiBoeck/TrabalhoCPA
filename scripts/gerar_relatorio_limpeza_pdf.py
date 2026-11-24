"""Gera um relatório simples das limpezas do INCT e da ANA."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                               PageTemplate, Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/relatorio_limpeza_bases.pdf"

FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont("Aluno", str(FONT_PATH)))
    FONT = "Aluno"
else:
    FONT = "Helvetica"

INK = colors.HexColor("#213c47")
TEAL = colors.HexColor("#176f7e")
PALE = colors.HexColor("#edf5f5")
LINE = colors.HexColor("#d3e1e2")
MUTED = colors.HexColor("#506b73")

STYLES = {
    "title": ParagraphStyle("title", fontName=FONT, fontSize=19, leading=24,
                            textColor=INK, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=10, leading=14,
                               textColor=MUTED, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName=FONT, fontSize=13.5, leading=18,
                         textColor=TEAL, spaceBefore=12, spaceAfter=7),
    "h2": ParagraphStyle("h2", fontName=FONT, fontSize=10.7, leading=15,
                         textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.7, leading=14.1,
                           textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=8.3, leading=11.5,
                            textColor=MUTED, spaceAfter=4),
    "table": ParagraphStyle("table", fontName=FONT, fontSize=8.35, leading=11.3,
                            textColor=INK),
    "table_head": ParagraphStyle("table_head", fontName=FONT, fontSize=8.4, leading=11.2,
                                 textColor=colors.white),
}


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str) -> Paragraph:
    return p(f"<font color='#176f7e'>•</font>  {text}")


def callout(text: str) -> Table:
    table = Table([[p(text)]], colWidths=[175 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), .6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def corrections_table() -> Table:
    rows = [
        ["Bairro", "O que chamou atenção", "O que fizemos"],
        ["Arquipélago", "7 valores isolados diferiam do valor visto em 64 dos 71 níveis.",
         "Usamos 4.680, o valor mais frequente na própria série."],
        ["Espírito Santo", "De 3,0 a 3,4 m havia 633 a 637 prédios; em 3,5 m caía para 25. Em 4,7 m, aparecia um pico de 2.101.",
         "Usamos 25 nos cinco primeiros níveis. No pico isolado, usamos 47, entre os valores vizinhos. A primeira decisão é incerta."],
        ["Centro Histórico, Lageado e Rubem Berta", "Havia zeros entre níveis com prédios atingidos.",
         "Preenchemos 4 pontos com valores intermediários calculados a partir dos níveis vizinhos."],
    ]
    wrapped = [[p(cell, "table_head" if row == 0 else "table") for cell in line] for row, line in enumerate(rows)]
    table = Table(wrapped, colWidths=[36 * mm, 68 * mm, 71 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8f8")]),
        ("GRID", (0, 0), (-1, -1), .4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def page_frame(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    canvas.setFont(FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 13 * mm, "Trabalho CPA  |  Projeto Extensionista")
    canvas.drawRightString(width - 18 * mm, 13 * mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 18 * mm, width - 18 * mm, 18 * mm)
    canvas.restoreState()


def validate_counts() -> None:
    processed = ROOT / "dados/processados"
    inct = pd.read_csv(processed / "inct_simai_limpo.csv")
    ia = pd.read_csv(processed / "auditoria_inct.csv")
    ana = pd.read_csv(processed / "ana_guaiba_2024_limpo.csv")
    aa = pd.read_csv(processed / "auditoria_ana.csv")
    assert len(inct) == 6674 and inct.nivel_m.nunique() == 71 and inct.bairro.nunique() == 94
    assert len(ia) == 41 and Counter(ia.campo)["affected_buildings"] == 17
    assert len(ana) == 5664 and ana.nivel_m.notna().sum() == 5444
    assert Counter(aa.problema) == {"horário sem registro no XML": 113, "nível ausente": 107}


def build() -> None:
    validate_counts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=20 * mm, bottomMargin=23 * mm,
                          title="Como limpamos as bases do INCT e da ANA",
                          author="Equipe Trabalho CPA")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="relatorio", frames=[frame], onPage=page_frame))
    story = [
        p("Como limpamos as bases de dados", "title"),
        p("INCT SiMAI e nível do Guaíba medido pela ANA  |  Relatório de trabalho  |  11/11/2026", "subtitle"),
        callout("<b>Nosso objetivo</b><br/>Deixar as duas bases organizadas para análise e para o dashboard. Guardamos os arquivos originais e registramos cada mudança, para que seja possível conferir o que fizemos."),
        p("1. Base de simulação do INCT", "h1"),
        p("Recebemos um arquivo JSON com cenários do nível do Guaíba de <b>3,0 a 10,0 m</b>, de 0,1 em 0,1 m. Cada cenário traz dados de <b>94 bairros</b>. Transformamos esse formato em uma tabela com uma linha por bairro e nível: <b>6.674 linhas</b> no total."),
        p("Antes de mudar qualquer valor, conferimos se havia todos os níveis e bairros, linhas repetidas, campos vazios ou números negativos. Também verificamos se o total de prédios e a população de cada bairro permaneciam iguais entre os níveis. Essas verificações passaram."),
        p("Como identificamos os pontos estranhos", "h2"),
        p("Comparamos, para cada bairro, a quantidade de prédios afetados conforme o nível subia. Um aumento do rio não deveria fazer essa quantidade cair de repente. Procuramos quedas e valores isolados que destoavam dos níveis logo antes e depois. <b>Não alteramos a série inteira:</b> corrigimos apenas os pontos com motivo registrado."),
        corrections_table(),
        Spacer(1, 8),
        p("Ao todo, ajustamos <b>17 contagens de prédios</b>. A tabela de auditoria guarda, em cada caso, o bairro, o nível, o valor que veio no JSON, o valor usado e o motivo. O ajuste de 3,0 a 3,4 m no Espírito Santo é uma estimativa mais incerta, pois não havia um valor anterior para comparar."),
        PageBreak(),
        p("O que recalculamos no INCT", "h1"),
        p("O próprio arquivo arredonda <b>para cima</b> a porcentagem de prédios afetados. Mantivemos essa regra. Depois dos ajustes, recalculamos a porcentagem e a população estimada afetada. Também encontramos alguns campos calculados que não batiam com a contagem, como em Boa Vista do Sul. Foram <b>24 recálculos</b> desses campos; somados aos 17 ajustes de prédios, são <b>41 mudanças registradas</b>."),
        callout("<b>Exemplo simples:</b> se 28 de 589 prédios são afetados, a conta dá 4,75%. Pela regra da fonte, o arquivo mostra 5%. Para estimar as pessoas afetadas, aplicamos esses 5% à população do bairro e arredondamos para cima. É uma estimativa da simulação, não uma contagem de moradores atingidos."),
        p("Por fim, criamos também uma porcentagem com casas decimais para os gráficos e um campo que indica se o bairro tem algum prédio afetado. Conferimos de novo se as contagens não diminuíam quando o nível subia e salvamos a tabela limpa, o JSON usado pelo site, o resumo por nível e a lista de mudanças."),
        p("2. Medições da ANA", "h1"),
        p("Esta base foi tratada <b>separadamente</b>. Baixamos pelo serviço da ANA as medições da estação <b>87450020 - Usina do Gasômetro</b>, de <b>03/05 a 30/06/2024</b>. Guardamos o XML recebido e a data da coleta. Os dados são medições em um ponto; não são resultados da simulação por bairro do INCT."),
        p("Como organizamos as medições", "h2"),
        bullet("Convertemos as datas para um formato único e os níveis de centímetros para metros (dividindo por 100)."),
        bullet("O programa verifica datas inválidas e horários repetidos. Nesta coleta, não foi necessário retirar registros por esses motivos."),
        bullet("Montamos a sequência esperada de um registro a cada 15 minutos. Assim, aparecem também os horários que não vieram no XML."),
        bullet("Mantivemos vazios os níveis sem valor. Não inventamos uma medição entre dois horários nem transformamos ausência em zero."),
        p("O resultado tem <b>5.664 horários</b>: <b>5.444</b> com nível medido e <b>220</b> sem nível. Desses 220, <b>107</b> já apareciam no XML sem valor e <b>113</b> horários nem tinham registro no arquivo. Cada caso está descrito na auditoria."),
        p("Algumas mudanças rápidas de nível podem chamar atenção, mas não foram apagadas automaticamente. Elas podem refletir o rio ou a medição, então precisam de análise própria. O maior valor dessa série limpa foi <b>4,17 m em 05/05/2024 às 05h30</b>, no referencial corrigido da estação. O número de <b>5,35 m</b>, divulgado para a régua emergencial, usa outra referência; tratamos os dois como medidas com referências diferentes."),
        p("Arquivos que deixamos prontos", "h1"),
        p("Os originais estão em <b>dados/originais/</b>. As bases prontas e as listas de mudanças estão em <b>dados/processados/</b>: <b>inct_simai_limpo.csv</b>, <b>inct_simai_limpo.json</b>, <b>auditoria_inct.csv</b>, <b>ana_guaiba_2024_limpo.csv</b> e <b>auditoria_ana.csv</b>. Os notebooks 01 e 02 mostram as etapas com os resultados salvos. Para refazer a preparação, usamos <b>python3 -m scripts.preparar_dados</b>."),
        p("Fontes: JSON do INCT fornecido ao projeto; <link href='https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL' color='#176f7e'>serviço de dados da ANA</link>; <link href='https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs' color='#176f7e'>explicação da ANA/SGB sobre a régua</link>.", "small"),
    ]
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()

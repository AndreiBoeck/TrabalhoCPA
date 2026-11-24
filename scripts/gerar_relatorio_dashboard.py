"""Gera relatorios/dashboard.pdf, o relatório do dashboard (Fase 3 e versão final).

Uso, a partir da raiz do repositório:

    python3 -m scripts.gerar_relatorio_dashboard

As capturas de tela ficam em relatorios/figuras_dashboard/. Os campos marcados
com "A PREENCHER" no topo deste arquivo devem ser completados pela equipe antes
de gerar a versão de entrega.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "relatorios/dashboard.pdf"
FIGS = ROOT / "relatorios/figuras_dashboard"

# --- Campos que a equipe deve completar -------------------------------------
EQUIPE = "A PREENCHER: nomes dos integrantes"
LINK_PUBLICO = "A PREENCHER: link público do dashboard"
DATA_RELATORIO = "24/11/2026"
# Observações da equipe sobre a ferramenta atual do INCT (Flood - INCT SiMAI).
# Cada item: (o que observamos, como o nosso dashboard responde).
OBSERVACOES_FERRAMENTA_ATUAL: list[tuple[str, str]] = [
    ("A PREENCHER: o que funciona bem na ferramenta atual.", "—"),
    ("A PREENCHER: o que é difícil de encontrar.", "—"),
    ("A PREENCHER: o que demora (carregamento, instabilidade).", "—"),
    ("A PREENCHER: o que não fica claro.", "—"),
]
# -----------------------------------------------------------------------------

FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD_PATH = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont("Aluno", str(FONT_PATH)))
    FONT = "Aluno"
    if FONT_BOLD_PATH.exists():
        pdfmetrics.registerFont(TTFont("Aluno-Bold", str(FONT_BOLD_PATH)))
        pdfmetrics.registerFontFamily("Aluno", normal="Aluno", bold="Aluno-Bold",
                                      italic="Aluno", boldItalic="Aluno-Bold")
else:
    FONT = "Helvetica"

INK = colors.HexColor("#213c47")
TEAL = colors.HexColor("#176f7e")
PALE = colors.HexColor("#edf5f5")
WARN = colors.HexColor("#fbf1e6")
LINE = colors.HexColor("#d3e1e2")
MUTED = colors.HexColor("#506b73")

STYLES = {
    "title": ParagraphStyle("title", fontName=FONT, fontSize=20, leading=25, textColor=INK, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=10, leading=14, textColor=MUTED, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName=FONT, fontSize=13.5, leading=18, textColor=TEAL, spaceBefore=12, spaceAfter=7),
    "h2": ParagraphStyle("h2", fontName=FONT, fontSize=10.7, leading=15, textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.6, leading=14, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=8.2, leading=11.3, textColor=MUTED, spaceAfter=4),
    "table": ParagraphStyle("table", fontName=FONT, fontSize=8.3, leading=11.2, textColor=INK),
    "table_head": ParagraphStyle("table_head", fontName=FONT, fontSize=8.4, leading=11.2, textColor=colors.white),
}
LINK = "color='#176f7e'"


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str) -> Paragraph:
    return p(f"<font color='#176f7e'>•</font>  {text}")


def box(text: str, background=PALE) -> Table:
    table = Table([[p(text)]], colWidths=[174 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), .6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def table(rows: list[list[str]], widths: list[float]) -> Table:
    wrapped = [[p(c, "table_head" if i == 0 else "table") for c in row] for i, row in enumerate(rows)]
    t = Table(wrapped, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8f8")]),
        ("GRID", (0, 0), (-1, -1), .4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def figure(name: str, caption: str, width_mm: float = 174, max_height_mm: float = 200) -> KeepTogether:
    path = FIGS / name
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    w = width_mm * mm
    h = w * ratio
    if h > max_height_mm * mm:
        h = max_height_mm * mm
        w = h / ratio
    img.drawWidth, img.drawHeight = w, h
    return KeepTogether([img, Spacer(1, 3), p(caption, "small"), Spacer(1, 6)])


def fmt(n: float) -> str:
    return f"{int(n):,}".replace(",", ".")


def page_frame(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    canvas.setFont(FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 13 * mm, "Trabalho CPA  |  Projeto Extensionista  |  Relatório do dashboard")
    canvas.drawRightString(width - 18 * mm, 13 * mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 18 * mm, width - 18 * mm, 18 * mm)
    canvas.restoreState()


def numbers() -> dict:
    resumo = pd.read_csv(ROOT / "dados/processados/inct_resumo_por_nivel.csv").set_index("nivel_m")
    ana = pd.read_csv(ROOT / "dados/processados/ana_guaiba_2024_limpo.csv")
    assert len(resumo) == 71
    return {
        "r3": resumo.loc[3.0], "r53": resumo.loc[5.3], "r54": resumo.loc[5.4], "r10": resumo.loc[10.0],
        "ana_total": len(ana), "ana_validos": int(ana.nivel_m.notna().sum()),
    }


def build() -> None:
    n = numbers()
    r3, r53, r54, r10 = n["r3"], n["r53"], n["r54"], n["r10"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=20 * mm, bottomMargin=23 * mm,
                          title="Relatório do dashboard: enchentes em Porto Alegre",
                          author="Equipe Trabalho CPA")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="relatorio", frames=[frame], onPage=page_frame))

    obs_rows = [["O que observamos na ferramenta atual", "Como o nosso dashboard responde"]]
    obs_rows += [[a, b] for a, b in OBSERVACOES_FERRAMENTA_ATUAL]

    story = [
        p("Relatório do dashboard", "title"),
        p(f"Enchentes em Porto Alegre: simulação do INCT SiMAI e bases externas  |  {DATA_RELATORIO}", "subtitle"),
        table([["Equipe", EQUIPE], ["Dashboard publicado", LINK_PUBLICO],
               ["Repositório", "<link href='https://github.com/AndreiBoeck/TrabalhoCPA' "
                f"{LINK}>github.com/AndreiBoeck/TrabalhoCPA</link>"],
               ["Execução local", "python3 -m uvicorn backend.main:app  →  http://127.0.0.1:8000"]],
              [40, 134]),
        Spacer(1, 10),
        box("<b>Para que serve este painel.</b> Responder rapidamente a duas perguntas: <b>(1)</b> se o Guaíba "
            "chegar a X metros, quais bairros e quantas pessoas seriam afetados, segundo a simulação do INCT SiMAI; "
            "<b>(2)</b> o que outras bases sobre a enchente de 2024 acrescentam a essa resposta. Todos os números de "
            "impacto são <b>estimativas de uma simulação</b>, não previsões nem contagens oficiais."),

        p("1. Ponto de partida: a ferramenta atual do INCT", "h1"),
        p("Antes de desenhar o painel, a equipe explorou a página <i>Flood - INCT SiMAI</i> e anotou o que "
          "funciona e o que atrapalha. Essas observações orientaram as escolhas descritas nas seções seguintes."),
        table(obs_rows, [87, 87]),
        Spacer(1, 4),
        p("Independentemente das observações acima, a arquitetura foi pensada para o problema de lentidão e "
          "instabilidade citado no enunciado: os 71 cenários já limpos são carregados uma vez na memória do "
          "servidor, cada mudança do controle deslizante faz uma consulta pequena (<b>/api/scenario</b>) e a página "
          "não depende de bibliotecas externas carregadas da internet para desenhar os gráficos da Tela 1.", "small"),

        p("2. Tela 1: Simulação do INCT", "h1"),
        p("<b>Objetivo.</b> Mostrar, para qualquer nível do Guaíba entre 3,0 e 10,0 m, quantas pessoas e prédios "
          "a simulação estima como afetados e em quais bairros o impacto se concentra. A única fonte é o JSON do "
          "INCT depois da limpeza documentada em <b>relatorios/limpeza_dados.pdf</b> (41 mudanças registradas em "
          "<b>dados/processados/auditoria_inct.csv</b>)."),
        p("Visualizações escolhidas e por quê", "h2"),
        table([
            ["Elemento", "Por que esta forma"],
            ["Controle deslizante 3,0–10,0 m, passo 0,1 m",
             "Corresponde exatamente aos 71 cenários do INCT; nenhum valor intermediário é inventado. A marca de "
             "5,35 m fica entre 5,3 e 5,4 m, sem interpolar impactos."],
            ["Três indicadores no topo",
             "Respondem à pergunta principal em uma leitura: pessoas afetadas, prédios afetados e bairros "
             "atingidos (de 94)."],
            ["Barras horizontais da % de prédios por bairro",
             "Barras horizontais comportam nomes longos de bairros e permitem comparar comprimentos com precisão. "
             "Só aparecem bairros atingidos, ordenados do maior para o menor percentual."],
            ["Curva da população afetada por nível",
             "Uma linha mostra a tendência entre todos os níveis e situa o nível escolhido (ponto) em relação ao "
             "recorde de 5,35 m (linha tracejada)."],
            ["Ranking dos bairros",
             "Ordena pela população afetada estimada, que difere da ordem por percentual: bairros grandes com "
             "percentual menor podem ter mais pessoas afetadas."],
        ], [52, 122]),
        Spacer(1, 6),
        p(f"<b>Leitura rápida dos números.</b> Em 3,0 m, a simulação já indica {fmt(r3.pessoas_afetadas)} pessoas e "
          f"{int(r3.bairros_atingidos)} bairros afetados. Em 5,3 m são {fmt(r53.pessoas_afetadas)} pessoas, "
          f"{fmt(r53.predios_afetados)} prédios e {int(r53.bairros_atingidos)} bairros; em 5,4 m, "
          f"{fmt(r54.pessoas_afetadas)} pessoas. Em 10,0 m, {fmt(r10.pessoas_afetadas)} pessoas e "
          f"{int(r10.bairros_atingidos)} bairros."),
        p("Como usar", "h2"),
        bullet("Arraste o controle ou use as setas do teclado para mudar o nível em passos de 0,1 m; o título, os "
               "indicadores, as barras, o ponto na curva e o ranking são atualizados juntos."),
        bullet("Use o link <b>Tela 2</b> no canto superior direito para ir às bases externas."),
        bullet("O link <b>Consultar API</b> no rodapé abre a documentação dos dados servidos pela tela."),

        figure("tela1_visao_geral.png", "Figura 1. Tela 1 no nível de 5,3 m, o cenário disponível mais próximo do "
               "recorde de maio de 2024.", max_height_mm=175),
        p("3. Tela 2: o Guaíba em 2024 e bases externas", "h1"),
        p("<b>Objetivo.</b> Acrescentar à simulação o que foi efetivamente medido e mapeado na enchente de 2024: "
          "o nível observado do Guaíba, a localização dos bairros, a mancha de água modelada por satélite e o "
          "efeito dessa mancha no deslocamento a pé pelo centro."),
        p("Bases externas, obtidas por código", "h2"),
        table([
            ["Base", "Como foi obtida", "Uso na tela", "Coleta"],
            ["ANA/SGB, estação 87450020 (Usina do Gasômetro)",
             f"WebService da ANA (<b>scripts/preparar_dados.py</b>); XML bruto guardado. {fmt(n['ana_total'])} "
             f"horários, {fmt(n['ana_validos'])} com nível.",
             "Série 03/05–30/06/2024, faixa diária, completude, leitura recente", "26/10/2026"],
            ["Limites oficiais dos bairros (Prefeitura/ObservaPOA)",
             "Download automatizado (<b>scripts/preparar_bairros.py</b>)", "Mapa temático por bairro",
             "10/11/2026"],
            ["Copernicus EMSN194", "Download automatizado (<b>scripts/preparar_rotas_2024.py</b>)",
             "Mancha e profundidade de 06/05/2024 (rotas e 3D)", "10/11/2026"],
            ["OpenStreetMap", "API do OSM (<b>scripts/preparar_rotas_2024.py</b>)", "Rede de ruas do centro",
             "10/11/2026"],
            ["Mapzen Terrain Tiles (AWS Open Data)", "Download automatizado (<b>scripts/preparar_relevo_3d.py</b>)",
             "Relevo da visualização 3D", "10/11/2026"],
        ], [42, 56, 52, 24]),
        Spacer(1, 4),
        p("Cada visualização exibe, logo abaixo, a fonte com link e a data de coleta, como pede o enunciado.",
          "small"),
        figure("tela2_ana.png", "Figura 2. Medições da ANA com filtro de período, indicadores, os três gráficos e o "
               "painel que liga a Tela 2 à Tela 1.", max_height_mm=125),
        p("Visualizações escolhidas e por quê", "h2"),
        table([
            ["Elemento", "Por que esta forma"],
            ["Filtro de período (datas De/Até)",
             "Filtro interativo que atualiza os indicadores e os três gráficos da ANA juntos."],
            ["Série temporal do nível observado",
             "Mostra a subida até o pico de 4,17 m em 05/05/2024 e a descida lenta. Lacunas ficam vazias, "
             "nunca desenhadas como zero."],
            ["Faixa diária (mínimo–máximo)",
             "Resume quase 100 leituras por dia em uma barra, deixando visível a oscilação diária."],
            ["Completude diária",
             "Mostra quanto de cada dia tem medição, para que o leitor saiba quando a série é menos confiável."],
            ["Cartões de leitura recente e de recorde",
             "A leitura atual só aparece como recente se tiver até 2 h; o recorde aparece nos dois referenciais "
             "(5,35 m na régua emergencial e 4,17 m no referencial corrigido), sem misturá-los no mesmo eixo."],
            ["Ligação com a Tela 1",
             "Painel lado a lado com o pico observado (ANA) e o impacto dos cenários INCT de 5,3 e 5,4 m, "
             "identificados como observação e simulação. Os referenciais não foram equiparados, então não há "
             "comparação numérica direta."],
            ["Mapa temático por bairro",
             "Colore os 94 limites oficiais pela % de prédios afetados no nível escolhido, com controle próprio. "
             "É o mapa opcional do enunciado; a cor resume o bairro e não localiza a água dentro dele."],
            ["Relevo e água em 3D",
             "Visualização exploratória de duas regiões do centro com a profundidade modelada de 06/05/2024; "
             "permite girar, exagerar o relevo e ocultar a água."],
            ["Rotas entre dois pontos",
             "Protótipo: o usuário marca A e B; o servidor calcula o caminho seco mais curto ou, se A estiver "
             "alagado, a saída de menor profundidade, e compara com o caminho sem alagamento."],
        ], [52, 122]),
        figure("tela2_mapa_3d.png", "Figura 3. Mapa temático por bairro (simulação INCT sobre limites oficiais) e "
               "relevo 3D com a água modelada em 06/05/2024.", max_height_mm=115),
        figure("tela2_rotas.png", "Figura 4. Protótipo de rotas no centro de Porto Alegre, cenário de 06/05/2024.",
               max_height_mm=100),
        p("Como usar", "h2"),
        bullet("Escolha as datas <b>De</b> e <b>Até</b> para recortar o período da série da ANA."),
        bullet("No mapa temático, mova o controle de nível e toque em um bairro para ver seus valores."),
        bullet("No 3D, escolha a região e ajuste rotação, exagero vertical e a camada de água."),
        bullet("Nas rotas, clique numa rua para marcar A e depois B, ou use <b>Exemplo de desvio</b> e "
               "<b>Origem alagada</b>; <b>Escolher outros pontos</b> recomeça."),

        p("4. Limitações", "h1"),
        bullet("<b>Simulação, não contagem.</b> A população afetada supõe pessoas distribuídas igualmente entre todos "
               "os prédios do bairro, inclusive os não residenciais (população do Censo 2022 × percentual de prédios)."),
        bullet("<b>Dados corrigidos.</b> O JSON do INCT tinha inconsistências; 17 contagens de prédios foram ajustadas "
               "e 24 campos recalculados. A correção do Espírito Santo de 3,0 a 3,4 m é a mais incerta."),
        bullet("<b>Percentual da fonte arredondado para cima.</b> O painel mantém essa regra para coerência com o INCT."),
        bullet("<b>Referenciais diferentes.</b> O recorde de 5,35 m é da régua emergencial; a série da ANA usa o "
               "referencial corrigido (4,17 m para o mesmo pico). O referencial dos níveis do INCT não foi confirmado."),
        bullet("<b>Bairro como unidade.</b> O mapa temático não indica quais ruas ficam alagadas."),
        bullet("<b>Rotas e 3D são históricos e exploratórios.</b> Usam um único cenário (06/05/2024), não consideram "
               "correnteza, bloqueios ou condições atuais e não são indicação de segurança."),
        bullet("<b>Sem previsão.</b> Não foi encontrada uma série oficial de níveis previstos acessível por código; "
               "a tela informa isso em vez de extrapolar."),

        p("5. O que mudou desde a Fase 3", "h1"),
        p("Na Fase 3, o repositório tinha a Tela 1 funcional e a checklist da Tela 2. Para a versão final:"),
        bullet("Tela 2 completa: série ANA com filtro de período, três gráficos, leitura recente e cartão de recorde."),
        bullet("Painel de ligação com a Tela 1 pela enchente de 2024."),
        bullet("Mapa temático dos 94 bairros com limites oficiais da Prefeitura (diferencial opcional do enunciado)."),
        bullet("Visualização 3D histórica e protótipo de rotas, com 12 testes automatizados (rotas, API e dados espaciais)."),
        bullet("Mockup que reúne as duas telas com navegação lateral (<b>/mockup</b>)."),
        bullet("Este relatório, gerado por <b>scripts/gerar_relatorio_dashboard.py</b>."),

        p("6. Uso de ferramentas de IA", "h1"),
        bullet("<b>Codex</b>, 26/10/2026: apoio na preparação de scripts, notebooks, limpeza, gráficos e relatórios "
               "iniciais (registrado no README)."),
        bullet("<b>Claude Code</b>, 24/11/2026: organização dos commits finais, capturas de tela e redação deste "
               "relatório a partir do código e dos dados do repositório."),
        p("A equipe revisou o conteúdo e deve conseguir explicar cada parte do código na apresentação.", "small"),

        p("Fontes", "h2"),
        p(f"JSON do INCT SiMAI fornecido com o enunciado · <link href='https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL' {LINK}>WebService ANA</link> · "
          f"<link href='https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs' {LINK}>ANA/SGB sobre o referencial</link> · "
          f"<link href='https://prefeitura.poa.br/smpg/observapoa/mapas' {LINK}>ObservaPOA</link> · "
          f"<link href='https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products' {LINK}>Copernicus EMSN194</link> · "
          f"<link href='https://www.openstreetmap.org/copyright' {LINK}>OpenStreetMap</link> · "
          f"<link href='https://registry.opendata.aws/terrain-tiles/' {LINK}>Mapzen Terrain Tiles</link> · "
          f"<link href='https://sace.sgb.gov.br/guaiba/' {LINK}>SACE/SGB</link>", "small"),
    ]
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()

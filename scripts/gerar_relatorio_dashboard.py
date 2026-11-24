"""Gera relatorios/dashboard.pdf, o relatório do dashboard (Fase 3 e versão final).

Uso, a partir da raiz do repositório:

    python3 -m scripts.gerar_relatorio_dashboard

As capturas de tela ficam em relatorios/figuras_dashboard/. Os campos marcados
com "A PREENCHER" no topo deste arquivo devem ser completados pela equipe antes
de gerar a versão de entrega.
"""

from __future__ import annotations

import json
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


def fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


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
    validation = json.loads((ROOT / "dados/processados/modelo_agua_validacao.json").read_text(encoding="utf-8"))
    v = {row["date"]: row for row in validation["validation"]}
    fc72 = json.loads((ROOT / "dados/processados/modelo_previsao.json").read_text(encoding="utf-8"))["horizons"][-1]
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
        bullet("Use o link <b>Tela 2 · Tempo real</b> no canto superior direito para ir à Tela 2."),
        bullet("O link <b>Consultar API</b> no rodapé abre a documentação dos dados servidos pela tela."),

        figure("tela1_visao_geral.png", "Figura 1. Tela 1 no nível de 5,3 m, o cenário disponível mais próximo do "
               "recorde de maio de 2024.", max_height_mm=175),
        p("3. Tela 2: o Guaíba agora e o que ele alaga", "h1"),
        p("<b>Objetivo.</b> Responder, a qualquer momento, quanto o Guaíba está marcando, para onde ele deve ir nas "
          "próximas 72 horas e onde a água chega nesse nível: em cada bairro (simulação do INCT), em um ponto "
          "escolhido da cidade e nas ruas do centro. A enchente de 2024 serve de referência e de validação."),
        box("<b>Um único cenário para a tela inteira.</b> Ao abrir, a tela fica <b>sincronizada com o tempo real</b>: "
            "o nível em uso é a leitura mais recente da ANA (consultada a cada 5 minutos). Ao escolher outro nível, um "
            "horário da previsão ou o recorde de 2024, a tela passa para <b>cenário manual</b> e todos os mapas, "
            "indicadores e gráficos mudam juntos. O botão <b>Voltar ao tempo real</b> retoma a leitura atual. "
            "Os níveis usam a régua do Cais Mauá, a mesma escala da Tela 1: régua = referencial corrigido da ANA + "
            "1,18 m, diferença documentada pela ANA/SGB para o pico de 05/05/2024 (5,35 m ↔ 4,17 m)."),
        Spacer(1, 6),
        figure("t2_1_topo.png", "Figura 2. Topo da Tela 2: leitura atual, cenário em uso, indicadores e o componente "
               "de mapas em abas (aba Bairros).", max_height_mm=135),
        p("Bases externas, obtidas por código", "h2"),
        table([
            ["Base", "Como foi obtida", "Uso na tela", "Coleta"],
            ["ANA/SGB, estação 87450020 (Usina do Gasômetro)",
             "WebService da ANA: leitura ao vivo (<b>backend/main.py</b>), série desde 2023 "
             "(<b>scripts/preparar_previsao.py</b>) e maio–junho de 2024 (<b>scripts/preparar_dados.py</b>).",
             "Leitura atual, previsão, gráficos de 2024 e calibração do modelo de água",
             "a cada 5 min; histórico em 24/11/2026"],
            ["Limites oficiais dos bairros (Prefeitura/ObservaPOA)",
             "Download automatizado (<b>scripts/preparar_bairros.py</b>)", "Aba Bairros", "10/11/2026"],
            ["Copernicus EMSN194", "Download automatizado (<b>scripts/preparar_modelo_agua.py</b>)",
             "Profundidade e manchas de 04 a 10/05/2024: calibração e validação do modelo de água", "24/11/2026"],
            ["Terrain Tiles (AWS Open Data)", "Download automatizado (<b>scripts/preparar_modelo_agua.py</b>)",
             "Relevo do modelo de água", "24/11/2026"],
            ["OpenStreetMap", "API do OSM (<b>scripts/preparar_rotas_2024.py</b>) e blocos do mapa",
             "Rede de ruas das rotas e mapa sobre o relevo 3D", "10/11/2026 e ao vivo"],
        ], [40, 58, 50, 26]),
        Spacer(1, 4),
        p("Cada visualização exibe a fonte com link e a data de coleta, como pede o enunciado.", "small"),
        p("Modelo de água por nível", "h2"),
        p("O JSON do INCT dá totais por bairro, mas não diz onde a água fica. Para a aba 3D e as rotas, montamos uma "
          "grade de 20 m sobre Porto Alegre. O relevo aberto inclui prédios e vegetação, então o chão foi corrigido "
          f"com a profundidade do Copernicus (chão = nível da ANA no dia − profundidade) e, fora das áreas molhadas, "
          f"com um viés local estimado num raio de 1 km. A água entra a partir do lago: cada célula guarda a menor cota "
          f"capaz de alcançá-la por células conectadas, supondo que o sistema de proteção deixe a água passar, como em "
          f"2024. Validação contra a mancha observada, dentro de Porto Alegre: IoU de {fmt_pct(v['2024-05-06']['iou'])} "
          f"em 06/05 (data usada na calibração), {fmt_pct(v['2024-05-04']['iou'])} em 04/05 e "
          f"{fmt_pct(v['2024-05-10']['iou'])} em 10/05/2024. A precisão fica acima de 98% (onde o modelo põe água, "
          "havia água), mas ele subestima a área porque não representa a água represada atrás dos diques quando o rio "
          "baixou."),
        figure("t2_2_3d.png", "Figura 3. Aba Água no ponto · 3D: 1,2 km × 1,2 km em volta da Rodoviária, com o "
               "mapa do OpenStreetMap sobre o relevo e a água no cenário de 5,35 m.", max_height_mm=110),
        figure("t2_3_rotas.png", "Figura 4. Aba Rotas a pé: trechos com água no centro no cenário de 5,35 m.",
               max_height_mm=105),
        p("Previsão do nível", "h2"),
        p(f"Para cada horizonte de 6 a 72 h, uma regressão linear prevê a variação do nível a partir da tendência "
          f"das últimas 6, 24 e 72 h e da distância à média de 30 dias. O treino usa a série horária da estação desde "
          f"2023, e o teste usa os 12 meses mais recentes, que o modelo não viu: erro médio em 72 h de "
          f"{fc72['mae_model_m'] * 100:.0f} cm, contra {fc72['mae_persistence_m'] * 100:.0f} cm de repetir o último "
          "nível. A faixa mostrada cobre 80% dos erros do teste. É um modelo estatístico experimental: não usa chuva "
          "prevista, vento nem vazão dos rios e não substitui os boletins do SGB, cuja série pública estruturada não "
          "foi encontrada."),
        figure("t2_4_previsao.png", "Figura 5. Últimos 7 dias e previsão de 72 h com faixa provável. Clicar em um "
               "ponto da previsão aplica aquele horário em toda a tela.", max_height_mm=80),
        figure("t2_5_2024.png", "Figura 6. Enchente de 2024: filtro de período, três gráficos da ANA com o cenário "
               "em uso como linha de referência e o painel de ligação com a Tela 1.", max_height_mm=125),
        p("Visualizações escolhidas e por quê", "h2"),
        table([
            ["Elemento", "Por que esta forma"],
            ["Leitura atual e selo Tempo real / Cenário manual",
             "Deixa claro, o tempo todo, se o que a tela mostra é o agora ou uma hipótese. Leitura com mais de 2 h é "
             "marcada como desatualizada."],
            ["Controle do cenário e botões de previsão e recorde",
             "Um só controle muda tudo: evita que cada gráfico mostre um nível diferente."],
            ["Indicadores do cenário",
             "Pessoas e bairros (INCT), ruas com água no centro e água no ponto escolhido, numa leitura só."],
            ["Mapas em abas (Bairros, 3D, Rotas)",
             "Três escalas da mesma pergunta (bairro, quarteirão, rua) no destaque da tela, sem rolar a página."],
            ["Vista 3D com mapa real",
             "Mostrar o mapa da rua sob a água torna a profundidade compreensível para moradores e imprensa."],
            ["Gráfico de previsão com faixa",
             "Linha contínua para o observado, tracejada para a previsão e faixa para a incerteza: o leitor vê o "
             "quanto confiar no número."],
            ["Série, faixa diária e completude de 2024 com filtro",
             "Mostram a subida até o pico e onde faltam medições; lacunas nunca aparecem como zero."],
            ["Ligação com a Tela 1",
             "Cenário em uso, impacto estimado pelo INCT e recorde de 2024 no mesmo eixo da régua."],
        ], [52, 122]),
        p("Como usar", "h2"),
        bullet("Sem fazer nada, a tela mostra o nível de agora. Use o controle, os botões <b>Previsão +24/48/72 h</b>, "
               "<b>Recorde 2024</b> ou um ponto do gráfico de previsão para mudar o cenário; <b>Voltar ao tempo "
               "real</b> retoma a leitura atual."),
        bullet("Na aba <b>Bairros</b>, clique em um bairro para ver os valores; o ponto do 3D vai para lá."),
        bullet("Na aba <b>Água no ponto · 3D</b>, clique no mini mapa para escolher outro ponto e arraste a vista "
               "para girar."),
        bullet("Na aba <b>Rotas a pé</b>, clique numa rua para marcar A e depois B, ou use os exemplos."),
        bullet("Na seção de 2024, escolha as datas <b>De</b> e <b>Até</b>. O endereço "
               "<b>/tela2#aba=point&amp;nivel=5.35</b> abre a tela já numa aba e num nível."),

        p("4. Limitações", "h1"),
        bullet("<b>Simulação, não contagem.</b> A população afetada supõe pessoas distribuídas igualmente entre todos "
               "os prédios do bairro, inclusive os não residenciais (população do Censo 2022 × percentual de prédios)."),
        bullet("<b>Dados corrigidos.</b> O JSON do INCT tinha inconsistências; 17 contagens de prédios foram ajustadas "
               "e 24 campos recalculados. A correção do Espírito Santo de 3,0 a 3,4 m é a mais incerta."),
        bullet("<b>Percentual da fonte arredondado para cima.</b> O painel mantém essa regra para coerência com o INCT."),
        bullet("<b>Referencial.</b> A conversão régua = ANA + 1,18 m vem do pico de 2024. Supomos que os níveis do "
               "INCT estão na régua, o que não foi confirmado com o parceiro."),
        bullet("<b>Modelo de água simplificado.</b> Enche a partir do lago, sem chuva local, bombas, correnteza ou "
               "obras recentes, e supõe que a proteção deixe a água passar. Subestima a água represada. Não serve "
               "para decisão de segurança."),
        bullet("<b>Previsão experimental.</b> Ganho pequeno sobre repetir o último nível; não antecipa cheias "
               "causadas por chuva ainda não registrada no nível."),
        bullet("<b>Bairro como unidade no INCT.</b> A aba Bairros não indica quais ruas ficam alagadas; para isso "
               "servem o 3D e as rotas, com o modelo próprio."),

        p("5. O que mudou desde a Fase 3", "h1"),
        p("Na Fase 3, o repositório tinha a Tela 1 funcional e a checklist da Tela 2. Para a versão final:"),
        bullet("Tela 2 reorganizada em torno do tempo real: leitura atual, cenário único com sincronização e botão "
               "<b>Voltar ao tempo real</b>."),
        bullet("Os três mapas viraram um componente só, em abas, logo abaixo do nível atual."),
        bullet("A vista 3D deixou de mostrar só 06/05/2024: agora mostra qualquer ponto da cidade, com mapa real, no "
               "nível escolhido, usando o novo modelo de água calibrado e validado."),
        bullet("As rotas passaram a usar o nível do cenário em vez de um único dia histórico."),
        bullet("Previsão de 72 h com modelo próprio, validada em 12 meses fora do treino."),
        bullet("Mapa temático dos 94 bairros com limites oficiais (diferencial opcional do enunciado)."),
        bullet("18 testes automatizados (rotas, API, dados espaciais, modelo de água e previsão)."),
        bullet("Este relatório, gerado por <b>scripts/gerar_relatorio_dashboard.py</b>."),

        p("6. Uso de ferramentas de IA", "h1"),
        bullet("<b>Codex</b>, 26/10/2026: apoio na preparação de scripts, notebooks, limpeza, gráficos e relatórios "
               "iniciais (registrado no README)."),
        bullet("<b>Claude Code</b>, 24/11/2026: organização dos commits finais; reorganização da Tela 2 (tempo real, "
               "abas, 3D por ponto); modelo de água e previsão com suas validações; capturas de tela e redação deste "
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

"""Gera os notebooks de preparação e análise exploratória."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
NOTEBOOKS.mkdir(exist_ok=True)


def notebook(name: str, cells: list[tuple[str, str]]) -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(content) if kind == "md" else nbf.v4.new_code_cell(content)
        for kind, content in cells
    ]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    nbf.write(nb, NOTEBOOKS / name)


setup = """from pathlib import Path
import sys
ROOT = Path.cwd()
if ROOT.name == 'notebooks':
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
FIG = ROOT / 'resultados' / 'figuras'
FIG.mkdir(parents=True, exist_ok=True)
"""


notebook("01_limpeza_inct.ipynb", [
    ("md", """# 01 — Preparação e limpeza do INCT SiMAI

**Fonte:** `data.json` fornecido com o enunciado. Esta análise usa apenas essa base.

Objetivo: converter os 71 cenários e 94 bairros em tabela longa, verificar estrutura e coerência, documentar cada correção e salvar os CSVs processados. O cálculo de pessoas afetadas é **estimativa da simulação**, baseada na distribuição uniforme da população entre prédios. O arquivo original fica preservado em `dados/originais`."""),
    ("code", setup + "\nimport pandas as pd\nfrom scripts.preparar_dados import load_inct, clean_inct\nraw = load_inct()\nprint(f'{len(raw)} linhas | {raw.nivel_m.nunique()} níveis | {raw.bairro.nunique()} bairros')\ndisplay(raw.head())"),
    ("md", """## Auditoria antes das correções

O arquivo usa arredondamento **para cima** em `percentage = ceil(100 × affected_buildings / total_buildings)` e `affected_population = ceil(population × percentage / 100)`. Essa convenção é sistemática e não deve ser confundida com erro. Buscamos divergências contra ela e quedas de prédios atingidos quando o nível aumenta."""),
    ("code", """import math
check = raw.copy()
check['percentual_esperado'] = (100 * check.affected_buildings / check.total_buildings).apply(math.ceil)
check['populacao_esperada'] = (check.population * check.percentage / 100).apply(math.ceil)
percent_errors = check[check.percentage.ne(check.percentual_esperado)]
pop_errors = check[check.affected_population.ne(check.populacao_esperada)]
decreases = check[check.groupby('bairro').affected_buildings.diff().lt(0)]
print('Percentuais divergentes:', len(percent_errors))
print('População derivada divergente:', len(pop_errors))
print('Quedas entre níveis sucessivos:', len(decreases))
display(percent_errors[['nivel_m','bairro','affected_buildings','total_buildings','percentage','percentual_esperado']])
display(decreases[['nivel_m','bairro','affected_buildings']])"""),
    ("md", """## Correções rastreáveis

As alterações nas contagens são pontuais: série quase constante do Arquipélago, patamar inicial e pico isolado no Espírito Santo, e zeros entre valores positivos no Centro Histórico, Lageado e Rubem Berta. Os campos derivados são então recalculados. A imputação inicial no Espírito Santo é incerta e está identificada no registro de auditoria."""),
    ("code", """clean, audit, summary = clean_inct()
print(f'{len(clean)} linhas limpas; {len(audit)} alterações de campos')
display(audit.groupby(['bairro','campo']).size().rename('alteracoes').reset_index())
display(audit.head(20))
print('Arquivos salvos em dados/processados/: inct_simai_limpo.csv, auditoria_inct.csv, inct_resumo_por_nivel.csv')"""),
    ("code", """assert not clean.groupby('bairro').affected_buildings.diff().lt(0).any()
assert clean.groupby('nivel_m').bairro.nunique().eq(94).all()
assert clean.affected_buildings.le(clean.total_buildings).all()
print('Validações finais aprovadas.')"""),
])


notebook("02_coleta_limpeza_ana.ipynb", [
    ("md", """# 02 — Coleta e preparação do nível do Guaíba

**Fonte:** ANA, serviço público [DadosHidrometeorologicos](https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL), estação **87450020 — Usina do Gasômetro**, série corrigida para o Marco IBGE 1788A. A [ANA/SGB documenta a série](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).

Recorte: 03/05 a 30/06/2024, Porto Alegre; medições de nível em centímetros convertidas para metros. O script obtém o XML por código e período, guarda o bruto em cache e registra a data de coleta. Esta é uma análise **independente** da simulação do INCT."""),
    ("code", setup + "\nimport pandas as pd\nfrom scripts.preparar_dados import clean_ana\nana, audit = clean_ana()\nprint(f'{len(ana)} horários na grade; {ana.nivel_m.notna().sum()} com nível; {len(audit)} lacunas auditadas')\ndisplay(ana.head())"),
    ("md", """## Qualidade e tratamento

Datas inválidas e duplicatas são removidas se existirem. Níveis ausentes ficam vazios: interpolá-los poderia criar valores artificiais próximos ao pico. Mudanças abruptas são listadas para inspeção, mas não são apagadas automaticamente, pois podem refletir variação real ou ruído de medição."""),
    ("code", """valid = ana.dropna(subset=['nivel_cm']).sort_values('data_hora').copy()
valid['variacao_cm'] = valid.nivel_cm.diff()
print('Registros sem nível:', audit.problema.eq('nível ausente').sum())
print('Horários sem registro:', audit.problema.eq('horário sem registro no XML').sum())
print('Máxima variação absoluta consecutiva (cm):', valid.variacao_cm.abs().max())
display(valid.loc[valid.variacao_cm.abs().nlargest(10).index, ['data_hora','nivel_cm','variacao_cm']])
display(pd.read_csv(ROOT / 'dados/originais/ana_metadados_coleta.csv'))"""),
    ("code", """peak = valid.loc[valid.nivel_m.idxmax()]
print(f'Pico na série: {peak.nivel_m:.2f} m em {peak.data_hora}')
assert ana.estacao_codigo.astype(str).eq('87450020').all()
assert ana.data_hora.is_unique
print('Arquivos salvos em dados/originais/ e dados/processados/.')"""),
])


notebook("03_eda_bases_separadas.ipynb", [
    ("md", """# 03 — Análise exploratória das bases

Oito gráficos comentados, organizados por fonte. Os cinco primeiros descrevem **cenários simulados** pelo INCT SiMAI; os três últimos descrevem **medições observadas** pela ANA. As escalas e os resultados não são usados para validar uma base com a outra.

**Fontes:** `data.json` do INCT SiMAI fornecido no projeto; [Hidro‑Telemetria da ANA](https://www.snirh.gov.br/hidrotelemetria/) (estação 87450020, coleta registrada em `dados/originais/ana_metadados_coleta.csv`)."""),
    ("code", setup + "\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom matplotlib.ticker import FuncFormatter\ninct = pd.read_csv(ROOT / 'dados/processados/inct_simai_limpo.csv')\nsummary = pd.read_csv(ROOT / 'dados/processados/inct_resumo_por_nivel.csv')\nana = pd.read_csv(ROOT / 'dados/processados/ana_guaiba_2024_limpo.csv', parse_dates=['data_hora'])\nplt.rcParams.update({'figure.figsize': (9, 5), 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 10})\nfmt = FuncFormatter(lambda x, p: f'{x:,.0f}'.replace(',', '.'))\ndef save(name):\n    plt.tight_layout(); plt.savefig(FIG / name, dpi=160, bbox_inches='tight'); plt.show()"),
    ("md", "## INCT 1/5 — Pessoas afetadas por nível\nA curva mostra como a estimativa da cidade inteira evolui nos 71 cenários. O pico citado no enunciado, 5,35 m, fica entre os cenários 5,3 e 5,4 m; não há cenário calculado exatamente em 5,35 m."),
    ("code", """fig, ax = plt.subplots()
ax.plot(summary.nivel_m, summary.pessoas_afetadas, color='#2b6c8a')
ax.axvline(5.35, color='#a65a3a', linestyle='--', label='5,35 m (enunciado)')
ax.set(xlabel='Nível do cenário (m)', ylabel='Pessoas afetadas (estimativa)', title='Simulação INCT: pessoas afetadas por nível')
ax.yaxis.set_major_formatter(fmt); ax.legend(); save('01_inct_pessoas_por_nivel.png')"""),
    ("md", "## INCT 2/5 — Prédios afetados por nível\nA contagem após limpeza é não decrescente, como esperado para cenários acumulativos de inundação."),
    ("code", """fig, ax = plt.subplots()
ax.plot(summary.nivel_m, summary.predios_afetados, color='#467b5b')
ax.set(xlabel='Nível do cenário (m)', ylabel='Prédios afetados', title='Simulação INCT: prédios afetados por nível')
ax.yaxis.set_major_formatter(fmt); save('02_inct_predios_por_nivel.png')"""),
    ("md", "## INCT 3/5 — Bairros atingidos por nível\nUm bairro conta como atingido quando há pelo menos um prédio afetado."),
    ("code", """fig, ax = plt.subplots()
ax.step(summary.nivel_m, summary.bairros_atingidos, where='post', color='#5c658b')
ax.set(xlabel='Nível do cenário (m)', ylabel='Bairros atingidos', title='Simulação INCT: bairros atingidos por nível')
save('03_inct_bairros_por_nivel.png')"""),
    ("md", "## INCT 4/5 — Ranking no cenário de 5,3 m\nO ranking usa a população afetada estimada, não pessoas observadas em 2024."),
    ("code", """snap = inct[inct.nivel_m.eq(5.3)].nlargest(12, 'affected_population').sort_values('affected_population')
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(snap.bairro, snap.affected_population, color='#3d7b88')
ax.set(xlabel='Pessoas afetadas (estimativa)', title='Simulação INCT: 12 bairros com mais pessoas afetadas a 5,3 m')
ax.xaxis.set_major_formatter(fmt); save('04_inct_ranking_53.png')"""),
    ("md", "## INCT 5/5 — Distribuição da fração de prédios afetados\nO percentual exato evita esconder pequenas diferenças causadas pelo arredondamento para cima usado no arquivo original."),
    ("code", """fig, ax = plt.subplots()
ax.hist(inct.loc[inct.nivel_m.eq(5.3), 'percentage_exact'], bins=np.arange(0, 105, 5), color='#6f8d7b', edgecolor='white')
ax.set(xlabel='Prédios afetados no bairro (%)', ylabel='Número de bairros', title='Simulação INCT: distribuição dos percentuais a 5,3 m')
save('05_inct_distribuicao_percentual_53.png')"""),
    ("md", "## ANA 1/3 — Série temporal observada\nA linha mostra somente as medições disponíveis. Lacunas são mantidas como lacunas no CSV processado; o gráfico não deve ser lido como previsão."),
    ("code", """fig, ax = plt.subplots()
ax.plot(ana.data_hora, ana.nivel_m, linewidth=0.8, color='#2b6c8a')
ax.set(xlabel='Data (2024)', ylabel='Nível medido (m)', title='ANA: nível do Guaíba no Gasômetro, 03/05 a 30/06/2024')
fig.autofmt_xdate(); save('06_ana_serie_temporal.png')"""),
    ("md", "## ANA 2/3 — Faixa diária de níveis\nMínimos e máximos diários resumem a variação observada sem substituir as medições originais."),
    ("code", """daily = ana.set_index('data_hora').nivel_m.resample('D').agg(['min','max','count'])
fig, ax = plt.subplots()
ax.fill_between(daily.index, daily['min'], daily['max'], alpha=0.25, color='#2b6c8a', label='Mínimo–máximo diário')
ax.plot(daily.index, daily['max'], color='#2b6c8a', linewidth=1, label='Máximo diário')
ax.set(xlabel='Data (2024)', ylabel='Nível medido (m)', title='ANA: faixa diária de nível do Guaíba')
ax.legend(); fig.autofmt_xdate(); save('07_ana_faixa_diaria.png')"""),
    ("md", "## ANA 3/3 — Completude diária\nA contagem de medições com nível mostra os dias com lacunas. Em intervalos de 15 minutos, 96 medições representariam um dia completo; isso é apenas referência de completude, não garantia de periodicidade em todos os registros."),
    ("code", """fig, ax = plt.subplots()
ax.bar(daily.index, daily['count'], width=0.8, color='#8292a8')
ax.axhline(96, color='#a65a3a', linestyle='--', label='96 medições em 24 h (15 min)')
ax.set(xlabel='Data (2024)', ylabel='Medições com nível', title='ANA: completude diária das medições')
ax.legend(); fig.autofmt_xdate(); save('08_ana_completude_diaria.png')"""),
    ("md", """## Síntese para o projeto

- **Tela 1:** a base limpa do INCT permite preencher indicadores, curva e ranking por cenário.
- **Tela 2:** a série observada da ANA permite apresentar a evolução do nível e a qualidade temporal das medições em 2024.
- O resultado do INCT é uma **simulação de exposição**; o resultado da ANA é uma **medição do nível**. As análises aqui permanecem separadas.
- Toda correção de dados está em `dados/processados/auditoria_inct.csv` ou `auditoria_ana.csv`."""),
])

print("Notebooks criados em", NOTEBOOKS)

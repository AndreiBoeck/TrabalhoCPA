# TrabalhoCPA

## Análise de Dados de Enchentes do INCT SiMAI
Em maio de 2024, o Guaíba chegou a 5,35 m na régua emergencial em Porto Alegre; no referencial
readequado da estação da ANA, o pico corresponde a 4,17 m. Para entender o que acontece com a cidade em cenários como esse, o INCT SiMAI
simulou quais prédios de cada bairro ficam alagados conforme o nível do rio sobe de 3,0 m a 10,0 m.
A ferramenta atual: Hoje o INCT mostra o resultado dessa simulação nesta página: Flood - INCT
SiMAI. Ela roda em um servidor próprio, porém sofre de instabilidade e lentidão, o que dificulta que a
informação chegue a quem precisa dela, como a defesa civil, a imprensa e os moradores.
Antes de começar, cada equipe deve explorar a ferramenta atual e anotar o que funciona e o que
atrapalha: o que é difícil de encontrar, o que demora, o que não fica claro. Essas observações são o
ponto de partida do dashboard de vocês e devem aparecer no relatório do dashboard.
O desafio é propor uma alternativa melhor, que responda rapidamente a duas perguntas:
1. Tela 1: se o rio chegar a X metros, quais bairros e quantas pessoas são afetados?
2. Tela 2: o que outras bases de dados sobre enchentes no Rio Grande do Sul acrescentam a
essa resposta?
O trabalho é em equipes de 3 a 5 alunos e percorre o ciclo da disciplina: coleta, preparação, limpeza,
análise exploratória (EDA) e comunicação dos resultados. Por ser um projeto extensionista, o produto
final é entregue ao parceiro e pode ser usado por ele.

## Estado atual

As fases de levantamento, limpeza e análise exploratória estão salvas neste repositório. As duas telas estão em `backend/` e `frontend/`.

- **Tela 1** (`/`): controle deslizante de 3,0 a 10,0 m em passos de 0,1 m, três indicadores, porcentagem de prédios afetados por bairro, curva da população afetada com a marca de 5,35 m e ranking. Usa apenas o JSON limpo do INCT.
- **Tela 2** (`/tela2`): acompanha o nível do Guaíba em tempo real e mostra o que ele alaga. Detalhes abaixo.

Os nomes dos integrantes, a avaliação manual da ferramenta atual do INCT e o link público do dashboard devem ser acrescentados pela equipe. O aviso de limitações em destaque foi retirado da Tela 1 a pedido da equipe, mas é exigido pelo enunciado.

## Executar a aplicação

Na raiz do repositório, use Python 3.9 ou mais recente:

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn backend.main:app --reload
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) (Tela 1) e [http://127.0.0.1:8000/tela2](http://127.0.0.1:8000/tela2) (Tela 2). A documentação da API fica em `/docs`. Execute `python3 -m unittest discover -s tests -v` para os testes.

## Tela 2: o Guaíba agora e o que ele alaga

**Um único cenário para a tela inteira.** Ao abrir, a tela fica **sincronizada com o tempo real**: o nível em uso é a leitura mais recente da estação ANA 87450020, consultada pelo servidor a cada 5 minutos (`GET /api/live`). O usuário pode escolher outro nível no controle, um horário da previsão ou o recorde de 2024; nesse momento a tela passa para **cenário manual** e todos os mapas, indicadores e gráficos mudam juntos. O botão **Voltar ao tempo real** retoma a leitura atual.

**Referencial.** Os níveis são mostrados na régua do Cais Mauá, a mesma escala da Tela 1 e do recorde de 5,35 m. A leitura da ANA está no referencial corrigido (nível médio do mar); a conversão soma 1,18 m, a diferença que a [ANA/SGB documenta](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs) para o pico de 05/05/2024 (5,35 m na régua ↔ 4,17 m).

**Componente de mapas, logo abaixo do nível atual, em três abas:**

1. **Bairros:** os [limites oficiais da Prefeitura](https://prefeitura.poa.br/smpg/observapoa/mapas) coloridos pela porcentagem de prédios afetados na simulação do INCT, no nível do cenário. Abaixo de 3,0 m o INCT não indica prédios afetados. Clicar em um bairro leva o ponto do 3D para lá.
2. **Água no ponto · 3D:** escolha um ponto da cidade no mini mapa. A tela mostra 1,2 km × 1,2 km em volta dele, com o mapa do OpenStreetMap sobre o relevo e a água no nível do cenário. Informa a profundidade no ponto e a partir de que nível da régua a água chega ali (`GET /api/water/point`).
3. **Rotas a pé:** rede de ruas do centro (OpenStreetMap). A profundidade de cada trecho vem do mesmo modelo de água, no nível do cenário; a mancha observada em 06/05/2024 pode ser exibida para comparação (`POST /api/routing/plan` com `level_regua_m`).

**Modelo de água por nível** (`scripts/preparar_modelo_agua.py` → `dados/processados/modelo_agua_poa.npz`). Grade de 20 m sobre Porto Alegre:

- O relevo aberto ([Terrain Tiles, AWS](https://registry.opendata.aws/terrain-tiles/)) inclui prédios e vegetação. Por isso o chão é corrigido com a profundidade do [Copernicus EMSN194](https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products) em 06 e 08/05/2024 (chão = nível da ANA no dia − profundidade) e, fora dessas áreas, com um viés local estimado num raio de 1 km.
- A água entra a partir do lago (*priority flood*): para cada célula guarda-se a menor cota da água que a alcança por células conectadas. Isso supõe que o sistema de proteção deixe a água passar, como em 2024.
- Terra firme não fica abaixo da cota de alerta (2,50 m na régua).
- Validação contra a mancha observada pelo Copernicus, dentro de Porto Alegre (`dados/processados/modelo_agua_validacao.json`): IoU de 0,80 em 06/05 (data usada na calibração), 0,45 em 04/05 e 0,32 em 10/05/2024. A precisão é quase total (≥ 0,99: onde o modelo põe água, havia água), mas o modelo subestima a área porque não representa a água que ficou represada atrás dos diques quando o rio baixou.

**Previsão do nível** (`scripts/preparar_previsao.py` → `dados/processados/modelo_previsao.json`). Para cada horizonte de 6 a 72 h, uma regressão linear prevê a variação do nível a partir da tendência das últimas 6, 24 e 72 h e da distância à média de 30 dias. Foi treinada com a série horária da estação desde 2023 e testada nos 12 meses mais recentes: erro médio de 16 cm em 72 h, contra 17 cm de repetir o último nível. A faixa mostrada cobre 80% dos erros do teste. É um modelo **estatístico experimental**: não usa chuva prevista, vento nem vazão dos rios e não substitui os [boletins do SGB](https://sace.sgb.gov.br/guaiba/), cuja série pública estruturada não foi encontrada.

**Enchente de 2024.** A série ANA de maio e junho de 2024 continua com filtro de período e três gráficos (nível, faixa diária e completude); o cenário em uso aparece como linha de referência. O painel de ligação compara o cenário, a simulação INCT e o recorde de 2024 no mesmo eixo.

**Cálculo de rotas.** Com origem seca, escolhe o caminho seco mais curto. Com origem alagada, minimiza primeiro a maior profundidade atravessada, depois a distância na água e, por fim, o comprimento total; ao alcançar área seca, não volta à água. Trechos sem cota (pontes) não são usados. Sem caminho verificável ou com destino alagado, a tela não recomenda rota. O protótipo é a pé e não indica passagem segura.

Para refazer as bases da Tela 2 por código:

```bash
python3 -m scripts.preparar_bairros
python3 -m scripts.preparar_rotas_2024
python3 -m scripts.preparar_modelo_agua
python3 -m scripts.preparar_previsao
```

Os downloads (Copernicus, blocos de relevo e série mensal da ANA) ficam em `dados/cache/`, fora do Git, para não repetir requisições.

## Como reproduzir

Use Python 3.9 ou mais recente, a partir da raiz do repositório:

```bash
python3 -m pip install -r requirements.txt
python3 -m scripts.preparar_dados
python3 -m scripts.gerar_relatorios
```

Abra os notebooks na ordem `01_limpeza_inct.ipynb`, `02_coleta_limpeza_ana.ipynb` e `03_eda_bases_separadas.ipynb`. Eles já estão executados e têm seus resultados salvos. A origem do INCT está em `dados/originais/inct_simai_data.json`; o XML da ANA também foi guardado, para não repetir a requisição. Use `python3 -m scripts.criar_notebooks` apenas se quiser recriar os notebooks vazios, pois esse comando sobrescreve as saídas das células.

## Arquivos principais

- `dados/originais/`: JSON do INCT, XML bruto da ANA e metadados da coleta.
- `dados/processados/inct_simai_limpo.csv`: uma linha por nível e bairro, com os dados corrigidos.
- `dados/processados/inct_simai_limpo.json`: mesma base limpa, consumida pela Tela 1.
- `dados/processados/auditoria_inct.csv`: valores originais, corrigidos e justificativas.
- `dados/processados/inct_resumo_por_nivel.csv`: indicadores da Tela 1.
- `dados/processados/ana_guaiba_2024_limpo.csv`: série observada da estação 87450020, com lacunas preservadas.
- `dados/processados/auditoria_ana.csv`: registros sem nível e horários sem medição.
- `resultados/figuras/`: oito gráficos da EDA.
- `relatorios/base_dados.pdf` e `relatorios/limpeza_dados.pdf`: entregas das fases 1 e 2.
- `relatorios/dashboard.pdf`: relatório do dashboard (objetivo das telas, visualizações, uso, limitações e mudanças desde a Fase 3), gerado por `python3 -m scripts.gerar_relatorio_dashboard`.
- `relatorios/wireframe.md`: esboço das duas telas.
- `relatorios/checklist_tela2.md`: requisitos, extras e critérios de conclusão da Tela 2.
- `dados/processados/bairros_poa.geojson`: limites oficiais simplificados dos 94 bairros.
- `dados/processados/modelo_agua_poa.npz` e `modelo_agua_validacao.json`: modelo de água por nível e sua validação.
- `dados/processados/modelo_previsao.json`: coeficientes e validação da previsão do nível.
- `backend/`: API das duas telas, modelo de água, previsão e cálculo de rotas.
- `frontend/`: Tela 1 (`index.html`) e Tela 2 (`tela2.html`).

## Fontes e limites

O JSON do INCT SiMAI foi fornecido com o enunciado; a licença de redistribuição ainda precisa ser confirmada com o parceiro. A série do Guaíba veio do [WebService da ANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL), estação 87450020, e a [ANA/SGB documenta seu referencial](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs). A [ANA descreve sua política de dados abertos](https://www.gov.br/ana/pt-br/acesso-a-informacao/dados-abertos). A data da coleta consta no arquivo `dados/originais/ana_metadados_coleta.csv`.

Os resultados do INCT são estimativas de uma simulação; as medições da ANA descrevem o nível em um ponto. As duas análises estão separadas. O serviço legado usado na coleta pode deixar de funcionar, então o XML bruto está incluído para permitir a reprodução sem internet.

## Uso de IA

Codex foi usado em 26/10/2026 para preparar os scripts, notebooks, limpeza, gráficos e relatórios iniciais. Claude Code foi usado em 24/11/2026 para organizar os commits finais, reorganizar a Tela 2 (tempo real, abas, 3D por ponto), criar o modelo de água e a previsão com suas validações e redigir `relatorios/dashboard.pdf`. A equipe deve revisar e conseguir explicar o código e registrar esse uso no fórum da disciplina, conforme o enunciado.

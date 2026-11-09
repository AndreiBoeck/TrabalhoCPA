# Checklist — Tela 2: enchentes no RS e nível observado do Guaíba

## Requisitos obrigatórios do enunciado

- [ ] Usar pelo menos uma base externa obtida por código. Base já disponível no projeto: medições da ANA/SGB, estação Usina do Gasômetro `87450020`, baixadas pelo WebService da ANA. A coleta histórica guardada no repositório cobre 03/05/2024 a 30/06/2024 e foi realizada em **26/10/2026**. Arquivos: `dados/originais/ana_metadados_coleta.csv` e `dados/processados/ana_guaiba_2024_limpo.csv`. [WebService ANA](https://www.ana.gov.br/telemetria1ws/ServiceANA.asmx) · [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/).
- [ ] Mostrar ao menos **três visualizações** da base externa:
  - [ ] Série temporal do nível observado em maio/junho de 2024, com o pico marcado.
  - [ ] Faixa diária de níveis mínimo e máximo, para mostrar a oscilação ao longo do evento.
  - [ ] Completude diária das medições, distinguindo horários com e sem leitura. Não desenhar lacunas como nível zero.
- [ ] Implementar ao menos **um filtro interativo** de período; ele deve atualizar as três visualizações e os indicadores derivados da série observada.
- [ ] Relacionar visualmente a base externa à Tela 1 pelo evento de 2024: um painel combinado deve mostrar a cheia observada e, ao lado, os cenários INCT de 5,3 e 5,4 m. Identificar as duas análises como observação e simulação; validar o referencial usado pelo INCT antes de afirmar equivalência numérica entre os níveis.
- [ ] Exibir junto a **cada visualização e indicador** a fonte com link e a data de coleta ou atualização correspondente. Para a coleta já guardada: 26/10/2026; para leituras futuras, mostrar o horário real da obtenção e o horário da medição.
- [ ] Identificar também o JSON INCT como material fornecido no projeto e registrar sua data de recebimento/coleta, se documentada; não inventar uma data para essa fonte.

## Extras desejados pela equipe

- [ ] Cartão “Nível atual do Guaíba”, obtido automaticamente da estação escolhida. Mostrar **última leitura disponível**, horário da medição, horário da consulta, nome/código da estação e situação de dado ausente ou desatualizado. Fonte prioritária: [ANA Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/) / [WebService ANA](https://www.ana.gov.br/telemetria1ws/ServiceANA.asmx), verificando a continuidade da estação `87450020`; consultar também o [SACE Guaíba](https://sace.sgb.gov.br/guaiba/). A [API da Defesa Civil RS](https://sistemas.defesacivil.rs.gov.br/api-redehidrometeorologica) é uma alternativa, após confirmar que há estação adequada ao Guaíba e seu referencial.
- [ ] Cartão “Maior nível registrado” com valor, data, estação e **referencial**. A ANA registra **5,35 m em 05/05/2024** na régua emergencial; na série readequada da estação `87450020`, o mesmo pico é **4,17 m** em relação ao nível médio do mar. Não misturar os dois valores no mesmo eixo sem conversão e identificação explícitas. [Explicação ANA/SGB](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).
- [ ] Indicadores com leitura rápida: nível atual, data da leitura, máximo de 2024 no referencial escolhido, nível máximo no período filtrado e disponibilidade das medições. Manter unidade e estação visíveis; usar cores apenas como apoio aos rótulos.
- [ ] Mapa 2D de impacto, com legenda, bairros e nível selecionado. Para mostrar **inundação espacial**, obter uma mancha de inundação georreferenciada por nível ou um modelo validado; os totais por bairro do JSON do INCT, sozinhos, não localizam a água dentro de cada bairro.
- [ ] Visualização 3D de uma região selecionável, com relevo e camada de água. Avaliar os [produtos MDE de Porto Alegre do SGB](https://rigeo.sgb.gov.br/items/6b0101c8-ff98-4fbf-aa59-c94779534468) e dados da [Prefeitura de Porto Alegre](https://prefeitura.poa.br/smamus/planejamento-urbano/mapas-digitais). Antes de calcular áreas atingidas, conferir resolução e precisão da elevação, mesmo referencial vertical entre terreno e nível d'água, conexão hidráulica, diques/barreiras e drenagem; validar com uma mancha observada ou modelo hidráulico. Um MDE sozinho permite renderizar o terreno, mas não garante uma simulação fiel da inundação. [Orientação técnica do SGB](https://rigeo.sgb.gov.br/jspui/bitstream/doc/22079/1/nota_tecnica_inundacao_modelagem.pdf).

## Critérios para considerar a Tela 2 pronta

- [ ] O filtro altera todas as visualizações e indicadores ligados ao período.
- [ ] Cada número exibido pode ser rastreado até arquivo, estação, unidade, referencial e data/hora.
- [ ] Leitura atual indisponível aparece como “sem dado recente”, sem reaproveitar silenciosamente o último valor.
- [ ] O pico histórico é rotulado com o referencial da régua correspondente.
- [ ] O mapa e o 3D distinguem claramente dado observado, cenário simulado e representação apenas ilustrativa.
- [ ] A Tela 2 não trata diferenças entre ANA e INCT como erro de uma das bases.

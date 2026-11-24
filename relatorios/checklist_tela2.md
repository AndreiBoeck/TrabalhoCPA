# Checklist — Tela 2: enchentes no RS e nível observado do Guaíba

## Requisitos obrigatórios do enunciado

- [x] Usar pelo menos uma base externa obtida por código. A Tela 2 usa a série ANA/SGB da estação Usina do Gasômetro `87450020`, baixada pelo WebService da ANA, o download automatizado do [Copernicus EMSN194](https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products) e a [API do OpenStreetMap](https://www.openstreetmap.org/api/0.6/map) no cenário histórico de rotas. A coleta ANA guardada no repositório cobre 03/05/2024 a 30/06/2024 e foi realizada em **26/10/2026**. Arquivos: `dados/originais/ana_metadados_coleta.csv` e `dados/processados/ana_guaiba_2024_limpo.csv`. [WebService ANA](https://www.ana.gov.br/telemetria1ws/ServiceANA.asmx) · [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/).
- [x] Mostrar ao menos **três visualizações** da base externa:
  - [x] Série temporal do nível observado em maio/junho de 2024, com o pico marcado.
  - [x] Faixa diária de níveis mínimo e máximo, para mostrar a oscilação ao longo do evento.
  - [x] Completude diária das medições, distinguindo horários com e sem leitura. Não desenhar lacunas como nível zero.
- [x] Implementar ao menos **um filtro interativo** de período; ele atualiza as três visualizações e os indicadores derivados da série observada.
- [x] Relacionar visualmente a base externa à Tela 1 pelo evento de 2024: painel com pico observado ANA e cenários INCT de 5,3 e 5,4 m, identificados como observação e simulação. O referencial INCT ainda não foi equiparado, então a tela não afirma equivalência numérica.
- [x] Exibir junto a cada visualização e indicador implementado a fonte com link e a data de coleta correspondente. Para a coleta ANA guardada: 26/10/2026. A tela de rotas também mostra as fontes Copernicus/OSM e a data da coleta espacial.
- [x] Identificar o JSON INCT como material fornecido no projeto e informar que sua data de recebimento/coleta não foi documentada.

## Extras desejados pela equipe

- [x] Cartão “Nível atual do Guaíba”, obtido automaticamente da estação `87450020`, com **última leitura disponível**, horários da medição e consulta, nome/código, referencial e estado recente/desatualizado/indisponível. A tela mostra “sem dado recente” após 2 h ou falha da consulta. Fonte: [ANA Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/) / [WebService ANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL). O horário da origem não informa fuso; a avaliação de recência usa o relógio local do servidor. [SACE Guaíba](https://sace.sgb.gov.br/guaiba/) e a [API da Defesa Civil RS](https://sistemas.defesacivil.rs.gov.br/api-redehidrometeorologica) permanecem fontes alternativas para avaliar.
- [x] Cartão “Maior nível registrado” com valor, data, estação e **referencial**. A ANA registra **5,35 m em 05/05/2024** na régua emergencial; na série readequada da estação `87450020`, o mesmo pico é **4,17 m** em relação ao nível médio do mar. Os dois valores não são misturados no mesmo eixo. [Explicação ANA/SGB](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).
- [x] Indicadores com leitura rápida: nível atual, data da leitura, máximo de 2024 no referencial escolhido, nível máximo no período filtrado e disponibilidade das medições. Unidade e estação visíveis; cores como apoio aos rótulos.
- [x] Mostrar a mancha georreferenciada **histórica de 06/05/2024** do Copernicus no mapa de rotas, separada dos cenários por nível do INCT.
- [x] Mapa 2D temático por bairro, com legenda e nível selecionável de 3,0 a 10,0 m. Os 94 limites oficiais da [Prefeitura de Porto Alegre](https://prefeitura.poa.br/smpg/observapoa/mapas), coletados em 10/11/2026 por código, foram associados aos 94 bairros do INCT. A cor é a porcentagem de prédios afetados no bairro, não uma mancha de água dentro dele.
- [x] Visualização 3D **histórica exploratória**, com duas regiões selecionáveis, relevo do [Mapzen Terrain Tiles no AWS Open Data](https://registry.opendata.aws/terrain-tiles/) e profundidade modelada de 06/05/2024 do [Copernicus EMSN194](https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products). A tela permite girar, alterar o exagero vertical e ocultar a camada de água. Coleta em 10/11/2026. O [MDE do SGB de Porto Alegre](https://rigeo.sgb.gov.br/items/6b0101c8-ff98-4fbf-aa59-c94779534468) foi avaliado, mas o arquivo ADF dentro do ZIP oficial falhou na verificação CRC e tinha blocos ilegíveis; por isso foi usada outra fonte aberta para a **visualização**.
- [ ] Simulação espacial de alagamento por nível do Guaíba no mapa 2D/3D. Exige manchas ou modelo hidráulico validado e compatibilidade de referenciais, precisão do relevo, conexão hidráulica, diques/barreiras e drenagem. Os totais por bairro do INCT e a sobreposição visual 3D não bastam. [Orientação técnica do SGB](https://rigeo.sgb.gov.br/jspui/bitstream/doc/22079/1/nota_tecnica_inundacao_modelagem.pdf).

### Previsão do nível e bairros potencialmente atingidos

- [ ] Confirmar uma fonte oficial de **níveis previstos** para o Guaíba que permita coleta automática por API ou download. Priorizar o [SACE/SAH Guaíba do SGB](https://sace.sgb.gov.br/guaiba/) e seus [boletins de monitoramento e previsão](https://www.sgb.gov.br/w/boletim-de-alerta-hidrologico-da-bacia-do-guaiba-monitoramento-segue-com-atualizacao-diaria-das-previsoes). Nova verificação em **10/11/2026**: a página SACE respondeu, mas a consulta ao serviço de “último boletim” retornou “Não existe nenhum dado a ser exibido”; não foi confirmada uma série pública estruturada e estável de níveis futuros. A Tela 2 exibe esse estado de indisponibilidade. Antes da integração, confirmar estação, formato, frequência, prazo e condições de publicação.
- [ ] Se não houver série de níveis previstos acessível por código, avaliar um **modelo próprio** com nível observado, chuva prevista na bacia e outras variáveis hidrológicas relevantes. Documentar fonte e data de cada entrada, calibrar com dados históricos e avaliar previsões em períodos não usados no ajuste. Não converter chuva diretamente em metros do Guaíba sem um modelo validado.
- [ ] Oferecer seleção dos próximos **X dias**, limitada ao horizonte realmente disponível e validado. Exibir gráfico com observações e previsões visualmente distintas, data/hora de emissão, atualização e faixa de incerteza quando disponível. Se a previsão estiver ausente ou vencida, informar isso na tela.
- [ ] Para cada dia previsto, relacionar o nível estimado aos cenários de 0,1 m do JSON limpo do INCT e listar os **bairros potencialmente atingidos**, com pessoas e prédios estimados. Confirmar antes que previsão e simulação usam referenciais verticais compatíveis; fora da faixa de 3,0 a 10,0 m ou sem compatibilidade confirmada, não calcular impacto por bairro. Identificar o valor exibido como cenário de simulação associado à previsão, não como inundação observada.
- [ ] Exibir um alerta visual quando o nível previsto alcançar cenários com bairros atingidos: pico e data estimados, bairros envolvidos e fonte da previsão. Considerar a incerteza da previsão ao comunicar o alerta e atualizar a lista quando chegarem novos dados.

### Rotas entre dois pontos conforme o alagamento

- [x] Permitir escolher **origem A e destino B** no mapa e calcular a rota viável mais curta pelas ruas secas no cenário histórico disponível.
- [x] Comparar a rota do cenário histórico com o caminho mais curto na mesma rede **sem alagamento** (hipótese de referência), mostrando o desvio em metros.
- [x] Oferecer exemplos reproduzíveis de desvio e de saída de origem alagada na interface.
- [ ] Acrescentar seleção de modo de deslocamento e cenários de nível do Guaíba quando houver manchas de profundidade compatíveis por nível.
- [x] Obter rede de ruas caminháveis do OpenStreetMap e profundidade modelada por trecho do Copernicus EMSN194 para **06/05/2024**. Fonte, coleta, resolução, unidade e referencial espacial estão registrados em `dados/processados/rotas_centro_2024_05_06.json`. Os totais por bairro do INCT não localizam água em ruas.
- [x] Associar comprimento e profundidade a cada trecho; para origem seca, bloquear qualquer trecho com água ou profundidade desconhecida e calcular o menor caminho restante. Mostrar os trechos com água no mapa.
- [ ] Definir limites de passagem por modo de deslocamento apenas após obter critério técnico apropriado; por enquanto, o protótipo é somente a pé e desvia de toda água estimada quando a origem é seca.
- [x] Se **A estiver em área alagada**, procurar uma saída para a rede seca. Entre saídas possíveis, minimizar a **maior profundidade** depois da origem; em empate, minimizar a distância na água e depois a distância total até B. Após alcançar área seca, não voltar à água. Exibir profundidade crítica e rotular como **menor exposição estimada**, sem afirmar segurança.
- [x] Se B estiver alagado ou não houver caminho verificável, informar isso em vez de traçar rota. Atualizar o resultado quando A ou B mudar.
- [x] Testar ruas secas, desvio, origem alagada, desempate após gargalo profundo, profundidade desconhecida, destino alagado e ausência de rota.
- [ ] Antes de uso público, conferir trechos críticos e condições locais; profundidade estimada não representa correnteza, buracos ou bloqueios temporários.

## Critérios para considerar a Tela 2 pronta

- [x] O filtro altera todas as visualizações e indicadores ligados ao período observado.
- [ ] Cada número exibido pode ser rastreado até arquivo, estação, unidade, referencial e data/hora; falta concluir a rastreabilidade dos recursos futuros.
- [x] Leitura atual indisponível aparece como “sem dado recente”, sem reaproveitar silenciosamente o último valor.
- [x] O pico histórico é rotulado com o referencial da régua correspondente.
- [x] O mapa temático identifica a simulação INCT por bairro, a mancha Copernicus informa a data histórica e o 3D é rotulado como sobreposição ilustrativa, sem equivalência com o nível observado na régua.
- [ ] A previsão informa método ou fonte, prazo, emissão, atualização e incerteza; alertas por bairro só aparecem após conferir a compatibilidade dos referenciais com o INCT.
- [x] No cenário histórico disponível, a rota exibida respeita a rede de ruas e o alagamento espacial; se a origem estiver alagada, o cálculo prioriza a saída de menor profundidade estimada. Sem caminho verificável, a tela não recomenda uma rota.
- [x] A Tela 2 não trata diferenças entre ANA e INCT como erro de uma das bases.

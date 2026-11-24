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

As fases de levantamento, limpeza e análise exploratória inicial estão salvas neste repositório. A primeira versão local da Tela 1 está em `backend/` e `frontend/`. Ela inclui controle deslizante de 3,0 a 10,0 m em passos de 0,1 m, três indicadores, gráfico da porcentagem de prédios afetados por bairro, curva da população afetada com a marca de 5,35 m e ranking. A Tela 2 mostra a série ANA/SGB de 2024 com três gráficos e filtro de período, mapa temático por bairro, relevo 3D histórico exploratório e protótipo de rotas em um cenário histórico. O alerta em destaque sobre as limitações foi retirado da Tela 1 a pedido da equipe. Os nomes dos integrantes, a avaliação manual da ferramenta atual e o link público do dashboard devem ser acrescentados pela equipe.

## Executar a aplicação

Na raiz do repositório, use Python 3.9 ou mais recente:

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn backend.main:app --reload
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). O backend lê `dados/processados/inct_simai_limpo.json`, gerado exclusivamente a partir do JSON do INCT pelo script de limpeza, e expõe os dados em `/api/metadata`, `/api/scenario` e `/api/curve`. O frontend está em `frontend/` e é servido pelo mesmo processo. A Tela 1 não usa os dados da ANA nem outra fonte externa. O mapa é opcional no enunciado e não integra esta versão.

### Mockup das duas telas

Abra [http://127.0.0.1:8000/mockup](http://127.0.0.1:8000/mockup). O arquivo `frontend/mockup.html` reúne a Tela 1 original, sem alterações visuais, e uma nova apresentação da Tela 2. Use a navegação lateral para trocar de tela. Na Tela 2, as abas alternam entre impacto por bairro, rotas do cenário histórico e relevo 3D; o controle do nível e o filtro de datas continuam interativos. O mockup usa os dados e as APIs do próprio projeto. A organização da interface foi inspirada em painéis de monitoramento da [USGS](https://dashboard.waterdata.usgs.gov/app/nwd/en/?aoi=default), [NOAA](https://water.noaa.gov/) e [SGB/SACE](https://sace.sgb.gov.br/).

### Início do cálculo de rotas da Tela 2

O endpoint `POST /api/routing/calculate` recebe uma rede de nós e trechos com comprimento e profundidade estimada da água. Exemplo de corpo:

```json
{
  "origin": "A",
  "destination": "B",
  "nodes": [{"id": "A", "depth_m": 0}, {"id": "B", "depth_m": 0}],
  "edges": [{"source": "A", "target": "B", "length_m": 120, "depth_m": 0, "bidirectional": true}]
}
```

Com origem seca, o cálculo escolhe o caminho seco mais curto. Com origem alagada, minimiza primeiro a maior profundidade atravessada após a origem, depois a distância percorrida na água e, por fim, o comprimento total. Ao alcançar uma área seca, não volta a entrar na água. Trechos com `depth_m: null` não são usados. O endpoint devolve `no_route` quando não há caminho verificável ou o destino está alagado.

O motor está ligado a um protótipo de mapa em [http://127.0.0.1:8000/tela2](http://127.0.0.1:8000/tela2). A Tela 2 também traz três gráficos da série ANA/SGB de maio e junho de 2024, filtro de datas, leitura recente e o recorde em seus dois referenciais. A leitura recente é consultada pelo servidor a cada cinco minutos e só aparece como atual se tiver até duas horas segundo o relógio local; o horário da fonte não informa fuso explícito.

A área do mapa é um recorte do centro de Porto Alegre e o único cenário espacial disponível é **06/05/2024**, com mancha e profundidade modeladas pelo [Copernicus EMSN194](https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products) e ruas do [OpenStreetMap](https://www.openstreetmap.org/copyright). A página escolhe A e B com cliques e usa `POST /api/routing/plan`; o servidor encaixa cada clique no trecho de rua mais próximo (até 25 m). O arquivo preparado está em `dados/processados/rotas_centro_2024_05_06.json`; a data da coleta, as fontes, o sistema de coordenadas e a resolução constam no próprio arquivo. Para refazer a coleta por código, execute `python3 -m scripts.preparar_rotas_2024`. O script também aceita `--source-zip` e `--osm-xml` para usar arquivos já baixados.

O mapa compara a rota de 06/05/2024 com o menor caminho na mesma rede **sem alagamento**. Este segundo caminho é uma hipótese de referência para medir o desvio, não uma medição de outro dia.
Os botões “Exemplo de desvio” e “Origem alagada” carregam pontos dentro do recorte para demonstrar os dois cálculos; também é possível escolher A e B diretamente no mapa.

O mapa é um **protótipo histórico para estudo**, sem condições atuais das vias nem validação local da profundidade. Não usa os níveis do INCT para inferir água em ruas: o JSON do INCT contém totais por bairro e não fornece essas profundidades. Execute `python3 -m unittest discover -s tests -v` para verificar os casos principais.

O mapa temático colore os [limites oficiais dos bairros da Prefeitura](https://prefeitura.poa.br/smpg/observapoa/mapas) pela porcentagem de prédios afetados na simulação INCT. A cor **não** localiza a inundação dentro do bairro. Para reproduzir a camada, execute `python3 -m scripts.preparar_bairros`; o arquivo leve gerado fica em `dados/processados/bairros_poa.geojson`.

A visualização 3D usa relevo do [Mapzen Terrain Tiles no AWS Open Data](https://registry.opendata.aws/terrain-tiles/) e a profundidade modelada do [Copernicus EMSN194](https://riskandrecovery.emergency.copernicus.eu/EMSN194/?section=products) para 06/05/2024. Execute `python3 -m scripts.preparar_relevo_3d` para recriar `dados/processados/relevo_3d_2024_05_06.json`. A sobreposição é **ilustrativa**: as duas fontes não foram integradas em um modelo hidráulico validado, e a cena não usa nem prevê a cota do Guaíba. O [produto MDE do SGB](https://rigeo.sgb.gov.br/items/6b0101c8-ff98-4fbf-aa59-c94779534468) foi avaliado, mas seu ZIP apresentou erro CRC no raster ADF e blocos ilegíveis nesta coleta.

A previsão do nível para os próximos dias ainda depende de uma fonte oficial de níveis futuros coletável por código ou de um modelo próprio validado. O [SGB divulga boletins durante eventos hidrológicos](https://www.sgb.gov.br/w/boletim-de-alerta-hidrologico-da-bacia-do-guaiba-monitoramento-segue-com-atualizacao-diaria-das-previsoes), mas não foi confirmada uma série pública estruturada para alimentar automaticamente alertas por bairro. A Tela 2 não gera esses alertas sem a previsão e a compatibilidade de referencial verificadas.

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
- `relatorios/wireframe.md`: esboço das duas telas.
- `relatorios/checklist_tela2.md`: requisitos, extras e critérios de conclusão da Tela 2.
- `dados/processados/bairros_poa.geojson`: limites oficiais simplificados dos 94 bairros.
- `dados/processados/relevo_3d_2024_05_06.json`: duas malhas históricas de relevo e profundidade para visualização.
- `backend/`: API das duas telas e cálculo de rotas.
- `frontend/`: interfaces locais do INCT e da análise ANA com mapa histórico.

## Fontes e limites

O JSON do INCT SiMAI foi fornecido com o enunciado; a licença de redistribuição ainda precisa ser confirmada com o parceiro. A série do Guaíba veio do [WebService da ANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL), estação 87450020, e a [ANA/SGB documenta seu referencial](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs). A [ANA descreve sua política de dados abertos](https://www.gov.br/ana/pt-br/acesso-a-informacao/dados-abertos). A data da coleta consta no arquivo `dados/originais/ana_metadados_coleta.csv`.

Os resultados do INCT são estimativas de uma simulação; as medições da ANA descrevem o nível em um ponto. As duas análises estão separadas. O serviço legado usado na coleta pode deixar de funcionar, então o XML bruto está incluído para permitir a reprodução sem internet.

## Uso de IA

Codex foi usado em 26/10/2026 para preparar os scripts, notebooks, limpeza, gráficos e relatórios iniciais. A equipe deve revisar e conseguir explicar o código e registrar esse uso no fórum da disciplina, conforme o enunciado.

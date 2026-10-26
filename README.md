# TrabalhoCPA

## Análise de Dados de Enchentes do INCT SiMAI
Em maio de 2024, o Guaíba chegou a 5,35 m em Porto Alegre, a maior marca da história (Jornal do
Comércio). Para entender o que acontece com a cidade em cenários como esse, o INCT SiMAI
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

As fases de levantamento, limpeza e análise exploratória inicial estão salvas neste repositório. O dashboard ainda será construído. Os nomes dos integrantes, a avaliação manual da ferramenta atual e o link público do dashboard devem ser acrescentados pela equipe.

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
- `dados/processados/auditoria_inct.csv`: valores originais, corrigidos e justificativas.
- `dados/processados/inct_resumo_por_nivel.csv`: indicadores da Tela 1.
- `dados/processados/ana_guaiba_2024_limpo.csv`: série observada da estação 87450020, com lacunas preservadas.
- `dados/processados/auditoria_ana.csv`: registros sem nível e horários sem medição.
- `resultados/figuras/`: oito gráficos da EDA.
- `relatorios/base_dados.pdf` e `relatorios/limpeza_dados.pdf`: entregas das fases 1 e 2.
- `relatorios/wireframe.md`: esboço das duas telas.

## Fontes e limites

O JSON do INCT SiMAI foi fornecido com o enunciado; a licença de redistribuição ainda precisa ser confirmada com o parceiro. A série do Guaíba veio do [WebService da ANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx?WSDL), estação 87450020, e a [ANA/SGB documenta seu referencial](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs). A [ANA descreve sua política de dados abertos](https://www.gov.br/ana/pt-br/acesso-a-informacao/dados-abertos). A data da coleta consta no arquivo `dados/originais/ana_metadados_coleta.csv`.

Os resultados do INCT são estimativas de uma simulação; as medições da ANA descrevem o nível em um ponto. As duas análises estão separadas. O serviço legado usado na coleta pode deixar de funcionar, então o XML bruto está incluído para permitir a reprodução sem internet.

## Uso de IA

Codex foi usado em 26/10/2026 para preparar os scripts, notebooks, limpeza, gráficos e relatórios iniciais. A equipe deve revisar e conseguir explicar o código e registrar esse uso no fórum da disciplina, conforme o enunciado.

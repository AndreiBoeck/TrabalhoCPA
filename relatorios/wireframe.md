# Esboço das duas telas

Este arquivo registra a proposta inicial para o dashboard. As análises de INCT e ANA são independentes.

## Tela 1 — Simulação do INCT SiMAI

```text
┌──────────────────────────────────────────────────────────────────┐
│ Simulação de exposição por nível do Guaíba                        │
│ Nível selecionado: [ 3,0 m ─────●──────────────────── 10,0 m ]  │
├──────────────────┬──────────────────┬────────────────────────────┤
│ Pessoas afetadas │ Prédios afetados │ Bairros atingidos          │
├──────────────────────────────┬───────────────────────────────────┤
│ % de prédios por bairro      │ Ranking de bairros afetados       │
├──────────────────────────────┴───────────────────────────────────┤
│ Curva de população estimada por nível; marca em 5,35 m          │
├──────────────────────────────────────────────────────────────────┤
│ Aviso: simulação e estimativa, não contagem oficial.             │
└──────────────────────────────────────────────────────────────────┘
```

Fonte única da tela: `dados/processados/inct_simai_limpo.csv`. O controle usa os 71 níveis de 3,0 a 10,0 m em passos de 0,1 m. O ponto 5,35 m é uma marca visual entre 5,3 e 5,4 m, sem inventar um novo cenário.

## Tela 2 — Nível observado pela ANA em 2024

```text
┌──────────────────────────────────────────────────────────────────┐
│ Evolução observada do Guaíba — Porto Alegre, maio/junho de 2024  │
│ Período: [ 03/05/2024 ──────────── 30/06/2024 ]                 │
├───────────────────────┬──────────────────────────────────────────┤
│ Nível máximo no filtro│ Medições disponíveis / horários previstos│
├───────────────────────┴──────────────────────────────────────────┤
│ Série temporal do nível medido                                    │
├──────────────────────────────┬───────────────────────────────────┤
│ Faixa diária mínimo–máximo    │ Completude diária das medições     │
├──────────────────────────────┴───────────────────────────────────┤
│ Fonte: ANA/SGB, estação 87450020; data de coleta e limitações.  │
└──────────────────────────────────────────────────────────────────┘
```

Fonte da tela: `dados/processados/ana_guaiba_2024_limpo.csv`. O filtro de período atualiza os indicadores e os três gráficos. A ligação temática com a Tela 1 é a enchente de 2024; os valores das duas bases não são comparados como teste de erro.

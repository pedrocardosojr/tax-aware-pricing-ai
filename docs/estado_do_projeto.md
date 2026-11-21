# Estado do projeto — 07/11/2026

Balanço do dia, para quem abrir o repositório e precisar saber onde as coisas
estão. **Apresentação: sábado 28/11.**

## Na main, funcionando

| O quê | Número | Quem |
|---|---|---|
| Base de preços auditada | 215.931 linhas, 33 meses de cobertura | Rodrigo |
| Catálogo com NCM | 37 SKUs, 37/37 achados no SI5, 6 corrigidos à mão | Rodrigo |
| Motor fiscal oficial | RTC 1.5.4 e 1.6.2, 50/50 produtos validados | Pedro |
| MVP de preço | três regimes, dois caminhos de preço | Pedro |
| Tela Streamlit | `app.py` e 11 módulos em `tax_pricing/ui/` | Pedro |

97 testes, pylint 10/10, mypy sem erros em 34 arquivos.

Oito PRs mergeados em 07/11: #1, #3, #4, #5, #6, #7, #9 e #11. A `main` estava
parada desde 29/10 porque a pilha de PRs estava encadeada branch a branch, sem
nenhum apontando para a `main`.

## Entradas do usuário — três, e só três

Grupo e produto, **custo de aquisição bruto** (o total da nota) e **regime**.
Depois, informar o preço praticado ou pedir sugestão de faixa. A margem aparece
somente no output. Nada de meta de margem, alíquota, faturamento ou crédito.

O que o lojista não tem como saber, o sistema deriva e mostra como premissa.

## O regime muda a conta, não o rótulo

| | Regular / Lucro Real e Presumido | Simples |
|---|---|---|
| Crédito do tributo na compra | sim, não cumulativo | não |
| Tributo na venda | somado ao preço | sai de dentro da receita |

Frações de crédito vigentes, premissas demonstrativas versionadas em
`dados/tributos/perfis_demo_mvp.json`: 0 no Simples, 0,18 no Lucro Presumido
(ICMS não cumulativo; PIS/COFINS cumulativos), 0,2725 no Lucro Real (ICMS mais
PIS/COFINS 9,25%).

## Pronto, mas ainda sem PR

- `base-precos` — limpeza com 15.730 observações únicas, 281 duplicatas
  investigadas uma por uma, Sorriso 90 g excluído do EAN do 70 g, Feijão Reserva
  classificado como conflito. IC95% por bootstrap e erro fora da amostra por SKU.
- `eduardo-estatisticas` — `referencia_mercado` com mediana por rede antes dos
  percentis, `historico_referencia` com janela móvel e lacunas preservadas,
  `similares` com índice base 100, índice de preço por rede.
- `expansao-catalogo` — os 13 SKUs que levam o catálogo de 37 para 50.

## O encaixe que falta

A saída de `referencia_mercado` já é quase o contrato que `analyze_mvp` consome:

| Edu devolve | App espera |
|---|---|
| `id_produto` | `ean` |
| `mediana` | `median` |
| `p25` / `p75` | `p25` / `p75` |
| `n_redes` | `network_count` |
| `ultima_obs` | `date` |
| `camada` = observado | `kind` = observed |
| — | `source`, único campo que falta |

O app valida sozinho: EAN tem de bater, data não pode ser futura,
P25 ≤ mediana ≤ P75, mínimo de três redes e no máximo 60 dias de idade. Dado
velho ou com pouca cobertura vira referência histórica, não faixa atual.

## Pesquisa registrada, fora do produto

**Previsão de preço: o baseline ganhou.** Referência do mês anterior 5,00% de
MAPE, Random Forest 5,09%, Ridge 5,35%, em 183 pares SKU/mês. Resultado medido e
honesto; mais dado não muda isso.

**Estimativa para SKU magro: ganhou.** `log(preço) ~ SKU + rede + mês` com Ridge,
avaliado segurando lojas e não linhas. Nos 9 SKUs de baixa precisão o erro cai de
17,00% para 13,00%, ganhando em 8 deles e em 7 de 7 sementes. Onde o SKU já tem
dado suficiente o encolhimento custa 0,22 pp, que é o comportamento esperado de
pooling parcial.

**Ampliação de observações.** Arquivos diários de outubro: +7.546 observações em
46 produtos e 18 datas novas. Mais datas das mesmas lojas não são mais
concorrentes.

## Premissas que precisam ser confirmadas antes da demonstração

- **Substituição tributária.** Os perfis debitam ICMS na venda, e refrigerante e
  cerveja da carteira provavelmente estão em ST, caso em que o varejista não
  debita nem credita. Confirmar por produto e registrar a fonte.
- **Alíquota de ICMS do Paraná.** Os 18% não foram conferidos contra a legislação
  vigente.

Ambas estão marcadas no próprio arquivo de configuração, não só aqui.

## Limites que valem para tudo

O lado Simples é aritmética sobre premissa declarada, não cálculo oficial: o
endpoint `regime-geral` não apura o recolhimento unificado. Alíquotas de 2033 são
ilustrativas. A compatibilidade técnica da classificação não é revisão fiscal. A
referência de mercado não comprova aceitação de preço nem preço ótimo. Margem de
contribuição não é lucro líquido.

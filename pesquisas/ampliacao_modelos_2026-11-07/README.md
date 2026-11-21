# Ampliar a base: resultados dos testes — 07/11/2026

**Para usar os adicionais:** [guia curto para Rodrigo e a IA dele](PARA_RODRIGO.md),
com arquivos para baixar e passos de validação/integração.

**Recomendação:** ampliar os arquivos da própria fonte de Curitiba e combinar
isso com os vínculos por descrição que Rodrigo está revisando. Os dois caminhos
recuperam dados observados. Modelos ficam como camada separada de estimativa.

## O que efetivamente foi medido

| Caminho | Resultado | Situação |
|---|---:|---|
| Reproduzir a limpeza dos 50 códigos escolhidos | 15.739 observações | Reproduzido |
| Acrescentar arquivos de outubro de 2026 | +7.546 observações, 46 produtos | Recorte por código exato, separado para integração |
| Recuperar códigos alternativos por descrição no histórico mensal | +1.204 observações potenciais, 9 produtos | Candidatos; reproduz os vínculos já apontados por Rodrigo |
| Buscar outros códigos por descrição nos arquivos diários de outubro | Nenhum candidato adicional neste teste | Não implica ausência de vínculos em outros meses |
| Estimar referência mensal com regressão/Random Forest | Não superaram a referência do mês anterior neste teste | Experimento, fora do app |

O universo de aproximadamente 52.498 linhas informado na nota do Rodrigo
abrange os grupos, não apenas os 50 SKUs. A comparação deste experimento começa
nas 15.739 observações do recorte por códigos exatos. A base recebida não foi
substituída, e as branches e os módulos de Edu/Rodrigo não foram alterados.

## 1. Mais observações reais: de onde vieram os 7.546

Fonte: [arquivo público Clique Economia no C3SL/UFPR](https://dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia/),
da mesma origem municipal da base atual. [Catálogo oficial da Prefeitura](https://dadosabertos.curitiba.pr.gov.br/conjuntodado/detalhe?chave=245ef1b9-f82a-42ed-a711-1dec4ccd4be1).
O arquivo consolidado do projeto seleciona fotos mensais; o arquivo público
contém datas intermediárias.

Piloto limitado a outubro de 2026: 20 arquivos listados, 19 legíveis e um vazio
(22/10), 11,6 MB de arquivos CSV, 76.655 linhas brutas. Selecionamos os **IDs
exatos dos 50 produtos**, preço regular positivo e finito e data válida.
Não foram usados matching por descrição, novos aliases ou outras cidades nesta
contagem. A origem e o SHA-256 de cada arquivo estão no manifesto.

Chave de repetição reproduzida do método publicado:
`id_produto + id_empresa + endereco_completo + data_pesquisa`.
Preços conflitantes na mesma chave são excluídos. IDs de loja ausentes continuam
na comparação com o endereço; o teste protege contra duplicá-los artificialmente.

**7.881 chaves únicas em outubro − 335 já presentes = 7.546 adicionais.**
Somadas às 15.739 anteriores: **23.285**, aumento de **47,9%**.
Não houve chaves conflitantes neste recorte.

| Cobertura de outubro | Foto mensal anterior | Arquivos adicionais incluídos |
|---|---:|---:|
| Observações | 335 | 7.881 |
| Produtos | 46 | 46 |
| Datas de pesquisa | 1 | 19 |
| Nomes de rede distintos na fonte | 8 | 30 |
| Pares rede/endereço (aproximação de estabelecimentos) | 10 | 73 |

Exemplos: Coca-Cola 2 L ganhou 197 observações; feijão Reserva preto 1 kg, 110.
As quatro cervejas não ganharam observações por código exato neste outubro.

**Frequência importa:** mais observações não significam novos concorrentes ou
amostras independentes. A mesma loja pode repetir o preço em vários dias. Para
posicionamento atual, definir uma janela recente e uma observação por loja;
para histórico, agregar por loja/rede/data antes de comparar períodos. Não
misturar todas as datas como se fossem uma fotografia de concorrentes atual.

O filtro por código também não corrige um código que represente o produto
errado. Como conferência auxiliar, as descrições dos registros adicionados já
aparecem sob esses mesmos códigos no histórico, após normalização de acentos e
pontuação. Isso não substitui uma auditoria de identidade/embalagem.

## 2. IDs errados ou trocados: teste por descrição

Normalização de acentos, caixa, pontuação e penne/pena; ranking TF-IDF de
caracteres de 3 a 5; condições de mesma marca, grupo, quantidade/unidade e
variantes explícitas compatíveis. O score organiza a revisão; não aprova o
vínculo. O código original permanece preservado.

O teste rejeita, por exemplo, macarrão espaguete versus pena, açúcar cristal
versus refinado, Coca-Cola 600 ml versus 2 L, normal versus sem açúcar e leite
pasteurizado versus longa vida. A identidade e a embalagem ainda precisam ser
confirmadas pelo time. A extração não é uma solução geral para descrições com
atributos ausentes, abreviaturas desconhecidas, erros de marca ou multipacks.

No histórico mensal, nove pares código/descrição → catálogo geraram 1.450
registros positivos candidatos; após repetições, 1.243 chaves; descontando 39
chaves já presentes, **1.204 potencialmente adicionais**:

- Refrigerantes sob códigos internos: **599**.
- Cervejas sob códigos internos: **569**.
- Reserva preto 1 kg sob outro EAN: **36**.

Isso **reproduz o levantamento já publicado pelo Rodrigo**, não representa
1.204 descobertas novas além do trabalho dele. Os códigos internos de bebidas
nessa fila aparecem entre janeiro e setembro de 2024; o alias do Reserva vai
até dezembro de 2025. Recuperar isso melhora histórico, não atualidade.

Não apareceram candidatos adicionais por descrição nos arquivos diários de
outubro de 2026 com essas regras. A fila contém somente registros mensais.
Se o time aprovar os nove vínculos, o total combinado potencial é **24.489**
(15.739 + 7.546 + 1.204); esse total **não é uma base homologada**.

## 3. Modelos: resultado honesto e limite do teste

Usada a base mensal original, **sem as novas observações diárias e sem os
aliases candidatos**. Alvo: mediana mensal das medianas por rede, com pelo
menos três redes. Isso é uma referência agregada, não preço individual de loja.

Treino em janela crescente, sempre anterior ao mês previsto. Janeiro–junho
de 2026 para comparar métodos; julho–outubro para avaliação final, com treino
atualizado a cada mês. A escolha e os parâmetros ficaram fixos antes de avaliar
essa janela final. Não houve divisão aleatória, preenchimento usando o futuro
ou seleção de parâmetros com o resultado final.

Entradas: identidade/grupo, três preços anteriores, tendência, tempo e ciclo
mensal. A referência imediatamente anterior precisa estar no mês anterior do
calendário. Os demais lags são observações anteriores e podem ter lacunas.

| Método | Erro percentual médio por SKU (MAPE) | Erro absoluto médio por SKU |
|---|---:|---:|
| Referência do mês anterior | **5,00%** | **R$ 0,64** |
| Random Forest | 5,09% | R$ 0,69 |
| Regressão Ridge | 5,35% | R$ 0,70 |
| Média das três observações anteriores | 5,42% | R$ 0,73 |
| Mediana das três observações anteriores | 5,49% | R$ 0,72 |

Comparação final em **183 pares SKU/mês, 46 produtos**, com os mesmos alvos
para todos os métodos. Cada SKU tem o mesmo peso no resumo. O mês anterior
também venceu na janela de desenvolvimento. A diferença para Random Forest é
pequena; este teste não estabelece superioridade estatística.

O teste exige histórico anterior: **não valida produtos novos, com dados muito
escassos, nem uma extrapolação longa das cervejas**. Também não estima demanda
ou elasticidade: não temos vendas. Regressão logística é para classificação;
para preço numérico usamos regressão. Previsões não podem aumentar a contagem
de observações reais nem a confiança de um gráfico de dispersão observado.

## Próximos passos sugeridos para o time

1. Edu/Rodrigo conferem a fila de nove vínculos com as decisões já tomadas.
2. Ampliar a coleta histórica da própria fonte por janelas de datas, com cache,
   manifesto e a mesma deduplicação; priorizar meses de cobertura fraca e as
   datas antigas dos códigos alternativos. Medir ganho por SKU/data/loja.
3. Definir janela e regra por loja/rede para referência atual. Preservar os
   preços regulares e os outros tipos de preço em camadas separadas.
4. Avaliar de novo a necessidade de modelo após essa expansão. Para poucos
   dados, fazer outro experimento de mascaramento controlado/avaliação por SKU,
   com saída identificada como estimativa e erro medido.

A busca externa não trouxe outra base já integrada. Outras cidades precisam de
compatibilidade de produto, data e localização e devem aparecer como contexto
externo. A prioridade recomendada é a fonte local que já produziu ganho medido.

## Arquivos e reprodução

Validação local: seis testes desta pesquisa e 103 testes existentes passaram.
Pylint: 10/10 nos três scripts e no arquivo de testes, com limite de 79
caracteres. Mypy: quatro arquivos sem erros, com imports sem stubs ignorados.
As verificações cobrem duplicatas, IDs de loja ausentes, conflitos de preço,
variantes incompatíveis, dados publicados e ausência de influência de preços
futuros nas entradas anteriores. Isso não equivale à aprovação dos aliases.

- `daily_summary.json`, `daily_manifest.json`, `daily_coverage_by_sku.csv`:
  contagens por código e rastreabilidade.
- `daily_added_exact_skus.parquet`: somente as 7.546 observações adicionais.
- `description_candidate_pairs.csv`, `description_candidate_quotes.parquet`,
  `description_summary.json`: fila de revisão com código de origem preservado.
- `model_predictions.csv`, `model_metrics_by_sku.csv`, `model_comparison.csv`,
  `model_summary.json`: previsões, erros e protocolo.

Executar na raiz do repositório, em um ambiente separado do app:

```bash
python -m venv .venv-research
source .venv-research/bin/activate
pip install -r pesquisas/ampliacao_modelos_2026-11-07/requirements.txt
python -m scripts.pilot_daily_prices
python -m scripts.pilot_description_prices
python -m scripts.benchmark_price_estimates
python -m unittest discover -s pesquisas/ampliacao_modelos_2026-11-07 -p 'test_*.py' -v
```

O piloto diário exige internet e usa cache temporário. O teste por descrição
reutiliza esses arquivos. Os CSVs brutos não foram incluídos no Git. Os scripts
sobrescrevem apenas os resultados desta pesquisa. Nenhuma expansão ou previsão
foi incorporada automaticamente à base oficial ou ao Streamlit.

Referências dos métodos: [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html),
[Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html),
[TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html).

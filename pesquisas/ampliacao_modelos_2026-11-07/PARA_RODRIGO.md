# Adicional para Rodrigo — validar e aproveitar os preços

Esta é uma entrega complementar. Os arquivos já estão baixados e separados;
a base oficial e os vínculos de produtos não foram alterados.

## O que baixar

- [Dados em Parquet](daily_added_exact_skus.parquet): 7.546 linhas adicionais
  no teste contra o recorte original, prontas para leitura com pandas.
- [Mesmos dados em CSV compactado](daily_added_exact_skus.csv.gz): alternativa
  para ferramentas que não leem Parquet. No GitHub, usar **Download raw file**.
- [Cobertura por produto](daily_coverage_by_sku.csv).
- [Origem e hashes dos arquivos públicos](daily_manifest.json).
- [Candidatos por descrição](description_candidate_pairs.csv): arquivo separado,
  ainda sem aprovação de identidade/embalagem.

Todos estão na branch `research/ampliacao-modelos-20261107`, nesta pasta.
O repositório é privado: a ferramenta/IA precisa ter acesso autenticado ou
receber os arquivos baixados por você.

## O que são as linhas

Preços regulares observados de 46 códigos do catálogo de 50 produtos.
Datas: 02, 05, 06, 07, 08, 09, 13, 14, 15, 16, 19, 20, 21, 23, 26, 27, 28 e
29/10/2026. As quatro cervejas não receberam acréscimos por código neste recorte.
Cada linha representa produto/loja/endereço/data, não um concorrente diferente.

Os 7.546 são adicionais contra a versão original usada no experimento.
**Recalcular o ganho contra a base mais recente de Rodrigo**, que pode já
conter parte dessas observações ou vínculos aprovados.

## Caminho curto para validar e incorporar

1. Ler códigos como texto. Conferir descrição, marca, versão e embalagem;
   código exato não garante identidade. Usar os vínculos já aprovados por Rodrigo.
2. Conferir datas, preços positivos/finitos e origem. Preservar `source_file`
   e o código original, inclusive quando houver um código canônico aprovado.
3. Comparar com a base atual pela chave produto canônico + loja + endereço +
   data. Tratar ID de loja ausente com a regra já adotada; listar conflitos de
   preços antes de decidir qual registro manter.
4. Medir antes/depois: linhas realmente novas, produtos, datas, lojas/redes,
   última observação por SKU e conflitos. Salvar uma nova versão para revisão.
5. Para comparação atual, escolher janela recente e consolidar por loja/rede.
   Não contar vinte datas de uma loja como vinte concorrentes independentes.

**Compatibilidade com o pipeline:** os adicionais têm `source_file` e `date`;
não têm os campos de fotografia mensal `__mes` e `__arq`. Se necessários,
definir explicitamente a adaptação: mês da data real e arquivo de origem,
preservando a diferença entre fotografia mensal e várias coletas no mês.
Conferir essa decisão com o módulo de estatísticas do Edu antes de integrar.

Leitura do CSV, preservando os códigos:

```python
import pandas as pd

dados = pd.read_csv(
    "daily_added_exact_skus.csv.gz",
    dtype={"id_produto": "string", "id_empresa": "string"},
    parse_dates=["date"],
)
```

## Texto para passar à IA que acompanha Rodrigo

Valide a entrega adicional na pasta
`pesquisas/ampliacao_modelos_2026-11-07` da branch
`research/ampliacao-modelos-20261107` do repositório `pedrocardosojr/tax-pricing`.
Comece por este guia, pelo relatório e pelo manifesto. Compare os adicionais
com a nossa versão mais recente da base, aproveitando o mapeamento por descrição
que já desenvolvemos. Preserve os códigos originais e confira marca, versão e
embalagem antes de aplicar um código canônico. Recalcule duplicatas e conflitos
após o mapeamento. Avalie a adaptação de `source_file`/`date` ao contrato do
pipeline, especialmente os campos `__mes`/`__arq` e o peso das múltiplas datas na
estatística. Entregue o diagnóstico antes/depois, as rejeições e uma versão
candidata de integração em branch própria. Mantenha observados e estimativas
separados e preserve a base oficial até a revisão do time.

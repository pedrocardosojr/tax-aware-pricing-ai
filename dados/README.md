# Bases compartilhadas para exploração

## Comece por aqui

- `clique_economia_mensal_2024_2026.parquet`: base consolidada de preços, 215.931 linhas, 34 fotos mensais de jan/2024 a out/2026. Cerca de 1 MB.
- `amostra_precos_500.csv`: primeiras 500 linhas, apenas para inspecionar o formato; não é amostra representativa para análise de mercado.
- `ncm_oficial/ncm_siscomex.json`: download oficial preservado da tabela NCM.
- `ncm_oficial/ncm8_texto_hierarquico.parquet`: 10.516 códigos de oito dígitos, descrição folha e texto hierárquico reconstruído.
- `ncm_oficial/ncm8_texto_hierarquico.csv`: a mesma tabela tratada em CSV para facilitar a inspeção.
- `manifesto.json`: tamanhos e hashes dos três arquivos originais compartilhados.
- [Calculadora da Receita e API local](../docs/api_receita.md)

Estes arquivos públicos de referência são pequenos e foram versionados em `dados/` para acesso do grupo. `raw_data/` continua ignorada para os arquivos locais e volumosos.

## Fontes

Preços: pesquisa Clique Economia, Prefeitura de Curitiba, histórico obtido pelo espelho UFPR/C3SL:
https://dadosabertos.curitiba.pr.gov.br/conjuntodado/detalhe?chave=245ef1b9-f82a-42ed-a711-1dec4ccd4be1
https://dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia/

NCM: Receita Federal / Portal Único Siscomex. Snapshot existente no projeto, documentado como Resolução Gecex 926/2026. Não é atualização automática:
https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/classificacao-fiscal-de-mercadorias/download-ncm-nomenclatura-comum-do-mercosul
https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json

## Como abrir em Python

Na raiz do repositório, com o ambiente do projeto ativo:

```bash
python -m pip install pandas pyarrow
```

```python
import pandas as pd

precos = pd.read_parquet("dados/clique_economia_mensal_2024_2026.parquet")
ncm = pd.read_parquet("dados/ncm_oficial/ncm8_texto_hierarquico.parquet")
print(precos.shape)
print(precos.head())
print(ncm.head())

# O snapshot de preços preserva os campos como texto.
precos["preco_regular"] = pd.to_numeric(precos["preco_regular"], errors="coerce")
precos["data_pesquisa"] = pd.to_datetime(precos["data_pesquisa"], errors="coerce")
```

No CSV de NCM, preservar zeros à esquerda:

```python
ncm_csv = pd.read_csv("dados/ncm_oficial/ncm8_texto_hierarquico.csv", dtype={"ncm": str})
```

## Campos de preços

| Campo | Conteúdo |
|---|---|
| data_pesquisa | Data observada na pesquisa |
| id_empresa | Identificador da empresa na fonte |
| rede | Rede pesquisada |
| endereco_completo | Endereço comercial da loja pesquisada |
| codigo_categoria | Código da categoria na fonte |
| id_produto | Identificador do produto; nem todo identificador é EAN válido |
| descricao | Descrição original do produto |
| preco_regular | Preço regular; usar valores positivos nas referências |
| preco_atacado / preco_atacado_qtd | Preço e quantidade informados para atacado |
| preco_promocao / preco_fidelidade | Preços especiais; zero não significa produto grátis |
| __mes / __arq | Mês do snapshot e arquivo de origem da consolidação |

## Limites para a exploração

- São fotos mensais, não uma série diária contínua.
- A base de preços não traz custo de compra, volume vendido, margem ou NCM validado de cada SKU.
- A tabela NCM não é um relacionamento pronto SKU → NCM. O catálogo selecionável exige classificação e vínculo conferidos pelo grupo.
- Produtos genéricos com indicação de mais barato não equivalem ao mesmo SKU de marca.
- Comparar produto, embalagem, data e cobertura equivalentes. No histórico, verificar meses ausentes.
- Os arquivos foram compartilhados sem alterar o conteúdo dos originais; versões tratadas e amostra estão identificadas separadamente.

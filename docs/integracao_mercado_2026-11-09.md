# Semana até 14/11: primeira integração entregue

**Objetivo da semana:** substituir o recorte de laboratório pelos dados e
estatísticas de Edu/Rodrigo. A primeira fatia está executável nesta proposta;
o aceite do time e as etapas abaixo continuam pendentes.

## 1. Primeira referência na tela — implementado e testado

A limpeza publicada por Rodrigo foi executada sobre a base mensal versionada,
usando os 50 produtos de `dados/catalogo/skus_50.json`. Resultado: **15.730**
observações, incluindo a exclusão dos nove Sorriso 90 g sob o código de 70 g.
Foi executada a função `referencia_mercado` publicada por Edu, sem alterar seus
módulos ou redefinir seu estimador.

| SKU | Janela | Última coleta | Mediana entre redes | Redes | Lojas |
|---|---|---|---:|---:|---:|
| Coca-Cola 2 L | ago–out/2026 | 01/10/2026 | R$ 11,85 | 15 | 28 |
| Sorriso 70 g | ago–out/2026 | 01/10/2026 | R$ 3,39 | 14 | 26 |

A referência por rede não é a mediana entre todas as lojas. Por isso os
R$ 11,85 da Coca não devem ser confundidos com os R$ 11,64 do estudo por loja.
O adaptador preserva o método publicado por Edu para a revisão do grupo.

O app recebe resumo, preços por rede, fonte, janela e cobertura. A janela
aparece separada da última coleta, evitando apresentar três meses como uma
foto de um único dia. Uma pasta de dados configurada nunca volta silenciosamente
ao laboratório se faltar um SKU, histórico ou similares.

**Ainda não incluídos:** adicionais diários de outubro, aliases sob outros
códigos, histórico, similares e intervalos bootstrap. Os arquivos são uma
primeira integração candidata, não uma nova base homologada de 50 produtos.
`cobertura_ok` nesta etapa significa o critério operacional de redes do Edu;
não representa confiança de 95% nem erro de até ±5%.

## Como abrir esta prévia

Na branch desta proposta, com as dependências instaladas conforme o README:

```bash
make team-preview
```

Selecionar Coca-Cola ou Creme dental/Sorriso 70 g, escolher o regime e ajustar
custo/preço. O custo inicial da interface é um exemplo, não custo real do SKU.
O motor RTC precisa estar disponível para uma nova consulta IBS/CBS; se estiver
desligado, a tela mostra a indisponibilidade. A contribuição usa os perfis
demonstrativos já existentes; esta entrega não altera tributos ou créditos.

Os inputs e snapshots estão em `evidencias/integracao_mercado_2026-11-09`.
Eles permitem reproduzir a exportação sem depender de `raw_data/ncm_37.csv`:

```bash
python -m scripts.export_team_market \
  --input evidencias/integracao_mercado_2026-11-09/inputs/7894900027013.json \
  --output-dir /tmp/team-market
TAX_PRICING_MARKET_DIR=/tmp/team-market make app
```

Para gerar novos inputs, no ambiente que contém os módulos da equipe:

```python
ref = referencia_mercado(obs, ean, '2026-10', n_rodadas=3)
sel = obs[obs.id_produto.eq(ean) & obs['__mes'].isin(ref['janela'])]
por_rede = sel.groupby('rede').preco_regular.median().to_dict()
payload = {'reference': ref, 'per_network_brl': por_rede, 'source': origem}
```

`obs` deve ser a camada observada aprovada e `origem` deve identificar as
versões usadas. Se houver várias camadas em `obs`, filtrar a mesma camada
observada também em `sel`. Nunca fornecer preços por rede de outra janela.

## 2. Adicionais de outubro — Edu/Rodrigo, depois integrar no app

- Consolidar as observações mensais e diárias com a limpeza vigente.
- Registrar os aliases aprovados e rejeitados. Reserva continua conflito na
  nota do Rodrigo; não aplicar os antigos 36 candidatos automaticamente.
- Definir o eixo de rodadas e a regra por loja/período. Várias coletas de uma
  loja não devem ganhar peso acidental na referência da janela.
- Gerar resumos pelo método escolhido e recalcular cobertura/precisão usando
  o mesmo estimador que será mostrado. O IC entre lojas não valida por si só
  uma mediana calculada entre redes.

## 3. Histórico e similares — integração conjunta

Conectar os complementos analíticos ao mesmo SKU, fonte e data do resumo.
O contrato atual tem campos de variação pareada e coorte de embalagem/tipo;
o resumo do Edu, sozinho, não preenche esses gráficos. Não inventar variações
ou misturar embalagens para completar a tela. Nesta prévia aparecem as mensagens
de complemento ainda não conectado.

## 4. Pedro — tributação e contribuição em paralelo

Conferir as premissas de ICMS/ST e créditos por produto/regime com fontes
oficiais e registrar versão/data. Manter perfis demonstrativos explícitos.
A validação técnica RTC 50/50 está entregue; não equivale à apuração fiscal
completa. Esta integração não resolve essas premissas.

## 5. Aceite até sábado, 14/11 — os três

Um colega abre a proposta, reproduz o app e confere os dois caminhos, cobertura,
dados antigos/ausentes e os três regimes. Depois incorporar por PRs revisados.
Manter a meta de integração de dados reais até 14/11; reprodução/deploy até
21/11; apresentação em 28/11. O congelamento deve reservar exceção para bugs
que impeçam a demonstração, sem abrir novas funcionalidades.

Pooling continua pesquisa até validar alvo, comparação e desempenho na base
ampliada. O erro agregado de 13% do estudo não é intervalo individual de cada
SKU. Este experimento não bloqueia a entrega principal.

## Evidências

Manifesto com versões de ambos os módulos e hash da base, inputs originais e
JSONs exportados versionados. Primeira execução: fonte mensal, códigos exatos,
sem aliases e sem chamadas RTC reais.

Validação em ambiente temporário limpo: Python 3.12.9, Streamlit 1.65.0,
pandas 3.1.1, Plotly 6.9.0; `make test lint typecheck`: 105 testes aprovados,
pylint 10/10, mypy sem erros. Os testes de tela usam indisponibilidade RTC
simulada e exercitam o Sorriso nos três regimes e nos dois caminhos de preço.

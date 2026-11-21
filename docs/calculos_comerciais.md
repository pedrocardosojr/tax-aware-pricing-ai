# Cálculos comerciais — primeira implementação de 07/11

**MVP vigente:** [inputs mínimos e perfis demonstrativos internos](mvp_inputs_e_outputs.md).
O regime é escolhido pelo usuário. Não há coleta fiscal adicional nem meta
de margem. O indicador é Margem de contribuição, com Tributação estimada e
premissas acessíveis. A personalização completa abaixo fica para evolução.

[Continuação vigente: conexão atualizada e perfil personalizado por parcelas](entrega_tax_2026-11-07.md).
Pedro escolheu coletar dados adicionais para apuração personalizada. Os
exemplos fictícios abaixo continuam como testes da aritmética.

Frente de Pedro, separada da integração RTC. A apresentação dos inputs será
ajustada com Pedro; esta entrega prepara funções reutilizáveis pela tela.

**Decisão vigente de 07/11:** margem somente no output, sem campo de meta
de margem nos dois caminhos. O cálculo inverso de preço descrito abaixo
fica preservado como utilitário interno testado, fora do fluxo da interface.

## O que está implementado

- Custo líquido = custo de aquisição bruto − crédito aproveitável declarado.
- Tributos do cenário = preço de venda × taxa declarada nessa mesma base.
- Despesas variáveis = preço × taxa variável + despesa variável por unidade.
- Contribuição em R$ = preço − custo líquido − tributos − despesas variáveis.
- Margem em % = contribuição / preço de venda × 100. Não é markup nem lucro
  líquido e não desconta despesas fixas da empresa.
- Preço para meta = (custo líquido + despesa variável por unidade) /
  (1 − taxa tributária − taxa de despesa − meta de contribuição).
- Price index = preço / referência comparável × 100. Diferenças em R$ e %
  usam a mesma referência. A identificação da fonte, data, embalagem e
  cobertura acompanha o resultado na integração, ainda a implementar.

As funções estão em `tax_pricing/commercial.py`. Reutilizam a aritmética de
`economics.py`; o protótipo anterior em `pricing.py` permanece preservado.
O novo módulo usa **preço de venda final como denominador**. O antigo usa
receita de referência sem IBS/CBS. Não intercambiar essas bases implicitamente.

## Exemplo reproduzível — valores fictícios

Este exemplo testa matemática, sem selecionar regime nem calcular impostos
reais da Coca-Cola ou de outro produto. A referência de mercado também é
fictícia. A taxa de 10% é uma premissa ilustrativa, não uma alíquota da Receita.

| Componente | Valor |
|---|---:|
| Preço de venda | R$ 10,00 |
| Custo bruto / crédito declarado | R$ 6,00 / R$ 0,00 |
| Tributos hipotéticos, 10% do preço | R$ 1,00 |
| Despesa variável, 5% + R$ 0,50/unidade | R$ 1,00 |
| Contribuição | R$ 2,00 / 20% |
| Preço para meta de 25% | R$ 10,84 |
| Referência fictícia de mercado | R$ 12,00 |
| Price index no preço atual | 83,33 |

R$ 10,84 é o primeiro centavo que atinge a meta neste modelo; R$ 10,83 não
atinge. Valores intermediários mantêm precisão decimal; exibição deve tratar
arredondamentos sem alterar as contas. O modelo não reproduz arredondamento
por documento fiscal nem imposto específico por quantidade.

Reproduzir a partir da raiz:

```sh
make commercial-example
make test
make lint
make typecheck
```

O exemplo gera JSON com rótulos de cenário ilustrativo, apuração fiscal
pendente e referência fictícia. Os nove testes novos verificam reconciliação,
crédito explícito, perdas, preço mínimo em centavos, índice de mercado e
parâmetros inválidos/ausentes. A margem alvo usa fração: 0,25 significa 25%.

## Contrato fiscal e limites desta entrega

As funções exigem taxa e despesas explícitas. Ausência de tributo não vira
zero. Crédito precisa ter elegibilidade estabelecida fora da função e é
descontado uma única vez. Não converter automaticamente o IBS/CBS da venda
em crédito da compra nem somar taxas cujas bases sejam diferentes.

A taxa tributária precisa representar a dedução do cenário na base do preço
escolhida, com fonte, competência e cobertura. O cálculo inverso pressupõe
taxas constantes; regras não lineares ou que mudem com o preço exigem outra
solução. O retorno RTC não foi ligado automaticamente à margem atual.

As três opções de regime permanecem confirmadas para o produto. Esta entrega
não implementa DAS, ICMS, PIS/Cofins ou IRPJ/CSLL e não declara apuração completa
de nenhum regime. Os parâmetros fictícios não habilitam um perfil fiscal real.

## Dados do perfil — preparação para discussão do input

Proposta de contrato interno, não desenho final do formulário. Pedro detalhará
como o usuário informará os dados. O que vier de configuração, catálogo ou
fonte fiscal não precisa virar campo digitável.

| Perfil | Dados/regras a investigar antes de habilitar cálculo real |
|---|---|
| Todos | Competência, UF/operação, atividade, SKU/classificação, fonte e cobertura das parcelas, custo/compra, crédito aproveitável e despesas |
| Simples Nacional | RBT12 e situação de início de atividade, anexo/faixa aplicável, tratamento/segregação da receita, particularidades estaduais e efetiva aplicável |
| Lucro Presumido | Tratamento de cada receita/produto, incidências aplicáveis e bases, particularidades de ICMS/ST e créditos efetivamente cabíveis |
| Lucro Real | Tratamento de cada receita/produto, regime de apuração das contribuições, elegibilidade dos créditos e particularidades estaduais |

Para Simples, o manual oficial usa receita acumulada, anexo/faixa e parcela
a deduzir e distingue tratamentos das receitas; foi atualizado parcialmente
em outubro de 2026 e avisa que a revisão da reforma segue em andamento.
[Perguntas e respostas oficiais, itens 5.3.1, 7.1 e 7.4](https://www8.receita.fazenda.gov.br/SimplesNacional/Arquivos/manual/PerguntaoSN.pdf).

Presumido e Real também não devem ser tratados como nomes equivalentes ao
regime geral do endpoint IBS/CBS. A referência da PGFN distingue os regimes
de renda e seus contextos de PIS/Cofins; regras e exceções do caso precisam
ser conferidas antes de parametrizar a conta.
[Referência oficial da PGFN](https://www.gov.br/pgfn/pt-br/cidadania-tributaria/por-assunto/irpj/lucro-real-lucro-presumido-e-lucro-arbitrado).

As referências foram consultadas em 07/11/2026. A tabela é uma lista de
investigação para implementar os perfis, sem alíquotas presumidas no código.
IRPJ/CSLL e tributos de apuração empresarial exigem definição de escopo antes
de qualquer atribuição ao SKU; a contribuição não se confunde com lucro líquido.

## Próxima entrega

### Continuação em 07/11: perfil ligado à margem

`FiscalProfile`, em `tax_pricing/fiscal_profile.py`, identifica Simples
Nacional, Lucro Presumido ou Lucro Real, competência, taxa na base do preço,
crédito aproveitável, fontes, cobertura e estado da hipótese.
`profile_margin`, em `tax_pricing/profile_calculation.py`, usa esses dados
no cálculo. Quando falta uma parcela ou fonte, retorna margem pendente e
lista os campos ausentes. Zero explícito com origem é diferente de ausência.
Os estados ilustrativo/declarado não certificam revisão fiscal.

O mesmo módulo implementa a fórmula da alíquota efetiva do Simples:
`(RBT12 × alíquota nominal − parcela a deduzir) / RBT12`, com entradas
validadas. A escolha de anexo/faixa e o tratamento da receita continuam
externos à função. Não há tabela fiscal embutida nem apuração de DAS por SKU.
No exemplo fornecido, RBT12 de R$ 360.000, nominal de 7,3% e dedução de
R$ 5.940 resultam em 5,65% antes dos ajustes específicos da receita.
[Regra oficial até 2026, item 5.3.1](https://www8.receita.fazenda.gov.br/SimplesNacional/Arquivos/manual/PerguntaoSN.pdf).

`make profile-example` reproduz os retornos RTC já preservados de arroz e
refrigerante, com base de R$ 30 e IBS/CBS de R$ 0 e R$ 0,30, respectivamente.
Não realiza chamada nova. Ao lado, os três perfis empresariais incompletos
permanecem com margem pendente. Um exemplo separado, explicitamente
ilustrativo, usa a fórmula do Simples e premissas comerciais fictícias para
demonstrar a ligação perfil → margem, sem atribuir essa taxa aos produtos.

Pedro confirmou o input em 07/11: grupo → produto → regime → custo → escolha
entre informar preço praticado ou receber sugestão de corredor. No segundo
caminho, não se informa preço atual. A meta de margem foi removida dos dois
caminhos; margem é resultado. Os dados deste
perfil são um contrato interno; a origem e apresentação dos campos adicionais
podem ser configuração, fonte ou formulário e ainda serão detalhadas.

Implementar os dois caminhos do fluxo confirmado, escolher o primeiro perfil/caso real,
validar suas parcelas e ligar o resultado de mercado de Edu/Rodrigo com data
e cobertura. Depois conectar as funções à árvore de preço no Streamlit.
Pedro é responsável por definir, implementar e testar o tratamento dos três
regimes. O método de formação do corredor segue como próxima definição;
o cálculo atual de preço para meta fica como utilitário interno e não é
oferecido como simulação na interface vigente.
[Plano Tax](plano_tax_perfis_2026.md) · [Fluxo vigente](fluxo_vigente.md).

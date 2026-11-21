# Entrega técnica de tributos e margem — 07/11/2026

**Atualização posterior de escopo:** o MVP usa perfis demonstrativos internos,
sem coleta fiscal adicional. O regime continua obrigatório. Usar os labels
Tributação estimada e Margem de contribuição, com premissas visíveis.
[Recorte vigente](mvp_inputs_e_outputs.md). A apuração personalizada descrita
abaixo foi preservada como backend e pesquisa para evolução.

Pedro escolheu **apuração personalizada, com coleta dos dados fiscais
adicionais necessários**. Os três regimes permanecem no projeto. Margem
aparece somente no output, sem campo de meta no input.

## O que está pronto e testado

| Componente | Resultado |
|---|---|
| Conexão RTC com data/base explícitas | Consulta versão, compatibilidade NCM/classificação e cálculo; confere base, classificação e flag de simulação na resposta |
| Motor anterior, 1.5.4/V0059 | 50/50 produtos aprovados, referência fiscal de 07/11/2026 e base de R$ 30 |
| Pacote oficial novo, 1.6.2/V0066 | 50/50 aprovados; resumos de IBS/CBS iguais aos anteriores nos 50 casos |
| Cálculo personalizado | Parcelas por regime com taxa, base e fonte explícitas; crédito da compra e despesas variáveis |
| Função para a tela | Junta análise personalizada e painel RTC, preservando suas coberturas separadas |
| Verificações | 67 testes aprovados; pylint 10/10; mypy sem erros em 17 arquivos fonte |
| Fluxo completo | Três casos com dados empresariais fictícios e chamadas reais ao RTC, todos aprovados |

Esses resultados comprovam o funcionamento técnico e a aritmética. Não
comprovam o enquadramento fiscal real de cada SKU nem a correção de uma
apuração empresarial sem seus dados e regras.

## Dados necessários à personalização

O perfil pode ser salvo e reutilizado. Os dados adicionais ficam em uma
etapa de configuração; não precisam ocupar a entrada principal de preço.

| Dados | Uso |
|---|---|
| Regime, competência e contexto da operação | Escolher o contrato e a vigência do cenário; Curitiba/PR continua o recorte |
| Parcelas fiscais aplicáveis ao produto, taxa, base e fonte | Calcular a dedução efetiva do cenário, incluindo tratamentos específicos |
| Simples: DAS efetivo do caso; faturamento/anexo/faixa quando for necessário derivá-lo | Evitar assumir 4% para todos; a fórmula já existe, mas seleção de faixa e segregação da receita ainda dependem das regras/dados |
| Presumido/Real: ICMS, PIS e Cofins do caso, incluindo zeros justificados | Contrato mínimo de varejo; as taxas não são escolhidas automaticamente pelo nome do regime |
| Crédito aproveitável na compra e sua origem | Deduzir do custo uma única vez, sem inferir crédito a partir do tributo da venda |
| Despesas variáveis percentuais e por unidade | Completar a contribuição; despesas fixas e lucro líquido têm outro escopo |

A condição de cada produto precisa ser conferida, incluindo substituição
tributária, monofásicos, reduções e demais particularidades. A implementação
recebe componentes cuja aplicabilidade já tenha sido estabelecida; não
substitui essa definição fiscal por uma taxa genérica.

## Contrato do cálculo personalizado

`personalized_margin` exige dados e fontes explícitos. Dados ausentes retornam
pendências e margem vazia. Zero só entra como zero informado e fundamentado.
As bases suportadas são preço de venda e preço menos o ICMS explicitamente
calculado. Taxas e valores intermediários mantêm precisão decimal; não é um
gerador de documento fiscal nem replica arredondamentos por nota.

O contrato exige DAS no perfil Simples; ICMS separado pede indicação de
recolhimento fora do DAS e confirmação de que o componente DAS o exclui.
Nos outros regimes exige ICMS/PIS/Cofins, com tratamentos e zeros informados.
Essas exigências definem o recorte implementado, não uma regra universal
para qualquer empresa ou operação.

`analyze_product` recebe produto, contexto fiscal, perfil e preço. O preço
pode ser praticado ou de cenário do corredor, com origem identificada.
Não pede meta de margem. A base fiscal do RTC é independente do custo de
aquisição e não é deduzida automaticamente dele. Falta de base ou falha na
API deixa o painel RTC pendente/indisponível, sem fabricar imposto zero.

## O que a API do Simples realmente cobriu na consulta

O portal oficial agora oferece API específica do Simples. O contrato exige
alíquotas efetivas de IBS/CBS fornecidas pelo chamador; não escolhe sozinho
a alíquota da empresa a partir do faturamento. Na consulta de 07/11:

- atividades em 07/11/2026: lista vazia;
- consulta filtrada pela classificação 000001 nessa data: HTTP 400 por falta
  de parametrização vigente;
- mesma consulta em 01/01/2027: 15 atividades.

Portanto, essa consulta não habilita a apuração do DAS de 2026 pelo endpoint.
O HTTP 200 da API pode conter itens não calculados, conforme o contrato.
As consultas e o resumo do schema estão preservados em evidências.
[Contrato oficial do Simples](https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api-simples-nacional/api-docs).

O RTC geral calcula IBS/CBS, cuja situação de recolhimento em 2026 deve
considerar as condições oficiais. Seu total não é somado automaticamente ao
DAS ou à carga declarada da empresa.
[Comunicado da Receita](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2025/dezembro/comunicado-conjunto/) ·
[Fórmula e tratamentos do Simples, itens 5.3.1, 7.1 e 7.4](https://www8.receita.fazenda.gov.br/SimplesNacional/Arquivos/manual/PerguntaoSN.pdf).

## Arquivos e reprodução

- `tax_pricing/rtc_service.py`: serviço de IBS/CBS para 2026, com contexto explícito.
- `tax_pricing/personalized_tax.py`: parcelas fiscais e margem personalizada.
- `tax_pricing/product_analysis.py`: contrato integrado para a tela.
- [Nova versão e comparação dos 50](../evidencias/rtc_servico_2026-11-07_atualizado/).
- [Contrato e consultas do Simples](../evidencias/contrato_simples_2026-11-07/).
- [Fluxo integrado, com perfis empresariais sintéticos](../evidencias/fluxo_personalizado_2026-11-07/).

Com o JAR oficial novo em execução na porta 8083, reproduzir em diretórios novos:

```sh
python -m scripts.verify_current_tax --fiscal-date 2026-11-07 --api http://127.0.0.1:8083/api --output /tmp/rtc-nova-execucao
python -m scripts.demo_personalized --api http://127.0.0.1:8083/api --output /tmp/perfis-nova-execucao
make test
make lint
make typecheck
```

`make catalog-integration` preserva o teste histórico com versão e data fixas.
Para o contrato atual, usar o comando acima ou `make current-tax-integration`
com `OUT` e `FISCAL_DATE`; o endereço padrão é a porta 8080.

Os testes anteriores ficam preservados. Os JARs/bancos não entram no GitHub;
obter pelo [portal oficial](https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/calculadora/calculadora-offline).
A nova cópia local fica isolada da versão anterior. Os serviços temporários
usados na verificação são encerrados após a execução.

## O que ainda falta para uso real

Coletar o primeiro perfil real, confirmar tratamentos e créditos por produto,
revisar as regras/dados com o grupo e implementar a coleta no Streamlit.
Preencher fontes no cadastro não certifica validação fiscal. A integração
técnica está pronta nesse recorte; a apuração personalizada só é utilizável
com os componentes reais e completos. Método do corredor e deploy continuam
como entregas separadas.

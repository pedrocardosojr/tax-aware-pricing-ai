# Frente Tax — aprofundamento dos perfis de 2026

**Recorte vigente do MVP:** perfis demonstrativos internos, mantendo o regime
como input e sem coleta fiscal adicional. Usar os labels Tributação estimada
e Margem de contribuição, com premissas acessíveis. A pesquisa de apuração
real abaixo fica para evolução. [Decisão final](mvp_inputs_e_outputs.md).

Responsável pela frente e pela integração com a margem: Pedro.
Atualização de produto em 07/11: a meta de margem foi retirada do input.
O usuário informa preço praticado ou pede sugestão de corredor; a margem
aparece no resultado. Contas inversas já desenvolvidas ficam como utilitários
internos e não representam um campo ou etapa da interface vigente.
Pesquisa e preparação realizadas em 05/11/2026. A entrega técnica da API
permanece concluída. Este documento organiza a próxima etapa fiscal/comercial.

## Material que já está pronto

- [50 fichas de IBS/CBS](../dados/tributos/fichas_rtc_50_2026.csv), com produto,
  NCM, classificação candidata, base do teste, alíquotas, reduções e valores.
- [Mapa dos 14 NCMs](../dados/tributos/mapa_ncm_rtc_2026.csv), para revisar as
  regras por família e identificar os SKUs afetados.
- [Proveniência dos arquivos](../dados/tributos/proveniencia.json), com hash
  do resultado de origem. As fichas foram conferidas contra os 50 resultados.
- [Componente de detalhamento](detalhamento_tributario.md) e as requisições
  e respostas completas da integração.

O lote contém 34 produtos com redução integral, seis com redução de 60% e
dez com tributação integral no cenário declarado. Os valores se referem ao
RTC de regime geral, Curitiba/PR, referência fiscal de 01/10/2026 e base fixa
de R$ 133,34. A revisão dos enquadramentos reais permanece pendente.

## O que muda conforme o perfil

| Perfil ou componente | Cobertura atual | Próximo tratamento |
|---|---|---|
| IBS/CBS do cenário de regime geral | Calculado e testado para os 50 | Conferir enquadramento e distinguir cálculo de recolhimento |
| Empresa do Simples, revenda em 2026 | Perfil e DAS ainda pendentes | Definir faixa, dados da empresa e tratamento da receita |
| Empresa fora do Simples | Só componente IBS/CBS está integrado | Definir incidência de PIS/Cofins, ICMS e particularidades da operação |
| Créditos aproveitáveis na compra | Entrada explícita no protótipo comercial | Definir fonte, elegibilidade e regra do perfil |
| ICMS-ST e situações monofásicas | Identificação e regras ainda pendentes | Revisar os casos da carteira e registrar efeito sobre cada parcela |
| IRPJ/CSLL e outros componentes de apuração empresarial | Convenção comercial a definir | Definir escopo e apresentação antes de atribuir parcelas ao SKU |

O nome do regime da empresa e a modalidade de apuração de IBS/CBS são dados
distintos no contrato do projeto. O perfil deve registrar o que cada cálculo
representa, sua competência, fonte e status de revisão.

## Achados das fontes oficiais

### Simples Nacional

O manual da Receita, atualizado parcialmente em outubro de 2026, descreve a
apuração até 2026 usando receita acumulada nos 12 meses anteriores, anexo/faixa
e parcela a deduzir. A alíquota efetiva depende desses dados. As receitas com
ICMS-ST ou incidência monofásica exigem tratamento específico. Conferir os itens
5.3.1, 7.1 e 7.4. Isso orienta a definição dos dados e das regras do perfil.
[Perguntas e respostas oficiais](https://www8.receita.fazenda.gov.br/SimplesNacional/Arquivos/manual/PerguntaoSN.pdf).

### Ano de teste de IBS/CBS

A Receita prevê dispensa de recolhimento em 2026 mediante condições do
comunicado. O cálculo do motor e a situação de pagamento do contribuinte devem
ficar identificados separadamente no resultado.
[Comunicado oficial](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2025/dezembro/comunicado-conjunto/).

### ICMS no Paraná

A pesquisa da incidência deve usar a regulamentação estadual e a situação da
operação. O portal da Fazenda do Paraná reúne as referências de substituição
tributária. Os efeitos sobre cada produto da carteira ainda precisam ser
conferidos e documentados.
[Fazenda do Paraná](https://www.fazenda.pr.gov.br/Pagina/ICMS-Substituicao-tributaria).

## Entrada confirmada e dados do perfil a definir

Na reunião com a professora de 05/11, relatada por Pedro, foi confirmado o
seletor **Simples Nacional, Lucro Presumido ou Lucro Real**. A decisão substitui
a proposta anterior de apenas regular/Simples. A implementação e a validação
das regras continuam pendentes; o nome escolhido não basta para determinar
todos os tributos. O endpoint de regime geral de IBS/CBS permanece uma camada
distinta do regime da empresa.

A tela tem como direção grupo, produto, regime e custo, seguidos da escolha
entre preço praticado e sugestão de corredor. Minha recomendação é configurar
o perfil da empresa em uma área
própria, deixando-o visível e reutilizando-o nos próximos produtos.

| Informação | Onde será usada |
|---|---|
| Regime e atividade da empresa | Seleção das regras suportadas |
| Competência, UF e tipo de operação | Vigência e contexto dos cálculos |
| Receita dos 12 meses anteriores, quando necessária | Cálculo da faixa/alíquota do Simples |
| Tratamento da receita do produto | Distinção entre situações normais e específicas |
| Taxas/parâmetros revisados e respectivas fontes | Apuração das parcelas do cenário |
| Créditos aproveitáveis e evidência | Conversão do custo bruto em custo líquido |
| Despesas variáveis e base da margem | Composição e interpretação da contribuição |

Se o perfil usar uma taxa efetiva declarada para a demonstração, registrar
quem a definiu, competência, fonte, cobertura e hipóteses. O usuário precisa
conseguir reconhecer esse cenário na tela. A taxa de 4% presente no protótipo
comercial continua sendo uma hipótese de teste, sujeita à validação do perfil.

## Planejamento intermediário de personalização — preservado para evolução

Pedro inicialmente escolheu apuração personalizada com coleta de dados
adicionais. Depois priorizou o MVP com perfis demonstrativos internos,
descrito no início desta página. O recorte personalizado abaixo é uma evolução.
Começar por um caso real de varejo em Curitiba, com parcelas, bases, fontes e
créditos conferidos. Manter os três regimes no contrato e indicar dados
pendentes. Exemplos fictícios servem para testar a conta, sem habilitar a
apuração real de um produto.

[Implementação atual, validação e coleta necessária](https://github.com/pedrocardosojr/tax-pricing/blob/feat/pedro-calculo-comercial/docs/entrega_tax_2026-11-07.md).

Os 50 produtos continuam disponíveis para análise de mercado e para os testes
IBS/CBS. A ficha tributária de cada SKU ajuda a selecionar o primeiro caso e
registrar quais situações podem usar a mesma regra e quais pedem outra revisão.

## Sequência de entregas proposta para Pedro

1. Coletar os dados do primeiro perfil real de empresa e documentar fontes,
   bases e tratamentos. Criar um caso manual de referência para comparação.
2. Revisar o primeiro SKU quanto ao tratamento da receita e da compra no perfil
   escolhido. Registrar fonte, vigência e justificativa na ficha.
3. Configurar as parcelas fiscais aplicáveis ao caso real, com parâmetros
   declarados e revisados. Explicitar cobertura; preservar os exemplos de teste.
4. Conectar custo, preço praticado, tributos e despesas para margem em R$ e %.
   Definir o denominador da margem e conferir a conta pelo caminho inverso.
5. Calcular a margem dos preços de cenário e confrontar os resultados com
   referência/price index de mercado, usando a saída da frente de preços.
6. Ampliar os perfis e casos apenas após conferir os testes e suas fontes.

## Banco de validação para a próxima etapa

| Caso | O que precisa ser demonstrado |
|---|---|
| Perfil informado e completo | Todas as parcelas do recorte têm origem e regra conhecidas |
| Perfil ausente/incompleto | A apuração empresarial fica identificada como pendente |
| Produto com IBS/CBS zero | A redução é exibida junto das demais parcelas do perfil |
| Receita com tratamento específico | A regra escolhida altera somente as parcelas correspondentes |
| Crédito declarado ou indisponível | A origem e o uso são visíveis e a conta evita duplicidade |
| Preço e custo conhecidos | A margem em R$ e % confere com o caso manual |
| Cenários do corredor | A margem de cada preço confere com suas parcelas e premissas |
| Vigência ou perfil diferente | O cálculo exige regra válida para o novo contexto |

Essa preparação antecipa a análise da frente Tax. O módulo completo de apuração
do perfil e sua integração com a margem serão implementados e testados na
próxima etapa. As três opções do seletor estão confirmadas; a implementação
do seletor e da tela Streamlit permanece pendente.

[Divisão e próximos passos após a reunião de 05/11](reuniao_2026-11-05.md).

## Correção do crédito de compra nos perfis demonstrativos — 07/11/2026

Os perfis demonstrativos debitavam tributo não cumulativo na venda e creditavam
zero na compra para o Lucro Presumido, e 0,05 para o Lucro Real. Isso não é
questão de alíquota: é assimetria do modelo. Se o cenário cobra um tributo não
cumulativo na saída, ele tem de creditar o mesmo tributo na entrada, senão a
comparação entre regimes fica estruturalmente enviesada.

Efeito medido com a mediana observada da Coca-Cola 2 L (R$ 11,64, nota de método
de Rodrigo) e custo de R$ 8,00:

| perfil | contribuição antes | contribuição depois |
|---|---:|---:|
| Simples Nacional | 16,33% | 16,33% |
| Lucro Presumido | 0,98% | 13,35% |
| Lucro Real | **−0,17%** | 15,12% |

Na configuração anterior o seletor afirmava que o Lucro Real dá prejuízo ao
vender pelo preço de mercado. Era artefato da premissa, não resultado.

Frações vigentes e sua base, todas premissas demonstrativas versionadas:

| perfil | fração | base |
|---|---:|---|
| Simples Nacional | 0 | optante não se credita de ICMS nem de PIS/COFINS |
| Lucro Presumido | 0,18 | ICMS não cumulativo; PIS/COFINS cumulativos, sem crédito |
| Lucro Real | 0,2725 | ICMS 18% mais PIS/COFINS 1,65% + 7,6% |

Dois testes passam a fixar o comportamento: o crédito tem de existir onde o
regime é não cumulativo e crescer do Presumido para o Real, e nenhum regime
pode produzir contribuição negativa no preço mediano de mercado. Contribuição
negativa na mediana é sinal de premissa errada, não de mercado ruim.

### Duas premissas que continuam a confirmar

**Substituição tributária.** Os perfis debitam ICMS na venda. Refrigerante e
cerveja da carteira costumam estar em ST, caso em que o varejista não debita
ICMS na revenda nem toma o crédito. Confirmar por produto antes da demonstração
e registrar a fonte, conforme a seção de ICMS no Paraná acima.

**Alíquota de ICMS.** Os 18% não foram conferidos contra a legislação vigente do
Paraná. Registrar alíquota, norma e data.

Ambas estão marcadas no próprio `dados/tributos/perfis_demo_mvp.json`, para quem
ler a configuração encontrar o aviso sem depender deste documento.

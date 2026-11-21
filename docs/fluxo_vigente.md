# Fluxo de referência do projeto

[Recorte final do MVP: inputs mínimos, perfis demonstrativos e labels](mvp_inputs_e_outputs.md).

Relato de Pedro em 05/11, com input detalhado em 07/11/2026. Registro para
orientar o grupo e as próximas
sessões de trabalho. Este fluxo atualiza a direção do produto. Os documentos
de reuniões anteriores permanecem como histórico. Os outputs continuam
abertos para discussão e ampliação pelo grupo.

## Objetivo

Dar ao empresário uma visão do produto no mercado e da composição do preço,
com custo de aquisição, tributação estimada no cenário e margem de contribuição.
Mostrar a margem resultante no preço praticado ou nos cenários do corredor.

## Caminho do usuário

1. Escolher um grupo de produtos, por exemplo refrigerantes.
2. Escolher o SKU e a apresentação, por exemplo Coca-Cola de dois litros.
3. Selecionar o regime da empresa: Simples Nacional, Lucro Presumido ou
   Lucro Real.
4. Informar o custo de aquisição do produto.
5. Escolher um dos dois caminhos abaixo.

### Já vendo esse produto

O usuário informa o preço praticado para o consumidor final. A ferramenta
apresenta árvore de preço e Margem de contribuição com Tributação estimada e
despesas configuradas, posicionamento frente aos concorrentes e visão dos
similares. O perfil é demonstrativo, com premissas acessíveis no resultado.

### Ainda não tenho preço; quero uma sugestão

O usuário não informa preço atual nesse caminho.
A ferramenta deverá propor um corredor de preço e mostrar como seus valores
se posicionam frente aos concorrentes. Em cada preço de cenário, calcular
a margem quando houver perfil fiscal e despesas suficientes.

O método do corredor ainda será definido e testado: distinguir a faixa
observada do mercado da viabilidade comercial pelo custo/tributos. Não há
regra de otimização ou recomendação de preço já validada por esta decisão.
Se faltar base suficiente, mostrar essa limitação em vez de inventar faixa.

**Decisão posterior de Pedro em 07/11:** retirar a meta de margem do input
nos dois caminhos. Margem passa a ser resultado, sem campo de meta ou
simulação que peça margem desejada ao usuário. Isso substitui a decisão
anterior de oferecer uma meta opcional.
Os dados adicionais do perfil podem vir de configuração, fonte ou campos
condicionais; a apresentação desses detalhes ainda será ajustada com Pedro.

## Proposta inicial de outputs

- Posicionamento do SKU selecionado nas redes da base de preços.
- Visão do grupo de similares para comparar marcas e produtos comparáveis.
- Dispersão e visualizações a discutir, incluindo tabela ou heatmap.
- Árvore de preço com componentes e premissas visíveis.
- Margem de contribuição no preço usado no cálculo.
- Margem estimada nos preços de cenário do corredor, quando o perfil permitir.
- Corredor sugerido e posicionamento dos cenários para quem ainda não tem preço,
  condicionado à definição e validação do método.

A lista acima registra a direção inicial. O grupo ainda vai escolher os
outputs da primeira versão e pode acrescentar informações. Gráficos, métricas
e recomendações adicionais dependem dessa discussão e dos dados disponíveis.

## Perfil tributário e detalhamento aprovado

**Decisão posterior e vigente de Pedro em 07/11:** simplificar o MVP com
perfis fiscais demonstrativos internos. O regime segue obrigatório e muda
as parcelas da conta. Não pedir dados fiscais adicionais ao usuário nesta
versão. A personalização real fica para evolução; os resultados identificam
Tributação estimada e Margem de contribuição com suas premissas.
[Mapa do que é informado, calculado e assumido](mvp_inputs_e_outputs.md).

O regime da empresa é uma entrada confirmada, com Simples Nacional, Lucro
Presumido e Lucro Real. Os dados adicionais e as regras de cada perfil ainda
serão definidos e validados. O seletor não garante apuração completa apenas
pelo nome do regime; perfis sem regra validada terão cobertura pendente
identificada. O regime da empresa é distinto do regime geral de IBS/CBS do
endpoint testado. A camada de tributos mostrará alíquotas de referência,
reduções, alíquotas efetivas e valores de IBS/CBS, com a cobertura da apuração
e as informações ainda necessárias ao perfil.
[Contrato e teste comparativo](detalhamento_tributario.md).

## Decisões para detalhar na etapa comercial

- Preço de venda praticado informado pelo usuário para calcular a margem
  atual. Quando houver preço de cenário ou de referência, a interface deverá
  identificar essa origem.
- Base e convenção da margem, despesas e eventuais créditos aplicáveis.
- Perfil tributário e dados necessários para representar o usuário.
- Critérios para formar grupos de similares, embalagem e unidade comparável.
- Fórmula e referência do price index, hierarquia dos outputs e mensagens
  para dados ausentes ou cobertura antiga.

Esses detalhes serão tratados nas próximas atividades, preservando o fluxo
que Pedro descreveu. A aprovação técnica das chamadas ao motor RTC cobre a
integração de IBS/CBS do cenário configurado. O vínculo entre custo, preço e
margem será validado na implementação comercial separada.

## Divisão de trabalho vigente

Pedro executou os testes tributários dos 50 produtos no cenário de 2026.
A partir de sábado, 07/11, e na semana seguinte, Edu e Rodrigo concentram-se
na normalização, identificação e recuperação de registros utilizáveis dos
grupos escolhidos. Avaliam a sugestão da professora de estimar preços de SKUs
com poucos dados, com experimento e avaliação próprios. Preços observados e
estimados permanecem identificados separadamente.

Pedro aprofunda os perfis tributários, valida margem e price index na entrega
comercial separada e, em seguida, conduz Streamlit e organização dos outputs.
Pedro confirmou em 07/11 que **definir, implementar e testar o tratamento dos
três regimes é parte da sua responsabilidade**, incluindo dados necessários,
fontes, cobertura e integração com a margem. O seletor por si só não conclui
essa entrega. Edu e Rodrigo continuam na frente de preços.
O grupo começa a escolher os outputs em 07/11. A tela integrada permanece
pendente. [Decisões da reunião e critérios de entrega](reuniao_2026-11-05.md).

Plano de trabalho
Discussão dos outputs e similares
[Método dos testes tributários](metodo_teste_rtc_2026.md)

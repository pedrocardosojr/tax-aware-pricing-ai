# Pesquisa de novas camadas de Data Science e IA

Status: possibilidades discutidas com Pedro, ainda sem escolha final do grupo, implementação ou novas medições. Esta pesquisa não bloqueia o app com catálogo selecionável.

## Direção confirmada por Pedro

O projeto já foi aprovado. O trabalho agora é explorar o que faz sentido com o grupo e mostrar a evolução ao professor para feedback, sem tratar nova aprovação como condição para avançar.

Mantém-se categoria → produto → embalagem, custo numérico e meta de margem opcional. NCM pode ser sugerido com IA nos bastidores de preparação/ampliação do catálogo, com revisão, sem introduzir interrogatório fiscal obrigatório no fluxo do usuário. O argumento de ARGUMENTO_DS.md é uma proposta de enquadramento da pesquisa anterior, não uma arquitetura obrigatória. Reescrita manual não mede o desempenho de um LLM.

## Data Science: tornar os dados úteis à decisão

| Possibilidade | Resultado para o usuário | Como começar |
|---|---|---|
| Posicionamento | Distância percentual do preço informado para a mediana e posição entre comparáveis | Mesmo SKU/embalagem/data, com cobertura explícita e peso por rede |
| Dispersão | Mostrar se os preços observados estão concentrados ou espalhados | Percentis e amplitude interquartil; distinguir de incerteza da estimativa |
| Evolução | Variação histórica e períodos de mudança | Série mensal de composição comparável, preservando lacunas; não confundir mudança de lojas com mudança de preço |
| Preços atípicos | Sinalizar observações para revisão | Regra estatística simples e conferência dos alertas; não descartar promoção verdadeira automaticamente |
| Referência estimada | Estimativa quando há poucos comparáveis | Experimento de regressão versus referência simples, com erro em dados retidos; não apresentar como preço observado |

As primeiras análises são estatística descritiva aplicada; não precisam ser chamadas de IA ou modelo preditivo. Nenhum indicador de preço comprova elasticidade, aceitação pelo consumidor ou preço ótimo.

Se houver experimento de estimativa, começar por um baseline simples, separar treino e teste de acordo com a pergunta e controlar vazamento por produto/data. Um teste de futuro precisa respeitar a ordem temporal. Avaliar erro e cobertura antes de colocar o resultado no app.

Referências metodológicas:
- https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyRegressor.html
- https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

## IA: apoiar preparação e comunicação

- Relacionar ofertas da internet ao catálogo por marca, volume, embalagem e quantidade.
- Explicar os números já calculados em linguagem do varejista, sem inventar valores ou recomendações fiscais.
- Sugerir NCM para novos produtos nos bastidores, com revisão antes de liberar no app.

Explicação deve ser avaliada por fidelidade dos números, respeito às premissas e utilidade para o usuário. Não depende de provar ganho no benchmark NCM para ter valor de produto.

## Preços na internet: candidatos de pesquisa

- [Armazém da Maria, Curitiba](https://www.armazemdamaria.com.br/loja-1/cervejas-2096): catálogo consultado com marca, embalagem e ofertas de clube.
- [Konvém, Curitiba](https://www.konvem.com.br/collections/cervejas-e-chopp): bebidas com condições por quantidade e produtos gelados/delivery.
- [Condor, Curitiba](https://institucional.condor.com.br/ofertas/cidade/ofertas-curitiba): ofertas com validade; a página distingue preço físico de compra online.

As páginas foram consultadas na pesquisa; coleta automática, condições de reutilização, estabilidade e cobertura do nosso catálogo ainda não foram validadas. Preços encontrados em snippets de busca não foram adotados como uma nova base auditada.

Registrar fonte, data de consulta, loja/localidade, canal, marca, embalagem, quantidade, preço regular/promocional/clube, disponibilidade e condições de compra. Não misturar essas condições silenciosamente na referência municipal.

Páginas novas não fornecem automaticamente 12 meses de histórico. Manter o histórico existente como fonte própria e identificar as observações online separadamente.

## Primeiro recorte proposto

1. Escolher 5 SKUs e 2–3 fontes para conferir cobertura, comparabilidade e esforço de atualização.
2. Produzir posicionamento, dispersão e evolução com a base existente para esse recorte.
3. Testar explicações de IA em alguns cenários já calculados e conferir fidelidade/utilidade.
4. O grupo escolhe o que entra na primeira entrega; responsáveis e prazos ainda a combinar.

Preços atípicos, referência estimada e expansão do catálogo ficam como opções para avaliar depois. Sem novas medições executadas nesta atualização.

## Acompanhamento

Cartão único de discussão no Trello.
Trello curto e visual; detalhes e fontes nesta documentação. Mensagem de WhatsApp apenas redigida para Pedro adaptar e enviar; nenhum envio realizado pelo assistente.

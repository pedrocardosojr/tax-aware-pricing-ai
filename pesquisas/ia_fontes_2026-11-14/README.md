# Piloto de busca de fontes para o assistente de preços

A etapa de recuperação usa TF-IDF e similaridade de cosseno para buscar em
cinco trechos curados, com links para os arquivos versionados que os sustentam.
O gabarito tem quinze perguntas. Mede-se a primeira fonte recuperada e a
capacidade de devolver uma busca vazia quando falta evidência.

## Reproduzir

Com as dependências do projeto, instale a dependência opcional desta pesquisa
(`scikit-learn==1.7.2`). Na raiz do repositório:

```sh
python pesquisas/ia_fontes_2026-11-14/avaliar_busca.py
```

Resultado exploratório no próprio conjunto de construção: **10/11 fontes
corretas e 3/4 recusas corretas**. A busca rejeitou uma pergunta válida sobre
consolidar coletas por endereço e sugeriu uma fonte indevida para uma pergunta
sobre a alíquota da própria empresa. O limiar de similaridade, por si só, não
separa esses dois casos. Próximo teste: delimitar o escopo das perguntas e
verificar fontes em paráfrases novas, reservadas para avaliação.

O ensaio mede recuperação. A geração de respostas com as fontes e a comparação
das três versões do assistente ficam para o teste com o modelo configurado.

## Primeira chamada autenticada do piloto atual

Configure a chave e o modelo nos Secrets do Streamlit ou nas variáveis de
ambiente. Na raiz do repositório, execute `python -m scripts.smoke_explanation`.
O comando faz uma única chamada para Coca-Cola 2 L no Simples Nacional, com
custo de R$ 7,00 e venda de R$ 12,00. Reporta latência, aceite ou fallback e
texto exibido. O custo por chamada ainda depende da coleta do uso de tokens.

## Segunda rodada (14/11): busca no módulo do app

A busca virou `tax_pricing/source_search.py`, com o acervo em `tax_pricing/fontes_ia.json`
(sete trechos com link fixo no commit). `find_sources(pergunta)` devolve até dois
trechos com link, ou uma recusa com o motivo. Mudanças:

- TF-IDF em palavras e em fragmentos de 4 a 5 letras, para aceitar variações como
  "consolidam" e "consolidar".
- Vocabulário do lojista em cada fonte (campo `terms`), por exemplo "vender a mais" e
  "desconto" no simulador.
- Recusa por escopo antes da busca: preço, promoção ou estoque em tempo real; imposto
  da própria empresa (a tributação usa perfis demonstrativos); pergunta sobre data futura.
- Pelo menos uma palavra em comum com a fonte; fragmentos sozinhos não bastam.
- Duas fontes novas: premissas da tributação estimada e o validador da explicação.
- `build_messages` monta o pedido ao modelo só com os fatos calculados e os trechos;
  `citations_are_valid` recusa resposta sem citação ou com fonte não recuperada.

| Conjunto | Uso | Fontes certas | Recusas certas |
|---|---|---|---|
| `perguntas.json` (17) | ajuste | 13/13 | 4/4 |
| `perguntas_reservadas.json` (16) | antes do ajuste: 7/11 e 3/5; depois virou ajuste | 10/11 | 5/5 |
| `perguntas_reservadas_2.json` (15) | rodado uma vez, depois do ajuste | **10/11** | **3/4** |

Limiar 0,12, escolhido só nos conjuntos de ajuste. Resultados em
`evidencias/ia_fontes_2026-11-14/`.

**Limites.** O conjunto reservado 2 foi escrito antes do ajuste, mas pela mesma pessoa
que fez o ajuste; não é totalmente cego. A avaliação final deve usar perguntas escritas
por outra pessoa. Erros que ficaram: "com o diário a referência ficou mais precisa?"
foi para a fonte errada, e uma pergunta sobre futebol em Curitiba não foi recusada
(o nome da cidade está no acervo). A geração da resposta com o modelo e a comparação
das três versões dependem da chave configurada.

## Avaliação com perguntas do grupo (14/11)

Oito perguntas escritas pelo Pedro sem ver o acervo, com gabarito fixado e versionado
antes da execução (`perguntas_grupo.json`, várias respostas aceitas quando faz sentido).
Rodado uma vez: **6/8**. Erros:

- "Esses números são confiáveis? De onde vêm?" foi para o validador da explicação
  ("confiar" está no vocabulário dele); o esperado era a origem dos preços.
- "Se eu fizer uma promocação vai valer a pena?" ficou sem evidência: "promoção" não
  está no vocabulário do simulador e a grafia veio com erro.

Acertou as três recusas (sazonalidade, datas comemorativas e o momento de pagar o
imposto) e as perguntas sobre quantidade de lojas, troca de regime e margem.

## Sazonalidade (14/11)

Pergunta do lojista: "nessa época faz sentido focar nesse SKU ou fazer promoção?". O app não
tem dado de vendas da loja, então a resposta é **sugestão com fonte**, sem previsão. Cinco
trechos novos no acervo (`id` começando com `saz_`, campo `external`), com cópia dos dados
em `dados/externo/`:

- **IBGE, PMC, tabela 8882**, volume de hiper e supermercados no Paraná, 2022 a 2025:
  dezembro 21% acima da média do ano (18% a 25%), novembro 3% acima; fevereiro 8% abaixo,
  junho 6% abaixo, janeiro 5% abaixo.
- **INMET, normais 1991–2020, estação 83842 Curitiba**: média de 21,3 °C em janeiro e
  13,8 °C em julho.
- **ABRAS (release de 2022)**: Páscoa, Dia das Mães e Natal são as datas de maior impacto.
- **SuperVarejo (25/01/2024)**: semana do Natal de 2023, refrigerante +28,9% e cerveja
  +23,3% (não diz se é volume ou faturamento).
- **SuperVarejo com dados da Scanntech (31/07/2026)**: Dia dos Pais de 2025, em volume,
  pão de alho +7,2%, carne bovina +6,2%, cerveja +4,4%.

Não encontramos fonte de vendas de café e leite no inverno; o app não afirma isso.
O pedido ao modelo manda apresentar esses trechos como sugestão do setor, nunca como
previsão para a loja. Recusa de data futura passou a exigir pedido de número ("quanto",
"preço", "vai custar"), para aceitar "faz sentido promoção em dezembro?".

Efeito nos conjuntos: iguais, exceto "quais marcas vendem mais no Natal?", que era
recusada e agora traz os dados do setor (mudança de escopo, não erro). As perguntas de
sazonalidade do grupo, antes recusadas, agora encontram Dia dos Pais e IBGE. Uma
avaliação justa do T6 precisa de perguntas novas do grupo.

## Calendário do varejo (14/11)

`dados/externo/calendario_varejo_2026_2027.csv` traz 42 eventos de 2026 e 2027: Carnaval,
Páscoa, Dia das Mães, Dia dos Namorados, festas juninas, Dia dos Pais, Dia das Crianças,
Black Friday, Natal e Ano Novo, mais os feriados nacionais e os de Curitiba. Datas móveis
calculadas pela regra da Páscoa. Cada evento aponta para um trecho do acervo com link, e a
coluna `grupos_do_catalogo` só lista um grupo quando a fonte o cita (por exemplo, Black
Friday cita óleo e café; Carnaval cita água, refrigerante e cerveja).

`tax_pricing.seasonal_calendar.upcoming(hoje, grupo, dias)` lista as próximas datas e marca
as que citam o produto; `sector_month(mes)` devolve o desvio do IBGE para o gráfico.

Cada número do acervo foi conferido na matéria original. A busca na web atribuía à Black
Friday de 2024 "leite 13%, cerveja 12%"; a matéria não traz esses números e eles ficaram
de fora. Datas sem produto do catálogo (Páscoa, Dia das Mães, Namorados, juninas,
Crianças) entram com o que a fonte diz, sem inventar efeito no produto.

## T4: geração com o modelo, três versões (14/11)

`python pesquisas/ia_fontes_2026-11-14/avaliar_geracao.py reservado2|grupo`, cenário Coca-Cola 2 L no Simples (custo R$ 7,00, preço R$ 12,00), modelo `gemini-flash-lite-latest` no plano gratuito, com pausa entre chamadas.

Versões: (a) resposta atual do app, sem modelo; (b) modelo só com os fatos calculados; (c) modelo com os fatos e os trechos da busca.

| Conjunto | Versão | Números do cálculo | Fonte certa citada | Recusa certa |
|---|---|---|---|---|
| reservado 2 (15) | (a) app | por construção | não cita fonte; 8 de 11 sem resposta útil | 4/4 |
| reservado 2 (15) | (b) só dados | 15/15 | 0/11 | 4/4 |
| reservado 2 (15) | (c) dados e trechos | 15/15 | **10/11** | **4/4** |
| grupo (8) | (c) dados e trechos | 8/8 | 3/6 pelo gabarito original | 1/2 |

- Rodada 1 do reservado 2: 5/11 porque o modelo marcava os fatos com colchetes, como `[contribution]`, e a checagem de citação recusava. A instrução passou a proibir isso e a checagem passou a ignorar esses nomes (`FACT_TAGS`); a tela remove as marcas com `strip_fact_tags`. Com a checagem nova, a rodada 1 também dá 10/11. A rodada 2 não é cega: veio depois da correção.
- O erro que sobra no reservado 2 é da busca ("Com o diário a referência ficou mais precisa?" recupera `disponibilidade`), e o modelo respondeu que não há evidência em vez de inventar.
- No grupo, o gabarito foi escrito antes da sazonalidade. A pergunta de Dia dos Pais e Natal e a de comportamento do consumidor agora recebem fontes do setor (`saz_*`), que é o comportamento pedido depois; contando isso, 4/6. Os erros restantes são da busca: "confiáveis? de onde vêm?" vai para o validador e "promocação", com erro de grafia, não encontra evidência.
- **Critério do T4 atendido pela versão (c):** não perde fidelidade ao cálculo, acerta a fonte em 10/11 e recusa o que está fora do acervo. Evidências em `evidencias/ia_fontes_2026-11-14/geracao_*.json`.

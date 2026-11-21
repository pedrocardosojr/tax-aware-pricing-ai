# Referências técnicas anteriores à implementação

Registro dos experimentos anteriores do projeto, preservado ao simplificar o Trello em 27/10/2026. Não representa implementação concluída do app nem aprovação das escolhas abertas do grupo.

## ✅ Convenção de cálculo comercial definida e testada (provisória)

**Feito antes da formação do grupo, mas segue PROVISÓRIA** — o grupo pode mudar.

## A convenção
Custo líquido dos créditos efetivamente aproveitáveis. Despesas variáveis e margem de contribuição calculadas **sobre a receita sem IBS/CBS**.

Sendo **B** a receita sem IBS/CBS, **C** o custo líquido, **d** a fração de despesas variáveis e **m** a margem-meta:

- Receita requerida: `B = C / (1 - d - m)`
- Preço ao consumidor: `P = B + T(B)`, com **T** devolvido pelo motor oficial
- Margem realizada: `(B - C - d*B) / B`
- Teto de compra: achar o B compatível com o preço escolhido e calcular `C_max = B * (1 - d - m)`

## Cuidados já identificados
- Usar **Decimal** para dinheiro, nunca float.
- **Preservar os totais do motor.** Parcelas já arredondadas podem dar diferença de centavo.
- Custo já líquido de crédito **não leva o mesmo crédito descontado de novo**.
- Conferir pelo caminho inverso (calcular o preço, depois voltar para a margem).
- A margem aqui é **de contribuição**, não lucro líquido nem markup.

## O que o grupo ainda decide
Se adota esta convenção como está, e quais entradas o usuário informa na interface.

---

## ✅ Motor tributário oficial validado rodando local

**Feito antes da formação do grupo.** Registrado aqui para o time não refazer.

## O que foi validado
A **calculadora RTC da Receita Federal roda na nossa máquina**, versão 1.5.4, banco V0059, por Java/JAR. O pacote offline é público, sem login.

- Chamada testada: `POST http://127.0.0.1:8080/api/calculadora/regime-geral`
- **24 verificações técnicas aprovadas** com três produtos: arroz, açúcar e creme dental
- Contrato completo de entrada e resposta documentado em `scripts/CONTRATO_RTC_E_CENARIOS.md`
- Script de subida: `scripts/iniciar_rtc_local.sh`; teste de cenários: `scripts/testar_motor_cenarios.py`

**Por que isso importa:** a demonstração não depende de nenhum serviço público remoto. Era a dúvida nº 1 do professor Hiroshi e está respondida.

## O que NÃO está resolvido
- **Bebidas ainda não foram validadas.** Precisam de verificação própria.
- O perfil fiscal testado é **hipotético, regime regular de IBS/CBS**. Simples Nacional não foi testado.
- A versão exige **alíquotas nominais informadas** para cenários de 2027 em diante, e marca o cálculo como simulado. Trocar o ano não traz alíquota futura automaticamente.
- Teste técnico do motor **não equivale a revisão fiscal**. O impacto líquido completo da reforma exige modelar créditos, tributos substituídos e transição.
- Docker é alternativa de execução, não pré-requisito — o caminho testado foi o JAR.

## O que o grupo ainda decide
Qual perfil fiscal e comercial explícito vamos adotar na demonstração.

---

## ✅ Fontes de dados levantadas e auditadas

**Feito antes da formação do grupo.** Registrado aqui para o time não refazer.

## O que foi medido
**Base de preços — Clique Economia (SEFA/PR), espelho UFPR/C3SL**
- 215.931 linhas, 34 fotos mensais, jan/2024 a out/2026
- ~663 produtos por foto, 59 redes, 119 lojas, Curitiba
- preço regular preenchido em 97,4% das linhas
- 82% dos pares dia-produto têm 3 ou mais redes → dá para comparar mercado
- dispersão mediana entre redes: 17%
- 225 a 510 produtos recorrentes, o que **sustenta investigar** previsão na fase 2 (não demonstra que a previsão funciona)

**Tabela NCM oficial — Portal Único Siscomex**
- Resolução Gecex 926/2026, vigente em 11/10/2026
- 10.516 códigos de 8 dígitos, com texto hierárquico reconstruído por herança

## Limitações que o grupo precisa assumir
- **Atacado é escasso:** preço de atacado aparece em só 1,1% das linhas. O projeto usa preço regular.
- **Custo, despesa, margem e volume não vêm desta base.** O empresário informa.
- **NCM não vem junto com o preço.** Ligar produto a código fiscal continua sendo problema aberto (ver cartão da frente de Classificação e IA).
- Códigos genéricos tipo "( + ) BARATO" são referência de categoria, não o mesmo SKU.

## Fonte reprovada — não reabrir
API pública estadual para buscar NCM por código de barras: cobertura de 1,7%, 64% dos campos "ncm" não eram NCM, 81% dos códigos de barras com dígito verificador inválido e resposta randomizada a cada chamada. Paginação e busca por GTIN testadas e eliminadas.

## Evidência
`ACHADOS_DADOS.md` seções 9 e 10, `evidencias/gate2_resultado.txt`, `evidencias/gate1_validacao_api.txt`.

# Calculadora da Receita e API local

## Atualização verificada em 07/11/2026

O pacote oficial 1.6.2/V0066 foi obtido em pasta isolada e testado nos 50
produtos com data fiscal explícita de 07/11. Os 50 passaram, sem alteração
dos resumos IBS/CBS em relação à versão anterior nas mesmas condições.
O pacote agora oferece também uma API específica do Simples; a consulta
realizada para 2026 não retornou atividades e o contrato exige alíquotas
efetivas fornecidas pelo chamador. Não equivale à apuração do DAS atual.

[Serviço atual, evidências e apuração personalizada](https://github.com/pedrocardosojr/tax-pricing/blob/feat/pedro-calculo-comercial/docs/entrega_tax_2026-11-07.md).
Os trechos abaixo preservam a instalação e os experimentos anteriores.

## Links oficiais para começar

- Pacote offline: https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/calculadora/calculadora-offline
- Instruções oficiais: https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/calculadora/calculadora-offline/calculadora-offline-instrucoes

No experimento anterior do projeto foi executada a versão RTC 1.5.4, banco V0059, via JAR com Java 21. Essa é a versão previamente testada, não uma afirmação de que seja a versão atual do portal. O JAR e seu banco não estão incluídos neste PR; obter o pacote oficial e seguir as instruções de execução. A documentação abaixo preserva o contrato observado naquela versão.

## Endereços depois de iniciar o serviço

Estes endereços são locais: funcionam no computador de quem iniciou o serviço. Não apontam para o computador de Pedro nem para uma API pública remota já disponível.

| Uso | Endereço local |
|---|---|
| Saúde do serviço | `http://127.0.0.1:9101/health` |
| Swagger | `http://127.0.0.1:8080/api/swagger-ui/index.html` |
| Especificação OpenAPI | `http://127.0.0.1:8080/api/api-docs` |
| Cálculo regime geral | `POST http://127.0.0.1:8080/api/calculadora/regime-geral` |
| Versão do serviço | `GET http://127.0.0.1:8080/api/calculadora/dados-abertos/versao` |

## Contrato observado no teste anterior

Entradas incluem data do cenário fiscal, município/UF, tipo de documento e itens com NCM, CST, cClassTrib, base de cálculo, quantidade e unidade. Na versão testada, cenários desde 2027 exigem alíquotas nominais explícitas e são marcados como simulados. Não interpretar valores ilustrativos do schema como alíquotas legais.

O teste anterior registrou 24 verificações técnicas com arroz, açúcar e creme dental. Bebidas e Simples Nacional não foram validados nesse experimento. Não foram reexecutados testes do motor neste compartilhamento.

NCM sozinho não determina todo o enquadramento. Conferir os campos e regras no Swagger da versão efetivamente executada. O motor calcula tributos da operação; não entrega sozinho a margem comercial nem o impacto líquido completo da reforma na empresa.

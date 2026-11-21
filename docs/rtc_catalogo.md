# Integração RTC e catálogo

## Escopo vigente de 2026

A execução padrão cobre os 50 produtos em 2026 e retornou 50 aprovados,
zero bloqueados e zero erros. O método completo, critérios, premissas e
comandos estão no [guia de revisão](metodo_teste_rtc_2026.md).
Os cenários futuros entram por solicitação explícita com --years.

## Referências e histórico

O adaptador consulta o motor oficial offline via REST local. O teste usa uma
base tributável fixa de R$ 133,34 para reproduzir as chamadas anteriores.
O catálogo recebe EAN e NCM como texto e rejeita duplicatas. O catálogo consolidado de 50 produtos preserva as origens dos 37 iniciais
e dos 13 adicionais de Rodrigo.

Com o RTC offline 1.5.4/V0059 em execução local, usando Java 21:

```sh
make test
make catalog-integration OUT=/tmp/rtc-nova-execucao
```

O diretório de saída deve ser novo. O script registra as chamadas e o status
de cada cenário. Para outro catálogo JSON, passe --catalog diretamente ao
módulo scripts.test_catalog_rtc. NCM sem classificação declarada fica bloqueado.

Cenários de 2033 usam alíquotas ilustrativas e exigem a flag de simulação.
A revisão fiscal de NCM, CST e cClassTrib continua pendente. A API pode exigir
dados adicionais de Imposto Seletivo, registrados como bloqueio. O script
retorna 2 para bloqueios e 1 para erros inesperados.

## Histórico do experimento de dois anos em 05/11/2026

O catálogo padrão agora é `dados/catalogo/skus_50.json`. Reúne os 37 anteriores
com a rastreabilidade do PR #6 e os 13 adicionais da branch expansao-catalogo.
Cada origem registra commit e hash, preservando NCM original/final, motivos,
revisor e exceções de cobertura. São 50 EANs distintos em 12 grupos e 14 NCMs.
O JSON é o snapshot consolidado desta integração.

Mantive os NCMs entregues por Rodrigo. Declarei três novos enquadramentos
experimentais para testar o motor. O leite 04012010 foi aceito com 200003.
O óleo 15079011 recusou 200003 e aceitou 200034, cuja descrição no próprio
RTC é alimento para consumo humano do Anexo VII. A cerveja 22030000 usou
000001. A revisão fiscal independente de cada produto/operação segue pendente.

| Resultado técnico | Casos |
|---|---:|
| Total, 50 produtos em 2026 e 2033 | 100 |
| Aprovados | 92 |
| Bloqueados por falta de dados de IS em 2033 | 8 |
| Erros inesperados na execução final | 0 |

Os oito bloqueios são quatro refrigerantes e quatro cervejas. Em 2026 os 50
passaram no experimento. Em 2033 passaram 42, e o motor recusou os oito casos
que exigem IS. Para estes, o JSON registra o bloqueio. O comando retorna 2.
A base tributável do lote é fixa em R$ 133,34. As nominais de 2033 continuam
ilustrativas, com flag de simulação conferida. A execução cobre IBS/CBS dos
cenários declarados. Os parâmetros do IS ainda precisam ser definidos.

Evidências finais em `evidencias/rtc_50_2026-11-05_final/`, com resultado,
201 chamadas, consulta de enquadramento do óleo, auditoria dos identificadores
e manifesto dos arquivos testados. O resultado da primeira tentativa com óleo
incompatível está em `evidencias/rtc_50_2026-11-05/result.json`.
Os nove testes automatizados passaram, pylint 10/10 e mypy sem erros.

### Identificadores e vínculo com preços

A auditoria conferiu dígito verificador dos 50 GTINs e vínculo exato de todos
com a base de preços. Para esta carteira, o vínculo funciona com os códigos
originais. A cobertura atual continua visível por SKU. As cervejas selecionadas
têm último preço positivo em fevereiro de 2026 no snapshot analisado.

Na base inteira há 215.931 registros e 1.359 identificadores distintos.
Os 272 registros com 12 dígitos representam 11 códigos distintos, todos com
dígito verificador válido. O campo também contém muitos códigos curtos.
Isso pede uma classificação dos identificadores antes de padronizar formatos.

Proposta para discussão com o grupo: conservar o identificador bruto e criar
uma chave GTIN de 14 dígitos apenas para identificadores reconhecidos e
validados. A GS1 documenta esse formato com zeros à esquerda para representar
GTINs menores. Dígito verificador válido indica coerência do código, e o
vínculo comercial depende de descrição e embalagem conferidas.
[Referência GS1](https://support.gs1.org/support/solutions/articles/43000734355-what-is-the-required-format-of-gtin-in-gs1-edi-standards-).

O processo de normalização dos preços e a camada de similares estão em
avaliação pelo grupo. Custo, crédito e margem permanecem na entrega comercial
do PR #7.

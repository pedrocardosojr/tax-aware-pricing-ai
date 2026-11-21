# Método de teste da integração RTC em 2026

## Entrega vigente em 05/11/2026

Validar a ligação técnica entre o catálogo de 50 SKUs e a calculadora oficial
RTC para o cenário de 2026. A execução padrão cobre esse ano. Resultado
reproduzido em 05/11, com **50 aprovados, zero bloqueados e zero erros**.
O motor executado é o componente oficial offline, acessado por REST local.

O cálculo desta entrega cobre IBS e CBS do cenário declarado. O imposto
efetivamente pago por uma empresa depende do seu perfil, operação e dos
tributos aplicáveis. A revisão fiscal dos enquadramentos permanece pendente.
Os testes de custo, crédito, margem e price index estão na próxima entrega.

## Dados e premissas

| Campo | Configuração da execução |
|---|---|
| Catálogo | 50 EANs distintos, 12 grupos, 14 NCMs |
| Origem | 37 iniciais do PR de SI5 e 13 adicionais de Rodrigo |
| Classificação | CST/cClassTrib declarados como candidatos experimentais |
| Motor | RTC offline 1.5.4, banco V0059 |
| Data fiscal | 01/10/2026, referência fixa do cenário |
| Data de execução | 05/11/2026 |
| Localidade | Curitiba/PR |
| Documento | NFC-e, tipo 65 |
| Quantidade | Uma unidade de teste |
| Base tributável | R$ 133,34, valor fixo para testar o motor |
| Alíquotas em 2026 | Parâmetros do motor, sem nominais futuras no pedido |

A base fixa permite comparar as respostas sob uma entrada conhecida. Cada
registro do catálogo preserva EAN, descrição, embalagem, NCM e proveniência.
A auditoria dos identificadores confirmou o dígito verificador e o vínculo
exato dos 50 códigos com o snapshot da base de preços. Descrição e embalagem
permanecem disponíveis para conferência do grupo.

## Procedimento executado

1. Carregar o catálogo JSON e rejeitar identificadores duplicados ou códigos
   malformados. Os códigos são tratados como texto para conservar zeros.
2. Consultar a versão do motor e exigir offline 1.5.4/V0059, identificando a
   configuração usada no teste.
3. Para cada SKU, obter o candidato CST/cClassTrib declarado para seu NCM.
   A ausência de candidato produz bloqueio explícito.
4. Consultar a compatibilidade NCM/cClassTrib na data fiscal configurada.
   A resposta deve indicar compatibilidade para prosseguir ao cálculo.
5. Montar uma operação NFC-e com a base tributável fixa e fazer a chamada ao
   endpoint de regime geral. Verificar sucesso HTTP e corpo da resposta.
6. Ler o IBS agregado oficial e a CBS retornados. Exigir valores finitos,
   não negativos e em centavos. Conferir a flag de simulação para o ano.
7. Registrar o resultado por SKU. Falta de parâmetros fiscais permanece
   bloqueada e erro de conexão ou resposta inesperada permanece visível.
8. Salvar requisições, respostas, resumo e hashes dos arquivos usados em
   um diretório novo. O comando impede sobrescrever uma execução anterior.

A execução padrão fez **101 chamadas**, com uma consulta de versão, 50
consultas de compatibilidade e 50 cálculos. Os 50 cálculos responderam com
sucesso e passaram nas verificações de estrutura, valores e flag de simulação.

## Critério de aprovação

Um caso passa quando o motor confirma a compatibilidade declarada, calcula
com sucesso e devolve os campos monetários esperados, com a flag compatível
com o ano. Isso comprova o contrato técnico entre nossa função e essa versão
do motor. A validação fiscal independente continua sendo uma etapa própria.

O NCM foi entregue por Rodrigo. Para leite, óleo e cerveja, Pedro declarou os
candidatos adicionais usados no experimento. O óleo recusou o primeiro
candidato 200003 e aceitou 200034 na consulta explícita ao motor. A consulta
está preservada nas evidências históricas do lote com dois anos.

## Código para revisão

| Arquivo | O que conferir |
|---|---|
| `tax_pricing/catalog.py` | Leitura, formato dos códigos e duplicatas |
| `tax_pricing/rtc.py` | Payload, comunicação HTTP, validação da resposta e totais |
| `scripts/test_catalog_rtc.py` | Sequência de chamadas, cenário padrão e evidências |
| `tests/test_catalog_integration_contract.py` | Cenário padrão 2026, bloqueios e falha de conexão |
| `tests/test_rtc.py` | Campos obrigatórios, valores inválidos e leitura do imposto |
| `dados/catalogo/skus_50.json` | Produtos, NCMs e rastreabilidade |
| `dados/catalogo/classificacoes_experimentais.json` | Candidatos declarados |

## Reproduzir

Preparar Python 3.10+ e Java 21. Obter e iniciar o pacote oficial conforme
[guia da API](api_receita.md). O motor deve estar acessível localmente em
`http://127.0.0.1:8080/api`. Depois, na raiz do repositório, executar

```sh
python -m pip install -r requirements-dev.txt
make test
make lint
make typecheck
make catalog-integration OUT=/tmp/rtc-2026-nova-execucao
```

Escolher um diretório novo em cada reprodução. Saída 0 indica que todos os
casos técnicos passaram, 1 indica erro e 2 indica bloqueios. A execução
vigente retornou 0. Os dez testes automatizados passaram, pylint 10/10 e
mypy sem erros nos quatro arquivos verificados.

Evidências da execução vigente em `evidencias/rtc_2026_50_2026-11-05/`.
O arquivo `result.json` contém ano, data fiscal, premissas e resultado de cada
EAN. `calls.json` contém pedidos e respostas reais. `manifest.json` registra
os hashes dos arquivos de código/configuração usados.

## Histórico de cenários futuros

O experimento anterior com 2026 e 2033 foi preservado. Em 2033, quatro
refrigerantes e quatro cervejas exigiram dados de Imposto Seletivo. Esse
experimento fica como possibilidade posterior, mediante solicitação explícita
com `--years`. O comando padrão executa apenas 2026.

## Próximas entregas do grupo

Edu e Rodrigo testam o processo na base de preços. Pedro testa custo, crédito,
margem e price index na próxima semana, na implementação comercial separada.
O grupo define métricas, gráficos e insights para os outputs por produto e
por grupo de similares. A entrega de um SKU completo na tela depende da
integração dessas frentes e da revisão dos colegas.

## Atualização da camada de detalhamento

O roteiro passou a registrar tax_detail por SKU. O componente traz as três
linhas de IBS/CBS, alíquotas, reduções e a cobertura da apuração. A nova execução
completa aprovou 50/50, com quinze testes automatizados aprovados.
[Contrato e exemplos](detalhamento_tributario.md).

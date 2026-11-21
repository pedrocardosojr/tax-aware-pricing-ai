# Camada de detalhamento tributário

Aprovada por Pedro em 05/11/2026 para integrar o resultado do produto.
O componente já prepara os dados de IBS/CBS para a futura tela Streamlit.

## O que o código entrega

A função summarize_tax, em tax_pricing/tax_summary.py, recebe uma resposta
bem-sucedida de um único item do RTC. Para os CSTs 000 e 200 usados na carteira,
ela devolve base tributável, classificação declarada, flag de simulação e três
linhas de componentes, CBS, IBS estadual e IBS municipal. Cada linha contém
alíquota de referência, redução, alíquota efetiva e valor em reais.

A rotina preserva o IBS agregado oficial para os totais, evitando recalcular
a soma a partir das parcelas arredondadas. Campos ausentes, negativos ou
inválidos produzem erro explícito. O roteiro dos 50 produtos já inclui esse
resumo em tax_detail de cada caso aprovado.

## Teste comparativo real do motor

Operações de regime geral com base fictícia de R$ 30,00, quantidade de uma
unidade, Curitiba/PR, NFC-e e data fiscal de 05/11/2026. Estes valores são
resultados dos candidatos declarados ao RTC offline 1.5.4/V0059.

| Produto | Redução | CBS efetiva | IBS efetivo | Total IBS/CBS |
|---|---:|---:|---:|---:|
| Arroz Tio João 5 kg | 100% | 0,00% | 0,00% | R$ 0,00 |
| Coca-Cola 2 L | 0% | 0,90% | 0,10% | R$ 0,30 |
| Óleo Liza 900 ml | 60% | 0,36% | 0,04% | R$ 0,12 |
| Sabonete Protex 85 g | 60% | 0,36% | 0,04% | R$ 0,12 |

As chamadas e respostas desse teste estão em tests/fixtures/rtc_2026_examples.json
como exemplos reais para os testes automatizados. O novo lote completo ficou
em evidencias/rtc_2026_detalhamento_50_2026-11-05/, mantendo a referência fiscal
fixa de 01/10/2026 e base de R$ 133,34 do teste de integração.

No lote dos 50, 34 itens tiveram IBS/CBS zero e 16 tiveram valores positivos.
Todos os 50 passaram, com zero bloqueados e zero erros. Quinze testes
unitários/contratos passaram, pylint 10/10 e mypy sem erros em cinco arquivos.

## Valor calculado e apuração da empresa

A Receita trata 2026 como ano de teste do IBS/CBS e prevê dispensa de
recolhimento mediante as condições do comunicado. O tratamento de pagamento
precisa considerar as obrigações e a situação do contribuinte.
[Comunicado oficial da Receita](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2025/dezembro/comunicado-conjunto/).

A futura tela deve chamar a soma retornada de Total IBS/CBS do cenário.
O código indica que a carga tributária total ainda depende do perfil e marca
ICMS, PIS/Cofins e DAS como fora dessa resposta. O estado pendente aparece
como informação a definir, preservando a distinção entre ausência de cálculo
e tributo calculado em zero. A tela Streamlit ainda será implementada.

## Perfil tributário confirmado; regras a detalhar

Após a reunião com a professora em 05/11, Pedro confirmou o regime da empresa
como entrada: Simples Nacional, Lucro Presumido ou Lucro Real. A escolha deve
orientar as premissas e a cobertura do cenário. As regras de cada perfil ainda
serão implementadas e validadas; a tela identificará apurações incompletas.

Regime geral de IBS/CBS é a modalidade do endpoint testado. A implementação
precisa distinguir esse contexto do enquadramento geral da empresa. O endpoint
usado aqui não apura o DAS. A etapa comercial da próxima semana deve definir
quais informações/perfis adicionais são necessários e como obter cada tributo,
crédito aproveitável e despesa para calcular a margem.

## Apresentação proposta

Uma área Tributos do cenário com as três linhas e acesso à classificação,
data fiscal, fonte e versão do motor. Destacar a redução aplicada quando o
valor for zero ou reduzido. Ao lado, mostrar a cobertura da apuração e o estado
do perfil da empresa. A árvore de preço usará os componentes validados para o
perfil escolhido, conservando a origem de cada parcela.

## Aprofundamento da frente de Pedro

[Plano Tax de 2026, fontes e perfis](plano_tax_perfis_2026.md).
A preparação inclui fichas dos 50 produtos, mapa dos 14 NCMs e casos a validar
na etapa de margem. As três opções do seletor estão confirmadas; parâmetros,
regras e cobertura efetivamente calculada de cada perfil continuam pendentes.

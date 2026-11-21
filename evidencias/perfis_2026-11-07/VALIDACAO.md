# Perfis e cálculo comercial — continuação de 07/11

- 48 testes aprovados, incluindo oito novos testes de perfil e fórmula.
- Pylint 10,00/10; mypy sem erros em 12 arquivos fonte.
- Exemplo executado e preservado em exemplo.json.
- Reprodução: `make profile-example`, `make test`, `make lint`,
  `make typecheck`, a partir da raiz do repositório.

Python 3.12.9 nos testes/exemplo; pylint no ambiente lewagon; mypy isolado
via PYTHONPATH=/private/tmp/tax-pricing-mypy-20261105.

## O que a evidência demonstra

1. Os retornos reais preservados de 05/11 para arroz e refrigerante contêm
   IBS/CBS de R$ 0 e R$ 0,30, sobre a base de R$ 30 do teste.
2. Para os três regimes empresariais, esses retornos isolados não preenchem
   taxa, crédito e fontes do perfil: a margem permanece pendente.
3. Um perfil ilustrativo separado usa a fórmula do Simples com parâmetros
   explicitados. RBT12 R$ 360.000, nominal 7,3% e dedução R$ 5.940 resultam
   em 5,65% antes dos tratamentos específicos da receita. Essa taxa não foi
   atribuída ao arroz nem ao refrigerante.
4. Remover a fonte da taxa torna a margem pendente, mesmo com número presente.

Não houve nova chamada RTC. Custos, despesas e crédito do exemplo comercial
são hipotéticos. Seleção de faixa, segregação da receita, enquadramento do
produto e demais incidências ainda exigem validação. Não houve implementação
de apuração completa de Simples, Lucro Presumido ou Lucro Real nesta etapa.

[Descrição e fonte oficial da fórmula](../../docs/calculos_comerciais.md).

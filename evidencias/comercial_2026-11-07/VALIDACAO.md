# Validação comercial — 07/11/2026

- `make test`: 40 testes aprovados, incluindo nove novos contratos comerciais.
- `make lint`: pylint 10,00/10.
- `make typecheck`: sem erros em nove arquivos fonte.
- `make commercial-example`: exemplo executado e preservado em exemplo.json.
- `git diff --check`: sem erros.

Execução dos testes e do exemplo com Python 3.12.9. Pylint no ambiente lewagon;
mypy isolado em /private/tmp/tax-pricing-mypy-20261105, fornecido via PYTHONPATH.
Não é necessário instalar dependências no runtime do motor RTC para essa conta.

O exemplo contém taxas, custos e referência fictícios. Não houve nova chamada
à API RTC nesta entrega. A integração de IBS/CBS dos 50 produtos conserva as
evidências de 05/11. A apuração por regime e o vínculo da margem aos tributos
reais ainda estão pendentes, assim como revisão por colega e integração da tela.

[Fórmulas, limites e reprodução](../../docs/calculos_comerciais.md).

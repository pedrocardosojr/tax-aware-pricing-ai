PYTHON ?= python

.PHONY: test catalog-integration current-tax-integration commercial-example profile-example lint typecheck app market-lab team-preview explanation-eval

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m pylint --persistent=n app.py tax_pricing scripts/build_market_lab.py scripts/test_catalog_rtc.py scripts/demo_commercial.py scripts/demo_profile.py scripts/verify_current_tax.py scripts/demo_personalized.py scripts/demo_mvp.py scripts/export_team_market.py scripts/demo_reviewed_tax.py scripts/audit_tax_catalog.py mercado tests

typecheck:
	$(PYTHON) -m mypy app.py tax_pricing scripts/build_market_lab.py scripts/test_catalog_rtc.py scripts/demo_commercial.py scripts/demo_profile.py scripts/verify_current_tax.py scripts/demo_personalized.py scripts/demo_mvp.py scripts/export_team_market.py scripts/demo_reviewed_tax.py scripts/audit_tax_catalog.py mercado

market-lab:
	$(PYTHON) -m scripts.build_market_lab

app:
	$(PYTHON) -m streamlit run app.py --server.address=127.0.0.1

team-preview: app

commercial-example:
	$(PYTHON) -m scripts.demo_commercial

profile-example:
	$(PYTHON) -m scripts.demo_profile

current-tax-integration:
	@test -n "$(OUT)" -a -n "$(FISCAL_DATE)" || (echo "Use OUT e FISCAL_DATE"; exit 1)
	$(PYTHON) -m scripts.verify_current_tax --output "$(OUT)" --fiscal-date "$(FISCAL_DATE)"

catalog-integration:
	@test -n "$(OUT)" || (echo "Use OUT=novo-diretorio"; exit 1)
	$(PYTHON) -m scripts.test_catalog_rtc --output "$(OUT)"

explanation-eval:
	TAX_PRICING_MARKET_DIR=evidencias/integracao_mercado_2026-11-09/snapshots $(PYTHON) -m scripts.eval_grounded_explanation

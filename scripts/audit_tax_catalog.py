"""Reproduce all catalogue demo rules without API or market observations."""
import csv
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from tax_pricing.catalog import load_catalog
from tax_pricing.demo_profile import ROOT, build_demo_profile, demo_settings
from tax_pricing.personalized_tax import personalized_margin
from tax_pricing.product_tax_demo import RULES

REGIMES = ('simples_nacional', 'lucro_presumido', 'lucro_real')
OUTPUT = ROOT / 'evidencias/revisao_fiscal_50_2026-11-09'


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Write a reproducible audit table with decimal strings."""
    with path.open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit_catalog(output: Path = OUTPUT) -> list[dict]:
    """Audit all product/regime recipes at two fictional selling prices.

    Parameters
    ----------
    output : pathlib.Path
        Separate evidence folder; catalogue and price observations stay intact.

    Returns
    -------
    list of dict
        Three hundred arithmetic checks, not API or legal certification tests.
        Cost is R$8 and sale is R$6 or R$12 solely as a synthetic test fixture.
    """
    output.mkdir(parents=True, exist_ok=True)
    rules = json.loads(RULES.read_text())
    matrix, examples = [], []
    for product in load_catalog(ROOT / 'dados/catalogo/skus_50.json'):
        recipe = rules['products'][product['ean']]
        for regime in REGIMES:
            demo = build_demo_profile(regime, Decimal(8), product=product)
            rates = {r['name']: str(r['rate'])
                     for r in demo['taxpayer']['tax_components']}
            matrix.append({
                'ean': product['ean'], 'description': product['description'],
                'group': product['group'], 'ncm': product['ncm'],
                'family': recipe['family'], 'regime': regime,
                'date': demo_settings()['fiscal_date'],
                'rates_fraction': json.dumps(rates, sort_keys=True),
                'credit_brl': str(demo['assumptions']['credit_brl']),
                'conditions': ' | '.join(recipe['conditions']),
                'sources': ' | '.join(demo['assumptions'][
                    'product_tax']['source_urls']),
                'status': rules['status']})
            for price in (Decimal(6), Decimal(12)):
                result = personalized_margin(price, Decimal(8),
                                             demo['taxpayer'],
                                             expenses=demo['expenses'])
                margin = result['margin']
                expected = (price - Decimal(8)
                            + demo['assumptions']['credit_brl']
                            - margin['expense_brl'] - margin['tax_brl'])
                if expected != margin['contribution_brl']:
                    raise ValueError('Price tree does not reconcile.')
                examples.append({
                    'ean': product['ean'], 'regime': regime,
                    'gross_cost_brl': '8', 'selling_price_brl': str(price),
                    'tax_brl': str(margin['tax_brl']),
                    'expense_brl': str(margin['expense_brl']),
                    'contribution_brl': str(margin['contribution_brl']),
                    'company_and_price_data': 'synthetic_not_market_data'})
    _write_csv(output / 'matrix_150.csv', matrix)
    _write_csv(output / 'arithmetic_300.csv', examples)
    files = [RULES, ROOT / 'dados/tributos/perfis_demo_mvp.json',
             ROOT / 'dados/catalogo/skus_50.json']
    (output / 'manifest.json').write_text(json.dumps({
        'date': demo_settings()['fiscal_date'], 'products': len(matrix) // 3,
        'regimes': 3, 'arithmetic_checks': len(examples),
        'rtc': 'not_called', 'market_data': 'not_used',
        'conditions': 'assumed_not_invoice_verified',
        'sha256': {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
                   for p in files}}, indent=2) + '\n')
    return examples


if __name__ == '__main__':
    print(f'{len(audit_catalog())} arithmetic checks reconciled: {OUTPUT}')

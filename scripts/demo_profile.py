"""Show saved RTC evidence beside pending and illustrative company profiles."""
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path

from tax_pricing.fiscal_profile import FiscalProfile, REGIMES
from tax_pricing.profile_calculation import (profile_margin,
                                            simples_effective_rate)
from tax_pricing.tax_summary import summarize_tax


def example() -> dict:
    """Build examples without a new API call or a taxpayer assessment.

    Returns
    -------
    dict
        Recorded IBS/CBS evidence, pending company margins and a distinct
        illustrative Simples formula case. Costs and expenses are fictional.
    """
    fixtures = json.loads((Path(__file__).resolve().parents[1] / 'tests'
                           / 'fixtures' / 'rtc_2026_examples.json').read_text())
    expenses = {'expense_rate': Decimal('.05'),
                'expense_per_unit': Decimal('.50')}
    recorded = []
    for fixture in fixtures[:2]:
        recorded.append({
            'product': fixture['product'],
            'rtc_request': fixture['call']['request'],
            'rtc_summary': summarize_tax(fixture['call']['body']),
            'company_results': [profile_margin(
                Decimal('30'), Decimal('20'),
                FiscalProfile(regime, '2026-11'), **expenses)
                for regime in REGIMES],
        })
    rate = simples_effective_rate(Decimal('360000'), Decimal('.073'),
                                 Decimal('5940'))
    profile = FiscalProfile(
        'simples_nacional', '2026-11', rate, Decimal(0),
        'illustrative supplied bracket; no revenue segregation assessed',
        'zero usable credit assumed only for this arithmetic example',
        'illustrative effective deduction, not actual per-SKU DAS',
        'illustrative')
    return {
        'evidence_source': 'tests/fixtures/rtc_2026_examples.json',
        'new_rtc_call': False,
        'rtc_role': 'IBS/CBS evidence, not added to company deduction',
        'fictional_commercial_inputs': {
            'sale_brl': '30.00', 'gross_cost_brl': '20.00', **expenses},
        'recorded_products': recorded,
        'separate_simples_example': {
            'rbt12_brl': '360000', 'nominal_fraction': '.073',
            'deduction_brl': '5940', 'effective_fraction': rate,
            'conditional_margin': profile_margin(
                Decimal('30'), Decimal('20'), profile, **expenses),
            'missing_source_example': profile_margin(
                Decimal('30'), Decimal('20'),
                replace(profile, tax_source=''), **expenses),
        },
    }


if __name__ == '__main__':
    print(json.dumps(example(), default=str, indent=2, ensure_ascii=False))

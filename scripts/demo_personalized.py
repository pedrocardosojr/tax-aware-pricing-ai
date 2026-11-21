"""Verify the product flow with synthetic taxpayer data and the real RTC."""
import argparse
from decimal import Decimal
import json
from pathlib import Path

from tax_pricing.catalog import load_catalog
from tax_pricing.product_analysis import analyze_product
from tax_pricing.rtc_service import DEFAULT_API

ROOT = Path(__file__).resolve().parents[1]


def _profile(regime: str, rates: dict[str, str], credit: str) -> dict:
    """Build fictional sourced rules solely for reproducible arithmetic."""
    return {
        'regime': regime, 'competence': '2026-11',
        'scope': 'synthetic test case; not an actual taxpayer assessment',
        'coverage_confirmed': True, 'icms_outside_das': False,
        'usable_purchase_credit_brl': Decimal(credit),
        'purchase_credit_source': 'explicit fictional test credit',
        'tax_components': [
            {'name': name, 'rate': Decimal(rate),
             'basis': ('selling_price_less_icms' if name in ('PIS', 'COFINS')
                       else 'selling_price'),
             'source': 'fictional supplied rate, not a prescribed legal rate'}
            for name, rate in rates.items()],
    }


def example(api: str) -> dict:
    """Run three synthetic company profiles against the selected soda SKU.

    Parameters
    ----------
    api : str
        Official local RTC base URL; every call and response is retained.

    Returns
    -------
    dict
        Reconciled flow, expected manual contributions and runtime evidence.
        Neither company inputs nor fiscal base are actual taxpayer data.
    """
    product = next(p for p in load_catalog(ROOT / 'dados/catalogo/skus_50.json')
                   if p['ean'] == '7894900027013')
    context = {'year': 2026, 'fiscal_date': '2026-11-07',
               'cst': '000', 'cclass': '000001', 'tax_base_brl': Decimal(30)}
    pricing = {'selling_price': Decimal(30), 'gross_cost': Decimal(20),
               'price_origin': 'user_price',
               'expenses': {'rate': Decimal('.05'),
                            'per_unit_brl': Decimal('.50')}}
    cases = [
        ('simples_nacional', {'DAS': '.0565'}, '0', '6.305'),
        ('lucro_presumido', {'ICMS': '.18', 'PIS': '.0065', 'COFINS': '.03'},
         '0', '1.7021'),
        ('lucro_real', {'ICMS': '.18', 'PIS': '.0165', 'COFINS': '.076'},
         '1', '1.3245')]
    rows = []
    for regime, rates, credit, expected in cases:
        analysis = analyze_product(product, context,
                                   _profile(regime, rates, credit), pricing, api)
        actual = analysis['personalized']['margin']['contribution_brl']
        passed = (actual == Decimal(expected)
                  and analysis['rtc']['status'] == 'calculated_ibs_cbs')
        rows.append({'regime': regime, 'passed': passed,
                     'expected_contribution_brl': expected,
                     'analysis': analysis})
    return {'example_kind': 'synthetic_taxpayer_plus_live_rtc',
            'fiscal_date': context['fiscal_date'], 'pricing': pricing,
            'tax_base_brl': context['tax_base_brl'],
            'passed': sum(row['passed'] for row in rows), 'rows': rows}


def main() -> None:
    """Save new evidence and exit nonzero when any expected result fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default=DEFAULT_API)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = example(args.api)
    (args.output / 'exemplo.json').write_text(json.dumps(
        report, default=str, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['rows'])}))
    if report['passed'] != 3:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

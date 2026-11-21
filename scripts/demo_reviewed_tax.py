"""Reproduce two fictional retail cases with traceable observed prices."""
import argparse
import csv
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from tax_pricing.demo_profile import ROOT, demo_settings
from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.pricing_scenarios import scenario_analysis

CASES = [('7894900027013', '8.00', '12.00'),
         ('7891528029498', '1.50', '3.99')]


# Keep the twelve-case orchestration and its reconciliation visible together.
# pylint: disable=too-many-locals
def run_examples(output: Path) -> list[dict]:
    """Save reproducible examples, source snapshots and reconciliations.

    Parameters
    ----------
    output : pathlib.Path
        Dedicated evidence folder, separate from original price observations.

    Returns
    -------
    list of dict
        Twelve product/regime/price-path results. Company values are fictional;
        market prices remain the team's observed reference.
    """
    output.mkdir(parents=True, exist_ok=True)
    rows, results = [], []
    for ean, cost, price in CASES:
        snapshot_path = ROOT / ('evidencias/integracao_mercado_2026-11-09/'
                                f'snapshots/{ean}.json')
        market = json.loads(snapshot_path.read_text())
        for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
            for mode in ('current', 'suggestion'):
                inputs = {'ean': ean, 'regime': regime,
                          'acquisition_cost': cost,
                          'selling_price': price if mode == 'current' else None}
                # A closed local port keeps this explicitly an offline example.
                result = analyze_mvp(inputs, market, api='http://127.0.0.1:1')
                margin = result['analysis']['personalized']['margin']
                credit = result['assumptions']['credit_brl']
                expected = (margin['selling_price_brl'] - Decimal(cost)
                            + credit - margin['expense_brl']
                            - margin['tax_brl'])
                if expected != margin['contribution_brl']:
                    raise ValueError('Price tree does not reconcile.')
                scenarios = scenario_analysis(result)
                if (scenarios['floor_contribution_brl'] < 0 or
                        scenarios['previous_cent_contribution_brl'] >= 0):
                    raise ValueError('Price floor is not the first cent.')
                row = {
                    'ean': ean, 'regime': regime, 'path': mode,
                    'gross_cost_brl': cost, 'credit_brl': str(credit),
                    'st_base_exclusion_brl': str(result['assumptions'][
                        'purchase_icms_st_exclusion_brl']),
                    'selling_price_brl': str(margin['selling_price_brl']),
                    'tax_brl': str(margin['tax_brl']),
                    'expenses_brl': str(margin['expense_brl']),
                    'contribution_brl': str(margin['contribution_brl']),
                    'contribution_percent': str(margin['contribution_percent']),
                    'market_median_brl': market['median'],
                    'price_index': str(result['market_position']['price_index']),
                    'zero_contribution_price_brl': str(
                        scenarios['zero_contribution_price_brl']),
                }
                rows.append(row)
                results.append({'inputs': inputs, 'result': result,
                                'scenarios': scenarios})
    (output / 'examples.json').write_text(json.dumps(
        results, ensure_ascii=False, indent=2, default=str) + '\n')
    with (output / 'examples.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    sources = ['dados/tributos/perfis_demo_mvp.json',
               'dados/tributos/revisao_2026_11.json']
    (output / 'manifest.json').write_text(json.dumps({
        'fiscal_date': demo_settings()['fiscal_date'], 'scenarios': len(rows),
        'company_data': 'fictional', 'conditions': 'assumed_not_invoice_verified',
        'rtc_mode': 'offline_closed_local_port_no_official_calculation',
        'reconciliation': 'sale - gross_cost + credit - taxes - expenses',
        'sha256': {name: sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in sources}}, indent=2) + '\n')
    return rows


def main() -> None:
    """Write evidence without querying a live official RTC service."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT /
                        'evidencias/revisao_fiscal_2026-11-09')
    args = parser.parse_args()
    rows = run_examples(args.output)
    print(f'{len(rows)} scenarios reconciled: {args.output}')


if __name__ == '__main__':
    main()

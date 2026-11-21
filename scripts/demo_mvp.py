"""Reproduce both minimal-input paths using an observed market snapshot."""
import argparse
from decimal import Decimal
import json
from pathlib import Path

from tax_pricing.demo_profile import ROOT
from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.rtc_service import DEFAULT_API


def example(market: dict, api: str = DEFAULT_API) -> dict:
    """Evaluate the three configured regimes with current and absent price.

    Parameters
    ----------
    market : dict
        Observed exact-SKU snapshot, including source, date and coverage.
    api : str
        RTC URL. An unavailable service remains identified in every result.

    Returns
    -------
    dict
        Six demonstrative results. Cost BRL 7 and price BRL 12 are fictional;
        the default market snapshot contains previously observed prices.
    """
    rows = []
    for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
        for price in (Decimal(12), None):
            inputs = {'ean': market['ean'], 'regime': regime,
                      'acquisition_cost': Decimal(7), 'selling_price': price}
            rows.append({'inputs': inputs,
                         'result': analyze_mvp(inputs, market, api=api)})
    return {'mode': 'demonstration',
            'fictional_values': 'company profiles, cost, current price and fees',
            'observed_values': 'the supplied dated market snapshot only',
            'cases': len(rows),
            'ready': sum(row['result']['status'] == 'ready' for row in rows),
            'rows': rows}


def main() -> None:
    """Write a new example directory without overwriting existing evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', type=Path, default=(
        ROOT / 'evidencias/mvp_estimativa_2026-11-07/mercado_coca_2l.json'))
    parser.add_argument('--api', default=DEFAULT_API)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = example(json.loads(args.market.read_text()), args.api)
    (args.output / 'exemplo.json').write_text(json.dumps(
        result, default=str, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases': result['cases'], 'ready': result['ready']}))
    if result['ready'] != result['cases']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

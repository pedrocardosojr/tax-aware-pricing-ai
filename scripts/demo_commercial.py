"""Reproduce illustrative commercial arithmetic, not a fiscal assessment."""
from decimal import Decimal
import json

from tax_pricing.commercial import (margin_breakdown, market_position,
                                    net_acquisition_cost,
                                    required_selling_price)


def example() -> dict:
    """Return a labeled scenario with fictional rates and market reference.

    Returns
    -------
    dict
        Declared assumptions, current margin, target price and market index.
        Decimal values are serialized as strings by the command-line entry.
    """
    rates = {'tax_rate': Decimal('.10'), 'expense_rate': Decimal('.05'),
             'expense_per_unit': Decimal('.50')}
    cost = net_acquisition_cost(Decimal('6'), Decimal(0))
    price = required_selling_price(cost, Decimal('.25'), **rates)
    return {
        'scenario_kind': 'illustrative_arithmetic',
        'fiscal_assessment_status': 'pending',
        'business_regime': 'not_selected',
        'market_reference_source': 'fictional_example',
        'assumptions': {'gross_cost_brl': '6.00', 'usable_credit_brl': '0',
                        'selling_price_brl': '10.00',
                        'market_reference_brl': '12.00',
                        'target_fraction': '.25', **rates},
        'current': margin_breakdown(Decimal('10'), cost, **rates),
        'current_market': market_position(Decimal('10'), Decimal('12')),
        'target_price_brl': price,
        'target': margin_breakdown(price, cost, **rates),
        'target_market': market_position(price, Decimal('12')),
    }


if __name__ == '__main__':
    print(json.dumps(example(), default=str, indent=2, ensure_ascii=False))

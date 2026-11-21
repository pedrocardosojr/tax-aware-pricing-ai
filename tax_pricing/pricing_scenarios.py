"""Commercial sensitivity with the same fictional profiles used by the MVP."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from tax_pricing.commercial import market_position
from tax_pricing.demo_profile import build_demo_profile
from tax_pricing.personalized_tax import personalized_margin

CENT = Decimal('.01')


def _at_price(price: Decimal, cost: Decimal, demo: dict) -> dict:
    """Reuse the checked contribution engine without another RTC request."""
    margin = personalized_margin(price, cost, demo['taxpayer'],
                                 expenses=demo['expenses'])['margin']
    return {'price_brl': price, 'contribution_brl': margin['contribution_brl'],
            'contribution_percent': margin['contribution_percent'],
            'tax_brl': margin['tax_brl']}


def volume_scenario(result: dict, price: Decimal, *,
                    acquisition_cost: Decimal | None = None) -> dict:
    """Simulate selling price and purchase cost against the original contribution."""
    margin = result['analysis']['personalized']['margin']
    original_cost = margin['net_cost_brl'] + result['assumptions']['credit_brl']
    cost = original_cost if acquisition_cost is None else acquisition_cost
    profile = build_demo_profile(result['assumptions']['regime'], cost,
                                 product=result['product'])
    scenario = _at_price(price, cost, profile)
    baseline = margin['contribution_brl']
    proposed = scenario['contribution_brl']
    market = result['market']
    return {
        **scenario, 'acquisition_cost_brl': cost,
        'units_per_100': (int((baseline * 100 / proposed).to_integral_value(
            rounding=ROUND_CEILING)) if baseline > 0 and proposed > 0 else None),
        'volume_change_percent': (
            (baseline / proposed - 1) * 100
            if baseline > 0 and proposed > 0 else None),
        'revenue_units_per_100': (int((result['evaluated_price_brl'] * 100 / price)
                                     .to_integral_value(rounding=ROUND_CEILING))
                                  if price > 0 else None),
        'position': (market_position(price, market['median'])
                     if market['status'] == 'current_reference' else None),
    }


def _curve(result: dict, cost: Decimal, demo: dict, floor: Decimal,
           simulated_price: Decimal | None) -> list[dict]:
    """Include the actual price and floor in a bounded illustrative curve."""
    current = result['evaluated_price_brl']
    market = result['market']
    band = market.get('usable_for_band', False)
    low = min(current, Decimal(str(market['p25']))) if band else current
    high = max(current, Decimal(str(market['p75']))) if band else current
    start = max(CENT, (low * Decimal('.85')).quantize(CENT))
    start = min(start, floor)
    end = max(high, floor)
    if simulated_price is not None:
        start, end = min(start, simulated_price), max(end, simulated_price)
    end = (end * Decimal('1.1')).quantize(CENT)
    prices = {max(CENT, (start + (end - start) * i / 30).quantize(
        CENT, rounding=ROUND_HALF_UP)) for i in range(31)}
    prices.update((current, floor))
    if simulated_price is not None:
        prices.add(simulated_price)
    return [_at_price(price, cost, demo) for price in sorted(prices)]


def _sensitivity(result: dict, cost: Decimal, floor: Decimal) -> dict:
    """Rebuild the internal profile for each hypothetical purchase cost."""
    costs = sorted({(cost * factor).quantize(CENT, rounding=ROUND_HALF_UP)
                    for factor in map(Decimal, ('.8', '.9', '1', '1.1', '1.2'))})
    prices = sorted({result['evaluated_price_brl'], floor} |
                    {p['price_brl'] for p in result['corridor_points']})
    grid = []
    for candidate in costs:
        profile = build_demo_profile(result['assumptions']['regime'], candidate,
                                     product=result['product'])
        grid.append([_at_price(price, candidate, profile)['contribution_brl']
                     for price in prices])
    return {'costs_brl': costs, 'grid_prices_brl': prices,
            'contribution_grid_brl': grid}


def _floor(cost: Decimal, demo: dict) -> Decimal:
    """Find the first nonnegative cent under the configured monotone recipe."""
    low = 0
    high = max(1, int(((cost + demo['expenses']['per_unit_brl']) * 100)
                     .to_integral_value(rounding=ROUND_CEILING)))
    for _ in range(60):
        if _at_price(CENT * high, cost, demo)['contribution_brl'] >= 0:
            break
        high *= 2
    else:
        raise ValueError('No nonnegative price floor in the supported range.')
    while high - low > 1:
        middle = (low + high) // 2
        if _at_price(CENT * middle, cost, demo)['contribution_brl'] >= 0:
            high = middle
        else:
            low = middle
    return CENT * high


def scenario_analysis(result: dict, *, acquisition_cost: Decimal | None = None,
                      simulated_price: Decimal | None = None) -> dict:
    """Cross the observed band with contribution and internal cost sensitivity.

    Parameters
    ----------
    result : dict
        Ready analyze_mvp demonstration result. This analytical price floor
        applies to the configured monotone profiles, not arbitrary fiscal rules.
    acquisition_cost : Decimal, optional
        Replaces the purchase cost for this simulation, preserving the input result.
    simulated_price : Decimal, optional
        Adds the simulated price as an exact observation on the curve.

    Returns
    -------
    dict
        First nonnegative contribution cent, evaluated curve, band status and
        cost-by-price sensitivity. No target margin or extra input is required.
        Zero contribution does not cover fixed overhead or guarantee demand.
    """
    if result['status'] != 'ready' or result['mode'] != 'demonstration':
        raise ValueError('A ready demonstration result is required.')
    margin = result['analysis']['personalized']['margin']
    original_cost = margin['net_cost_brl'] + result['assumptions']['credit_brl']
    cost = original_cost if acquisition_cost is None else acquisition_cost
    demo = build_demo_profile(result['assumptions']['regime'], cost,
                              product=result['product'])
    floor = _floor(cost, demo)
    contributions = [_at_price(p['price_brl'], cost, demo)['contribution_brl']
                     for p in result['corridor_points']]
    status = ('unavailable' if not contributions else 'all_negative'
              if max(contributions) < 0 else 'all_nonnegative'
              if min(contributions) >= 0 else 'partially_viable')
    previous = _at_price(floor - CENT, cost, demo) if floor > CENT else None
    return {'zero_contribution_price_brl': floor,
            'floor_contribution_brl': _at_price(floor, cost, demo)[
                'contribution_brl'],
            'previous_cent_contribution_brl': (previous['contribution_brl']
                                               if previous else None),
            'curve': _curve(result, cost, demo, floor, simulated_price), 'band_status': status,
            **_sensitivity(result, cost, floor)}

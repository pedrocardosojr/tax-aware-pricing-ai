"""Minimal-input MVP: market context and explicitly demonstrative taxation."""
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
import json

from tax_pricing.catalog import load_catalog
from tax_pricing.commercial import market_position
from tax_pricing.demo_profile import ROOT, build_demo_profile, demo_settings
from tax_pricing.personalized_tax import personalized_margin
from tax_pricing.product_analysis import analyze_product
from tax_pricing.rtc_service import DEFAULT_API

CENT = Decimal('.01')


def _selected_product(inputs: dict) -> dict:
    """Resolve the selected SKU and its group from the existing catalog."""
    products = load_catalog(ROOT / 'dados/catalogo/skus_50.json')
    product = next((p for p in products if p['ean'] == inputs.get('ean')), None)
    if product is None or inputs.get('group', product['group']) != product['group']:
        raise ValueError('Choose a catalog SKU in the selected group.')
    return product


def _money(value: object) -> Decimal:
    """Require a finite positive reference price without losing precision."""
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0:
        raise ValueError('Reference prices must be finite and positive.')
    return number


def _market(raw: dict | None, ean: str, settings: dict) -> dict:
    """Check SKU, source, date and coverage before proposing a market band."""
    if raw is None:
        return {'status': 'unavailable', 'usable_for_band': False}
    if raw.get('ean') != ean:
        raise ValueError('Market reference must describe the selected SKU.')
    if raw.get('kind') not in ('observed', 'estimated'):
        raise ValueError('Market reference must identify observed/estimated data.')
    day = date.fromisoformat(raw['date'])
    age = (date.fromisoformat(settings['fiscal_date']) - day).days
    if age < 0:
        raise ValueError('A market reference cannot come from the future.')
    networks = raw.get('network_count')
    if (not isinstance(networks, int) or isinstance(networks, bool)
            or networks <= 0 or not raw.get('source')):
        raise ValueError('Market source and network coverage are required.')
    normalized = {**raw, 'median': _money(raw['median']), 'age_days': age}
    has_band = raw.get('p25') is not None and raw.get('p75') is not None
    if has_band:
        low, high = _money(raw['p25']), _money(raw['p75'])
        if not low <= normalized['median'] <= high:
            raise ValueError('Expected P25 <= median <= P75.')
        normalized.update(p25=low, p75=high)
    fresh = age <= settings['market_max_age_days']
    normalized.update(
        status='current_reference' if fresh else 'historical_reference',
        usable_for_band=(has_band and fresh
                         and networks >= settings['market_min_networks']
                         and raw['kind'] == 'observed'))
    return normalized


def _points(market: dict, gross_cost: Decimal, demo: dict) -> list[dict]:
    """Evaluate distinct cents within an observed P25/P75 interval."""
    if not market['usable_for_band']:
        return []
    low = market['p25'].quantize(CENT, rounding=ROUND_CEILING)
    high = market['p75'].quantize(CENT, rounding=ROUND_FLOOR)
    if low > high:
        return []
    median = market['median'].quantize(CENT, rounding=ROUND_HALF_UP)
    center = max(low, min(high, median))
    points = []
    for price in dict.fromkeys((low, center, high)):
        result = personalized_margin(price, gross_cost, demo['taxpayer'],
                                     expenses=demo['expenses'])
        points.append({'price_brl': price,
                       'contribution_brl': result['margin']['contribution_brl'],
                       'contribution_percent': result['margin'][
                           'contribution_percent']})
    return points


def _insights(result: dict) -> list[str]:
    """Describe calculated facts without claiming a personalized tax result."""
    if result['analysis'] is None:
        return ['A sugestão depende de uma referência de mercado atual '
                'com cobertura suficiente para este produto.']
    margin = result['analysis']['personalized']['margin']
    insights = [f"Contribuição no cenário: R$ {margin['contribution_brl']:.2f} "
                f"por unidade ({margin['contribution_percent']:.1f}%)."]
    if margin['contribution_brl'] < 0:
        insights.append('O preço avaliado não cobre custo e tributação estimada.')
    position = result['market_position']
    if position is not None:
        gap = position['gap_percent']
        if gap == 0:
            insights.append('O preço coincide com a mediana da referência '
                            'de mercado informada.')
        else:
            direction = 'acima' if gap > 0 else 'abaixo'
            label = ('referência estimada' if result['market']['kind'] == 'estimated'
                     else 'mediana observada')
            insights.append(f"Na referência de {result['market']['date']}, "
                            f"o preço está {abs(gap):.1f}% {direction} "
                            f'da {label}.')
    if result['market']['status'] == 'historical_reference':
        insights.append('A referência é histórica; não foi usada para '
                        'sugerir um corredor atual.')
    return insights


def analyze_mvp(inputs: dict, market: dict | None = None, *,
                api: str = DEFAULT_API) -> dict:
    """Analyze the selected SKU with only the agreed business inputs.

    Parameters
    ----------
    inputs : dict
        ean, mandatory regime, acquisition_cost and optional selling_price.
        An optional group must match the catalog. No target margin, revenue,
        rates, credit or expense fields are requested from the user.
    market : dict, optional
        Internal exact-SKU snapshot: ean, date, source, median, p25, p75 and
        network_count and kind (observed or estimated).
    api : str
        Configured RTC URL; failure remains separate from demo arithmetic.

    Returns
    -------
    dict
        Product, demonstrative assumptions, contribution, tax estimate,
        market position and a provisional observed band with scenario margins.
        Missing/stale market data never produces an invented current band.
    """
    product = _selected_product(inputs)
    settings = demo_settings()
    cost = Decimal(str(inputs['acquisition_cost']))
    if not isinstance(inputs.get('regime'), str):
        raise ValueError('Company regime is a mandatory selection.')
    demo = build_demo_profile(inputs['regime'], cost, product=product)
    reference = _market(market, product['ean'], settings)
    points = _points(reference, cost, demo)
    price = inputs.get('selling_price')
    origin = 'user_price' if price is not None else 'corridor_scenario'
    if price is None and points:
        center = reference['median'].quantize(CENT, rounding=ROUND_HALF_UP)
        price = max(points[0]['price_brl'], min(points[-1]['price_brl'], center))
    result: dict = {
        'mode': 'demonstration', 'notice': settings['notice'],
        'labels': {'margin': settings['margin_label'], 'tax': settings['tax_label'],
                   'margin_note': settings['margin_note']},
        'product': product, 'assumptions': demo['assumptions'],
        'market': reference, 'corridor_points': points,
        'corridor_method': 'provisional_observed_P25_P75_with_scenario_margins',
        'price_origin': origin, 'evaluated_price_brl': None,
        'analysis': None, 'market_position': None,
        'status': 'pending_market_data', 'pending_internal_data': ['market'],
    }
    if price is not None:
        price = Decimal(str(price))
        candidates = json.loads((ROOT / 'dados/catalogo/'
                                 'classificacoes_experimentais.json').read_text())
        context = {**candidates[product['ncm']], 'year': 2026,
                   'fiscal_date': settings['fiscal_date'],
                   'tax_base_brl': price}
        result = {**result,
            'status': 'ready', 'pending_internal_data': [],
            'evaluated_price_brl': price,
            'analysis': analyze_product(product, context, demo['taxpayer'], {
                'selling_price': price, 'gross_cost': cost, 'price_origin': origin,
                'expenses': demo['expenses']}, api=api),
            'market_position': (market_position(price, reference['median'])
                                if market is not None else None)}
    result['insights'] = _insights(result)
    return result

"""Product-level contract for current-price or corridor-scenario analysis."""
from datetime import date

from tax_pricing.personalized_tax import personalized_margin
from tax_pricing.rtc_service import DEFAULT_API, calculate_current_tax


def analyze_product(product: dict, fiscal_context: dict, taxpayer: dict,
                    pricing: dict, api: str = DEFAULT_API) -> dict:
    """Keep personalized deductions separate from the RTC calculation.

    Parameters
    ----------
    product : dict
        Selected catalog EAN and NCM.
    fiscal_context : dict
        Explicit fiscal_date/year/CST/cclass and optional tax_base_brl.
        An absent fiscal base means the RTC panel is pending, not zero.
    taxpayer : dict
        Personalized regime, competence, sourced tax components and credits.
    pricing : dict
        selling_price, gross_cost, expenses and price_origin, either
        user_price or corridor_scenario. No target margin is requested.
    api : str
        Configured official RTC service URL.

    Returns
    -------
    dict
        Personalized margin and a separate RTC evidence panel. A transport
        failure does not overwrite supplied taxpayer deductions with zero.
    """
    origin = pricing.get('price_origin')
    if origin not in ('user_price', 'corridor_scenario'):
        raise ValueError('Price origin must distinguish user and scenario.')
    day = fiscal_context.get('fiscal_date')
    if (not isinstance(day, str) or len(day) != 10
            or taxpayer.get('competence') != day[:7]):
        raise ValueError('Taxpayer competence must match the fiscal context.')
    parsed = date.fromisoformat(day)
    if parsed.isoformat() != day or parsed.year != 2026:
        raise ValueError('An explicit current-year fiscal date is required.')
    margin = personalized_margin(pricing['selling_price'], pricing['gross_cost'],
                                 taxpayer, expenses=pricing['expenses'])
    panel: dict = {'status': 'pending_fiscal_base', 'result': None}
    base = fiscal_context.get('tax_base_brl')
    if base is not None:
        try:
            panel = {'status': 'calculated_ibs_cbs', 'result': (
                calculate_current_tax(product, fiscal_context, base, api=api))}
        except RuntimeError as error:
            panel = {'status': 'unavailable', 'result': None,
                     'reason': str(error)}
        except ValueError as error:
            panel = {'status': 'invalid_fiscal_context', 'result': None,
                     'reason': str(error)}
    return {'ean': product['ean'], 'ncm': product['ncm'],
            'price_origin': origin, 'personalized': margin, 'rtc': panel,
            'rtc_role': 'separate_ibs_cbs_evidence_not_added_to_margin'}

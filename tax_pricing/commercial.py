"""Selling-price arithmetic; fiscal parameters must be supplied explicitly."""
from decimal import Decimal

from tax_pricing.economics import contribution_margin, required_base


def _nonnegative(value: Decimal) -> None:
    """Reject unavailable, nonfinite or negative numeric assumptions."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError('Expected a finite non-negative Decimal.')


def _deductions(tax_rate: Decimal, expense_rate: Decimal,
                expense_per_unit: Decimal) -> Decimal:
    """Validate deductions expressed on the same selling-price basis."""
    for value in (tax_rate, expense_rate, expense_per_unit):
        _nonnegative(value)
    if tax_rate + expense_rate >= 1:
        raise ValueError('Tax plus expense fractions must be below one.')
    return tax_rate + expense_rate


def net_acquisition_cost(gross_cost: Decimal,
                         usable_credit: Decimal) -> Decimal:
    """Subtract an explicitly established purchase credit once.

    Parameters
    ----------
    gross_cost, usable_credit : Decimal
        Acquisition cost and usable credit per unit in BRL. Eligibility is
        established outside this arithmetic; never inferred from sale tax.

    Returns
    -------
    Decimal
        Cost net of the declared credit. Zero credit must be explicit.
    """
    _nonnegative(gross_cost)
    _nonnegative(usable_credit)
    if usable_credit > gross_cost:
        raise ValueError('Credit cannot exceed acquisition cost.')
    return gross_cost - usable_credit


def margin_breakdown(selling_price: Decimal, net_cost: Decimal, *,
                     tax_rate: Decimal, expense_rate: Decimal,
                     expense_per_unit: Decimal) -> dict[str, Decimal]:
    """Decompose the consumer selling price using declared deductions.

    Parameters
    ----------
    selling_price, net_cost : Decimal
        Positive selling price and non-negative net acquisition cost in BRL.
    tax_rate, expense_rate : Decimal
        Fractions deducted from that same selling price. Tax must already
        reflect the selected scenario and coverage; no regime is inferred.
    expense_per_unit : Decimal
        Additional variable expense per sold unit in BRL, not fixed overhead.

    Returns
    -------
    dict
        Price tree, contribution in BRL and percentage of selling price.
        Intermediate amounts retain precision; round only for display.
    """
    deduction = _deductions(tax_rate, expense_rate, expense_per_unit)
    fraction = contribution_margin(selling_price,
                                   net_cost + expense_per_unit, deduction)
    _nonnegative(net_cost)
    return {
        'selling_price_brl': selling_price,
        'net_cost_brl': net_cost,
        'tax_brl': selling_price * tax_rate,
        'expense_brl': selling_price * expense_rate + expense_per_unit,
        'contribution_brl': (selling_price * (1 - deduction)
                             - net_cost - expense_per_unit),
        'contribution_percent': fraction * 100,
    }


def required_selling_price(net_cost: Decimal, target_margin: Decimal, *,
                           tax_rate: Decimal, expense_rate: Decimal,
                           expense_per_unit: Decimal) -> Decimal:
    """Return the minimum selling cent meeting the target in this model.

    Parameters
    ----------
    net_cost, expense_per_unit : Decimal
        Net acquisition cost and additional variable expense per unit in BRL.
    target_margin : Decimal
        Contribution target as a fraction of the same selling price.
    tax_rate, expense_rate : Decimal
        Constant deductions on selling price for the declared scenario.
        Recompute outside this formula if a rate changes with the price.

    Returns
    -------
    Decimal
        Positive price rounded upwards to cents. Excludes demand optimization
        and nonlinear or amount-specific tax rules.
    """
    _nonnegative(net_cost)
    deduction = _deductions(tax_rate, expense_rate, expense_per_unit)
    price = required_base(net_cost + expense_per_unit, deduction,
                          target_margin)
    if price <= 0:
        raise ValueError('A positive selling price is required.')
    return price


def market_position(selling_price: Decimal,
                    reference_price: Decimal) -> dict[str, Decimal]:
    """Compare a selling price with a caller-validated market reference.

    Parameters
    ----------
    selling_price, reference_price : Decimal
        Positive comparable prices, with SKU, packaging and date checked by
        the caller. Reference can retain sub-cent precision, e.g. a median.

    Returns
    -------
    dict
        Index with reference 100, signed BRL and percentage differences.
        Reference source and coverage must accompany these figures in output.
    """
    for value in (selling_price, reference_price):
        _nonnegative(value)
        if value == 0:
            raise ValueError('Comparison prices must be positive.')
    ratio = selling_price / reference_price
    return {'price_index': ratio * 100,
            'gap_brl': selling_price - reference_price,
            'gap_percent': (ratio - 1) * 100}

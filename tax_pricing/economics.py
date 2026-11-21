"""Contribution margin on revenue excluding IBS/CBS; not net profit."""
from decimal import Decimal, ROUND_CEILING

CENT = Decimal('0.01')


def _validate(cost: Decimal, expense: Decimal) -> None:
    """Reject invalid cost or variable expense fractions."""
    if not cost.is_finite() or cost < 0:
        raise ValueError('Cost must be finite and non-negative.')
    if not expense.is_finite() or not Decimal(0) <= expense < 1:
        raise ValueError('Expense fraction must be finite in [0, 1).')


def required_base(cost: Decimal, expense: Decimal,
                  target: Decimal) -> Decimal:
    """Return the minimum cent of revenue meeting the declared target.

    Parameters
    ----------
    cost : Decimal
        Acquisition cost already net of usable credits, in reais.
    expense : Decimal
        Variable expenses as a fraction of revenue excluding IBS/CBS.
    target : Decimal
        Contribution margin target on that same revenue.

    Returns
    -------
    Decimal
        Required revenue excluding IBS/CBS, rounded upwards to cents.
    """
    _validate(cost, expense)
    if (not target.is_finite() or target < 0
            or expense + target >= 1):
        raise ValueError('Target must be non-negative; expenses + target < 1.')
    return (cost / (1 - expense - target)).quantize(
        CENT, rounding=ROUND_CEILING)


def contribution_margin(base: Decimal, cost: Decimal,
                        expense: Decimal) -> Decimal:
    """Calculate contribution margin on revenue excluding IBS/CBS.

    Parameters
    ----------
    base : Decimal
        Positive revenue excluding IBS/CBS, in reais.
    cost : Decimal
        Acquisition cost net of usable credits, in reais.
    expense : Decimal
        Variable expense fraction on the same revenue.

    Returns
    -------
    Decimal
        Margin as a fraction; losses are returned as negative values.
    """
    _validate(cost, expense)
    if not base.is_finite() or base <= 0:
        raise ValueError('Revenue must be finite and positive.')
    return (base - cost - expense * base) / base

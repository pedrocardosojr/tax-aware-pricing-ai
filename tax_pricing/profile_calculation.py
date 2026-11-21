"""Connect explicit company profiles to conditional commercial arithmetic."""
from decimal import Decimal
from typing import Any

from tax_pricing.commercial import margin_breakdown, net_acquisition_cost
from tax_pricing.fiscal_profile import FiscalProfile


def profile_margin(selling_price: Decimal, gross_cost: Decimal,
                   profile: FiscalProfile, *, expense_rate: Decimal,
                   expense_per_unit: Decimal) -> dict[str, Any]:
    """Calculate only when the profile supplies explicit fiscal assumptions.

    Parameters
    ----------
    selling_price, gross_cost : Decimal
        Final price and gross acquisition cost per unit in BRL.
    profile : FiscalProfile
        Tax fraction, usable credit, provenance and scope of the scenario.
    expense_rate, expense_per_unit : Decimal
        Variable expense fraction on price and additional BRL per sold unit.

    Returns
    -------
    dict
        Scenario status, missing fields and conditional margin, or None when
        the profile is pending. This does not calculate or certify taxes.
    """
    missing = profile.missing_fields()
    result: dict[str, Any] = {
        'business_regime': profile.regime,
        'competence': profile.competence,
        'status': 'pending_profile' if missing else profile.status,
        'missing_fields': missing, 'coverage': profile.coverage,
        'sources': {'tax': profile.tax_source,
                    'credit': profile.credit_source},
        'margin': None,
    }
    if missing:
        return result
    # Narrow the optional fields only after the explicit completeness check.
    if profile.tax_rate is None or profile.usable_credit_brl is None:
        raise ValueError('Missing fiscal assumptions.')
    cost = net_acquisition_cost(gross_cost, profile.usable_credit_brl)
    return {**result, 'margin': margin_breakdown(
        selling_price, cost, tax_rate=profile.tax_rate,
        expense_rate=expense_rate, expense_per_unit=expense_per_unit)}


def simples_effective_rate(rbt12: Decimal, nominal_rate: Decimal,
                           deduction_brl: Decimal) -> Decimal:
    """Apply the official effective-rate formula to supplied table inputs.

    Parameters
    ----------
    rbt12 : Decimal
        Positive revenue over the relevant preceding twelve-month period.
    nominal_rate : Decimal
        Nominal fraction from the applicable annex and bracket, supplied by
        the caller. This function does not select or establish the bracket.
    deduction_brl : Decimal
        Deduction amount from that same applicable bracket in BRL.

    Returns
    -------
    Decimal
        (RBT12 * nominal_rate - deduction) / RBT12, before treatment of
        segregated product revenue, exemptions and other specific rules.
        Not a per-SKU DAS assessment or an automatic rate for the margin.
    """
    for value in (rbt12, nominal_rate, deduction_brl):
        if (not isinstance(value, Decimal) or not value.is_finite()
                or value < 0):
            raise ValueError('Effective-rate inputs must be nonnegative.')
    if rbt12 <= 0 or nominal_rate >= 1:
        raise ValueError('Positive RBT12 and nominal fraction below one needed.')
    rate = (rbt12 * nominal_rate - deduction_brl) / rbt12
    if not 0 <= rate < 1:
        raise ValueError('Inconsistent bracket or deduction inputs.')
    return rate

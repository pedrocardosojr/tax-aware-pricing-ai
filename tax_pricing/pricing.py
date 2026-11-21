"""Commercial inputs kept separate from fiscal scenario assumptions."""
from decimal import Decimal

from tax_pricing.economics import contribution_margin, required_base


# Six independent financial premises stay explicit at the call site.
# pylint: disable-next=too-many-arguments
def commercial_quote(gross_cost: Decimal, recoverable_credit: Decimal,
                     expense: Decimal, target: Decimal, *, regime: str,
                     unified_rate: Decimal) -> dict[str, Decimal]:
    """Price declared inputs without deriving credits or DAS from an NCM.

    Parameters
    ----------
    gross_cost : Decimal
        Acquisition cost paid per unit, in reais and cents.
    recoverable_credit : Decimal
        Explicit usable credit, in reais; not inferred from the sale tax.
    expense : Decimal
        Variable expense fraction on revenue excluding IBS/CBS.
    target : Decimal
        Desired contribution margin on the same revenue, not net profit.
    regime : str
        Experimental profile: regular or simples without regular collection.
    unified_rate : Decimal
        Explicit effective deduction for the Simples profile; zero otherwise.

    Returns
    -------
    dict
        Net cost, deduction, required revenue and achieved margin.
    """
    if regime not in ('regular', 'simples'):
        raise ValueError('Unsupported experimental regime.')
    for money in (gross_cost, recoverable_credit):
        if (not money.is_finite() or money < 0
                or money != money.quantize(Decimal('.01'))):
            raise ValueError('Costs and credits must be finite cents.')
    if gross_cost <= 0 or recoverable_credit >= gross_cost:
        raise ValueError('Cost must be positive and credit smaller than cost.')
    if (not unified_rate.is_finite() or not 0 <= unified_rate < 1
            or not expense.is_finite() or not 0 <= expense < 1):
        raise ValueError('Rates must be finite fractions in [0, 1).')
    if regime == 'simples' and recoverable_credit != 0:
        raise ValueError('This Simples profile does not model credits.')
    if regime == 'regular' and unified_rate != 0:
        raise ValueError('Regular profile does not deduct a unified rate.')
    cost = gross_cost - recoverable_credit
    deduction = expense + unified_rate
    base = required_base(cost, deduction, target)
    return {'gross_cost': gross_cost, 'recoverable_credit': recoverable_credit,
            'net_cost': cost, 'deduction': deduction, 'base': base,
            'achieved_margin': contribution_margin(base, cost, deduction)}

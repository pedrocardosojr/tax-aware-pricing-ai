"""Explicit fiscal assumptions; company regime alone never supplies a rate."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

REGIMES = ('simples_nacional', 'lucro_presumido', 'lucro_real')


@dataclass(frozen=True)
# Eight independent audit fields deliberately remain explicit.
class FiscalProfile:  # pylint: disable=too-many-instance-attributes
    """Carry the provenance and coverage of a declared commercial scenario.

    Parameters
    ----------
    regime, competence : str
        Company regime key and YYYY-MM competence. Not an RTC endpoint name.
    tax_rate, usable_credit_brl : Decimal or None
        Deduction fraction on final selling price and usable purchase credit.
        None means unknown; zero must be established and supplied explicitly.
    tax_source, credit_source, coverage : str
        Origins of both parameters and the scope represented by the rate.
    status : str
        pending, illustrative or declared. No status certifies fiscal review.
    """

    regime: str
    competence: str
    tax_rate: Decimal | None = None
    usable_credit_brl: Decimal | None = None
    tax_source: str = ''
    credit_source: str = ''
    coverage: str = ''
    status: str = 'pending'

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise ValueError('Unsupported company regime.')
        if (not isinstance(self.competence, str) or len(self.competence) != 7
                or date.fromisoformat(self.competence + '-01').strftime(
                    '%Y-%m') != self.competence):
            raise ValueError('Competence must use YYYY-MM.')
        if self.status not in ('pending', 'illustrative', 'declared'):
            raise ValueError('Unknown assessment status.')
        for amount in (self.tax_rate, self.usable_credit_brl):
            if amount is not None and (
                    not isinstance(amount, Decimal)
                    or not amount.is_finite() or amount < 0):
                raise ValueError('Fiscal values must be nonnegative Decimals.')
        if self.tax_rate is not None and self.tax_rate >= 1:
            raise ValueError('Tax fraction must be below one.')
        for text in (self.tax_source, self.credit_source, self.coverage):
            if not isinstance(text, str):
                raise ValueError('Fiscal provenance must be text.')

    def missing_fields(self) -> list[str]:
        """Return unresolved parameters and provenance without guessing them.

        Returns
        -------
        list of str
            Fields needed before exposing even a conditional scenario margin.
        """
        missing = [name for name in ('tax_rate', 'usable_credit_brl')
                   if getattr(self, name) is None]
        missing.extend(name for name in (
            'tax_source', 'credit_source', 'coverage')
            if not getattr(self, name).strip())
        if self.status == 'pending':
            missing.append('assessment_status')
        return missing

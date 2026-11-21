"""Build explicitly fictional MVP profiles without extra user inputs."""
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

from tax_pricing.commercial import net_acquisition_cost
from tax_pricing.profile_calculation import simples_effective_rate
from tax_pricing.product_tax_demo import product_demo_profile

ROOT = Path(__file__).resolve().parents[1]


def demo_settings() -> dict:
    """Load versioned demonstration assumptions, never actual client data.

    Returns
    -------
    dict
        Labels, reference date, three profiles and internal market parameters.
    """
    return json.loads((ROOT / 'dados/tributos/perfis_demo_mvp.json').read_text())


def build_demo_profile(regime: str, gross_cost: Decimal, *,
                       product: dict | None = None) -> dict:
    """Resolve the selected regime into a labeled hypothetical company.

    Parameters
    ----------
    regime : str
        Mandatory company regime selected by the user.
    gross_cost : Decimal
        Acquisition cost per unit. Only the configured hypothetical purchase
        credit fraction is applied; no sale-tax credit is inferred.
    product : dict or None
        Catalogue product selecting a bounded retail demonstration recipe.

    Returns
    -------
    dict
        Taxpayer component contract, expenses and visible demo assumptions.
        Rates, revenue, credit and expense assumptions are not legal defaults.
    """
    settings = demo_settings()
    if regime not in settings['profiles']:
        raise ValueError('Choose a supported company regime.')
    net_acquisition_cost(gross_cost, Decimal(0))
    profile = product_demo_profile(settings['profiles'][regime], regime,
                                   settings, product)
    fraction = Decimal(profile['purchase_credit_fraction'])
    if not fraction.is_finite() or not 0 <= fraction <= 1:
        raise ValueError('Invalid demonstration credit fraction.')
    credit = (gross_cost * fraction).quantize(Decimal('.01'),
                                             rounding=ROUND_HALF_UP)
    st_exclusion = (gross_cost * Decimal(profile.get(
        'purchase_st_exclusion_fraction', '0'))).quantize(
            Decimal('.01'), rounding=ROUND_HALF_UP)
    components = []
    for component in profile['components']:
        if component.get('formula') == 'simples_effective_rate':
            rate = simples_effective_rate(Decimal(profile['rbt12_brl']),
                                         Decimal(profile['nominal_fraction']),
                                         Decimal(profile['deduction_brl']))
            rate *= 1 - Decimal(profile.get('simples_excluded_share', '0'))
        else:
            rate = Decimal(component['rate'])
        components.append({**component, 'rate': rate,
                           'source': component.get('source',
                               'versioned hypothetical MVP assumptions')})
    return {
        'taxpayer': {
            'regime': regime, 'competence': settings['fiscal_date'][:7],
            'scope': 'MVP demonstration, not actual taxpayer liability',
            'coverage_confirmed': True, 'icms_outside_das': False,
            'usable_purchase_credit_brl': credit,
            'purchase_credit_source': profile['purchase_credit_basis'],
            'purchase_icms_st_exclusion_brl': st_exclusion,
            'purchase_icms_st_exclusion_source': (
                'Parcela de ICMS-ST fictícia configurada internamente; '
                'não é alíquota legal nem crédito recuperável.'),
            'tax_components': components},
        'expenses': {'rate': Decimal(settings['expense_rate']),
                     'per_unit_brl': Decimal(settings['expense_per_unit_brl'])},
        'assumptions': {'mode': 'demonstration', 'regime': regime,
                        'profile': profile,
                        'product_tax': profile['product_tax'],
                        'purchase_icms_st_exclusion_brl': st_exclusion,
                        'credit_fraction': fraction, 'credit_brl': credit,
                        'expense_rate': settings['expense_rate'],
                        'expense_per_unit_brl': settings['expense_per_unit_brl'],
                        'rtc_base_rule': settings['rtc_base_rule']},
    }

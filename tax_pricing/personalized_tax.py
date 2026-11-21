"""Personalized price analysis from sourced taxpayer deduction components."""
from decimal import Decimal
from typing import Any

from tax_pricing.commercial import margin_breakdown, net_acquisition_cost
from tax_pricing.fiscal_profile import FiscalProfile

REQUIRED = {'simples_nacional': ('DAS',),
            'lucro_presumido': ('ICMS', 'PIS', 'COFINS'),
            'lucro_real': ('ICMS', 'PIS', 'COFINS')}
ALLOWED = {'DAS', 'ICMS', 'PIS', 'COFINS', 'IBS', 'CBS', 'IS'}
BASES = {'selling_price', 'selling_price_less_icms',
         'selling_price_less_purchase_icms_st'}


def _rule(row: dict) -> list[str]:
    """Validate one supplied tax component and list missing evidence."""
    name = row['name']
    missing = []
    rate = row.get('rate')
    if rate is None:
        missing.append(f'{name}.rate')
    elif (not isinstance(rate, Decimal) or not rate.is_finite()
          or not 0 <= rate < 1):
        raise ValueError('Component rates must be Decimal fractions.')
    for key in ('basis', 'source'):
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            missing.append(f'{name}.{key}')
    basis = row.get('basis')
    if basis and (basis not in BASES or (
            name in ('ICMS', 'DAS') and basis != 'selling_price')):
        raise ValueError('Unsupported tax basis recipe.')
    return missing


def _regime_requirements(profile: dict, rules: dict) -> list[str]:
    """Check the retail contract, especially deductions already inside DAS."""
    missing = [name for name in REQUIRED[profile['regime']] if name not in rules]
    if profile['regime'] != 'simples_nacional':
        if 'DAS' in rules:
            raise ValueError('DAS is not a deduction for this company regime.')
        return missing
    outside = profile.get('icms_outside_das')
    if not isinstance(outside, bool):
        missing.append('icms_outside_das')
    if outside is True:
        if 'ICMS' not in rules:
            missing.append('ICMS')
        if rules.get('DAS', {}).get('excludes_icms') is not True:
            missing.append('DAS.excludes_icms')
    elif 'ICMS' in rules:
        raise ValueError('Separate ICMS requires an outside-DAS profile.')
    if any(name in rules for name in ('PIS', 'COFINS')):
        raise ValueError('Separate contributions with DAS need another scope.')
    return missing


def _st_exclusion_requirements(profile: dict, rules: dict) -> list[str]:
    """Require an amount and provenance for excluding embedded purchase ST."""
    missing = []
    if any(row.get('basis') == 'selling_price_less_purchase_icms_st'
           for row in rules.values()):
        amount = profile.get('purchase_icms_st_exclusion_brl')
        if amount is None:
            missing.append('purchase_icms_st_exclusion_brl')
        elif (not isinstance(amount, Decimal) or not amount.is_finite()
              or amount < 0):
            raise ValueError('ST exclusion must be a nonnegative Decimal.')
        if not profile.get('purchase_icms_st_exclusion_source'):
            missing.append('purchase_icms_st_exclusion_source')
    return missing


def _rules(profile: dict) -> tuple[dict[str, dict], list[str]]:
    """Validate supplied component recipes and list unresolved data."""
    FiscalProfile(profile['regime'], profile['competence'])
    rows = profile.get('tax_components', [])
    if not isinstance(rows, list):
        raise ValueError('tax_components must be a list.')
    rules: dict[str, dict] = {}
    missing = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each tax component must be an object.')
        name = row.get('name')
        if name not in ALLOWED or name in rules:
            raise ValueError('Unknown or duplicate tax component.')
        rules[name] = row
        missing.extend(_rule(row))
    missing.extend(_regime_requirements(profile, rules))
    for name, rule in rules.items():
        if rule.get('basis') == 'selling_price_less_icms' and 'ICMS' not in rules:
            missing.append(f'{name}.ICMS_basis')
    missing.extend(_st_exclusion_requirements(profile, rules))
    for key in ('scope', 'purchase_credit_source'):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            missing.append(key)
    if profile.get('usable_purchase_credit_brl') is None:
        missing.append('usable_purchase_credit_brl')
    if profile.get('coverage_confirmed') is not True:
        missing.append('coverage_confirmed')
    return rules, sorted(set(missing))


def _components(price: Decimal, rules: dict[str, dict],
                st_exclusion: Decimal = Decimal(0)) -> list[dict]:
    """Evaluate every explicit recipe on its own base, retaining precision."""
    icms = price * rules['ICMS']['rate'] if 'ICMS' in rules else Decimal(0)
    components = []
    for name, rule in rules.items():
        base = {'selling_price': price,
                'selling_price_less_icms': price - icms,
                'selling_price_less_purchase_icms_st': max(
                    Decimal(0), price - st_exclusion)}[rule['basis']]
        components.append({'name': name, 'base_brl': base,
                           'rate': rule['rate'], 'amount_brl': base * rule['rate'],
                           'basis': rule['basis'], 'source': rule['source']})
    return components


def personalized_margin(selling_price: Decimal, gross_cost: Decimal,
                        profile: dict, *, expenses: dict) -> dict[str, Any]:
    """Reconcile sourced personalized deductions and variable contribution.

    Parameters
    ----------
    selling_price, gross_cost : Decimal
        Final consumer price and gross acquisition cost per unit in BRL.
    profile : dict
        Company regime, competence, explicit component rate/base/source,
        declared coverage and eligible purchase credit with its source.
        Required components define this retail contract, not universal law.
    expenses : dict
        Explicit rate on selling price and per_unit_brl variable expense.

    Returns
    -------
    dict
        Reconciled tax ledger and conditional margin from supplied data, or
        pending fields with margin=None. Does not select product tax treatment,
        establish credit eligibility, certify liability or calculate net profit.
        RTC calculated IBS/CBS must not be imported as paid tax automatically.
    """
    initial = margin_breakdown(selling_price, gross_cost, tax_rate=Decimal(0),
                               expense_rate=expenses['rate'],
                               expense_per_unit=expenses['per_unit_brl'])
    rules, missing = _rules(profile)
    result: dict[str, Any] = {
        'regime': profile['regime'], 'competence': profile['competence'],
        'status': 'pending_taxpayer_data' if missing else (
            'calculated_from_supplied_profile'),
        'missing_fields': missing, 'scope': profile.get('scope'),
        'fiscal_validation': 'not_certified', 'margin': None,
        'tax_components': None, 'tax_total_brl': None,
    }
    if missing:
        return result
    cost = net_acquisition_cost(gross_cost,
                                profile['usable_purchase_credit_brl'])
    st_exclusion = profile.get('purchase_icms_st_exclusion_brl', Decimal(0))
    if st_exclusion > gross_cost:
        raise ValueError('Embedded ST exclusion cannot exceed gross cost.')
    components = _components(selling_price, rules, st_exclusion)
    total = sum((row['amount_brl'] for row in components), Decimal(0))
    contribution = selling_price - cost - initial['expense_brl'] - total
    return {**result, 'tax_components': components, 'tax_total_brl': total,
            'purchase_credit_source': profile['purchase_credit_source'],
            'margin': {**initial, 'net_cost_brl': cost, 'tax_brl': total,
                       'contribution_brl': contribution,
                       'contribution_percent': contribution / selling_price * 100}}

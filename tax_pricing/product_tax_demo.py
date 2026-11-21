"""Select catalogue source-based retail scenarios with explicit fictional conditions."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / 'dados/tributos/revisao_2026_11.json'


def product_demo_profile(profile: dict, regime: str, settings: dict,
                         product: dict | None) -> dict:
    """Apply a bounded product recipe, never certify taxpayer eligibility.

    Parameters
    ----------
    profile : dict
        Generic illustrative company profile, copied before applying changes.
    regime : str
        Mandatory company regime already selected in the MVP.
    settings : dict
        Demonstration date and general assumptions.
    product : dict or None
        Catalogue EAN/NCM, supplied internally without additional user inputs.

    Returns
    -------
    dict
        Product-specific profile with sources and assumed operation conditions,
        or an explicitly unreviewed generic profile.
    """
    resolved = deepcopy(profile)
    rules = json.loads(RULES.read_text())
    recipe = rules['products'].get(product['ean']) if product else None
    resolved['product_tax'] = {
        'status': 'generic_illustrative_unreviewed',
        'label': 'Perfil didático genérico; tratamento deste SKU não revisado.',
        'conditions': ['Crédito e taxas são hipóteses, não dados da NF-e.'],
        'source_urls': [],
    }
    if recipe is None:
        return resolved
    if product is None or product['ncm'] != recipe['ncm']:
        raise ValueError('Product NCM differs from the reviewed demo recipe.')
    day = date.fromisoformat(settings['fiscal_date'])
    if not (date.fromisoformat(rules['valid_from']) <= day
            <= date.fromisoformat(rules['valid_through'])):
        raise ValueError('Product demo recipe requires a new dated review.')
    resolved['product_tax'] = {
        'status': rules['status'], 'label': recipe['label'],
        'conditions': recipe['conditions'],
        'interpretation_note': recipe['interpretation_note'],
        'source_urls': [rules['sources'][key] for key in recipe['source_keys']],
        'review_date': rules['retrieved_on'],
        'purchase_icms_st_assumed': recipe.get('family') in {
            'cold_beverage_retail_st', 'hygiene_st_linear_reduction',
            'natural_mineral_water_st', 'uht_milk_retail_st',
        },
    }
    resolved['purchase_credit_fraction'] = '0'
    resolved['purchase_credit_basis'] = (
        'No cenário escolhido não há crédito recuperável da compra; '
        'Condições precisam da NF-e real.')
    resolved['purchase_credit_basis'] = recipe.get(
        'purchase_credit_basis', resolved['purchase_credit_basis'])
    if regime == 'simples_nacional':
        if (profile['rbt12_brl'], profile['nominal_fraction'],
                profile['deduction_brl']) != ('360000', '0.073', '5940'):
            raise ValueError('Revenue bracket changed; review the DAS shares.')
        resolved['simples_excluded_share'] = recipe['simples_excluded_share']
        resolved['components'][0]['source'] = '; '.join(
            resolved['product_tax']['source_urls'])
    else:
        for row in resolved['components']:
            row['rate'] = ('0' if row['name'] == 'ICMS' else
                           str(Decimal(row['rate']) * Decimal(
                               recipe['regular_pis_cofins_factor'])))
            row['basis'] = 'selling_price'
            row['source'] = '; '.join(resolved['product_tax']['source_urls'])
            if row['name'] in ('PIS', 'COFINS'):
                row['basis'] = 'selling_price_less_purchase_icms_st'
        resolved['purchase_st_exclusion_fraction'] = recipe[
            'purchase_st_exclusion_fraction']
    return resolved

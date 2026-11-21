"""Describe the RTC tax calculation for a future user-facing result panel."""
from decimal import Decimal, InvalidOperation
from typing import Any

from tax_pricing.rtc import read_tax


def _number(value: Any, *, percent: bool = False) -> Decimal:
    """Validate a nonnegative number received from the engine."""
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError('Expected a finite nonnegative tax value.')
    if percent and number > 100:
        raise ValueError('Expected a percentage in [0, 100].')
    if not percent and number != number.quantize(Decimal('.01')):
        raise ValueError('Expected a monetary value in cents.')
    return number


def _component(group: dict, label: str, rate_key: str,
               amount_key: str) -> dict:
    """Read the reference/reduced rate and amount for one tax component."""
    reference = _number(group[rate_key], percent=True)
    if 'gRed' in group:
        reduction = _number(group['gRed']['pRedAliq'], percent=True)
        effective = _number(group['gRed']['pAliqEfet'], percent=True)
    else:
        reduction, effective = Decimal(0), reference
    return {'label': label, 'reference_rate_percent': reference,
            'reduction_percent': reduction,
            'effective_rate_percent': effective,
            'amount_brl': _number(group[amount_key])}


def summarize_tax(response: dict) -> dict:
    """Expose factual IBS/CBS details for a single regular/reduced item.

    Parameters
    ----------
    response : dict
        Successful RTC JSON body with CST 000 or 200. HTTP status is checked
        by the caller. Current catalog scenarios use these two CSTs.

    Returns
    -------
    dict
        Base, classification, reference/effective rates, reductions and
        official amounts. Coverage flags identify IBS/CBS calculation and
        keep the full taxpayer burden pending a separate profile assessment.
    """
    total = read_tax(response)
    try:
        item = response['objetos'][0]
        classification = item['tribCalc']['IBSCBS']
        if classification['CST'] not in ('000', '200'):
            raise ValueError('Tax summary supports catalog CST 000 and 200.')
        group = classification['gIBSCBS']
        simulated = item['calculoSimulado']
        if not isinstance(simulated, bool):
            raise ValueError('Simulation flag must be explicit.')
        components = [
            _component(group['gCBS'], 'CBS', 'pCBS', 'vCBS'),
            _component(group['gIBSUF'], 'IBS estadual', 'pIBSUF', 'vIBSUF'),
            _component(group['gIBSMun'], 'IBS municipal',
                       'pIBSMun', 'vIBSMun')]
        return {'tax_base_brl': _number(group['vBC']),
                'classification': {'cst': classification['CST'],
                                   'cclass': classification['cClassTrib']},
                'simulated': simulated, 'components': components,
                'ibs_official_total_brl': _number(group['vIBS']),
                'total_ibs_cbs_brl': total,
                'coverage': 'IBS/CBS calculated by RTC',
                'total_tax_burden_calculated': False,
                'payment_assessment': 'requires_taxpayer_profile',
                'other_taxes': {'ICMS': 'outside_response',
                                'PIS/COFINS': 'outside_response',
                                'DAS': 'outside_response'}}
    except (KeyError, IndexError, TypeError, InvalidOperation) as error:
        raise ValueError('Incomplete or invalid RTC tax detail.') from error

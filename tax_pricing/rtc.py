"""Reusable adapter for the official local RTC, with explicit scenarios."""
from decimal import Decimal, InvalidOperation
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CENT = Decimal('.01')


def build_operation(product: dict, scenario: dict, base: Decimal,
                    doc: int = 65) -> dict:
    """Build a Curitiba test operation; require explicit future rates.

    Parameters
    ----------
    product : dict
        Textual ean and eight-digit ncm.
    scenario : dict
        Integer year, cst, cclass and future nominal_rates in percent.
    base : Decimal
        Positive revenue base in cents, excluding IBS/CBS.
    doc : int
        Supported experimental document, 55 or 65.

    Returns
    -------
    dict
        RTC request. Compatibility still requires an engine check.
    """
    if (not base.is_finite() or base <= 0
            or base != base.quantize(CENT)):
        raise ValueError('Base must be positive, finite and in cents.')
    for code, length in ((product.get('ncm'), 8),
                         (scenario.get('cst'), 3),
                         (scenario.get('cclass'), 6)):
        if (not isinstance(code, str) or not code.isascii()
                or not code.isdigit() or len(code) != length):
            raise ValueError('NCM, CST and classification must be explicit.')
    year = scenario.get('year')
    if (not isinstance(year, int) or isinstance(year, bool)
            or not 2026 <= year <= 2033):
        raise ValueError('Supported experiment years: 2026 through 2033.')
    if doc not in (55, 65):
        raise ValueError('Supported experimental documents: 55 and 65.')
    item = {'numero': 1, 'ncm': product['ncm'], 'cst': scenario['cst'],
            'cClassTrib': scenario['cclass'], 'baseCalculo': float(base),
            'quantidade': 1, 'unidade': 'UN'}
    rates = scenario.get('nominal_rates')
    if year >= 2027:
        keys = {'cbs', 'ibsEstadual', 'ibsMunicipal'}
        if not isinstance(rates, dict) or set(rates) != keys:
            raise ValueError('Future nominal rates must be explicit.')
        for value in rates.values():
            number = Decimal(str(value))
            if not number.is_finite() or not 0 <= number <= 100:
                raise ValueError('Nominal rates must be finite percentages.')
        item['aliquotasNominais'] = {k: float(v) for k, v in rates.items()}
    elif rates is not None:
        raise ValueError('The 2026 experiment uses the engine rates.')
    return {'id': f"experiment-{product['ean']}-{year}-{doc}",
            'versao': '0.0.1',
            'dhFatoGerador': f'{year}-10-01T12:00:00-03:00',
            'municipio': 4106902, 'uf': 'PR', 'tpDoc': doc, 'itens': [item]}


def read_tax(response: dict) -> Decimal:
    """Extract official aggregate IBS plus CBS, rejecting malformed values.

    Parameters
    ----------
    response : dict
        Successful RTC JSON body for exactly one item.

    Returns
    -------
    Decimal
        Nonnegative IBS/CBS, preserving the returned aggregate.
    """
    try:
        if len(response['objetos']) != 1:
            raise ValueError('Expected exactly one calculated item.')
        group = response['objetos'][0]['tribCalc']['IBSCBS']['gIBSCBS']
        values = [Decimal(str(group['vIBS'])),
                  Decimal(str(group['gCBS']['vCBS']))]
        if any(not v.is_finite() or v < 0 or v != v.quantize(CENT)
               for v in values):
            raise ValueError('Tax must be nonnegative and in cents.')
        return sum(values, Decimal(0))
    except (KeyError, IndexError, TypeError, InvalidOperation) as error:
        raise ValueError('Malformed RTC tax response.') from error


def call_rtc(path: str, payload: dict | None = None,
             api: str = 'http://127.0.0.1:8080/api') -> dict[str, Any]:
    """Call RTC with a bounded timeout and retain HTTP errors as evidence.

    Parameters
    ----------
    path : str
        RTC endpoint path, optionally including a query string.
    payload : dict, optional
        POST body; absent means GET.
    api : str
        Local or explicitly configured RTC base URL.

    Returns
    -------
    dict
        Request, HTTP status and parsed body; callers must check status.
    """
    request = Request(api + path, headers={
        'Content-Type': 'application/json'}, data=(
            json.dumps(payload).encode() if payload is not None else None))
    try:
        # HTTP errors also provide a context-managed response.
        # pylint: disable-next=consider-using-with
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        response = error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(
            'RTC unavailable; no tax estimate produced.') from error
    with response:
        raw = response.read().decode()
        try:
            body = json.loads(raw, parse_float=Decimal)
        except json.JSONDecodeError as error:
            raise RuntimeError('RTC returned invalid JSON.') from error
        return {'path': path, 'request': payload,
                'status': response.code, 'body': body}

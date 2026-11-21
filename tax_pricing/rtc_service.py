"""Current-year RTC service with explicit fiscal context and response checks."""
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from tax_pricing.rtc import build_operation, call_rtc
from tax_pricing.tax_summary import summarize_tax

DEFAULT_API = 'http://127.0.0.1:8080/api'
SUPPORTED_ENGINES = {('1.5.4', 'V0059', 'offline'),
                     ('1.6.2', 'V0066', 'offline')}


def _body(call: dict) -> dict:
    """Reject HTTP failures and malformed bodies before reading tax values."""
    if call['status'] != 200 or not isinstance(call['body'], dict):
        raise RuntimeError(f"RTC call failed with HTTP {call['status']}.")
    return call['body']


def _operation(product: dict, scenario: dict, base: Decimal) -> dict:
    """Require a canonical 2026 fiscal date instead of a hidden test date."""
    day = scenario.get('fiscal_date')
    if not isinstance(day, str):
        raise ValueError('Explicit fiscal_date in YYYY-MM-DD is required.')
    parsed = date.fromisoformat(day)
    if (parsed.isoformat() != day or parsed.year != 2026
            or scenario.get('year') != 2026):
        raise ValueError('Current service supports explicit 2026 dates only.')
    operation = build_operation(product, scenario, base)
    operation['dhFatoGerador'] = f'{day}T12:00:00-03:00'
    operation['id'] = f"current-{product['ean']}-{day}"
    return operation


def calculate_current_tax(product: dict, scenario: dict, tax_base: Decimal,
                          api: str = DEFAULT_API) -> dict:
    """Calculate IBS/CBS with traceable context, not company tax liability.

    Parameters
    ----------
    product : dict
        Catalog EAN and NCM, kept textual.
    scenario : dict
        year=2026, explicit fiscal_date, CST and cclass candidate.
    tax_base : Decimal
        Fiscal base excluding IBS/CBS, positive and in cents. Not acquisition
        cost, nor an automatic conversion of the consumer selling price.
    api : str
        Configured RTC base URL; defaults to the official local runtime.

    Returns
    -------
    dict
        Checked request, engine version, summary and complete call evidence.
        Classification review and company assessment remain explicit.
    """
    operation = _operation(product, scenario, tax_base)
    calls = []

    def request(path: str, payload: dict | None = None) -> dict:
        call = call_rtc(path, payload, api=api)
        calls.append(call)
        return _body(call)

    version = request('/calculadora/dados-abertos/versao')
    if (version.get('versaoApp'), version.get('versaoDb'),
            version.get('ambiente')) not in SUPPORTED_ENGINES:
        raise RuntimeError('Untested RTC version; revalidate before use.')
    query = urlencode({'cClassTrib': scenario['cclass'],
                       'ncm': product['ncm'],
                       'dataOcorrenciaFatoGerador': scenario['fiscal_date']})
    compatible = request('/calculadora/dados-abertos/'
                         'classificacoes-tributarias/ncm-aplicavel?' + query)
    if compatible.get('valido') is not True:
        raise ValueError('NCM/classification incompatible for the fiscal date.')
    response = request('/calculadora/regime-geral', operation)
    summary = summarize_tax(response)
    if (summary['tax_base_brl'] != tax_base
            or summary['classification'] != {
                'cst': scenario['cst'], 'cclass': scenario['cclass']}
            or summary['simulated'] is not False):
        raise ValueError('RTC response does not match the current request.')
    return {'ean': product['ean'], 'ncm': product['ncm'],
            'engine': version, 'request': operation, 'summary': summary,
            'classification_review': 'pending',
            'company_tax_assessment': 'not_calculated', 'calls': calls}

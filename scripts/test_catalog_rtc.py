"""Test the current 2026 RTC scope; future years require explicit opt-in."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from typing import Callable

from tax_pricing.catalog import load_catalog
from tax_pricing.rtc import build_operation, call_rtc
from tax_pricing.tax_summary import summarize_tax

ROOT = Path(__file__).resolve().parents[1]
TAX_BASE = Decimal('133.34')
RATES = {'cbs': 8.8, 'ibsEstadual': 8.85, 'ibsMunicipal': 8.85}


def _successful_body(call: dict) -> dict:
    """Never treat an HTTP error as a zero-tax response."""
    if call['status'] != 200:
        raise RuntimeError(f"RTC HTTP {call['status']}: {call['body']}")
    return call['body']


def _check_case(product: dict, candidate: dict | None, year: int,
                request: Callable) -> dict:
    """Keep unavailable classification/IS separate from success."""
    row: dict = {'ean': product['ean'], 'ncm': product['ncm'],
                 'year': year, 'status': 'error',
                 'fiscal_review_status': 'pending',
                 'scope': 'experimental_ibs_cbs_only'}
    if not candidate:
        return {**row, 'status': 'blocked',
                'reason': 'Missing explicit classification'}
    try:
        scenario = {**candidate, 'year': year}
        if year >= 2027:
            scenario['nominal_rates'] = RATES
        query = urlencode({'cClassTrib': candidate['cclass'],
                           'ncm': product['ncm'],
                           'dataOcorrenciaFatoGerador': f'{year}-10-01'})
        body = _successful_body(request('/calculadora/dados-abertos/'
                                        'classificacoes-tributarias/'
                                        'ncm-aplicavel?' + query))
        if body.get('valido') is not True:
            raise ValueError('NCM/classification incompatible.')
        call = request('/calculadora/regime-geral',
                       build_operation(product, scenario, TAX_BASE))
        if (call['status'] == 422 and call['body'].get('type', '').endswith(
                '/dados-imposto-seletivo-nao-informados')):
            return {**row, 'status': 'blocked',
                    'reason': 'RTC requires explicit Imposto Seletivo data',
                    'http_status': 422}
        body = _successful_body(call)
        detail = summarize_tax(body)
        tax = detail['total_ibs_cbs_brl']
        simulated = body['objetos'][0]['calculoSimulado']
        if simulated is not (year >= 2027):
            raise ValueError('Unexpected simulation flag.')
        row.update(status='passed', ibs_cbs=tax, simulated=simulated,
                   tax_detail=detail)
    except (ValueError, RuntimeError, KeyError) as error:
        row['reason'] = str(error)
    return row


def run_catalog(catalog: Path, profiles: Path, output: Path,
                years: tuple[int, ...] = (2026,)) -> dict:
    """Record compatibility and tax calculations.

    Parameters
    ----------
    catalog : Path
        JSON snapshot with products and source provenance.
    profiles : Path
        Explicit experimental NCM/CST/classification candidates.
    output : Path
        New evidence directory; existing results are never overwritten.

    years : tuple
        Explicit years to test. The default delivery covers 2026.

    Returns
    -------
    dict
        Technical matrix, separate from pending independent fiscal review.
    """
    if not years or len(set(years)) != len(years):
        raise ValueError('Choose distinct scenario years.')
    if any(year not in range(2026, 2034) for year in years):
        raise ValueError('Supported scenario years: 2026 through 2033.')
    products = load_catalog(catalog)
    candidates = json.loads(profiles.read_text())
    output.mkdir(parents=True, exist_ok=False)
    calls: list[dict] = []
    rows: list[dict] = []

    def request(path: str, payload: dict | None = None) -> dict:
        result = call_rtc(path, payload)
        calls.append(result)
        return result

    try:
        version_call = request('/calculadora/dados-abertos/versao')
        version = _successful_body(version_call)
        if (version.get('versaoApp'), version.get('versaoDb'),
                version.get('ambiente')) != ('1.5.4', 'V0059', 'offline'):
            raise RuntimeError('Unexpected RTC version; revalidate baseline.')
        for product in products:
            for year in years:
                candidate = candidates.get(product['ncm'])
                rows.append(_check_case(product, candidate, year, request))
        result = {
            'executed_at_utc': datetime.now(timezone.utc).isoformat(),
            'engine': version, 'products': len(products),
            'distinct_ncms': len({p['ncm'] for p in products}),
            'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(),
            'profiles_sha256': hashlib.sha256(
                profiles.read_bytes()).hexdigest(),
            'scenario_years': list(years),
            'fiscal_dates': [f'{year}-10-01' for year in years],
            'future_nominal_rates_illustrative_percent': (
                RATES if any(year >= 2027 for year in years) else None),
            'tax_base_brl': TAX_BASE,
            'passed': sum(r['status'] == 'passed' for r in rows),
            'blocked': sum(r['status'] == 'blocked' for r in rows),
            'errors': sum(r['status'] == 'error' for r in rows),
            'rows': rows}
        (output / 'result.json').write_text(json.dumps(
            result, ensure_ascii=False, indent=2, default=str) + '\n')
        return result
    finally:
        (output / 'calls.json').write_text(json.dumps(
            calls, ensure_ascii=False, indent=2, default=str) + '\n')


def main() -> None:
    """Run against the official local offline service, retaining evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=(
        ROOT / 'dados/catalogo/skus_50.json'))
    parser.add_argument('--profiles', type=Path, default=(
        ROOT / 'dados/catalogo/classificacoes_experimentais.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--years', nargs='+', type=int,
                        choices=range(2026, 2034), default=[2026])
    args = parser.parse_args()
    result = run_catalog(args.catalog, args.profiles, args.output,
                         years=tuple(args.years))
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'},
                     ensure_ascii=False, indent=2, default=str))
    if result['errors']:
        raise SystemExit(1)
    if result['blocked']:
        print('Incomplete fiscal scenarios: inspect blocked rows.')
        raise SystemExit(2)


if __name__ == '__main__':
    main()

"""Verify the current-year service against all selected products."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from tax_pricing.catalog import load_catalog
from tax_pricing.rtc_service import DEFAULT_API, calculate_current_tax

ROOT = Path(__file__).resolve().parents[1]


def verify(output: Path, fiscal_date: str, api: str = DEFAULT_API) -> dict:
    """Record the 50-case current service validation without overwriting.

    Parameters
    ----------
    output : Path
        New directory for requests, responses and aggregate results.
    fiscal_date : str
        Explicit YYYY-MM-DD in 2026, checked by the service for every SKU.
    api : str
        Official RTC runtime base URL.

    Returns
    -------
    dict
        Pass/failure totals and trace for a fiscal base of BRL 30 per item.
        This integration run does not validate taxpayer-specific liability.
    """
    catalog = ROOT / 'dados/catalogo/skus_50.json'
    profiles = ROOT / 'dados/catalogo/classificacoes_experimentais.json'
    products = load_catalog(catalog)
    candidates = json.loads(profiles.read_text())
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for product in products:
        row: dict = {'ean': product['ean'], 'product': product['description']}
        try:
            scenario = {**candidates[product['ncm']], 'year': 2026,
                        'fiscal_date': fiscal_date}
            result = calculate_current_tax(product, scenario, Decimal('30'),
                                           api=api)
            row.update(status='passed', result=result)
        except (ValueError, RuntimeError, KeyError) as error:
            row.update(status='error', reason=str(error))
        rows.append(row)
    report = {
        'executed_at_utc': datetime.now(timezone.utc).isoformat(),
        'fiscal_date': fiscal_date, 'tax_base_brl': '30.00',
        'scope': 'experimental_ibs_cbs_only',
        'company_assessment': 'not_calculated',
        'classification_review': 'pending',
        'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(),
        'profiles_sha256': hashlib.sha256(profiles.read_bytes()).hexdigest(),
        'products': len(rows),
        'passed': sum(row['status'] == 'passed' for row in rows),
        'errors': sum(row['status'] == 'error' for row in rows), 'rows': rows,
    }
    (output / 'result.json').write_text(json.dumps(
        report, default=str, ensure_ascii=False, indent=2) + '\n')
    return report


def main() -> None:
    """Run the declared fiscal date and return nonzero on any case failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fiscal-date', required=True)
    parser.add_argument('--api', default=DEFAULT_API)
    args = parser.parse_args()
    report = verify(args.output, args.fiscal_date, args.api)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'},
                     ensure_ascii=False, indent=2))
    if report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

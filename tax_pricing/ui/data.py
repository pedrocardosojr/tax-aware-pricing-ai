"""Read-only adapters for the catalog and observed market data."""
import csv
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tax_pricing.catalog import load_catalog
from tax_pricing.demo_profile import ROOT
from tax_pricing.market_statistics import comparable_matrix
from tax_pricing.team_market import adapt_team_reference

LAB = ROOT / 'evidencias/market_lab_2026-11-07'
TEAM_MARKET = ROOT / 'evidencias/referencias_edu_2026-11-10'


def products() -> list[dict]:
    """Return the shared selected catalog without changing its records.

    Returns
    -------
    list of dict
        Products used by the group and SKU selectors.
    """
    return load_catalog(ROOT / 'dados/catalogo/skus_50.json')


def market_snapshot(ean: str) -> dict | None:
    """Read a configured per-SKU snapshot or the bundled team reference.

    Parameters
    ----------
    ean : str
        Valid catalog identifier. No free-form filesystem paths are accepted.

    Returns
    -------
    dict or None
        Source/coverage-preserving snapshot. A configured folder takes
        precedence; absent files do not silently use preview data.
    """
    if (not ean.isascii() or not ean.isdigit()
            or len(ean) not in (8, 12, 13, 14)):
        raise ValueError('Invalid catalog identifier.')
    directory = os.environ.get('TAX_PRICING_MARKET_DIR')
    if directory:
        path = Path(directory) / f'{ean}.json'
        return json.loads(path.read_text()) if path.is_file() else None
    path = TEAM_MARKET / 'inputs' / f'{ean}.json'
    if path.is_file():
        payload = json.loads(path.read_text(encoding='utf-8'))
        snapshot = adapt_team_reference(
            payload['reference'], payload['per_network_brl'], source=payload['source'])
        with (TEAM_MARKET / 'status_50.csv').open(encoding='utf-8', newline='') as status:
            row = next((row for row in csv.DictReader(status) if row['id_produto'] == ean),
                       None)
        if row is not None and row['status'] == 'baixa_precisao':
            snapshot['low_precision'] = True
        return snapshot
    path = LAB / f'{ean}.json'
    if path.is_file():
        return json.loads(path.read_text())
    path = ROOT / 'evidencias/mvp_estimativa_2026-11-07/mercado_coca_2l.json'
    snapshot = json.loads(path.read_text())
    return snapshot if snapshot['ean'] == ean else None


def market_extras(ean: str, snapshot_date: str) -> dict | None:
    """Read an optional matching history/cohort contract, with no fallback.

    Parameters
    ----------
    ean, snapshot_date : str
        Selected identifier and the current snapshot date.

    Returns
    -------
    dict or None
        Observed analytical bundle for the same SKU/date, if provided.
    """
    if not ean.isascii() or not ean.isdigit() or len(ean) not in (8, 12, 13, 14):
        raise ValueError('Invalid catalog identifier.')
    configured = os.environ.get('TAX_PRICING_MARKET_DIR')
    directory = Path(configured) if configured else LAB
    path = directory / f'{ean}_analytics.json'
    if not path.is_file():
        return None
    bundle = json.loads(path.read_text())
    if not configured and bundle.get('date') != snapshot_date:
        return None
    if (bundle.get('schema_version') != 1 or bundle.get('ean') != ean
            or bundle.get('date') != snapshot_date):
        raise ValueError('Analytical bundle does not match the selected snapshot.')
    _check_history(bundle.get('history', []), ean, snapshot_date)
    if bundle.get('comparables'):
        matrix = comparable_matrix(bundle['comparables'])
        if (ean not in matrix['eans']
                or matrix['cohort']['date'] != snapshot_date):
            raise ValueError('Comparable cohort does not match the selected SKU/date.')
    return bundle


def _check_history(history: list[dict], ean: str, snapshot_date: str) -> None:
    """Reject future, unordered or non-observed historical summaries."""
    days = []
    for row in history:
        day = date.fromisoformat(row['date'])
        if day.isoformat() != row['date']:
            raise ValueError('Canonical history date required.')
        if (row['ean'] != ean or row['kind'] != 'observed'
                or not row.get('source') or row['date'] > snapshot_date
                or row['network_count'] < 1):
            raise ValueError('History must be observed, sourced and nonfuture.')
        try:
            values = [Decimal(str(row[k])) for k in ('p25', 'median', 'p75')]
        except InvalidOperation as error:
            raise ValueError('Invalid historical price.') from error
        if (any(not v.is_finite() or v <= 0 for v in values)
                or values != sorted(values)):
            raise ValueError('Invalid historical quartiles.')
        days.append(row['date'])
    if days != sorted(set(days)):
        raise ValueError('Historical periods must be unique and ordered.')

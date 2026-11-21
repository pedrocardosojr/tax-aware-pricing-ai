"""Reproduce an exploratory preview; do not replace the team's price pipeline."""
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from tax_pricing.demo_profile import ROOT
from tax_pricing.market_statistics import (
    comparable_matrix, paired_history, summarize_quotes)

OUT = ROOT / 'evidencias/market_lab_2026-11-07'
EAN = '7894900027013'
SOURCE = 'dados/clique_economia_mensal_2024_2026.parquet'
DISPLAY_NAMES = {EAN: 'Coca-Cola 2 L', '7892840800246': 'Pepsi 2 L'}


def _read_quotes(path: Path, eans: set[str]) -> tuple[list[dict], Counter]:
    """Select exact source codes and preserve explicit exclusions."""
    columns = ['id_produto', 'data_pesquisa', 'rede', 'id_empresa',
               'endereco_completo', 'preco_regular', '__mes']
    rows: list[dict] = []
    excluded: Counter[str] = Counter()
    for row in pq.read_table(path, columns=columns).to_pylist():
        if row['id_produto'] not in eans:
            continue
        try:
            price = Decimal(row['preco_regular'])
            day = date.fromisoformat(row['data_pesquisa']).isoformat()
        except (ValueError, InvalidOperation):
            excluded['invalid_price_or_date'] += 1
            continue
        if not price.is_finite() or price <= 0:
            excluded['missing_nonpositive_regular_price'] += 1
            continue
        company = (row['id_empresa'] or '').strip()
        address = ' '.join((row['endereco_completo'] or '').casefold().split())
        store = 'id:' + company if company else 'address:' + address
        if not row['rede'] or (not company and not address):
            excluded['missing_network_or_store'] += 1
            continue
        rows.append({'ean': row['id_produto'], 'date': day, 'period': row['__mes'],
                     'network': row['rede'].strip(), 'store': store,
                     'store_identity': 'company_id' if company else 'address',
                     'price': price, 'price_kind': 'regular'})
    return rows, excluded


def main() -> None:
    """Write the selected snapshot, analytics bundle and reproducible manifest."""
    catalog_path = ROOT / 'dados/catalogo/skus_50.json'
    catalog = json.loads(catalog_path.read_text())['products']
    selected = next(p for p in catalog if p['ean'] == EAN)
    cohort = [p for p in catalog if all(p[k] == selected[k]
              for k in ('group', 'type', 'package'))]
    path = ROOT / SOURCE
    rows, excluded = _read_quotes(path, {p['ean'] for p in cohort})
    latest = max(r['date'] for r in rows if r['ean'] == EAN)
    snapshot = summarize_quotes(rows, EAN, latest, source=SOURCE)
    snapshots = [{**p, **summarize_quotes(rows, p['ean'], latest, source=SOURCE),
                  'display_name': DISPLAY_NAMES.get(p['ean'], p['description'])}
                 for p in cohort if any(r['ean'] == p['ean'] and
                                        r['date'] == latest for r in rows)]
    comparable_matrix(snapshots)
    history = paired_history(rows, EAN, SOURCE)
    manifest = {'source': SOURCE, 'source_sha256': hashlib.sha256(
        path.read_bytes()).hexdigest(), 'catalog_sha256': hashlib.sha256(
            catalog_path.read_bytes()).hexdigest(),
        'selected_ean': EAN, 'snapshot_date': latest,
        'identity_method': 'exact_source_code_only_pending_team_review',
        'excluded_rows_in_cohort': dict(excluded),
        'store_identity_rule': 'company_id_else_normalized_full_address',
        'catalog_note': 'Original Pepsi description also mentions Coca Cola; '
                        'kept unchanged, separate display label for review.',
        'limitations': 'Exploratory exact-code subset, no recovered aliases. '
                       'No shopper profile, demand or forecasting model.'}
    bundle = {'schema_version': 1, 'ean': EAN, 'date': latest,
              'review_status': 'exploratory_pending_team',
              'history': history, 'comparables': snapshots, **manifest}
    snapshot.update(source_label='Clique Economia · Prefeitura de Curitiba',
                    source_sha256=manifest['source_sha256'])
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in ((f'{EAN}.json', snapshot),
                        (f'{EAN}_analytics.json', bundle),
                        ('manifest.json', manifest)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                          default=str) + '\n')
    print(json.dumps({'output': str(OUT), 'date': latest,
                      'networks': snapshot['network_count'],
                      'stores': snapshot['store_count'],
                      'history_dates': len(history),
                      'comparable_skus': len(snapshots),
                      'last_matched_networks': history[-1][
                          'common_network_count']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

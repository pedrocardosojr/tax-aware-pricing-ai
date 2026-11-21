"""Monthly price history from the public Clique Economia base, for extra charts.

Exploratory view built from the versioned public monthly base (regular
price, exact product code). It is not the team's treated reference used in
the main result; the screen says so next to each chart.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MONTHLY_PATH = ROOT / 'dados' / 'clique_economia_mensal_2024_2026.parquet'
CATALOG_PATH = ROOT / 'dados' / 'catalogo' / 'skus_50.json'
SOURCE_LABEL = 'Clique Economia · base pública mensal, preço regular'
PACKAGE = re.compile(r'^\s*(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml)\s*$', re.IGNORECASE)
TO_BASE = {'kg': (1.0, 'kg'), 'g': (0.001, 'kg'), 'l': (1.0, 'L'), 'ml': (0.001, 'L')}


@lru_cache(maxsize=1)
def _observations(path: Path = MONTHLY_PATH) -> pd.DataFrame:
    """Regular prices with a valid positive value, one row per store visit."""
    data = pd.read_parquet(path, columns=['id_produto', 'rede', 'endereco_completo',
                                          '__mes', 'preco_regular'])
    data['preco'] = pd.to_numeric(data['preco_regular'], errors='coerce')
    data = data[data['preco'] > 0].rename(columns={'__mes': 'mes'})
    return data[['id_produto', 'rede', 'endereco_completo', 'mes', 'preco']]


def product_rows(ean: str, months: int = 12) -> pd.DataFrame:
    """Observations of one product in its last ``months`` months with data."""
    rows = _observations()
    rows = rows[rows['id_produto'] == ean]
    if rows.empty:
        return rows
    keep = sorted(rows['mes'].unique())[-months:]
    return rows[rows['mes'].isin(keep)]


def monthly_band(ean: str, months: int = 12) -> pd.DataFrame:
    """Median, quartiles and network count per month."""
    rows = product_rows(ean, months)
    if rows.empty:
        return pd.DataFrame(columns=['mes', 'mediana', 'p25', 'p75', 'redes'])
    grouped = rows.groupby('mes')['preco']
    return pd.DataFrame({
        'mediana': grouped.median(), 'p25': grouped.quantile(.25),
        'p75': grouped.quantile(.75),
        'redes': rows.groupby('mes')['rede'].nunique(),
    }).reset_index()


def network_by_month(ean: str, months: int = 12, top: int = 12) -> pd.DataFrame:
    """Median price per network and month for the most observed networks."""
    rows = product_rows(ean, months)
    if rows.empty:
        return pd.DataFrame()
    busiest = rows['rede'].value_counts().head(top).index
    table = (rows[rows['rede'].isin(busiest)]
             .pivot_table(index='rede', columns='mes', values='preco', aggfunc='median'))
    last = table.ffill(axis=1).iloc[:, -1]
    return table.loc[last.sort_values().index]


def unit_factor(package: str) -> tuple[float, str] | None:
    """Quantity in kg or L for a package such as '500 g' or '2 L'."""
    match = PACKAGE.match(package or '')
    if not match:
        return None
    value = float(match.group(1).replace(',', '.'))
    scale, unit = TO_BASE[match.group(2).lower()]
    return value * scale, unit


@lru_cache(maxsize=1)
def _catalog(path: Path = CATALOG_PATH) -> tuple[dict, ...]:
    return tuple(json.loads(path.read_text())['products'])


def similar_unit_prices(group: str, months: int = 3) -> pd.DataFrame:
    """Recent median price per kg or L of every catalog product in a group."""
    rows = []
    for product in _catalog():
        if product['group'] != group:
            continue
        factor = unit_factor(product['package'])
        observed = product_rows(product['ean'], months)
        if factor is None or observed.empty:
            continue
        quantity, unit = factor
        median = float(observed['preco'].median())
        rows.append({'ean': product['ean'], 'produto': product['description'],
                     'embalagem': product['package'], 'mediana': median,
                     'preco_unidade': median / quantity, 'unidade': unit})
    return pd.DataFrame(rows).sort_values('preco_unidade') if rows else pd.DataFrame()

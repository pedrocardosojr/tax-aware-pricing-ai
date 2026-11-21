"""Observed regular-price statistics with explicit stores and network weights."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median


def _positive(value: object) -> Decimal:
    """Require a positive finite observation before calculating statistics."""
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Invalid observed price.') from error
    if not number.is_finite() or number <= 0:
        raise ValueError('Observed prices must be finite and positive.')
    return number


def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal:
    """Use a documented linear interpolation between adjacent order values."""
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _quotes(rows: list[dict], ean: str, day: str) -> tuple[dict, int]:
    """Deduplicate identical quotes; conflicting prices require review."""
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError('Canonical observation date required.')
    unique: dict = {}
    duplicates = 0
    for row in rows:
        if row.get('ean') != ean or row.get('date') != day:
            continue
        if row.get('price_kind') != 'regular':
            raise ValueError('Only explicitly regular prices enter this sample.')
        if not row.get('network') or not row.get('store'):
            raise ValueError('Network and stable store identity are required.')
        key = (row['network'], row['store'])
        price = _positive(row['price'])
        if key in unique:
            if unique[key] != price:
                raise ValueError('Conflicting prices for the same SKU/store/date.')
            duplicates += 1
        unique[key] = price
    return unique, duplicates


def summarize_quotes(rows: list[dict], ean: str, day: str, *,
                     source: str) -> dict:
    """Aggregate unique stores, then give each network equal reference weight.

    Parameters
    ----------
    rows : list of dict
        ean, date, network, store, price and explicit price_kind='regular'.
        Identity matching and price-condition validation precede this function.
    ean, day, source : str
        Exact selected SKU, ISO date and traceable source identifier.

    Returns
    -------
    dict
        analyze_mvp snapshot, network prices, coverage and robust dispersion.
        Quartiles use linear interpolation across network medians.
    """
    if not source:
        raise ValueError('A traceable source is required.')
    unique, duplicates = _quotes(rows, ean, day)
    if not unique:
        raise ValueError('No usable observations for this SKU/date.')
    by_network: dict = defaultdict(list)
    for (network, _), price in unique.items():
        by_network[network].append(price)
    prices = {name: median(values) for name, values in by_network.items()}
    values = list(prices.values())
    center = median(values)
    p25, p75 = (_quantile(values, Decimal('.25')),
                _quantile(values, Decimal('.75')))
    return {'ean': ean, 'date': day, 'kind': 'observed', 'source': source,
            'median': center, 'p25': p25, 'p75': p75,
            'network_count': len(prices), 'store_count': len(unique),
            'duplicate_count': duplicates, 'per_network_brl': prices,
            'aggregation': 'unique_store_then_network_median_equal_weight',
            'mean_stores_brl': sum(unique.values()) / len(unique),
            'mean_networks_brl': sum(values) / len(values),
            'iqr_brl': p75 - p25, 'iqr_relative_percent': (
                (p75 - p25) / center * 100),
            'mad_brl': median([abs(value - center) for value in values])}


def price_rank(snapshot: dict, price: Decimal) -> dict | None:
    """Count cheaper, equal and dearer networks without pooling their stores.

    Parameters
    ----------
    snapshot : dict
        Observed snapshot with per_network_brl.
    price : Decimal
        Evaluated selling price, in the same presentation and price condition.

    Returns
    -------
    dict or None
        Counts and percentages of the observed network sample, not market share.
    """
    if snapshot.get('kind') != 'observed' or not snapshot.get('per_network_brl'):
        return None
    reference = _positive(price)
    values = [_positive(value) for value in snapshot['per_network_brl'].values()]
    cheaper = sum(value < reference for value in values)
    equal = sum(value == reference for value in values)
    return {'cheaper': cheaper, 'equal': equal,
            'dearer': len(values) - cheaper - equal, 'count': len(values),
            'cheaper_percent': Decimal(cheaper) / len(values) * 100}


def _monthly_rows(rows: list[dict], ean: str) -> dict:
    """Keep the last observation per store in each declared snapshot month."""
    periods: dict = defaultdict(list)
    for row in rows:
        if row['ean'] == ean:
            periods[row.get('period', row['date'][:7])].append(row)
    selected = {}
    for period, observations in sorted(periods.items()):
        latest: dict = {}
        for row in observations:
            key = (row['network'], row['store'])
            latest[key] = max(latest.get(key, row['date']), row['date'])
        selected[period] = [{**r, 'date': period + '-01',
                             'observed_date': r['date']} for r in observations
                            if r['date'] == latest[(r['network'], r['store'])]]
    return selected


def _paired_change(previous: dict, current: dict, adjacent: bool,
                   threshold: int) -> dict:
    """Compare only repeated store identities, then aggregate by network."""
    common = current.keys() & previous.keys()
    networks = sorted({key[0] for key in common})
    change = None
    if adjacent and len(networks) >= threshold:
        old = [median([previous[k] for k in common if k[0] == n]) for n in networks]
        new = [median([current[k] for k in common if k[0] == n]) for n in networks]
        change = (median(new) / median(old) - 1) * 100
    return {'common_network_count': len(networks),
            'common_store_count': len(common), 'paired_change_percent': change,
            'paired_status': ('available' if change is not None
                              else 'insufficient_matched_panel'),
            'min_common_networks': threshold}


def paired_history(rows: list[dict], ean: str, source: str,
                   min_common_networks: int = 3) -> list[dict]:
    """Separate historical reference levels from changes in matched stores.

    Parameters
    ----------
    rows : list of dict
        Regular quotes with stable store identifiers across dates.
    ean, source : str
        Exact SKU and data provenance.
    min_common_networks : int
        Provisional operational threshold, not a statistical guarantee.

    Returns
    -------
    list of dict
        Date, quartiles, coverage and optional adjacent-month paired change.
        Missing months or insufficient repeated networks do not yield a change.
    """
    if min_common_networks < 1:
        raise ValueError('A positive matched-network threshold is required.')
    periods = _monthly_rows(rows, ean)
    history: list[dict] = []
    previous: dict = {}
    previous_period = None
    for period, selected in sorted(periods.items()):
        snapshot = summarize_quotes(selected, ean, period + '-01', source=source)
        snapshot.update(period=period,
                        observed_from=min(r['observed_date'] for r in selected),
                        observed_through=max(r['observed_date'] for r in selected))
        current, _ = _quotes(selected, ean, period + '-01')
        serial = int(period[:4]) * 12 + int(period[5:])
        adjacent = previous_period is not None and serial - previous_period == 1
        history.append({**snapshot, **_paired_change(
            previous, current, adjacent, min_common_networks)})
        previous, previous_period = current, serial
    return history


def comparable_matrix(snapshots: list[dict]) -> dict:
    """Compare exact-SKU snapshots within an explicit presentation cohort.

    Parameters
    ----------
    snapshots : list of dict
        Observed snapshots with group, type, package, description and same date.

    Returns
    -------
    dict
        SKU-by-network price indices; missing cells stay None. Network group
        indices use only the complete identical basket with equal SKU weights.
    """
    if not snapshots:
        raise ValueError('At least one comparable snapshot is required.')
    signature = tuple(snapshots[0][k] for k in ('group', 'type', 'package', 'date'))
    if any(tuple(s[k] for k in ('group', 'type', 'package', 'date')) != signature
           or s.get('kind') != 'observed' for s in snapshots):
        raise ValueError('Comparable snapshots must share cohort/date and origin.')
    if len({s['ean'] for s in snapshots}) != len(snapshots):
        raise ValueError('Each SKU must appear only once in the cohort.')
    networks = sorted({n for s in snapshots for n in s['per_network_brl']})
    indices, raw_prices = [], []
    for snapshot in snapshots:
        center = _positive(snapshot['median'])
        prices = [(_positive(snapshot['per_network_brl'][n])
                   if n in snapshot['per_network_brl'] else None)
                  for n in networks]
        raw_prices.append(prices)
        indices.append([p / center * 100 if p is not None else None
                        for p in prices])
    common = [n for i, n in enumerate(networks)
              if all(row[i] is not None for row in indices)]
    network_index = []
    if len(snapshots) >= 2:
        for name in common:
            i = networks.index(name)
            values = [_positive(row[i]) / 100 for row in indices]
            log_mean = sum((value.ln() for value in values), Decimal(0)) / len(values)
            index = log_mean.exp() * 100
            network_index.append({'network': name, 'index': index,
                                  'sku_count': len(values)})
    return {'networks': networks, 'indices': indices, 'prices_brl': raw_prices,
            'labels': [s.get('display_name', s['description']) for s in snapshots],
            'eans': [s['ean'] for s in snapshots],
            'common_basket_networks': common, 'network_index': network_index,
            'cohort': dict(zip(('group', 'type', 'package', 'date'), signature))}

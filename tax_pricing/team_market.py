"""Translate reviewed team statistics without changing their estimator."""
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median as sample_median


NETWORK_AGGREGATION = 'median_within_network_then_between_networks'
STORE_AGGREGATION = 'median_across_stores'


def _price(value: object) -> str:
    """Require a finite positive monetary value represented as text."""
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Invalid team price.') from error
    if not number.is_finite() or number <= 0:
        raise ValueError('Team prices must be positive and finite.')
    return str(number)


def _validate_metadata(reference: dict, per_network: dict,
                       source: str) -> None:
    """Check source, collection rounds and declared coverage."""
    ean = reference['id_produto']
    if (not isinstance(ean, str) or not ean.isascii() or not ean.isdigit()
            or len(ean) not in (8, 12, 13, 14)):
        raise ValueError('A textual catalogue code is required.')
    if (reference['camada'] != 'observado' or not isinstance(source, str)
            or not source.strip()):
        raise ValueError('Observed layer and explicit source are required.')
    day = reference['ultima_obs']
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError('Canonical observation date required.')
    window = reference['janela']
    if (not isinstance(window, list) or not window
            or window != sorted(set(window))):
        raise ValueError('Window must contain ordered distinct rounds.')
    for month in window:
        if date.fromisoformat(month + '-01').strftime('%Y-%m') != month:
            raise ValueError('Invalid collection round.')
    networks = reference['n_redes']
    for field in ('n_redes', 'n_obs', 'n_lojas'):
        count = reference[field]
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError('Positive integer coverage counts required.')
    if networks != len(per_network) or reference['n_obs'] < networks:
        raise ValueError('Network prices disagree with the team coverage.')


def adapt_team_reference(reference: dict, per_network: dict, *,
                         source: str) -> dict:
    """Translate Edu's observed reference to the application's contract.

    Parameters
    ----------
    reference : dict
        Output of referencia_mercado on Rodrigo's cleaned observations.
        Set aggregation to median_across_stores for store-level quartiles.
        Older payloads default to the network-level method.
    per_network : dict
        Network medians from exactly the same SKU, layer and window.
    source : str
        Explicit provenance including the data/module revisions used.

    Returns
    -------
    dict
        App snapshot. Coverage rejection withholds quartiles, not the source.
    """
    _validate_metadata(reference, per_network, source)
    prices = {}
    for network, value in per_network.items():
        if not isinstance(network, str) or not network.strip():
            raise ValueError('Each network requires a name.')
        prices[network] = _price(value)
    low, median, high = [_price(reference[key])
                         for key in ('p25', 'mediana', 'p75')]
    if not Decimal(low) <= Decimal(median) <= Decimal(high):
        raise ValueError('Expected P25 <= median <= P75.')
    aggregation = reference.get('aggregation', NETWORK_AGGREGATION)
    if aggregation not in (NETWORK_AGGREGATION, STORE_AGGREGATION):
        raise ValueError('Unknown team reference aggregation.')
    if aggregation == NETWORK_AGGREGATION:
        # Preserve the legacy check, allowing one cent for upstream rounding.
        center = sample_median([Decimal(v) for v in prices.values()])
        if abs(center - Decimal(median)) > Decimal('.01'):
            raise ValueError('Network prices disagree with the team median.')
    if not isinstance(reference['cobertura_ok'], bool):
        raise ValueError('Team coverage decision must be explicit.')
    covered = reference['cobertura_ok']
    return {
        'ean': reference['id_produto'], 'date': reference['ultima_obs'],
        'kind': 'observed', 'source': source,
        'source_label': 'Clique Economia · pesquisa de preços em Curitiba',
        'median': median, 'p25': low if covered else None,
        'p75': high if covered else None, 'network_count': reference['n_redes'],
        'store_count': reference['n_lojas'],
        'observation_count': reference['n_obs'],
        'window': list(reference['janela']), 'per_network_brl': prices,
        'team_coverage_ok': covered,
        'aggregation': aggregation,
    }

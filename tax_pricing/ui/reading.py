"""Plain business explanations derived from the checked scenario only."""
from decimal import Decimal

from tax_pricing.ui.formatting import brl_markdown, display_date, percent


def observed_spread(snapshot: dict) -> dict | None:
    """Describe the available network-price sample without inventing rows.

    Parameters
    ----------
    snapshot : dict
        Snapshot with optional observed per_network_brl values.

    Returns
    -------
    dict or None
        Minimum, maximum, range and plotted network count, not history size.
    """
    if snapshot.get('kind') != 'observed':
        return None
    values = [Decimal(str(value)) for value in
              snapshot.get('per_network_brl', {}).values() if value is not None]
    if not values:
        return None
    if any(not value.is_finite() or value <= 0 for value in values):
        raise ValueError('Observed network prices must be finite and positive.')
    return {'minimum': min(values), 'maximum': max(values),
            'range': max(values) - min(values), 'count': len(values)}


def decision_text(result: dict) -> dict[str, str]:
    """Explain contribution, positioning and a justified next check.

    Parameters
    ----------
    result : dict
        Ready analyze_mvp output. No demand, shopper or brand claims inferred.

    Returns
    -------
    dict of str
        Contribution, position and next-action paragraphs.
    """
    margin = result['analysis']['personalized']['margin']
    contribution = margin['contribution_brl']
    if contribution < 0:
        summary = (f"A {brl_markdown(result['evaluated_price_brl'])}, faltam "
                   f'{brl_markdown(abs(contribution))} por unidade para pagar o custo '
                   'de compra e os impostos.')
    else:
        summary = (f'Depois de pagar o custo de compra e os impostos, sobram '
                   f"{brl_markdown(contribution)} por unidade "
                   f"({percent(margin['contribution_percent'])} do preço).")
    market = result['market']
    position = result['market_position']
    if position is None:
        comparison = 'Ainda não temos preços da concorrência para este produto.'
    else:
        gap = position['gap_percent']
        direction = 'acima' if gap >= 0 else 'abaixo'
        label = ('mediana estimada do mercado' if market['kind'] == 'estimated'
                 else 'mediana do mercado (o preço do meio das lojas)')
        comparison = (f"Em {display_date(market['date'])}, o seu preço "
                      f'está {brl_markdown(abs(position["gap_brl"]))} '
                      f'({percent(abs(gap))}) {direction} da {label}.')
        if gap == 0:
            comparison = (f"Em {display_date(market['date'])}, o seu preço "
                          f'é igual à {label}.')
    if contribution < 0:
        action = ('Reveja custo e preço antes de '
                  'usar esse cenário como referência comercial.')
    elif market['status'] == 'historical_reference':
        action = ('Esses preços de mercado são antigos (histórico). Atualize antes de '
                  'decidir mudar o preço.')
    elif position is None:
        action = 'Use o quanto sobra por unidade para avaliar o seu preço.'
    elif market.get('kind') == 'estimated':
        action = ('O preço de mercado aqui é uma estimativa. Com preços reais do mesmo '
                  'produto em outras lojas, a comparação fica mais segura.')
    else:
        action = ('Antes de mudar o preço, veja quanto sobra por unidade em outros '
                  'preços, na aba Margem e promoção. Um preço maior pode fazer você '
                  'vender menos, e o app ainda não mede esse efeito.')
    return {'contribution': summary, 'position': comparison, 'action': action}

"""Interactive charts derived only from calculated and sourced values."""
from decimal import Decimal

import plotly.graph_objects as go

from tax_pricing.ui.formatting import brl, network_name

TEAL = '#08715D'
INK = '#192844'
PRICE = '#354BB5'
OBSERVED = '#7486C0'
MEDIAN = '#475569'


def _layout(figure: go.Figure, height: int) -> go.Figure:
    """Apply a consistent readable chart theme."""
    figure.update_layout(
        height=height, margin={'l': 8, 'r': 18, 't': 18, 'b': 10},
        font={'family': '"Source Sans", "Source Sans Pro", sans-serif',
              'size': 13, 'color': INK},
        paper_bgcolor='white', plot_bgcolor='white', separators=',.',
        legend={'orientation': 'h', 'y': 1.12, 'x': 0},
        hoverlabel={'bgcolor': 'white'})
    axis_text = {'tickfont': {'size': 14, 'color': INK}, 'title_font': {'size': 14, 'color': INK}}
    figure.update_xaxes(automargin=True, **axis_text)
    figure.update_yaxes(automargin=True, **axis_text)
    return figure


def market_chart(snapshot: dict, price: Decimal) -> go.Figure | None:
    """Plot actual per-network values, with median and scenario references.

    Parameters
    ----------
    snapshot : dict
        Observed market snapshot with optional per_network_brl values.
    price : Decimal
        Evaluated user or corridor-scenario price.

    Returns
    -------
    Figure or None
        Dot chart. Missing network observations are never fabricated.
    """
    observations = snapshot.get('per_network_brl')
    if not observations or snapshot.get('kind') != 'observed':
        return None
    ordered = sorted(((network_name(name), float(value))
                      for name, value in observations.items()
                      if value is not None), key=lambda item: item[1])
    if not ordered:
        return None
    names, values = zip(*ordered)
    figure = go.Figure(go.Scatter(
        x=values, y=names,
        mode='markers', marker={'size': 10, 'color': OBSERVED,
                                'line': {'width': 1.5, 'color': 'white'}},
        name='Preço observado', hovertemplate='%{y}<br>R$ %{x:.2f}<extra></extra>'))
    median = float(snapshot['median'])
    figure.add_vline(x=float(price), line_dash='solid', line_width=4, line_color=PRICE)
    figure.add_vline(x=median, line_dash='dash', line_width=2, line_color=MEDIAN)
    boundaries = [*values, median, float(price)]
    if snapshot.get('p25') is not None and snapshot.get('p75') is not None:
        low, high = float(snapshot['p25']), float(snapshot['p75'])
        boundaries.extend((low, high))
        figure.add_vrect(x0=low, x1=high,
                         fillcolor='rgba(112,135,220,.19)', line_width=0,
                         layer='below')
    left, right = min(boundaries), max(boundaries)
    padding = max((right - left) * .08, .05)
    figure.update_xaxes(title='Preço por unidade', tickprefix='R$ ', tickformat='.2f',
                        nticks=5, tickangle=0, gridcolor='#E7ECF6', zeroline=False,
                        range=[max(0, left - padding), right + padding])
    figure.update_yaxes(autorange='reversed', showgrid=False, tickmode='array',
                        tickvals=names)
    figure.update_layout(showlegend=False)
    return _layout(figure, max(300, len(names) * 22 + 90))



def price_tree(margin: dict, credit: Decimal = Decimal(0)) -> go.Figure:
    """Build a reconciled price waterfall from the domain result.

    Parameters
    ----------
    margin : dict
        Price, net acquisition cost, tax, variable expenses and contribution.
    credit : Decimal
        Scenario purchase credit, already included in net cost. Show it once
        as a separate positive bar after the gross acquisition cost.

    Returns
    -------
    Figure
        Interactive composition of the selected scenario price.
    """
    amounts = [margin['selling_price_brl'], -(margin['net_cost_brl'] + credit)]
    labels = ['Preço de venda', 'Custo de aquisição']
    if credit > 0:
        amounts.append(credit)
        labels.append('Crédito do cenário')
    amounts.append(-margin['tax_brl'])
    labels.append('Tributação estimada')
    if margin['expense_brl']:
        amounts.append(-margin['expense_brl'])
        labels.append('Despesas variáveis')
    labels.append('Margem de contribuição')
    displayed = amounts + [margin['contribution_brl']]
    text = [('−' if amount < 0 else '') + brl(abs(amount))
            for amount in displayed]
    figure = go.Figure(go.Waterfall(
        x=labels, y=[float(amount) for amount in amounts] + [0],
        measure=['absolute'] + ['relative'] * (len(amounts) - 1) + ['total'],
        text=text, textposition='outside', cliponaxis=False,
        increasing={'marker': {'color': TEAL}},
        decreasing={'marker': {'color': '#94A3B8'}},
        totals={'marker': {'color': INK}},
        connector={'line': {'color': '#D7DFEB'}},
        customdata=text,
        hovertemplate='%{x}<br>%{customdata}<extra></extra>'))
    high = float(margin['selling_price_brl'])
    low = min(0, float(margin['contribution_brl']))
    padding = (high - low) * .15
    short_labels = {
        'Preço de venda': 'Preço<br>de venda', 'Custo de aquisição': 'Custo<br>de compra',
        'Crédito do cenário': 'Crédito', 'Tributação estimada': 'Tributos<br>estimados',
        'Despesas variáveis': 'Despesas', 'Margem de contribuição': 'Margem',
    }
    figure.update_xaxes(tickmode='array', tickvals=labels,
                        ticktext=[short_labels[label] for label in labels],
                        tickangle=0)
    figure.update_yaxes(tickprefix='R$ ', gridcolor='#EDF1F7', zeroline=False,
                        range=[low - padding, high + padding])
    figure.update_layout(showlegend=False)
    return _layout(figure, 420)

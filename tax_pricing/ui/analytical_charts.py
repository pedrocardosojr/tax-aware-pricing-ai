"""Market and contribution charts with their populations kept explicit."""
from datetime import date
import math
from decimal import Decimal

import plotly.graph_objects as go

from tax_pricing.ui.charts import INK, PRICE, TEAL, _layout
from tax_pricing.ui.formatting import brl


def distribution_chart(snapshot: dict, price: Decimal) -> go.Figure:
    """Draw supplied network quartiles, min/max and evaluated price.

    Parameters
    ----------
    snapshot : dict
        Checked observed network snapshot with quartiles.
    price : Decimal
        Evaluated price in the same presentation.

    Returns
    -------
    Figure
        Box with explicit min/max whiskers, not an outlier classifier.
    """
    values = [float(p) for p in snapshot['per_network_brl'].values()]
    figure = go.Figure(go.Box(
        q1=[float(snapshot['p25'])], median=[float(snapshot['median'])],
        q3=[float(snapshot['p75'])], lowerfence=[min(values)],
        upperfence=[max(values)], y=['Redes'], orientation='h',
        boxpoints=False, name='Faixa observada', line={'color': TEAL},
        fillcolor='rgba(0,139,146,.15)', showlegend=False))
    figure.add_trace(go.Scatter(x=[float(price)], y=['Redes'], mode='markers',
        marker={'symbol': 'diamond', 'size': 14, 'color': INK},
        name='Preço avaliado', hovertemplate='Preço: R$ %{x:.2f}<extra></extra>'))
    figure.update_xaxes(tickprefix='R$ ', gridcolor='#EDF1F7', tickformat='.2f')
    return _layout(figure, 180)


def contribution_curve(scenarios: dict, snapshot: dict, price: Decimal,
                       simulated: Decimal | None = None) -> go.Figure:
    """Show unit contribution versus selling price, without demand inference.

    Parameters
    ----------
    scenarios : dict
        Output of scenario_analysis.
    snapshot : dict
        Checked current market reference, possibly unavailable.
    price : Decimal
        Current evaluated price.

    Returns
    -------
    Figure
        Scenario curve, zero line and eligible observed central band.
    """
    xs = [float(p['price_brl']) for p in scenarios['curve']]
    ys = [float(p['contribution_brl']) for p in scenarios['curve']]
    figure = go.Figure(go.Scatter(
        x=xs, y=ys, mode='lines', line={'color': TEAL, 'width': 3},
        fill='tozeroy', fillcolor='rgba(0,105,99,.10)',
        name='Margem de contribuição por unidade',
        hovertemplate='Preço R$ %{x:.2f}<br>Margem R$ %{y:.2f}<extra></extra>'))
    figure.add_hline(y=0, line_color='#C25B5B', line_width=1, line_dash='dot')
    if snapshot.get('usable_for_band'):
        figure.add_vrect(x0=float(snapshot['p25']), x1=float(snapshot['p75']),
                         fillcolor='rgba(112,135,220,.19)', line_width=0, layer='below')
    points = [(float(scenarios['zero_contribution_price_brl']), 'Margem zero', '#C25B5B')]
    if snapshot.get('usable_for_band'):
        points += [(float(snapshot['p25']), 'Início da faixa', '#4F6B1F'),
                   (float(snapshot['p75']), 'Fim da faixa', '#4F6B1F')]
    for x, label, color in points:
        y = _interpolate(xs, ys, x)
        figure.add_trace(go.Scatter(
            x=[x], y=[y], mode='markers', showlegend=False,
            marker={'size': 10, 'color': 'white', 'line': {'color': color, 'width': 2}},
            hovertemplate=f'{label}<br>Preço R$ %{{x:.2f}}<br>Margem R$ %{{y:.2f}}<extra></extra>'))
    own = _interpolate(xs, ys, float(price))
    figure.add_trace(go.Scatter(
        x=[float(price)], y=[own], mode='markers', showlegend=False,
        marker={'size': 15, 'color': PRICE, 'line': {'color': 'white', 'width': 3}},
        hovertemplate='Seu preço R$ %{x:.2f}<br>Margem R$ %{y:.2f}<extra></extra>'))
    if simulated is not None and simulated != price:
        sim = _interpolate(xs, ys, float(simulated))
        figure.add_vline(x=float(simulated), line_dash='dot', line_width=2,
                         line_color='#4F6B1F')
        figure.add_trace(go.Scatter(
            x=[float(simulated)], y=[sim], mode='markers', showlegend=False,
            marker={'size': 15, 'color': '#B9D557', 'line': {'color': '#4F6B1F', 'width': 3}},
            hovertemplate='Preço simulado R$ %{x:.2f}<br>Margem R$ %{y:.2f}<extra></extra>'))
    figure.update_xaxes(title='Preço de venda (R$)', tickformat='.2f', nticks=5,
                        tickangle=0, showgrid=False)
    figure.update_yaxes(title='Margem por unidade (R$)', tickformat='.2f',
                        gridcolor='#E7ECF6')
    figure.update_layout(showlegend=False)
    return _layout(figure, 400)


def _interpolate(xs: list[float], ys: list[float], x: float) -> float:
    """Linear interpolation on the scenario curve, clamped to its ends."""
    if x <= xs[0]:
        return ys[0]
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


def sensitivity_chart(scenarios: dict) -> go.Figure:
    """Display hypothetical acquisition costs against selected price points.

    Parameters
    ----------
    scenarios : dict
        Checked cost/price grid using the same contribution engine.

    Returns
    -------
    Figure
        Scenario contribution heatmap; colors are centered at zero.
    """
    values = scenarios['contribution_grid_brl']
    figure = go.Figure(go.Heatmap(
        x=[brl(p) for p in scenarios['grid_prices_brl']],
        y=[brl(c) for c in scenarios['costs_brl']],
        z=[[float(v) for v in row] for row in values],
        text=[[brl(v) for v in row] for row in values],
        texttemplate='%{text}', zmid=0,
        colorscale=[[0, '#C98383'], [.5, '#FAFAFA'], [1, '#65A7A8']],
        colorbar={'title': 'R$/un.'},
        hovertemplate='Preço: %{x}<br>Custo: %{y}<br>Contribuição: %{text}<extra></extra>'))
    figure.update_xaxes(title='Preço de venda do cenário')
    figure.update_yaxes(title='Custo de aquisição hipotético', autorange='reversed')
    return _layout(figure, 340)


def history_chart(history: list[dict]) -> go.Figure:
    """Plot monthly reference levels and preserve missing-month gaps.

    Parameters
    ----------
    history : list of dict
        Validated monthly aggregates with date, median, p25 and p75.

    Returns
    -------
    Figure
        Descriptive historical band; no forecast or matched-change claim.
    """
    points: list[dict] = []
    for row in history:
        if points:
            previous = date.fromisoformat(points[-1]['date'])
            current = date.fromisoformat(row['date'])
            month = previous.year * 12 + previous.month
            while month + 1 < current.year * 12 + current.month:
                month += 1
                year, zero_month = divmod(month - 1, 12)
                points.append({'date': f'{year:04d}-{zero_month+1:02d}-01',
                               'median': None, 'p25': None, 'p75': None})
        points.append(row)
    figure = go.Figure()
    for field, name, fill in [('p25', 'P25', None), ('p75', 'P75', 'tonexty'),
                              ('median', 'Mediana entre redes', None)]:
        figure.add_trace(go.Scatter(
            x=[r['date'] for r in points],
            y=[float(r[field]) if r[field] is not None else None for r in points],
            name=name, mode='lines', connectgaps=False, fill=fill,
            fillcolor='rgba(0,139,146,.10)',
            line={'color': TEAL if field == 'median' else '#C3DADB',
                  'width': 3 if field == 'median' else 1}))
    figure.update_yaxes(tickprefix='R$ ', gridcolor='#EDF1F7')
    return _layout(figure, 370)


def cohort_heatmap(matrix: dict) -> go.Figure:
    """Show SKU/network indices with missing cells left empty.

    Parameters
    ----------
    matrix : dict
        Validated comparable_matrix result with identical cohort/date.

    Returns
    -------
    Figure
        Heatmap relative to each SKU median (100), not shopper profiles.
    """
    values = matrix['indices']
    figure = go.Figure(go.Heatmap(
        x=matrix['networks'], y=matrix['labels'],
        z=[[float(v) if v is not None else None for v in row] for row in values],
        zmid=100, text=[[f'{v:.1f}' if v is not None else '' for v in row]
                       for row in values], texttemplate='%{text}',
        colorscale=[[0, '#65A7A8'], [.5, '#FAFAFA'], [1, '#D3A16B']],
        hoverongaps=False, colorbar={'title': 'Mediana = 100'},
        hovertemplate='%{y}<br>%{x}<br>Índice: %{z:.1f}<extra></extra>'))
    figure.update_yaxes(autorange='reversed')
    return _layout(figure, max(250, 90 + len(matrix['labels']) * 45))


MONTH_ABBR = ('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out',
              'nov', 'dez')


def _month_label(month: str) -> str:
    """'2026-10' -> 'out/26'."""
    year, number = month.split('-')
    return f'{MONTH_ABBR[int(number) - 1]}/{year[2:]}'


def _brl_text(value: float) -> str:
    return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def median_history_chart(band, price: Decimal) -> go.Figure:
    """Monthly median with the central band and the evaluated price."""
    months = [_month_label(month) for month in band['mes']]
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=months, y=band['p75'], mode='lines',
                                line={'width': 0}, hoverinfo='skip'))
    figure.add_trace(go.Scatter(
        x=months, y=band['p25'], mode='lines', line={'width': 0}, fill='tonexty',
        fillcolor='rgba(185,213,87,.35)', hoverinfo='skip'))
    figure.add_trace(go.Scatter(
        x=months, y=band['mediana'], mode='lines+markers',
        line={'color': TEAL, 'width': 3}, marker={'size': 8, 'color': TEAL},
        customdata=band['redes'],
        hovertemplate='%{x}<br>Mediana R$ %{y:.2f}<br>%{customdata} redes<extra></extra>'))
    figure.add_hline(y=float(price), line_dash='dash', line_width=2, line_color=INK,
                     annotation_text=f'Seu preço  <b>{_brl_text(float(price))}</b>',
                     annotation_position='top left',
                     annotation={'bgcolor': INK, 'bordercolor': INK, 'borderpad': 5,
                                 'font': {'color': 'white', 'size': 12}})
    figure.update_yaxes(tickprefix='R$ ', gridcolor='#E6ECE8', tickformat='.2f')
    figure.update_xaxes(showgrid=False)
    figure.update_layout(showlegend=False)
    return _layout(figure, 360)


def network_heatmap(table) -> go.Figure:
    """Median price per network and month; months without data stay blank."""
    values = table.to_numpy()
    text = [[_brl_text(v) if not math.isnan(v) else '' for v in row] for row in values]
    figure = go.Figure(go.Heatmap(
        z=values, x=[_month_label(month) for month in table.columns], y=list(table.index),
        text=text, texttemplate='%{text}', textfont={'size': 10},
        colorscale=[[0, '#F3F8EE'], [.5, '#8FC1A9'], [1, '#006963']],
        hovertemplate='%{y} · %{x}<br>R$ %{z:.2f}<extra></extra>',
        colorbar={'title': 'R$', 'thickness': 10, 'tickprefix': 'R$ '}, xgap=2, ygap=2))
    figure.update_yaxes(autorange='reversed')
    return _layout(figure, max(320, 32 * len(table.index) + 90))


def similars_chart(similars, ean: str) -> go.Figure:
    """Price per kg or litre of the products in the same group."""
    unit = similars['unidade'].iloc[0]
    names = [f"{row.produto.title().replace(' -', ' · ')}" for row in similars.itertuples()]
    colors = [TEAL if row.ean == ean else '#C9D8D2' for row in similars.itertuples()]
    figure = go.Figure(go.Bar(
        x=similars['preco_unidade'], y=names, orientation='h', marker_color=colors,
        text=[f'{_brl_text(v)}/{unit}' for v in similars['preco_unidade']],
        textposition='outside', cliponaxis=False,
        customdata=similars[['embalagem', 'mediana']].to_numpy(),
        hovertemplate=('%{y}<br>%{customdata[0]} por R$ %{customdata[1]:.2f}'
                       f'<br>R$ %{{x:.2f}}/{unit}<extra></extra>')))
    figure.update_xaxes(tickprefix='R$ ', showgrid=False, showticklabels=False)
    figure.update_yaxes(autorange='reversed')
    figure = _layout(figure, max(260, 46 * len(similars) + 60))
    figure.update_layout(margin={'l': 8, 'r': 110, 't': 10, 'b': 10})
    return figure

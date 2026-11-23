"""Render analytical views while keeping source coverage visible."""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from html import escape
import re
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st

from tax_pricing.demo_profile import build_demo_profile
from tax_pricing.market_statistics import comparable_matrix, price_rank
from tax_pricing.personalized_tax import personalized_margin
from tax_pricing.price_history import (
    SOURCE_LABEL, monthly_band, network_by_month, similar_unit_prices,
)
from tax_pricing.weather import (INMET_SOURCE_URL, SOURCE_URL, fetch_forecast,
                                 fetch_inmet_forecast)
from tax_pricing.seasonal_calendar import (
    MONTHS, climate_month, sector_by_month, sector_month, upcoming,
)
from tax_pricing.source_search import (
    Excerpt, REFUSALS, find_sources, normalize, out_of_scope_reason,
)
from tax_pricing.pricing_scenarios import scenario_analysis, volume_scenario
from tax_pricing.ui.analytical_charts import (
    cohort_heatmap, contribution_curve, distribution_chart, history_chart,
    median_history_chart, network_heatmap, sensitivity_chart, similars_chart)
from tax_pricing.ui.formatting import brl, brl_markdown, display_date, percent


def distribution(result: dict) -> None:
    """Explain the selected price against the observed network distribution.

    Parameters
    ----------
    result : dict
        Ready MVP result with a checked market snapshot.
    """
    market = result['market']
    rank = price_rank(market, result['evaluated_price_brl'])
    if rank is None:
        return
    st.subheader('Onde seu preço fica na distribuição?')
    st.write(f"Seu preço está acima de **{rank['cheaper']} das "
             f"{rank['count']} redes** desta amostra "
             f"({percent(rank['cheaper_percent'])}). "
             f"Há {rank['equal']} empate(s) e {rank['dearer']} rede(s) acima.")
    if market.get('p25') is not None and market.get('p75') is not None:
        st.plotly_chart(distribution_chart(market, result['evaluated_price_brl']),
                        width='stretch', config={'displayModeBar': False})
        iqr = Decimal(str(market['p75'])) - Decimal(str(market['p25']))
        relative = iqr / Decimal(str(market['median'])) * 100
        st.caption(f"Caixa: P25–P75; hastes: mínimo e máximo. "
                   f"Dispersão central: {brl(iqr)} ({percent(relative)} da "
                   'mediana). Não é intervalo de confiança nem classificador '
                   'de preços errados. Cada rede tem o mesmo peso.')


def _comparison_cards(result: dict, sim: dict) -> None:
    """Show the initial and simulated scenarios side by side with the same labels."""
    comparison = sim['position']
    baseline_position = result['market_position'] if comparison is not None else None
    baseline = result['analysis']['personalized']['margin']
    own = result['price_origin'] == 'user_price'
    cost = baseline['net_cost_brl'] + result['assumptions']['credit_brl']
    start = 'atual' if own else 'de partida'
    scenarios_shown = (
        ((f'Cenário {start}', f'Preço {start}', f'Margem {start}'),
         (result['evaluated_price_brl'], cost, baseline, baseline_position)),
        (('Cenário simulado', 'Preço simulado', 'Margem simulada'),
         (sim['price_brl'], sim['acquisition_cost_brl'], sim, comparison)))
    for column, (labels, values) in zip(st.columns(2), scenarios_shown):
        with column, st.container(border=True):
            _scenario_card(labels, values)


def _scenario_card(labels: tuple[str, str, str], values: tuple) -> None:
    """Fill one scenario card in the same order for both sides."""
    title, price_label, margin_label = labels
    price, purchase, margin, position = values
    st.markdown(f'**{title}**')
    st.metric(price_label, brl(price))
    st.caption('Custo de compra ' + brl(purchase))
    st.metric(margin_label, brl(margin['contribution_brl']))
    st.caption(percent(margin['contribution_percent']) + ' do preço de venda')
    st.metric('Frente ao meio do mercado',
              percent(position['gap_percent'], signed=True)
              if position is not None else '—')


def _baseline_margin_summary(result: dict, floor: Decimal) -> None:
    """Describe the submitted price and its distance from the price floor."""
    margin = result['analysis']['personalized']['margin']
    price = result['evaluated_price_brl']
    value = margin['contribution_brl']
    rate = percent(margin['contribution_percent'])
    label = 'Margem atual' if result['price_origin'] == 'user_price' else 'Margem de partida'
    with st.container(border=True):
        st.markdown(f'#### {label}')
        if value > 0:
            st.write(f"A {brl_markdown(price)}, sobram **{brl_markdown(value)} por unidade** "
                     f"({rate} do preço).")
        elif value < 0:
            st.write(f"A {brl_markdown(price)}, você perde **{brl_markdown(abs(value))} "
                     f"por unidade** ({rate} de margem).")
        else:
            st.write(f"A {brl_markdown(price)}, a margem por unidade é **zero**.")
        if price != floor:
            distance = brl_markdown(abs(price - floor))
            position = 'acima' if price > floor else 'abaixo'
            st.write(f"Com o custo informado, esse preço está **{distance} {position}** "
                     f"do mínimo de **{brl_markdown(floor)}** para cobrir os gastos da venda.")
        else:
            st.write('Esse é o menor preço que cobre os gastos da venda com o custo informado.')
        cost_label = ('custo de compra após créditos' if result['assumptions']['credit_brl']
                      else 'custo de compra')
        expenses = ' − despesas variáveis' if margin['expense_brl'] else ''
        st.caption(f'Cálculo: preço de venda − {cost_label} − tributos estimados{expenses}.')

def _promotion_summary(result: dict, sim: dict, floor: Decimal) -> None:
    """Explain the result with calculated amounts and the applicable volume case."""
    margin = sim['contribution_brl']
    units = sim['units_per_100']
    baseline = result['analysis']['personalized']['margin']
    unchanged = (sim['price_brl'] == result['evaluated_price_brl'] and
                 sim['acquisition_cost_brl'] ==
                 baseline['net_cost_brl'] + result['assumptions']['credit_brl'])
    with st.container(border=True):
        st.markdown('#### Resumo da simulação')
        if unchanged:
            st.write('Mova o preço de venda ou o custo de compra para simular uma promoção.')
            st.write(f"**Preço mínimo para cobrir custo e tributos: {brl_markdown(floor)}.** "
                     'Abaixo desse valor, cada venda dá prejuízo.')
            return
        price = brl_markdown(sim['price_brl'])
        amount = brl_markdown(abs(margin))
        if margin > 0:
            st.write(f"Se vender por {price}, sobram **{amount} por unidade** "
                     f"({percent(sim['contribution_percent'])} do preço).")
        elif margin < 0:
            st.warning(f"Se vender por {price}, você perde **{amount} por unidade**.")
        else:
            st.warning(f"A {price}, a venda cobre os gastos, mas não sobra nada.")
        if units is not None:
            change = sim['volume_change_percent']
            rounded = int(abs(change).to_integral_value(rounding=ROUND_HALF_UP))
            direction = 'a mais' if change > 0 else 'a menos'
            detail = f' (cerca de {rounded}% {direction})' if rounded else ''
            st.write('Para sobrar o mesmo que em 100 vendas nas condições iniciais, '
                     f'você precisa vender pelo menos **{units} unidades**{detail}.')
        elif margin < 0:
            st.write('Cada unidade a mais aumenta o prejuízo.')
        elif margin == 0:
            st.write('A margem total fica em zero mesmo se o volume aumentar.')
        else:
            st.write('O cenário inicial tinha margem zero ou negativa.')
        revenue_units = sim['revenue_units_per_100']
        if revenue_units is not None and revenue_units != units:
            st.write(f"Para manter só o faturamento, o mínimo é de **{revenue_units} unidades**.")
        st.write(f"**Preço mínimo para cobrir custo e tributos: {brl_markdown(floor)}.** "
                 'Abaixo desse valor, cada venda dá prejuízo.')
        st.caption('Unidades arredondadas para cima. A reação dos clientes ao preço '
                   'depende da sua loja.')


def _copy_control(source: str, target: str) -> None:
    """Keep the slider and the typed value on the same cent."""
    st.session_state[target] = round(float(st.session_state[source]), 2)


def _linked_control(column, label: str, bounds: tuple[float, float],
                    initial: float, key: str) -> float:
    """Offer a slider to explore and a field to type an exact value."""
    low, high = bounds
    input_key = f'{key}_input'
    for name in (key, input_key):
        st.session_state.setdefault(name, initial)
    slider_col, input_col = column.columns([3, 2], vertical_alignment='bottom')
    value = slider_col.slider(label, min_value=low, max_value=high, step=.01, key=key,
                              on_change=_copy_control, args=(key, input_key))
    input_col.number_input(f'Digitar {label}', min_value=low, max_value=high, step=.01,
                           format='%.2f', key=input_key, label_visibility='collapsed',
                           on_change=_copy_control, args=(input_key, key))
    return value


def _volume_control(result: dict, curve: list[dict]) -> dict:
    """Keep the submitted scenario fixed while moving price and purchase cost."""
    low, high = (float(curve[i]['price_brl']) for i in (0, -1))
    initial = float(result['evaluated_price_brl'])
    margin = result['analysis']['personalized']['margin']
    cost = margin['net_cost_brl'] + result['assumptions']['credit_brl']
    signature = (result['product']['ean'], result['assumptions']['regime'],
                 initial, str(cost), low, high, result['price_origin'])
    price_col, cost_col = st.columns(2)
    price = initial
    if low < high:
        price = _linked_control(price_col, 'Preço simulado (R$)', (low, high), initial,
                                f'volume_price_{signature}')
        price_col.caption(f'De {brl_markdown(str(low))} a {brl_markdown(str(high))}')
    chosen_cost = _linked_control(cost_col, 'Custo simulado (R$)',
                                  (0.0, max(.01, float(cost) * 1.5)), float(cost),
                                  f'volume_cost_{signature}')
    cost_col.caption(f'Custo informado: {brl_markdown(cost)}')
    return volume_scenario(result, Decimal(str(price)),
                           acquisition_cost=Decimal(str(chosen_cost)))


def scenarios(result: dict) -> None:
    """Cross competitor prices with the contribution and acquisition scenarios.

    Parameters
    ----------
    result : dict
        Ready demonstration result. All calculations reuse the same profile.
    """
    st.markdown('### Margem de contribuição')
    analysis = scenario_analysis(result)
    _baseline_margin_summary(result, analysis['zero_contribution_price_brl'])
    st.markdown('#### Simule uma promoção')
    st.caption('Altere o preço de venda ou o custo de compra para comparar os cenários.')
    sim = _volume_control(result, analysis['curve'])
    cost = sim['acquisition_cost_brl']
    analysis = scenario_analysis(result, acquisition_cost=cost,
                                 simulated_price=sim['price_brl'])
    _promotion_summary(result, sim, analysis['zero_contribution_price_brl'])
    _comparison_cards(result, sim)
    if analysis['band_status'] == 'all_negative':
        st.warning('Toda a faixa central observada gera contribuição negativa '
                   'com esse custo e as premissas do cenário. Revise o custo '
                   'de aquisição e a conta antes de adotar essa faixa.')
    elif analysis['band_status'] == 'partially_viable':
        st.warning('Parte da faixa observada gera contribuição negativa. '
                   'Compare os pontos antes de decidir o preço.')
    st.markdown('#### Como uma promoção muda a margem por unidade?')
    st.caption('Leia o preço no eixo horizontal e a margem por unidade no vertical. '
               'A curva e seus pontos usam o custo de compra simulado. Abaixo '
               'da linha pontilhada de margem zero, a venda gera perda por unidade.')
    st.plotly_chart(contribution_curve(analysis, result['market'],
                                       result['evaluated_price_brl'],
                                       simulated=sim['price_brl'],
                                       price_label=('Preço atual'
                                                    if result['price_origin'] == 'user_price'
                                                    else 'Preço de partida')),
                    width='stretch', config={'displayModeBar': False})
    with st.expander('Ver os detalhes da simulação'):
        st.caption('No preço mínimo, o arredondamento em centavos pode resultar '
                   'em uma margem ligeiramente acima de zero.')
        points = [volume_scenario(result, p['price_brl'], acquisition_cost=cost)
                  for p in result['corridor_points']]
        if points:
            st.dataframe([{'Preço observado de cenário': brl(p['price_brl']),
                           'Contribuição/unidade': brl(p['contribution_brl']),
                           'Margem de contribuição': percent(p['contribution_percent'])}
                          for p in points], hide_index=True, width='stretch')
        st.caption('As contas abaixo usam o custo simulado. '
                   'O diagnóstico inicial permanece como referência de comparação.')
        st.plotly_chart(sensitivity_chart(analysis), width='stretch',
                        config={'displayModeBar': False})


def compare_regimes(result: dict, labels: dict[str, str]) -> None:
    """Compare the same evaluated price and gross cost under the demo profiles."""
    price = result['evaluated_price_brl']
    margin = result['analysis']['personalized']['margin']
    cost = margin['net_cost_brl'] + result['assumptions']['credit_brl']
    rows = []
    for regime, label in labels.items():
        profile = build_demo_profile(regime, cost, product=result['product'])
        comparison = personalized_margin(price, cost, profile['taxpayer'],
                                         expenses=profile['expenses'])['margin']
        credit = profile['assumptions']['credit_brl']
        rows.append({
            'Regime': label,
            'Tributação estimada': brl(comparison['tax_brl']),
            'Crédito na compra': brl(credit),
            'Contribuição por unidade': brl(comparison['contribution_brl']),
            'Margem de contribuição': percent(comparison['contribution_percent']),
            'Premissa do produto': profile['assumptions']['product_tax']['label'],
        })
    st.caption(f'Preço de venda de {brl_markdown(price)} '
               f'e custo de aquisição de {brl_markdown(cost)} '
               'por unidade em todos os cenários.')
    st.dataframe(rows, hide_index=True, width='stretch')
    st.caption('Perfis demonstrativos para comparar o efeito das premissas '
               'na margem. A tabela usa os tributos na venda e os créditos '
               'considerados no cálculo da contribuição.')

def question_context(question: str, group: str) -> bool:
    """Show cited methodology or sector context for the selected question."""
    text = normalize(question)
    reason = out_of_scope_reason(question)
    evidence = find_sources(question)
    seasonal = bool(re.search(
        r'\b(?:natal|pascoa|carnaval|black friday|ano novo|sazonalidade|'
        r'epoca do ano|dia das maes|dia dos pais)\b', text))
    asks_for_source = re.search(
        r'\b(?:fonte|origem|confi\w*|de onde|metodologia)\b', text)
    if reason == 'tempo_real' and re.search(
            r'\b(?:em promocao|estoque|preco (?:de )?(?:hoje|agora))\b', text):
        st.markdown(REFUSALS['tempo_real'])
        return True
    if seasonal and reason is None:
        _seasonal_context(group, text, evidence.excerpts)
    elif asks_for_source or reason in ('previsao', 'dados_da_empresa'):
        if evidence.answerable:
            st.markdown('**Fontes para esta resposta**')
            for excerpt in evidence.excerpts:
                st.write(excerpt.text)
                st.markdown(f'[{excerpt.title}]({excerpt.url})')
        else:
            st.markdown(evidence.reason)
    return False


MONTH_LABELS = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
                'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')


def _signed(value: float) -> str:
    """Signed percentage with a decimal comma."""
    return f'{value:+.1f}%'.replace('.', ',')


def insight_cards(group: str) -> None:
    """Three sourced signals that show up without a click."""
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    event_col, month_col, climate_col = st.columns(3)
    with event_col, st.container(border=True, key='insight_event'):
        _event_card(group, today)
    with month_col, st.container(border=True, key='insight_month'):
        _month_card(today.month)
    with climate_col, st.container(border=True, key='insight_climate'):
        _climate_card(today.month)
    forecast = st.expander('Previsão do tempo para Curitiba',
                           icon=':material/partly_cloudy_day:',
                           key='curitiba_weather_forecast', on_change='rerun')
    if forecast.open:
        with forecast:
            _forecast_panel()
    st.caption('Sinais do setor e do clima, sempre com fonte. Não são previsões '
               'para a sua loja.')


def _event_card(group: str, today) -> None:
    """Next retail date, preferring one whose source names the product."""
    events = upcoming(today, group, days=60)
    cited = [event for event in events if event['cita_o_produto']]
    dated = [event for event in events if event['tipo'] != 'feriado']
    candidates = cited or dated or events
    if not candidates:
        st.metric('Próxima data do varejo', '—')
        st.caption('Sem datas comemorativas nos próximos 60 dias.')
        return
    chosen = candidates[0]
    start = display_date(str(chosen['inicio']))[:5]
    end = display_date(str(chosen['fim']))[:5]
    when = start if start == end else f'{start} a {end}'
    st.metric('Próxima data do varejo', str(chosen['evento']))
    cites = (f'A fonte cita {group[:1].lower() + group[1:]} nessa data'
             if chosen['cita_o_produto'] else 'A fonte não cita este produto')
    st.caption(f"{when} · {cites} · [fonte]({chosen['fonte_url']})")


def _month_card(month_number: int) -> None:
    """IBGE signal for this month and the next one."""
    month = sector_month(month_number)
    following = sector_month(month_number % 12 + 1)
    st.metric(f'{MONTH_LABELS[month_number - 1]} no setor',
              _signed(float(str(month['desvio_medio_pct']))))
    st.caption('Volume dos supermercados do Paraná frente à média do ano. '
               f"{MONTH_LABELS[month_number % 12]}: "
               f"{_signed(float(str(following['desvio_medio_pct'])))} · "
               f"[IBGE]({month['fonte_url']})")


def _climate_card(month_number: int) -> None:
    """INMET climate normal for Curitiba, plus the next days on demand."""
    climate = climate_month(month_number)
    st.metric('Clima em Curitiba', f"{climate['media']:.1f} °C".replace('.', ','))
    st.caption(f"Média de {MONTH_LABELS[month_number - 1].lower()}, máxima de "
               f"{climate['maxima']:.0f} °C · normais 1991–2020 · "
               f"[INMET]({climate['fonte_url']})")


@st.cache_data(ttl=300, show_spinner=False)
def _cached_forecast() -> tuple[list[dict] | None, str]:
    days = fetch_forecast()
    if days:
        return days, 'Open-Meteo'
    return fetch_inmet_forecast(), 'INMET'


def _retry_forecast() -> None:
    """Discard a failed lookup and keep the panel open for the new result."""
    _cached_forecast.clear()
    st.session_state['curitiba_weather_forecast'] = True


def _forecast_panel() -> None:
    """Seven small day cards with icon, temperatures and chance of rain."""
    with st.spinner('Consultando a previsão de Curitiba...'):
        days, source = _cached_forecast()
    if not days:
        st.caption('A previsão está indisponível agora. As médias do INMET continuam acima.')
        st.button('Tentar novamente', key='retry_curitiba_weather',
                  on_click=_retry_forecast)
        st.link_button('Consultar no INMET', INMET_SOURCE_URL)
        return
    cards = []
    for day in days:
        rain = f"{day['chuva']}%" if day['chuva'] is not None else '—'
        cards.append(
            f"<div class='forecast-day'><div class='fd-name'>{day['dia']}</div>"
            f"<div class='fd-date'>{day['data']:%d/%m}</div>"
            f"<div class='fd-icon' title='{escape(day['descricao'])}'>{day['icone']}</div>"
            f"<div class='fd-temp'><b>{day['maxima']}°</b> {day['minima']}°</div>"
            f"<div class='fd-rain'>💧 {rain}</div></div>")
    st.markdown("<div class='forecast-grid'>" + ''.join(cards) + '</div>',
                unsafe_allow_html=True)
    if source == 'INMET':
        st.caption(f'{len(days)} dias disponíveis. Máxima e mínima do '
                   f'[INMET]({INMET_SOURCE_URL}). Chance de chuva indisponível nesta fonte.')
    else:
        st.caption(f'Máxima, mínima e chance de chuva. [Open-Meteo]({SOURCE_URL}).')
    st.caption('Contexto meteorológico para o varejo.')


def season_panel(group: str) -> None:
    """Always-visible season block: sector signal by month and upcoming dates."""
    _seasonal_context(group, '', ())


def _seasonal_context(group: str, question: str, excerpts: tuple[Excerpt, ...]) -> None:
    """Show the sector signal and upcoming dates, with sources."""
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    st.markdown('#### Época do ano · sinais do setor')
    for excerpt in excerpts:
        if excerpt.source_id.startswith('saz_') and excerpt.source_id != 'saz_supermercados_pr':
            st.write(excerpt.text)
            st.markdown(f'[{excerpt.title}]({excerpt.url})')
    st.caption('Dados do setor. O app não tem as vendas da sua loja.')
    month_data = sector_by_month()
    focus = 'dez' if 'natal' in question else MONTHS[today.month - 1]
    chart = go.Figure(go.Bar(
        x=list(MONTHS),
        y=[month_data[month]['desvio_medio_pct'] for month in MONTHS],
        marker_color=['#006963' if month == focus else '#D5E3DC' for month in MONTHS],
        hovertemplate='%{x}: %{y:+.1f}%<extra></extra>'))
    chart.update_layout(height=220, margin={'l': 8, 'r': 8, 't': 5, 'b': 8})
    chart.update_yaxes(ticksuffix='%', zeroline=True, zerolinecolor='#132B32')
    st.plotly_chart(chart, width='stretch', config={'displayModeBar': False})
    st.markdown('Desvio médio em relação à média de cada ano, 2022–2025. '
                '[IBGE · volume de supermercados no Paraná](https://sidra.ibge.gov.br/tabela/8882)')
    dates = upcoming(today, group)
    if dates:
        st.markdown('**Próximas datas para este produto**')
    for event in sorted(dates, key=lambda row: not row['cita_o_produto'])[:3]:
        star = '★ ' if event['cita_o_produto'] else ''
        start = display_date(str(event['inicio']))
        st.markdown(f"- {star}[{event['evento']}]({event['fonte_url']}) · {start}")
    if any(event['cita_o_produto'] for event in dates):
        st.caption('★ A fonte cita esta categoria.')

def historical(bundle: dict | None) -> None:
    """Display monthly levels separately from matched-establishment changes.

    Parameters
    ----------
    bundle : dict or None
        Optional validated observed analytics bundle.
    """
    st.subheader('Como os preços evoluíram?')
    if not bundle or not bundle.get('history'):
        st.info('Sem histórico de preços disponível para este produto.')
        return
    history = bundle['history']
    st.plotly_chart(history_chart(history), width='stretch',
                    config={'displayModeBar': False})
    st.caption('Mediana e P25–P75 por mês da foto. Usa a última observação '
               'disponível por loja no período; meses ausentes ficam em branco. '
               'Mudanças nas redes da amostra também afetam o nível observado.')
    last = history[-1]
    if last['paired_change_percent'] is None:
        st.info(f"No último intervalo há {last['common_store_count']} loja(s) "
                f"repetida(s) em {last['common_network_count']} rede(s). "
                'A variação pareada não foi divulgada por falta de cobertura '
                'comparável suficiente ou de meses consecutivos.')
    else:
        st.write('**Variação nas mesmas lojas, agregada por rede:** ' +
                 percent(last['paired_change_percent'], signed=True))
    with st.expander('Conferir cobertura e comparações por período'):
        st.dataframe([{'Mês': r['period'], 'Mediana': brl(r['median']),
                       'Redes': r['network_count'], 'Lojas': r['store_count'],
                       'Redes com lojas repetidas': r['common_network_count'],
                       'Variação pareada': percent(r['paired_change_percent'],
                           signed=True) if r['paired_change_percent'] is not None
                       else 'Sem cobertura comparável'} for r in history],
                     hide_index=True, width='stretch')
    st.caption('A comparação exige ao menos três redes com lojas repetidas. '
               'Confira a cobertura de cada período antes de interpretar a variação.')


def comparables(bundle: dict | None) -> None:
    """Show the cohort heatmap and an identical-basket network comparison.

    Parameters
    ----------
    bundle : dict or None
        Optional observed same-type/presentation/date cohort.
    """
    st.subheader('O produto e seus similares')
    if not bundle or not bundle.get('comparables'):
        st.info('Sem comparação de similares disponível para este produto. '
                'A comparação exige tipo, embalagem e data equivalentes.')
        return
    matrix = comparable_matrix(bundle['comparables'])
    cohort = matrix['cohort']
    st.write(f"**Recorte:** {cohort['group']} · {cohort['type']} · "
             f"{cohort['package']} · {display_date(cohort['date'])}")
    st.plotly_chart(cohort_heatmap(matrix), width='stretch',
                    config={'displayModeBar': False})
    st.caption('Cada linha usa a mediana daquele SKU como índice 100. '
               'Célula vazia significa ausência de preço, não preço zero. '
               'Cores comparam preços; não descrevem o perfil de clientes.')
    if matrix['network_index'] and len(matrix['common_basket_networks']) >= 2:
        st.write('**Índice por rede na mesma cesta de produtos**')
        st.dataframe([{'Rede': r['network'], 'Índice (referência 100)':
                       f"{r['index']:.2f}", 'SKUs na cesta': r['sku_count']}
                      for r in sorted(matrix['network_index'],
                                      key=lambda r: r['index'])],
                     hide_index=True, width='stretch')
        st.caption('Média geométrica dos relativos de preços, com pesos iguais '
                   'por SKU. Apenas redes com a cesta completa são comparadas; '
                   'o índice não usa participação de vendas.')
    else:
        st.info('Ainda não há uma cesta comum suficiente para comparar '
                'o índice de várias redes neste grupo.')


def extra_price_charts(result: dict) -> None:
    """Optional charts from the public monthly base, clearly labelled."""
    ean = result['product']['ean']
    price = result['evaluated_price_brl']
    evolution, networks = st.tabs(['Evolução do preço', 'Redes mês a mês'])
    with evolution:
        band = monthly_band(ean)
        if band.empty:
            st.info('Sem histórico deste produto na base pública.')
        else:
            st.markdown('**Como a mediana do mercado andou nos últimos meses**')
            st.plotly_chart(median_history_chart(band, price), width='stretch',
                            config={'displayModeBar': False})
            st.caption('Linha: mediana do mês. Faixa verde: preços entre o primeiro e o '
                       'terceiro quartil da amostra. Tracejado: o seu preço.')
    with networks:
        table = network_by_month(ean)
        if table.empty:
            st.info('Sem preços por rede deste produto na base pública.')
        else:
            st.markdown('**Quem cobra mais e quem cobra menos, mês a mês**')
            st.plotly_chart(network_heatmap(table), width='stretch',
                            config={'displayModeBar': False})
            st.caption('Cor mais escura: preço mais alto. Célula vazia: mês sem coleta '
                       'naquela rede. Redes em ordem do último preço. '
                       'Toque em uma célula para ver o valor.')
    st.caption(f'Fonte: {SOURCE_LABEL}. O histórico usa uma amostra mensal própria, '
               'que pode diferir da referência principal de preço.')


def category_view(result: dict) -> None:
    """The product against the rest of its category, by kg or litre."""
    ean = result['product']['ean']
    group = result['product']['group']
    table = similar_unit_prices(group)
    if len(table) < 2:
        st.caption(f'Ainda não há similares suficientes de {group.lower()} no catálogo '
                   'para comparar.')
        return
    unit = table['unidade'].iloc[0]
    ranked = table.reset_index(drop=True)
    prices = [float(value) for value in ranked['preco_unidade'].tolist()]
    eans = ranked['ean'].tolist()
    position = eans.index(ean) + 1 if ean in eans else None
    cheapest = prices[0]
    insight = st.columns([1, 1, 1])
    if position is not None:
        own = prices[position - 1]
        insight[0].metric(f'Preço por {unit}', _money(own))
        insight[1].metric('Posição na categoria', f'{position}º de {len(ranked)}',
                          help='Do mais barato (1º) ao mais caro, por kg ou litro.')
        insight[2].metric('Frente ao mais barato',
                          f"{own / cheapest:.1f}x".replace('.', ','))
    st.plotly_chart(similars_chart(table, ean), width='stretch',
                    config={'displayModeBar': False})
    st.caption(f'Mediana dos últimos 3 meses dividida pelo tamanho da embalagem, '
               f'para comparar produtos de tamanhos diferentes. Fonte: {SOURCE_LABEL}.')


def _money(value: float) -> str:
    return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

"""Render analytical views while keeping source coverage visible."""
from datetime import datetime
from decimal import Decimal
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
    """Compare the two scenarios while keeping the required volume distinct."""
    comparison = sim['position']
    baseline_position = result['market_position'] if comparison is not None else None
    baseline = result['analysis']['personalized']['margin']
    change = sim['volume_change_percent']
    current, simulated, volume = st.columns(3)
    with current, st.container(border=True):
        label = 'Preço atual' if result['price_origin'] == 'user_price' else 'Preço de partida'
        st.metric(label, brl(result['evaluated_price_brl']))
        cost = baseline['net_cost_brl'] + result['assumptions']['credit_brl']
        st.caption('Custo de compra ' + brl(cost))
        st.metric('Contribuição de partida', brl(baseline['contribution_brl']))
        st.caption(percent(baseline['contribution_percent']) + ' do preço de partida')
        st.metric('Posição de partida', percent(baseline_position['gap_percent'], signed=True)
                  if baseline_position is not None else '—')
    with simulated, st.container(border=True):
        st.metric('Preço simulado', brl(sim['price_brl']))
        st.caption('Custo simulado ' + brl(sim['acquisition_cost_brl']))
        st.metric('Contribuição simulada', brl(sim['contribution_brl']))
        st.caption(percent(sim['contribution_percent']) + ' do preço simulado')
        st.metric('Preço simulado vs. mediana', percent(comparison['gap_percent'], signed=True)
                  if comparison is not None else '—')
    with volume, st.container(border=True):
        st.metric('Variação de volume necessária',
                  percent(change, signed=True) if change is not None else '—')
        st.caption('Para manter a contribuição total do cenário de partida.')
        if sim['units_per_100'] is not None:
            st.write(f"**Exemplo:** a cada 100 unidades no cenário de partida, "
                     f"seriam necessárias **{sim['units_per_100']} unidades** "
                     'no cenário simulado.')


def _volume_control(result: dict, curve: list[dict]) -> tuple[Decimal, Decimal]:
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
        price = price_col.slider('Preço simulado (R$)', min_value=low, max_value=high,
                                 value=initial, step=.01, key=f'volume_price_{signature}')
    chosen_cost = cost_col.slider(
        'Custo simulado (R$)', min_value=0.0, max_value=max(.01, float(cost) * 1.5),
        value=float(cost), step=.01, key=f'volume_cost_{signature}')
    price_value, cost_value = Decimal(str(price)), Decimal(str(chosen_cost))
    sim = volume_scenario(result, price_value, acquisition_cost=cost_value)
    _comparison_cards(result, sim)
    if sim['contribution_brl'] <= 0:
        st.warning('Com contribuição unitária zero ou negativa, aumentar '
                   'o volume não gera contribuição positiva.')
    elif sim['volume_change_percent'] is None:
        st.info('O preço de partida tem contribuição zero ou negativa. '
                'A comparação de volume exige uma contribuição inicial positiva.')
    st.caption('O exemplo em unidades é arredondado para cima. '
               'A reação dos clientes à mudança de preço depende da sua loja.')
    return price_value, cost_value


def scenarios(result: dict) -> None:
    """Cross competitor prices with the contribution and acquisition scenarios.

    Parameters
    ----------
    result : dict
        Ready demonstration result. All calculations reuse the same profile.
    """
    st.markdown('### Simule preço e custo')
    analysis = scenario_analysis(result)
    simulated, cost = _volume_control(result, analysis['curve'])
    analysis = scenario_analysis(result, acquisition_cost=cost)
    if analysis['band_status'] == 'all_negative':
        st.warning('Toda a faixa central observada gera contribuição negativa '
                   'com esse custo e as premissas do cenário. Revise o custo '
                   'de aquisição e a conta antes de adotar essa faixa.')
    elif analysis['band_status'] == 'partially_viable':
        st.warning('Parte da faixa observada gera contribuição negativa. '
                   'Compare os pontos antes de decidir o preço.')
    st.markdown('#### Como uma promoção muda a margem por unidade?')
    st.caption('A curva usa o custo simulado. O ponto azul mostra o preço de partida '
               'e o verde mostra o preço simulado quando ele muda.')
    st.plotly_chart(contribution_curve(analysis, result['market'],
                                       result['evaluated_price_brl'],
                                       simulated=simulated),
                    width='stretch', config={'displayModeBar': False})
    with st.expander('Ver os detalhes da simulação'):
        st.info('Preço com contribuição zero neste cenário: **' +
                brl(analysis['zero_contribution_price_brl']) +
                '**. Abaixo dele, a venda não cobre custo e tributos.')
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

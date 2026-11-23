"""Render business results without duplicating domain calculations."""
import csv
import io
import logging
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import os
from zoneinfo import ZoneInfo

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from tax_pricing.demo_profile import demo_settings
from tax_pricing.team_market import STORE_AGGREGATION
from tax_pricing.ui.charts import market_chart, price_tree
from tax_pricing.ui.formatting import (
    brl, brl_markdown, display_date, display_month, network_name, percent, product_name,
)
from tax_pricing.source_search import (
    build_messages, citations_are_valid, find_sources, strip_fact_tags,
)
from tax_pricing.ui.grounded_explanation import (
    explanation_facts, invented_numbers, markdown_safe, request_answer, season_context,
    sourced_answer_is_valid,
)
from tax_pricing.ui.price_brief import position_insight, prioritize_brief, promotion_insight
from tax_pricing.ui.price_questions import answer_question
from tax_pricing.ui.reading import decision_text
from tax_pricing.ui import forecast_view, lab_view

GENERIC_ANSWERS = ('Tente perguntar',)
ANSWER_ATTEMPTS = 2
SEASON_QUESTION = 'Vale promoção nesta época do ano?'
STORE_QUESTION = 'Por que cada loja conta uma vez?'
BAND_QUESTION = 'O que significa a faixa de preço?'
SOURCE_QUESTIONS = {
    STORE_QUESTION: 'Por que a referência é por loja?',
    BAND_QUESTION: 'Como interpretar a faixa P25–P75?',
}
CHRISTMAS_QUESTION = 'O que a pesquisa diz sobre bebidas no Natal?'
BLACK_FRIDAY_QUESTION = 'O que a pesquisa diz sobre a Black Friday?'
CONTEXT_QUESTIONS = (
    STORE_QUESTION,
    'Qual a fonte dos preços do Clique Economia?',
    BAND_QUESTION,
    SEASON_QUESTION,
    'Quais são as premissas da tributação estimada?',
    CHRISTMAS_QUESTION,
)
BEVERAGE_GROUPS = frozenset({'Refrigerante 2 L', 'Cerveja', 'Água mineral'})
SOURCE_ASK = re.compile(r'\b(por que|porque|de onde|fonte|origem|confi|como .*calcul|'
                        r'metodo|método|diario|diário)', re.IGNORECASE)

REGIME_LABELS = {'simples_nacional': 'Simples Nacional',
                 'lucro_presumido': 'Lucro Presumido', 'lucro_real': 'Lucro Real'}


def _period(snapshot: dict) -> str:
    """Distinguish a multi-round reference from its last observation date."""
    last = display_date(snapshot['date'])
    window = snapshot.get('window')
    if window:
        start, end = display_month(window[0]), display_month(window[-1])
        period = f'em {end}'
        if start != end:
            if window[0][:4] == window[-1][:4]:
                start = start.split(' de ', maxsplit=1)[0]
            period = f'de {start} a {end}'
        return f'Preços coletados {period} · Última coleta: {last}'
    return f'Última coleta: {last}'


def header(*, compact: bool = False) -> None:
    """Use a centered starting point and a smaller masthead after analysis."""
    with st.container(key='masthead' if compact else 'intro_hero'):
        st.image(str(Path(__file__).resolve().parents[2] / 'assets' / 'logo.png'),
                 width=280 if compact else 360)
        if not compact:
            st.title('Seu preço faz sentido no mercado?')
            st.markdown('<p class="lead">Compare seu preço com o mercado de Curitiba '
                        'e veja quanto sobra por unidade.</p>', unsafe_allow_html=True)


def _kpis(result: dict) -> None:
    """Three answers at a glance: what is left, where the price sits, the tax."""
    margin = result['analysis']['personalized']['margin']
    price = result['evaluated_price_brl']
    snapshot = result['market']
    position = result['market_position']
    left, market, tax = st.columns(3)
    with left, st.container(border=True, key=(
            'margin_loss' if margin['contribution_brl'] < 0 else 'margin_gain')):
        st.metric('Margem de contribuição', brl(margin['contribution_brl']))
        st.caption(f"por unidade · {percent(margin['contribution_percent'])} do preço "
                   'de venda, depois de custo e tributos')
    with market, st.container(border=True, key='market_kpi'):
        if position is None or snapshot['status'] == 'unavailable':
            st.metric('Seu preço frente ao mercado', '—')
            st.caption('Sem referência de mercado disponível')
        else:
            gap = position['gap_brl']
            side = 'acima' if gap > 0 else 'abaixo' if gap < 0 else 'igual'
            value = (brl(abs(gap)) + f' {side}') if gap else 'No preço do meio'
            st.metric('Seu preço frente ao mercado', value)
            by_store = snapshot.get('aggregation') == STORE_AGGREGATION
            base = (f"{snapshot['store_count']} lojas" if by_store
                    else f"{snapshot['network_count']} redes")
            st.caption(f"Preço do meio do mercado: {brl(snapshot['median'])} · {base} · "
                       f"{percent(position['gap_percent'], signed=True)}")
            if snapshot['status'] == 'historical_reference':
                st.caption('Preços antigos. Última coleta em '
                           f"{display_month(snapshot['date'][:7])}.")
            if snapshot.get('low_precision'):
                st.caption('A referência de preço tem mais incerteza. '
                           'Use a faixa como orientação.')
            if snapshot.get('kind') == 'estimated':
                st.caption('Referência estimada, sem faixa observada.')
    with tax, st.container(border=True, key='tax_kpi'):
        st.metric('Tributação estimada', brl(margin['tax_brl']),
                  help='Calculada para uma empresa de exemplo no regime selecionado.')
        st.caption(f"{percent(margin['tax_brl'] / price * 100)} do preço · "
                   f"{REGIME_LABELS[result['assumptions']['regime']]} · tributação de exemplo")


def _llm_setting(name: str) -> str:
    """Use a nonblank environment value, then the Streamlit root secret."""
    value = os.getenv(name, '').strip()
    if value:
        return value
    try:
        secret = st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        return ''
    return secret.strip() if isinstance(secret, str) else ''


def _tax_line(result: dict, *, brief: bool = False) -> str:
    """Explain what the tax estimate is made of, in one short line."""
    margin = result['analysis']['personalized']['margin']
    assumptions = result['assumptions']
    regime = REGIME_LABELS[assumptions['regime']]
    tax = margin['tax_brl']
    paid = [row for row in result['analysis']['personalized']['tax_components']
            if row['amount_brl'] > 0]
    share = percent(tax / result['evaluated_price_brl'] * 100)
    if tax > 0:
        names = ['guia única do Simples (DAS)' if row['name'] == 'DAS' else row['name']
                 for row in paid]
        detail = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' e ' + names[-1]
        line = (f'A estimativa inclui {detail} sobre a venda.'
                if brief else
                f'Tributação estimada de {brl_markdown(tax)} por unidade ({share} do '
                f'preço) no {regime}, com {detail} sobre a venda.')
    else:
        line = f'Sem tributo sobre a venda neste cenário do {regime}.'
    treatment = assumptions.get('product_tax') or {}
    if treatment.get('purchase_icms_st_assumed'):
        line += ' O ICMS-ST foi retido na compra e já está no custo.'
    credit = Decimal(str(assumptions.get('credit_brl') or 0))
    if credit > 0:
        line += (' A estimativa inclui o crédito de compra assumido.' if brief else
                 f' Crédito de {brl_markdown(credit)} da compra já descontado.')
    return line + ' Tributação de exemplo.'


def _network_table(market: dict, price: Decimal) -> None:
    """Use the same per-network values the chart already plots."""
    with st.expander('Ver preços por rede'):
        rows: list[dict] = []
        for name, value in market['per_network_brl'].items():
            if value is not None:
                amount = Decimal(str(value))
                rows.append({'Rede': network_name(name), 'Preço observado': float(amount),
                             'Diferença para seu preço': float(amount - price)})
        columns = {label: st.column_config.NumberColumn(label, format='R$ %.2f')
                   for label in ('Preço observado', 'Diferença para seu preço')}
        st.dataframe(sorted(rows, key=lambda row: row['Preço observado']),
                     column_config=columns, hide_index=True, width='stretch')
        st.caption('Diferença negativa indica uma rede mais barata que o preço analisado.')


def _market_view(result: dict) -> None:
    """Show one observed-price chart with provenance next to the marks."""
    market = result['market']
    price = result['evaluated_price_brl']
    figure = market_chart(market, price)
    if figure is None:
        st.info('Sem preços observados por rede para exibir neste cenário.')
        return
    has_band = market.get('p25') is not None and market.get('p75') is not None
    band_legend = ('<span><i class="market-band"></i>Faixa central de preços</span>'
                   if has_band else '')
    st.markdown(
        '<div class="market-legend">'
        f'<span><i class="market-own"></i>Seu preço <strong>{brl(price)}</strong></span>'
        f'<span><i class="market-median"></i>Preço do meio do mercado '
        f'<strong>{brl(market["median"])}</strong></span>'
        '<span><i class="market-observed"></i>Preço observado da rede</span>'
        f'{band_legend}</div>',
        unsafe_allow_html=True)
    st.plotly_chart(figure, width='stretch', config={'displayModeBar': False})
    source = market.get('source_label', market['source'])
    unit = 'loja' if market.get('aggregation') == STORE_AGGREGATION else 'rede'
    coverage = f"{market['network_count']} redes"
    if market.get('store_count'):
        coverage = f"{market['store_count']} lojas · " + coverage
    st.caption(f'{source} · {_period(market)} · {coverage}')
    if has_band:
        st.caption(f"Cada ponto é uma rede. A área sombreada é a faixa central, com a metade "
                   f"dos preços por {unit}: **{brl_markdown(market['p25'])} "
                   f"a {brl_markdown(market['p75'])}.**")
    else:
        st.caption('Cada ponto é o preço de uma rede.')
    _network_table(market, price)


def _csv_cell(value: object) -> str:
    """Keep numeric columns readable in pt-BR and neutralize text formulas."""
    if isinstance(value, Decimal):
        return format(value, '.2f').replace('.', ',')
    text = '' if value is None else str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def _download(result: dict) -> None:
    """Export the checked scenario and the matching market reference."""
    market = result['market']
    margin = result['analysis']['personalized']['margin']
    window = market.get('window') or []
    fields = {
        'Produto': result['product']['description'],
        'EAN': result['product']['ean'],
        'Regime demonstrativo': REGIME_LABELS[result['assumptions']['regime']],
        'Cenário': ('Preço informado' if result['price_origin'] == 'user_price'
                    else 'Preço pela referência de mercado'),
        'Preço (R$)': result['evaluated_price_brl'],
        'Margem por unidade (R$)': margin['contribution_brl'],
        'Margem (%)': margin['contribution_percent'].quantize(Decimal('.01')),
        'Tributação estimada (R$)': margin['tax_brl'],
        'Mediana de mercado (R$)': market.get('median'),
        'P25 (R$)': market.get('p25'),
        'P75 (R$)': market.get('p75'),
        'Referência de mercado': {'current_reference': 'Atual',
                                  'historical_reference': 'Histórica',
                                  'unavailable': 'Indisponível'}[market['status']],
        'Tipo de referência': {'observed': 'Observada', 'estimated': 'Estimada'}.get(
            market.get('kind', '')),
        'Precisão': 'Baixa precisão' if market.get('low_precision') else '',
        'Fonte': market.get('source_label', market.get('source')),
        'Última coleta': market.get('date'),
        'Período': ' a '.join([window[0], window[-1]] if len(window) > 1 else window),
        'Lojas': market.get('store_count'),
        'Redes': market.get('network_count'),
    }
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(fields)
    writer.writerow([_csv_cell(value) for value in fields.values()])
    st.caption('O CSV registra o cenário analisado no topo da tela.')
    st.download_button('Baixar análise em CSV', buffer.getvalue().encode('utf-8-sig'),
                       file_name=f"tax-aware-{result['product']['ean']}.csv",
                       mime='text/csv', on_click='ignore', icon=':material/download:')


def _premises(result: dict) -> None:
    """Keep demonstration assumptions accessible without extra inputs."""
    st.write(result['notice'])
    assumptions = result['assumptions']
    st.write(f"**Perfil:** {REGIME_LABELS[assumptions['regime']]} · "
             f"**Data fiscal:** {display_date(demo_settings()['fiscal_date'])}")
    st.write(f"**Crédito hipotético da compra:** "
             f"{brl(assumptions['credit_brl'])} por unidade.")
    st.caption('Taxas, receita de referência e créditos são premissas '
               'demonstrativas, sem personalização fiscal da empresa.')
    profile = assumptions['profile']
    treatment = assumptions.get('product_tax')
    if treatment:
        st.write('**Tratamento do cenário:** ' + treatment['label'])
        for condition in treatment['conditions']:
            st.caption(condition)
        exclusion = assumptions.get('purchase_icms_st_exclusion_brl')
        if exclusion:
            st.caption('ICMS-ST hipotético excluído da base PIS/Cofins: '
                       f'{brl(exclusion)}. Já incluído no custo; '
                       'não é crédito recuperável.')
        for source in treatment.get('source_urls', []):
            st.markdown('[Fonte da regra do cenário](' + source + ')')
    if assumptions['regime'] == 'simples_nacional':
        st.write(f"**Receita de referência em 12 meses:** "
                 f"{brl_markdown(profile['rbt12_brl'])} · "
                 f"**Taxa nominal do cenário:** "
                 f"{percent(Decimal(profile['nominal_fraction']) * 100)} · "
                 f"**Parcela a deduzir:** {brl_markdown(profile['deduction_brl'])}.")
    ledger = result['analysis']['personalized']['tax_components']
    st.dataframe([{'Parcela': row['name'], 'Base': brl(row['base_brl']),
                   'Taxa do cenário': percent(row['rate'] * 100),
                   'Valor': brl(row['amount_brl'])} for row in ledger],
                 hide_index=True, width='stretch')
    st.caption(f"Catálogo: EAN {result['product']['ean']} · "
               f"NCM {result['product']['ncm']}. "
               'Enquadramento ainda sujeito à revisão fiscal.')
    if result['market']['status'] != 'unavailable':
        st.write('**Origem da referência de mercado:**')
        st.caption(result['market'].get('source_label', 'Pesquisa de preços observados'))
        if 'Clique Economia' in result['market']['source']:
            st.markdown('[Base pública Clique Economia – Curitiba]('
                        'https://dadosabertos.curitiba.pr.gov.br/'
                        'conjuntodado/detalhe?chave='
                        '245ef1b9-f82a-42ed-a711-1dec4ccd4be1)')
    rtc = result['analysis']['rtc']
    if rtc['status'] == 'calculated_ibs_cbs':
        st.write('**IBS/CBS no cenário consultado à Receita**')
        st.dataframe([
            {'Tributo': part['label'], 'Alíquota efetiva': percent(
                part['effective_rate_percent']), 'Valor': brl(part['amount_brl'])}
            for part in rtc['result']['summary']['components']],
            hide_index=True, width='stretch')
        st.caption('Esse cálculo está separado da dedução usada na margem. '
                   'A base adotada é uma convenção demonstrativa.')
    else:
        st.caption('A consulta oficial de IBS/CBS está indisponível. '
                   'A margem acima usa as premissas da tributação estimada.')


def _overview(result: dict) -> None:
    """Lead with the observed band in suggestion mode and the three answers."""
    if result['price_origin'] == 'corridor_scenario':
        points = result['corridor_points']
        if points:
            low, high = points[0], points[-1]
            st.write(f"**Faixa comum de preços no mercado:** {brl_markdown(low['price_brl'])} "
                     f"a {brl_markdown(high['price_brl'])}")
            st.caption('Margem por unidade no menor e no maior preço da faixa: '
                       f"{brl_markdown(low['contribution_brl'])} a "
                       f"{brl_markdown(high['contribution_brl'])}.")
    _kpis(result)


def source_facts(result: dict) -> dict[str, str]:
    """Attach the selected product and its actual demo assumptions to retrieval."""
    facts = {name: str(text) for name, text in explanation_facts(result).items()}
    facts['product'] = product_name(result['product']['description'])
    facts['tax'] = _tax_line(result)
    assumed = (result['assumptions'].get('product_tax') or {}).get('purchase_icms_st_assumed')
    facts['purchase_st'] = (
        'ICMS-ST retido na compra é premissa deste cenário.' if assumed else
        'ICMS-ST retido na compra não é premissa deste cenário.')
    market = result['market']
    if market.get('median') is not None:
        facts['reference'] = (
            f"Mediana {brl(market['median'])}; {market.get('store_count', '—')} lojas; "
            f"{market['network_count']} redes; última coleta {display_date(market['date'])}.")
    return facts


def _checked_answer(question: str, facts: dict[str, str], evidence, model: str,
                    api_key: str) -> str | None:
    """Try twice and keep only an answer whose figures and citations pass."""
    allowed = ' '.join([question, *facts.values(),
                        *(item.text for item in evidence.excerpts)])
    for attempt in range(1, ANSWER_ATTEMPTS + 1):
        answer = request_answer(build_messages(question, facts, evidence), model=model,
                                api_key=api_key, url=_llm_setting('TAX_PRICING_LLM_URL'))
        cites = citations_are_valid(answer or '', evidence)
        if sourced_answer_is_valid(answer, allowed, cites):
            return answer
        logging.getLogger(__name__).warning(
            'Sourced answer rejected: attempt=%s empty=%s citations=%s invented=%s',
            attempt, not answer, cites, invented_numbers(answer, allowed))
    return None


def _sourced_answer(question: str, result: dict) -> bool:
    """Answer from the retrieved sources; show it only if every check passes."""
    evidence = find_sources(question)
    api_key = _llm_setting('OPENAI_API_KEY')
    model = _llm_setting('TAX_PRICING_LLM_MODEL')
    if not (evidence.answerable and api_key and model):
        return False
    answers = st.session_state.setdefault('source_answers', {})
    if question not in answers:
        with st.spinner('Buscando nas fontes...'):
            answers[question] = _checked_answer(question, source_facts(result), evidence,
                                                model, api_key)
    answer = answers[question]
    if answer is None:
        return False
    shown = strip_fact_tags(answer)
    for number, item in enumerate(evidence.excerpts, start=1):
        shown = shown.replace(f'[{item.source_id}]', f'[{number}]')
    st.markdown(markdown_safe(shown))
    links = ' · '.join(f'[{number}] [{item.title}]({item.url})'
                       for number, item in enumerate(evidence.excerpts, start=1))
    st.caption('Resposta com IA · fontes consultadas: ' + links)
    return True


def _price_brief(result: dict) -> None:
    """Render a single interpretation directly beneath the market chart."""
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    season, source = season_context(result['product']['group'], today)
    lines = {
        'Posicionamento': position_insight(result),
        'Tributação estimada': _tax_line(result, brief=True),
        'Época do ano': season or 'A fonte setorial não traz um sinal forte para este mês.',
        'Promoção': promotion_insight(result),
    }
    api_key, model = _llm_setting('OPENAI_API_KEY'), _llm_setting('TAX_PRICING_LLM_MODEL')
    with st.container(border=True, key='summary_box'):
        st.markdown('#### Resumo do preço')
        if api_key and model and 'brief_order' not in st.session_state:
            with st.spinner('Organizando os pontos do seu cenário...'):
                st.session_state['brief_order'] = prioritize_brief(
                    lines, model=model, api_key=api_key, url=_llm_setting('TAX_PRICING_LLM_URL'))
        order = st.session_state.get('brief_order', ()) if api_key and model else ()
        if season:
            lines['Época do ano'] += f' [Fonte]({source})'
        st.markdown('\n'.join(f'- **{key}.** {lines[key]}' for key in (order or lines)))
        if order:
            st.caption('Prioridades sugeridas com apoio de IA.')


def _group_questions(group: str) -> tuple[str, ...]:
    """Offer the beverage study only for products it describes."""
    if group in BEVERAGE_GROUPS:
        return CONTEXT_QUESTIONS
    return tuple(BLACK_FRIDAY_QUESTION if question == CHRISTMAS_QUESTION else question
                 for question in CONTEXT_QUESTIONS)


def _questions(result: dict) -> None:
    """Questions that add context: calculations first, then cited sources."""
    st.caption('Clique em uma pergunta para consultar as fontes.')
    columns = st.columns(2)
    selection = st.session_state.get('suggested_price_question', '')
    for index, suggested in enumerate(_group_questions(result['product']['group'])):
        if columns[index % len(columns)].button(
                suggested, width='stretch', on_click=st.session_state.pop,
                args=('price_question', None)):
            selection = suggested
            source_question = SOURCE_QUESTIONS.get(suggested, suggested)
            answers = st.session_state.get('source_answers', {})
            if answers.get(source_question, '') is None:
                del answers[source_question]
            st.session_state['suggested_price_question'] = suggested
    question = st.text_input('Ou escreva sua pergunta', key='price_question',
                             max_chars=240,
                             placeholder=STORE_QUESTION)
    if not (question.strip() or selection):
        return
    selected = question.strip() or selection
    with st.container(border=True, key='answer_box'):
        st.caption('Pergunta: ' + selected)
        _answer(selected, result)


def _answer(selected: str, result: dict) -> None:
    """Calculations come from the simulator; context comes from the sources."""
    if selected in (*CONTEXT_QUESTIONS, BLACK_FRIDAY_QUESTION):
        question_for_sources = SOURCE_QUESTIONS.get(selected, selected)
        if _sourced_answer(question_for_sources, result):
            return
        if selected == SEASON_QUESTION:
            lab_view.question_context(selected, result['product']['group'])
            return
        for excerpt in find_sources(question_for_sources).excerpts:
            st.write(excerpt.text)
            st.markdown(f'[{excerpt.title}]({excerpt.url})')
        return
    if lab_view.question_context(selected, result['product']['group']):
        return
    if SOURCE_ASK.search(selected) and _sourced_answer(selected, result):
        return
    calculated = answer_question(selected, result)
    if not calculated.startswith(GENERIC_ANSWERS):
        st.write(calculated)
    elif not _sourced_answer(selected, result):
        st.write(calculated)


def _market_intelligence(result: dict) -> None:
    """A dedicated space for context: sourced answers and the season."""
    st.markdown('### Inteligência de mercado')
    st.caption('Pergunte sobre os preços, a época do ano e os cuidados '
               'antes de fazer uma promoção.')
    with st.container(border=True, key='ask_box'):
        _questions(result)
    group = result['product']['group']
    st.markdown('#### Época do ano e clima')
    lab_view.insight_cards(group)
    with st.expander('Ver calendário e histórico do setor', icon=':material/calendar_month:'):
        lab_view.season_panel(group)


def _how_we_calculate(result: dict) -> None:
    """Price tree and deductions, on demand."""
    st.subheader('Como o preço vira margem')
    st.write('Comece pelo valor da venda e tire o custo de aquisição e os '
             'tributos. A última coluna é a margem de contribuição por unidade.')
    margin = result['analysis']['personalized']['margin']
    st.metric('Tributação estimada', brl(margin['tax_brl']))
    st.caption(percent(margin['tax_brl'] / result['evaluated_price_brl'] * 100)
               + ' do preço avaliado.')
    treatment = result['assumptions'].get('product_tax') or {}
    if margin['tax_brl'] == 0 and treatment.get('purchase_icms_st_assumed'):
        st.caption('O cenário assume ICMS-ST retido na compra e '
                   'incluído no custo informado.')
    st.plotly_chart(price_tree(margin, result['assumptions']['credit_brl']),
                    width='stretch', config={'displayModeBar': False})
    st.markdown(_tax_line(result))
    st.write(decision_text(result)['contribution'])
    st.caption('Eventual crédito é hipotético e aparece separado do custo '
               'de aquisição. Margem de contribuição é preço menos custo e '
               'tributos; não equivale a lucro líquido.')


def _category(result: dict) -> None:
    """Optional comparison using the separately labeled public monthly data."""
    lab_view.category_view(result)


def _open_current_price(result: dict, historical_price: Decimal | None = None) -> None:
    """Reopen the analyzed SKU with the original cost and an optional editable anchor."""
    submitted = result['submitted_inputs']
    st.session_state['group'] = submitted['group']
    st.session_state['product'] = submitted['ean']
    st.session_state['scenario_ean'] = submitted['ean']
    st.session_state['regime'] = submitted['regime']
    st.session_state['mode'] = 'current'
    st.session_state['cost'] = float(submitted['acquisition_cost'])
    price = float(historical_price) if historical_price is not None else None
    st.session_state['price'] = price
    st.session_state['last_current_price'] = price
    st.session_state.pop('analysis_result', None)


def _missing_suggestion(result: dict) -> None:
    """Offer dated historical prices as editable scenarios when appropriate."""
    market = result['market']
    if market['status'] == 'unavailable':
        st.info('Sem referência de mercado disponível para este produto.')
    elif market['status'] == 'historical_reference':
        st.info('A última coleta é antiga para sugerir uma faixa de preço.')
    else:
        st.info('A cobertura atual é insuficiente para sugerir uma faixa de preço.')
    if market.get('date'):
        st.caption(_period(market))
    if market['status'] == 'historical_reference' and market['kind'] == 'observed':
        median = market['median'].quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        st.caption(f'Mediana histórica: {brl(median)}. Confira ou edite antes de analisar.')
        st.button('Simular com a mediana histórica', on_click=_open_current_price,
                  args=(result, median), type='primary', key='simulate_historical_median')
    st.button('Analisar um preço que eu informar', on_click=_open_current_price,
              args=(result,), key='switch_to_current')


def _market_history(result: dict) -> None:
    """Place research about the market next to its chart."""
    bundle = result.get('market_extras')
    if result.get('market_extras_error'):
        st.warning('O histórico e a comparação com similares estão indisponíveis. '
                   'Você pode continuar com a análise de preço acima.')
    with st.expander('Histórico e similares', icon=':material/insights:'):
        history, comparisons, category = st.tabs(['Histórico', 'Similares', 'Categoria'])
        with history:
            lab_view.extra_price_charts(result)
            if bundle:
                lab_view.historical(bundle)
        with comparisons:
            if bundle:
                lab_view.comparables(bundle)
                if bundle.get('review_status') != 'team_validated':
                    st.caption('Comparação exploratória com vínculo por código exato.')
            else:
                st.caption('Sem dados de similares para este produto.')
        with category:
            _category(result)


def _transition(result: dict) -> None:
    """Estimate margin sensitivity using this SKU's price, cost and current tax."""
    st.write(f"**{product_name(result['product']['description'])}** · "
             f"{REGIME_LABELS[result['assumptions']['regime']]}")
    margin = result['analysis']['personalized']['margin']
    price = result['evaluated_price_brl']
    tax = margin['tax_brl']
    contribution = margin['contribution_brl']
    st.markdown('**Quanto sua margem pode mudar em 2027?**')
    st.write('A tabela compara a margem de 2026 com duas hipóteses para 2027: '
             'se a tributação na venda cair ou subir 1 ponto percentual do preço.')
    st.caption(f"Preço de venda: {brl_markdown(price)}. Custo de compra: "
               f"{brl_markdown(result['submitted_inputs']['acquisition_cost'])} por unidade. "
               'Preço, custo e créditos de compra são os mesmos em todas as linhas.')
    step = (price / 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    rows = []
    for label, delta in (('2026 · referência do app', Decimal(0)),
                         ('2027 · hipótese com menos tributos', -step),
                         ('2027 · hipótese com mais tributos', step)):
        if tax + delta < 0:
            continue
        rows.append({'Cenário': label,
                     'Tributação por unidade': brl(tax + delta),
                     'Margem por unidade': brl(contribution - delta)})
    st.dataframe(rows, hide_index=True, width='stretch')
    st.caption(f"Para este preço, 1 ponto percentual equivale a {brl_markdown(step)} "
               'por unidade. A tabela ilustra o efeito na margem. A carga real de 2027 '
               'depende do enquadramento e dos créditos da empresa.')
    if tax < step:
        st.caption('A hipótese de redução fica indisponível quando levaria '
                   'os tributos abaixo de zero.')
    st.markdown('**O que muda no calendário da reforma**')
    st.write('Em 2027, a CBS substitui PIS/Cofins e o IBS segue em transição. '
             'Em 2029, começa a substituição gradual de ICMS e ISS pelo IBS, '
             'com conclusão em 2033.')
    if result['assumptions']['regime'] == 'simples_nacional':
        st.caption('Confirme se a empresa recolherá IBS e CBS na guia única do Simples '
                   '(DAS) ou pelo regime regular. Isso afeta a apuração e os créditos.')
    else:
        st.caption('Em 2027 e 2028, a alíquota padrão do IBS no regime regular soma '
                   '0,10% (0,05% estadual e 0,05% municipal), antes das reduções aplicáveis. '
                   'Para estimar a carga efetiva, confira também a CBS e os créditos de compra.')
    st.caption(f"NCM do catálogo: {result['product']['ncm']}. Confira o enquadramento fiscal "
               'do produto e do fornecedor para o novo período.')

    st.markdown('[Cronograma oficial da reforma](https://www.gov.br/fazenda/pt-br/'
                'acesso-a-informacao/acoes-e-programas/reforma-tributaria/'
                'perguntas-e-respostas/como-sera-a-transicao-para) · '
                '[LC 214/2025](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm) · '
                '[Simples Nacional em 2027](https://www.gov.br/receitafederal/pt-br/'
                'assuntos/noticias/2026/setembro/simples-nacional-2027-entenda-os-'
                'novos-prazos-e-faca-sua-escolha-com-consciencia-e-tranquilidade/)')


def _details(result: dict) -> None:
    """Keep four entries for assumptions, comparison, forecast and transition."""
    st.markdown('### Detalhes')
    with st.expander('Premissas e composição do preço'):
        composition, assumptions = st.tabs(['Composição do preço', 'Premissas e fontes'])
        with composition:
            _how_we_calculate(result)
        with assumptions:
            _premises(result)
    with st.expander('Comparar regimes tributários'):
        lab_view.compare_regimes(result, REGIME_LABELS)
    with st.expander('Previsão do preço no próximo mês'):
        forecast_view.forecast(result['product']['ean'])
    with st.expander('Reforma tributária · Cenário 2027'):
        _transition(result)


def _price_and_market(result: dict) -> None:
    """Open with the price, market chart and interpretation for this SKU."""
    _overview(result)
    market = result['market']
    contribution = result['analysis']['personalized']['margin']['contribution_brl']
    if contribution < 0 or market['status'] == 'historical_reference':
        st.info(decision_text(result)['action'])
    with st.container(border=True, key='market_panel'):
        st.markdown('### Mercado')
        _market_view(result)
        _market_history(result)
    _price_brief(result)
    _download(result)


def results(result: dict) -> None:
    """Keep the scenario visible and show a single section at a time."""
    if result['status'] == 'pending_market_data':
        _missing_suggestion(result)
        return
    price_kind = ('Preço informado' if result['price_origin'] == 'user_price'
                  else 'Preço para testar, pela referência de mercado')
    st.caption(f"{price_kind} · {brl(result['evaluated_price_brl'])} · "
               f"{REGIME_LABELS[result['assumptions']['regime']]}")
    market, simulation, intelligence, details = st.tabs(
        ['Preço e mercado', 'Margem e promoção', 'Inteligência de mercado', 'Detalhes'])
    with market:
        _price_and_market(result)
    with simulation, st.container(border=True, key='price_simulator'):
        lab_view.scenarios(result)
    with intelligence:
        _market_intelligence(result)
    with details:
        _details(result)

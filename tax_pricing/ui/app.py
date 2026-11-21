"""Streamlit journey from scenario input to the checked pricing result."""
from contextlib import AbstractContextManager
from decimal import Decimal
import logging
import os
from pathlib import Path

import streamlit as st

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.rtc_service import DEFAULT_API
from tax_pricing.ui import view
from tax_pricing.ui.data import market_extras, market_snapshot, products
from tax_pricing.ui.formatting import product_name
from tax_pricing.ui.styles import CSS


ASSETS = Path(__file__).resolve().parents[2] / 'assets'


def _product_inputs(catalog: list[dict]) -> tuple[str, str]:
    """Choose a product within its group."""
    example = next(p for p in catalog if p['ean'] == '7894900027013')
    groups = sorted({product['group'] for product in catalog})
    with st.container(key='product_fields'):
        left, right = st.columns([2, 3])
        group_index = None if st.session_state.get('group') in groups else groups.index(
            example['group'])
        group = left.selectbox('Grupo de produtos', groups, index=group_index, key='group')
        group = group or example['group']
        selected = {p['ean']: p for p in catalog if p['group'] == group}
        eans = list(selected)
        default_ean = example['ean'] if example['ean'] in eans else eans[0]
        product_index = (None if st.session_state.get('product') in eans
                         else eans.index(default_ean))
        ean = right.selectbox(
            'Produto', eans, key='product', index=product_index,
            format_func=lambda value: product_name(selected[value]['description']))
    return group, ean or default_ean


def _scenario_inputs(catalog: list[dict]) -> tuple[dict, bool]:
    """Group the product, analysis settings and prices in reading order."""
    group, ean = _product_inputs(catalog)
    selected_ean = st.session_state.get('scenario_ean')
    if selected_ean is not None and selected_ean != ean:
        for field in ('cost', 'price', 'last_current_price'):
            st.session_state[field] = None
    st.session_state['scenario_ean'] = ean
    with st.container(key='analysis_fields'):
        left, right = st.columns([2, 3])
        regime = left.selectbox('Regime tributário', list(view.REGIME_LABELS),
                                index=None, placeholder='Selecione seu regime',
                                format_func=view.REGIME_LABELS.__getitem__, key='regime')
        mode = right.radio('Como você quer analisar?', ['current', 'suggestion'],
                           format_func=lambda value: {'current': 'Analisar meu preço',
                                                      'suggestion': 'Sugira um preço'}[value],
                           horizontal=True, key='mode',
                           index=None if 'mode' in st.session_state else 0)
    cost, price, submitted = _price_form(mode or 'current', regime)
    return {'group': group, 'ean': ean, 'regime': regime,
            'acquisition_cost': Decimal(str(cost)) if cost is not None else None,
            'selling_price': Decimal(str(price)) if price is not None else None}, submitted


def _price_form(mode: str, regime: str | None) -> tuple[float | None, float | None, bool]:
    """Submit purchase cost and, when applicable, the retailer's current price."""
    with st.form('scenario_form'):
        cost_col, price_col = st.columns(2) if mode == 'current' else (st.container(), None)
        initial_cost = None if 'cost' in st.session_state else 7.0
        cost = cost_col.number_input('Custo de aquisição (R$)', min_value=0.0,
                                     value=initial_cost, step=0.10, format='%.2f', key='cost')
        price = None
        if price_col is not None:
            initial_price = (None if 'price' in st.session_state else
                             st.session_state.get('last_current_price', 12.0))
            price = price_col.number_input('Preço de venda praticado (R$)', min_value=0.01,
                                           value=initial_price,
                                           step=0.10, format='%.2f', key='price')
        with st.container(key='scenario_submit'):
            st.caption('Os valores iniciais são exemplos. '
                       'A tributação é estimada para uma empresa de exemplo.')
            submitted = st.form_submit_button(
                'Analisar preço' if mode == 'current' else 'Sugira um preço',
                type='primary', width='stretch', disabled=regime is None, key='analyze')
    return cost, price, submitted


def _run_scenario(inputs: dict) -> dict:
    """Analyze a submitted scenario and attach compatible optional history."""
    snapshot = market_snapshot(inputs['ean'])
    result = analyze_mvp(inputs, snapshot, api=os.environ.get('TAX_PRICING_RTC_API', DEFAULT_API))
    try:
        result['market_extras'] = (market_extras(inputs['ean'], snapshot['date'])
                                   if snapshot else None)
    except (ValueError, KeyError, OSError) as error:
        result['market_extras'] = None
        result['market_extras_error'] = str(error)
    result['submitted_inputs'] = inputs
    return result


def _editor(result: dict | None) -> AbstractContextManager:
    """Place the same widgets in the opening screen or a compact top editor."""
    if result is None:
        return st.container(border=True, key='scenario_intro')
    return st.expander('Editar cenário', icon=':material/edit:')


def main() -> None:
    """Keep the checked result visible while the user edits a new scenario."""
    st.set_page_config(page_title='Tax-Aware Pricing AI',
                       page_icon=str(ASSETS / 'logo_simbolo.png'), layout='wide')
    st.markdown(CSS, unsafe_allow_html=True)
    result = st.session_state.get('analysis_result')
    view.header(compact=result is not None)
    with _editor(result):
        if result is not None:
            st.caption('Os resultados abaixo mudam quando você envia o novo cenário.')
        inputs, submitted = _scenario_inputs(products())
    if submitted and (inputs['acquisition_cost'] is None
                      or (st.session_state['mode'] == 'current'
                          and inputs['selling_price'] is None)):
        st.error('Preencha o custo de aquisição e, ao analisar seu preço, o preço de venda.')
    elif submitted:
        try:
            with st.spinner('Analisando seu cenário...'):
                updated = _run_scenario(inputs)
        except (ValueError, KeyError, OSError) as error:
            st.error('Não foi possível analisar este cenário. Confira os valores informados.')
            logging.getLogger(__name__).warning('Price analysis failed: %s', error)
            return
        if inputs['selling_price'] is not None:
            st.session_state['last_current_price'] = float(inputs['selling_price'])
        st.session_state['analysis_result'] = updated
        for key in ('suggested_price_question', 'price_question', 'source_answers', 'brief_order'):
            st.session_state.pop(key, None)
        st.rerun()
    if result is not None:
        st.subheader(product_name(result['product']['description']))
        view.results(result)

"""Render the next-month price forecast from a reviewed team file."""
import json
from pathlib import Path

import streamlit as st

from tax_pricing.demo_profile import ROOT
from tax_pricing.ui.formatting import brl, percent

FORECAST = ROOT / 'evidencias/previsao_2026-11-14/previsao.json'
ORIGINS = {'preco_rede': 'Preço da rede no mês base',
           'nivel_rede': 'Nível típico da rede (modelo)'}
STAGES = {'validacao': 'Validação', 'teste': 'Teste'}


def load_forecast(path: Path = FORECAST) -> dict | None:
    """Read the forecast bundle produced by mercado/previsao.py.

    Parameters
    ----------
    path : pathlib.Path
        Versioned JSON; the app never trains the model itself.

    Returns
    -------
    dict or None
        Checked bundle, or None when the file was not published.
    """
    if not path.is_file():
        return None
    bundle = json.loads(path.read_text(encoding='utf-8'))
    if bundle.get('schema_version') != 1:
        raise ValueError('Unsupported forecast schema.')
    for item in bundle['previsoes'].values():
        if item['mes_previsto'] <= item['mes_base'] or not item['redes']:
            raise ValueError('Forecast must point to a later month with networks.')
        for row in item['redes']:
            if row['origem'] not in ORIGINS or row['previsto'] <= 0:
                raise ValueError('Invalid forecast row.')
    return bundle


def forecast_rows(item: dict) -> list[dict]:
    """Format one SKU's network forecasts for display.

    Parameters
    ----------
    item : dict
        Entry of bundle['previsoes'] for the selected EAN.

    Returns
    -------
    list of dict
        One row per network, cheapest first.
    """
    return [{'Rede': row['rede'], 'Previsto': brl(str(row['previsto'])),
             'Base da previsão': ORIGINS[row['origem']],
             'Preço no mês base': (brl(str(row['preco_mes_base']))
                                   if row['preco_mes_base'] is not None else '—')}
            for row in item['redes']]


def evaluation_rows(bundle: dict) -> list[dict]:
    """Compare baselines and the hybrid model on each temporal split.

    Parameters
    ----------
    bundle : dict
        Checked forecast bundle.

    Returns
    -------
    list of dict
        One row per split and model, with the same three metrics.
    """
    return [{'Etapa': STAGES[stage], 'Modelo': row['modelo'],
             'Erro médio': brl(str(row['mae_brl'])),
             'Erro típico': percent(str(row['mdape_pct'])),
             'Erro de até 5%': percent(str(row['erro_ate_5_pct']))}
            for stage, rows in bundle['avaliacao'].items() for row in rows]


def _points(value: float) -> str:
    """Format percentage points with a decimal comma."""
    return f'{value:.2f}'.replace('.', ',')


def _quality(bundle: dict) -> None:
    """Explain how the model was validated against simple rules."""
    with st.expander('Quão bom é este modelo?'):
        st.dataframe(evaluation_rows(bundle), hide_index=True, width='stretch')
        boot = bundle['bootstrap_teste']
        gain, low, high = (_points(v) for v in (boot['ganho_medio_pp'],
                                                *boot['ic95_pp']))
        st.write(f'No teste, o híbrido erra em média **{gain} ponto percentual** '
                 f'a menos que repetir o preço da rede (IC 95% sorteando lojas: '
                 f'{low} a {high}). Quando há preço da rede no mês anterior, '
                 'os dois coincidem; o ganho vem das redes sem coleta recente.')
        st.caption('Treino no passado e avaliação nos meses seguintes, sem sorteio '
                   'de linhas. Erro típico é a mediana do erro percentual.')


def forecast(ean: str) -> None:
    """Show the expected price per network for the month after the last round.

    Parameters
    ----------
    ean : str
        Selected catalog identifier.
    """
    st.subheader('Quanto este produto deve custar no próximo mês?')
    try:
        bundle = load_forecast()
    except (ValueError, KeyError, json.JSONDecodeError):
        st.warning('A previsão está indisponível. '
                   'Você pode continuar com a análise de preço acima.')
        return
    if bundle is None:
        st.info('Sem previsão de preço disponível para este produto.')
        return
    item = bundle['previsoes'].get(ean)
    if item is None:
        st.info('Este produto não foi coletado na última rodada, então não há '
                'base recente para prever o mês seguinte.')
        return
    columns = st.columns(2)
    columns[0].metric(f"Mediana prevista ({item['mes_previsto']})",
                      brl(str(item['mediana_prevista'])))
    columns[1].metric(f"Referência em {item['mes_base']}",
                      brl(str(item['referencia_mes_base'])))
    st.dataframe(forecast_rows(item), hide_index=True, width='stretch')
    st.caption('Quando a rede foi coletada no mês base, a previsão repete esse '
               'preço: preços de supermercado mudam pouco de um mês para o outro. '
               'Quando não foi, o modelo parte da referência do mercado e aplica o '
               'nível típico da rede e do produto.')
    _quality(bundle)
    st.caption('Previsão de um mês à frente. Não antecipa promoções nem choques '
               f"de custo. Fonte: {bundle['fonte'].split(';', 1)[0]}.")

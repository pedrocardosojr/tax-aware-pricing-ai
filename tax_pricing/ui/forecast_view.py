"""Render the next-month price forecast from a reviewed team file."""
from datetime import date, timedelta
import json
from pathlib import Path

import streamlit as st

from tax_pricing.demo_profile import ROOT
from tax_pricing.ui.formatting import brl, display_month, percent

FORECAST = ROOT / 'evidencias/previsao_2026-11-14/previsao.json'
ORIGINS = {'preco_rede': 'Repete o preço observado para a rede',
           'nivel_rede': 'Estimado pelo padrão de preços da rede'}
MODELS = {'baseline 1: referência do mês anterior': 'Repetir o preço do mercado',
          'baseline 2: preço da rede no mês anterior': 'Repetir o preço da rede',
          'híbrido': 'Modelo do projeto'}
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
    base = 'Preço em ' + display_month(item['mes_base'])
    return [{'Rede': row['rede'], 'Preço estimado': brl(str(row['previsto'])),
             'Como estimamos': ORIGINS[row['origem']],
             base: (brl(str(row['preco_mes_base']))
                    if row['preco_mes_base'] is not None else '—')}
            for row in item['redes']]


def _stage_label(stage: str, cut: dict) -> str:
    """Use the dates of the versioned assessment when they are available."""
    if not cut:
        return STAGES.get(stage, stage)
    start = date.fromisoformat(cut['treino_ate'] + '-01') + timedelta(days=31)
    start_label = display_month(start.strftime('%Y-%m'))
    end = cut['avaliacao_ate']
    if str(start.year) == end[:4]:
        start_label = start_label.split(' de ', maxsplit=1)[0]
    return f'{STAGES.get(stage, stage)} de {start_label} a {display_month(end)}'


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
    cuts = bundle.get('cortes', {})
    return [{'Período avaliado': _stage_label(stage, cuts.get(stage, {})),
             'Método': MODELS.get(row['modelo'], row['modelo']),
             'Erro médio em reais': brl(str(row['mae_brl'])),
             'Erro percentual mediano': percent(str(row['mdape_pct'])),
             'Previsões com erro de até 5%': percent(str(row['erro_ate_5_pct']))}
            for stage, rows in bundle['avaliacao'].items() for row in rows]


def _points(value: float) -> str:
    """Format percentage points with a decimal comma."""
    return f'{value:.2f}'.replace('.', ',')


def _quality(bundle: dict) -> None:
    """Explain how the model was validated against simple rules."""
    with st.expander('Qual foi o erro nos testes?'):
        st.dataframe(evaluation_rows(bundle), hide_index=True, width='stretch')
        boot = bundle['bootstrap_teste']
        gain = _points(boot['ganho_medio_pp'])
        low, high = boot['ic95_pp']
        st.write('Comparado à regra de repetir o preço da rede, o modelo teve '
                 f'vantagem média de **{gain} ponto percentual** no teste. '
                 f'Intervalo de 95%: **{_points(low)} a {_points(high)} p.p.**, '
                 'calculado por reamostragem de lojas.')
        if low <= 0 <= high:
            st.info('O intervalo inclui zero. Com estes dados, a vantagem sobre '
                    'a regra simples ainda é incerta.')
        st.caption('O treino usa os meses anteriores à avaliação. Em metade das '
                   'observações, o erro percentual ficou até o valor mediano.')


def forecast(ean: str) -> None:
    """Show the expected price per network for the month after the last round.

    Parameters
    ----------
    ean : str
        Selected catalog identifier.
    """
    st.subheader('Estimativa de preço por rede')
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
    observed = display_month(item['mes_base'])
    target = display_month(item['mes_previsto'])
    columns = st.columns(2)
    columns[0].metric(f'Preço estimado em {target}',
                      brl(str(item['mediana_prevista'])),
                      help='Preço do meio entre as estimativas das redes.')
    columns[1].metric(f'Preço observado em {observed}',
                      brl(str(item['referencia_mes_base'])),
                      help='Preço do meio entre as redes com coleta no mês.')
    st.caption('Os dois valores resumem redes em um único mês. '
               'A faixa de mercado do diagnóstico resume lojas em vários meses.')
    st.dataframe(forecast_rows(item), hide_index=True, width='stretch')
    st.caption('Para uma rede com coleta no último mês, a estimativa repete o preço '
               'observado. Para as demais, o modelo usa o histórico do produto e da rede.')
    _quality(bundle)
    st.caption('A estimativa não antecipa promoções nem choques de custo. '
               f"Fonte: {bundle['fonte'].split(';', 1)[0]}.")

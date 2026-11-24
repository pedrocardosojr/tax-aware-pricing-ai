"""Run the UI against published team snapshots rather than lab fallback."""
import csv
import io
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from tax_pricing.ui.data import market_extras, market_snapshot, products
from tax_pricing.ui.lab_view import _cached_forecast
from tax_pricing.ui.view import CONTEXT_QUESTIONS

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / 'evidencias/integracao_mercado_2026-11-09/snapshots'


class TeamAppTests(unittest.TestCase):
    """Verify observed prices, both business paths and safe missing data."""

    def test_default_app_reads_the_complete_team_batch(self) -> None:
        """Every catalog SKU resolves without deployment configuration."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}):
            snapshots = {p['ean']: market_snapshot(p['ean']) for p in products()}
            cola = snapshots['7894900027013']
            coffee = snapshots['7896089011357']
            self.assertEqual(len(snapshots), 50)
            self.assertTrue(all(s and s['aggregation'] == 'median_across_stores'
                                for s in snapshots.values()))
            self.assertEqual(sum(bool(s.get('low_precision')) for s in snapshots.values()), 5)
            self.assertEqual(sum(s['date'] == '2026-02-02' for s in snapshots.values()), 4)
            self.assertEqual((cola['median'], cola['store_count']), ('11.98', 62))
            self.assertEqual((coffee['median'], coffee['store_count']), ('25.89', 57))
            self.assertIsNone(market_extras(cola['ean'], cola['date']))

    def test_default_screen_labels_store_quartiles_and_low_precision(self) -> None:
        """The plotted network points and store-level quartiles have distinct labels."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('faixa central, com a metade dos preços por loja' in item.value
                                for item in app.caption))
            app.selectbox(key='group').select('Arroz').run()
            app.selectbox(key='product').select('7893500020158').run()
            app.number_input(key='cost').set_value(7.0)
            app.number_input(key='price').set_value(12.0)
            app.button(key='analyze').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('A referência de preço tem mais incerteza' in item.value
                                for item in app.caption))

    def test_cola_products_have_distinct_labels_and_prices(self) -> None:
        """The legacy description never identifies Pepsi as Coca-Cola on the screen."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            options = app.selectbox(key='product').options
            pepsi = next(label for label in options if 'Pepsi' in label)
            self.assertNotIn('Coca', pepsi)
            self.assertTrue(any('Coca-Cola' in label for label in options))
            app.selectbox(key='regime').select('simples_nacional').run()
            for ean, median in (('7894900027013', '11.98'), ('7892840800246', '8.99')):
                app.selectbox(key='product').select(ean).run()
                app.number_input(key='cost').set_value(7.0)
                app.number_input(key='price').set_value(12.0)
                app.button(key='analyze').click().run()
                result = app.session_state['analysis_result']
                self.assertEqual(result['product']['ean'], ean)
                self.assertEqual(result['market']['median'], Decimal(median))

    def test_weather_loads_on_open_and_retries_after_unavailability(self) -> None:
        """Opening the panel triggers a fetch and the retry clears the cached failure."""
        days = [{'data': date(2026, 11, 17) + timedelta(days=i), 'dia': 'dia',
                 'descricao': 'Nublado', 'icone': '☁️', 'maxima': 25,
                 'minima': 16, 'chuva': None} for i in range(7)]
        _cached_forecast.clear()
        self.addCleanup(_cached_forecast.clear)
        with patch('tax_pricing.ui.lab_view.fetch_forecast',
                   side_effect=[None, days]) as forecast, patch(
                       'tax_pricing.ui.lab_view.fetch_inmet_forecast', return_value=None), patch(
                           'tax_pricing.product_analysis.calculate_current_tax',
                           side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            forecast.assert_not_called()
            app.session_state['curitiba_weather_forecast'] = True
            app.run()
            forecast.assert_called_once()
            app.button(key='retry_curitiba_weather').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(forecast.call_count, 2)
            markup = next(x.value for x in app.markdown if 'forecast-grid' in x.value
                          and 'fd-rain' in x.value and '<div class=' in x.value)
            self.assertEqual(markup.count("class='forecast-day'"), 7)
            self.assertIn("class='fd-rain'>💧 —", markup)

    def test_weather_displays_inmet_source_when_primary_is_down(self) -> None:
        """Use INMET's observed forecast horizon and no fabricated rain probability."""
        days = [{'data': date(2026, 11, 17) + timedelta(days=i), 'dia': 'dia',
                 'descricao': 'Nublado', 'icone': '🌡️', 'maxima': 25,
                 'minima': 16, 'chuva': None} for i in range(5)]
        _cached_forecast.clear()
        self.addCleanup(_cached_forecast.clear)
        with patch('tax_pricing.ui.lab_view.fetch_forecast', return_value=None), patch(
                'tax_pricing.ui.lab_view.fetch_inmet_forecast', return_value=days), patch(
                    'tax_pricing.product_analysis.calculate_current_tax',
                    side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            app.session_state['curitiba_weather_forecast'] = True
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any('5 dias disponíveis' in item.value and '[INMET]' in item.value
                                for item in app.caption))

    def test_historical_suggestion_reopens_the_current_price_editor(self) -> None:
        """The historical median is dated and the prefilled price stays editable."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='group').select('Cerveja').run()
            app.selectbox(key='product').select('7891149010509').run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.radio(key='mode').set_value('suggestion').run()
            app.number_input(key='cost').set_value(2.60)
            app.button(key='analyze').click().run()
            self.assertEqual(app.session_state['analysis_result']['status'],
                             'pending_market_data')
            self.assertTrue(any('02/02/2026' in item.value for item in app.caption))
            median = app.session_state['analysis_result']['market']['median']
            app.button(key='simulate_historical_median').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio(key='mode').value, 'current')
            self.assertEqual(app.selectbox(key='product').value, '7891149010509')
            self.assertEqual(app.selectbox(key='regime').value, 'simples_nacional')
            self.assertEqual(app.number_input(key='cost').value, 2.60)
            self.assertEqual(app.number_input(key='price').value, float(median))
            app.number_input(key='price').set_value(3.75)
            app.button(key='analyze').click().run()
            self.assertEqual(app.session_state['analysis_result']['evaluated_price_brl'],
                             Decimal('3.75'))
            self.assertEqual(app.session_state['analysis_result']['market']['status'],
                             'historical_reference')

    def test_download_uses_the_submitted_result_and_market_source(self) -> None:
        """The export preserves the selected price, source, date and coverage."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}), patch(
                'tax_pricing.ui.view.st.download_button') as download, patch(
                    'tax_pricing.product_analysis.calculate_current_tax',
                    side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            app.selectbox(key='regime').select('lucro_real').run()
        content = download.call_args.args[1].decode('utf-8-sig')
        row = next(csv.DictReader(io.StringIO(content), delimiter=';'))
        self.assertEqual(row['Regime demonstrativo'], 'Simples Nacional')
        self.assertEqual(row['Preço (R$)'], '12,00')
        self.assertEqual(row['Margem por unidade (R$)'], '4,66')
        self.assertEqual(row['Tributação estimada (R$)'], '0,34')
        self.assertEqual(row['Mediana de mercado (R$)'], '11,98')
        self.assertEqual(row['Última coleta'], '2026-10-29')
        self.assertEqual(row['Redes'], '29')

    def test_configured_data_never_falls_back_to_lab(self) -> None:
        """The configured team folder is the only source of market data."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR':
                                    str(SNAPSHOTS)}):
            snapshot = market_snapshot('7894900027013')
            self.assertEqual(snapshot['median'], '11.85')
            self.assertEqual(snapshot['network_count'], 15)
            self.assertIsNone(market_snapshot('7893500020158'))
            self.assertIsNone(market_extras('7894900027013', '2026-10-01'))

    def test_sorriso_all_regimes_and_both_price_paths(self) -> None:
        """Real team statistics reach the UI with mock RTC unavailability."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR':
                                    str(SNAPSHOTS)}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')):
            for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
                for mode in ('current', 'suggestion'):
                    with self.subTest(regime=regime, mode=mode):
                        app = AppTest.from_file(str(ROOT / 'app.py'),
                                                default_timeout=20).run()
                        app.selectbox(key='group').select('Creme dental').run()
                        app.selectbox(key='regime').select(regime).run()
                        app.radio(key='mode').set_value(mode).run()
                        app.number_input(key='cost').set_value(1.50)
                        if mode == 'current':
                            app.number_input(key='price').set_value(3.99)
                        app.button(key='analyze').click().run()
                        self.assertFalse(app.exception)
                        result = app.session_state['analysis_result']
                        self.assertEqual(result['status'], 'ready')
                        self.assertEqual(result['market']['median'],
                                         Decimal('3.39'))
                        self.assertEqual(result['market']['network_count'], 14)
                        self.assertEqual(result['market']['window'],
                                         ['2026-08', '2026-09', '2026-10'])
                        self.assertIsNone(result['market_extras'])
                        self.assertEqual(
                            result['analysis']['rtc']['status'], 'unavailable')

    def test_pricing_question_in_team_preview(self) -> None:
        """Answer an optional question against the real Coca snapshot."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR':
                                    str(SNAPSHOTS)}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')):
            app = AppTest.from_file(str(ROOT / 'app.py'),
                                    default_timeout=20).run()
            app.selectbox(key='regime').select('lucro_real').run()
            app.button(key='analyze').click().run()
            app.text_input(key='price_question').set_value('Vale acompanhar uma promoção?').run()
            self.assertTrue(any('Para manter a mesma contribuição total'
                                in item.value for item in app.markdown))
            app.text_input(key='price_question').set_value(
                'Quanto eu teria de vender a mais se baixasse o preço?').run()
            self.assertFalse(app.exception)
            answers = [item.value for item in app.markdown
                       if 'Para manter a mesma contribuição total' in item.value]
            self.assertEqual(len(answers), 1)
            self.assertIn('não estima a reação da demanda', answers[0])


    def test_price_brief_reuses_valid_order_and_falls_back_after_new_analysis(self) -> None:
        """Only the priority from the model reaches the summary; each scenario is separate."""
        with patch.dict(os.environ, {
                'TAX_PRICING_MARKET_DIR': '', 'TAX_PRICING_LLM_MODEL': 'test-model',
                'OPENAI_API_KEY': 'test-key'}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')), patch(
                'tax_pricing.ui.price_brief.request_answer', side_effect=[
                    '["Promoção", "Tributação estimada", "Posicionamento", "Época do ano"]',
                    '["Promoção", "Valor inventado"]',
                ]) as model:
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            brief = next(item.value for item in app.markdown if '- **Promoção.**' in item.value)
            self.assertTrue(brief.startswith('- **Promoção.**'))
            self.assertNotIn('R$', brief)
            self.assertTrue(all(f'**{label}.**' in brief for label in (
                'Tributação estimada', 'Posicionamento', 'Época do ano')))
            app.run()
            self.assertEqual(model.call_count, 1)
            app.button(key='analyze').click().run()
            brief = next(item.value for item in app.markdown if '- **Promoção.**' in item.value)
            self.assertTrue(brief.startswith('- **Posicionamento.**'))
            self.assertNotIn('Valor inventado', brief)
            self.assertEqual(model.call_count, 2)

    def test_clicked_context_questions_show_supported_sources(self) -> None:
        """The expanded suggestions lead to evidence without provider credentials."""
        with patch.dict(os.environ, {'TAX_PRICING_MARKET_DIR': ''}), patch(
                'tax_pricing.product_analysis.calculate_current_tax',
                side_effect=RuntimeError('RTC offline in UI test')), patch(
                'tax_pricing.ui.view._llm_setting', return_value=''):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            self.assertEqual(
                sum(button.label in CONTEXT_QUESTIONS for button in app.button), 6)
            for question, title in (
                    ('Qual a fonte dos preços do Clique Economia?', 'Origem dos preços'),
                    ('O que significa a faixa de preço?', 'Disponibilidade da referência'),
                    ('Por que cada loja conta uma vez?',
                     'Como se calcula a referência de preço por loja'),
                    ('Quais são as premissas da tributação estimada?', 'Premissas da tributação'),
                    ('O que a pesquisa diz sobre bebidas no Natal?', 'Bebidas na semana do Natal')):
                with self.subTest(question=question):
                    app.text_input(key='price_question').set_value('Estou caro?')
                    next(button for button in app.button if button.label == question).click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.text_input(key='price_question').value, '')
                    self.assertTrue(any(f'Fonte: [{title}' in item.value
                                        for item in app.caption))

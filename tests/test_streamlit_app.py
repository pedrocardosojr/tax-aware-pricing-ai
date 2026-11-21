"""App-level checks of both business paths and correct data provenance."""
import os
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from tax_pricing.tax_summary import summarize_tax

ROOT = Path(__file__).resolve().parents[1]


class StreamlitAppTests(unittest.TestCase):
    """Check real widgets, calculations and states without a browser/server."""

    def setUp(self):
        legacy_preview = patch('tax_pricing.ui.data.TEAM_MARKET', ROOT / 'tests/fixtures')
        legacy_preview.start()
        self.addCleanup(legacy_preview.stop)
        self.rtc = patch('tax_pricing.product_analysis.calculate_current_tax',
                         side_effect=RuntimeError('test service unavailable'))
        self.rtc_mock = self.rtc.start()
        self.addCleanup(self.rtc.stop)
        self.app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20)
        self.app.run()

    def test_regime_is_required_and_no_margin_target_exists(self):
        """Only the agreed inputs are shown; taxation remains a demo."""
        self.assertFalse(self.app.exception)
        self.assertIsNone(self.app.selectbox(key='regime').value)
        self.assertTrue(self.app.button(key='analyze').disabled)
        self.assertEqual(len(self.app.number_input), 2)
        labels = [widget.label.lower() for widget in self.app.number_input]
        self.assertFalse(any('margem' in label for label in labels))

    def test_product_without_market_reference_still_shows_margin(self):
        """A SKU with no reference file is a supported flow, not an error."""
        with tempfile.TemporaryDirectory() as empty, patch.dict(
                os.environ, {'TAX_PRICING_MARKET_DIR': empty}):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20)
            app.run()
            app.selectbox(key='regime').select('simples_nacional').run()
            app.button(key='analyze').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            metrics = {metric.label: metric.value for metric in app.metric}
            self.assertEqual(metrics['Margem de contribuição'], 'R$ 4,66')
            self.assertEqual(metrics['Seu preço frente ao mercado'], '—')

    def test_current_price_computes_contribution_and_market_position(self):
        """An actual form submission connects to the tested arithmetic."""
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Margem de contribuição'], 'R$ 4,66')
        self.assertEqual(metrics['Tributação estimada'], 'R$ 0,34')
        self.assertEqual(metrics['Seu preço frente ao mercado'], 'R$ 0,01 acima')

    def test_zero_tax_note_requires_an_assumed_icms_st_purchase(self):
        """Two zero-tax cases show the purchase note only for the ST recipe."""
        note = 'O cenário assume ICMS-ST retido na compra'
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.app.button(key='analyze').click().run()
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Tributação estimada'], 'R$ 0,00')
        self.assertTrue(any(note in caption.value
                            for caption in self.app.caption))

        self.app.selectbox(key='group').select('Arroz').run()
        self.app.number_input(key='cost').set_value(7.0)
        self.app.number_input(key='price').set_value(12.0)
        self.app.button(key='analyze').click().run()
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Tributação estimada'], 'R$ 0,00')
        self.assertFalse(any(note in caption.value
                             for caption in self.app.caption))

    def test_suggestion_path_needs_cost_but_no_current_price(self):
        """A market-based scenario works without a selling-price field."""
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.app.radio(key='mode').set_value('suggestion').run()
        self.assertEqual(len(self.app.number_input), 1)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['analysis_result'][
            'price_origin'], 'corridor_scenario')
        self.assertEqual(self.app.session_state['analysis_result'][
            'evaluated_price_brl'].as_tuple().exponent, -2)
        margin_line = next(item.value for item in self.app.caption
                           if 'Margem por unidade no menor e no maior preço' in item.value)
        self.assertEqual(margin_line.count(r'R\$'), 2)

    def test_unconnected_market_is_not_fabricated(self):
        """An unconnected SKU has no reference or suggested current band."""
        self.app.selectbox(key='group').select('Arroz').run()
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.radio(key='mode').set_value('suggestion').run()
        self.app.number_input(key='cost').set_value(7.0)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['analysis_result']['status'],
                         'pending_market_data')
        self.assertTrue(any('Sem referência de mercado disponível' in info.value
                            for info in self.app.info))

    def test_current_price_without_market_still_has_contribution(self):
        """Other SKUs calculate the contribution but expose no fake median."""
        self.app.selectbox(key='group').select('Arroz').run()
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.number_input(key='cost').set_value(7.0)
        self.app.number_input(key='price').set_value(12.0)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Margem de contribuição'], 'R$ 4,55')
        self.assertEqual(metrics['Seu preço frente ao mercado'], '—')

    def test_editing_keeps_the_last_result_until_submission(self):
        """Draft changes do not mutate the scenario the user is reading."""
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.button(key='analyze').click().run()
        result = self.app.session_state['analysis_result']
        self.assertEqual(result['assumptions']['regime'], 'simples_nacional')
        self.assertTrue(any('Editar cenário' == item.label for item in self.app.expander))
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.assertEqual(self.app.session_state['analysis_result']['assumptions']['regime'],
                         'simples_nacional')
        self.app.button(key='analyze').click().run()
        self.assertEqual(self.app.session_state['analysis_result']['assumptions']['regime'],
                         'lucro_real')
        self.assertFalse(self.app.exception)

    def test_product_change_clears_price_and_cost_but_keeps_the_last_result(self):
        """The next SKU cannot be submitted with another SKU's price and cost."""
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.number_input(key='cost').set_value(7.31)
        self.app.number_input(key='price').set_value(12.37)
        self.app.button(key='analyze').click().run()
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.assertEqual(self.app.number_input(key='cost').value, 7.31)
        self.assertEqual(self.app.number_input(key='price').value, 12.37)
        self.app.selectbox(key='group').select('Café').run()
        self.assertIsNone(self.app.number_input(key='cost').value)
        self.assertIsNone(self.app.number_input(key='price').value)
        self.app.button(key='analyze').click().run()
        self.assertTrue(any('Preencha o custo' in error.value for error in self.app.error))
        self.assertEqual(self.app.session_state['analysis_result']['product']['ean'],
                         '7894900027013')
        self.assertFalse(self.app.exception)

    def test_cafe_transition_keeps_price_and_cost_and_shows_four_detail_panels(self):
        """The tax sensitivity table uses the selected SKU's baseline."""
        self.app.selectbox(key='group').select('Café').run()
        self.app.selectbox(key='product').select('7896089011357').run()
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.number_input(key='cost').set_value(18.0)
        self.app.number_input(key='price').set_value(27.90)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        navigation = ['Preço e mercado', 'Simular preço', 'Inteligência de mercado', 'Detalhes']
        self.assertEqual([tab.label for tab in self.app.tabs if tab.label in navigation],
                         navigation)
        labels = [panel.label for panel in self.app.expander
                  if panel.label != 'Qual foi o erro nos testes?']
        self.assertEqual(labels[-4:], [
            'Premissas e composição do preço', 'Comparar regimes tributários',
            'Previsão do preço no próximo mês', 'Reforma tributária · Cenário 2027'])
        frame = next(item.value for item in self.app.dataframe
                     if 'Tributação por unidade' in item.value.columns)
        table = frame.to_dict('records')
        self.assertEqual([row['Tributação por unidade'] for row in table],
                         ['R$ 1,04', 'R$ 0,76', 'R$ 1,32'])
        self.assertEqual([row['Margem por unidade'] for row in table],
                         ['R$ 8,86', 'R$ 9,14', 'R$ 8,58'])
        self.assertTrue(any('na guia única do Simples' in caption.value
                            for caption in self.app.caption))

    def test_available_rtc_detail_is_rendered_separately(self):
        """A saved official response renders without replacing the estimate."""
        fixtures = json.loads((ROOT / 'tests/fixtures/rtc_2026_examples.json'
                               ).read_text())
        self.rtc_mock.side_effect = None
        self.rtc_mock.return_value = {
            'summary': summarize_tax(fixtures[1]['call']['body'])}
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.number_input(key='price').set_value(30.0)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        detail = self.app.session_state['analysis_result']['analysis']['rtc']
        self.assertEqual(detail['status'], 'calculated_ibs_cbs')
        tax = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(tax['Tributação estimada'], 'R$ 0,86')
        self.assertTrue(any('IBS/CBS no cenário' in text.value
                            for text in self.app.markdown))

    def test_unprofitable_band_warns_without_repeated_rtc_calls(self):
        """Cost scenarios cannot hide losses or trigger many fiscal requests."""
        self.app.selectbox(key='regime').select('simples_nacional').run()
        self.app.number_input(key='cost').set_value(13.0)
        self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('Toda a faixa central' in w.value
                            for w in self.app.warning))
        self.assertTrue(any('13,39' in info.value for info in self.app.info))
        self.assertEqual(self.rtc_mock.call_count, 1)

    def test_price_slider_recalculates_without_another_rtc_call(self):
        """Preserve the base case while simulating the volume trade-off."""
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.app.button(key='analyze').click().run()
        slider = next(iter(self.app.slider))
        slider.set_value(11.48).run()
        self.assertFalse(self.app.exception)
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Contribuição simulada'], 'R$ 4,48')
        self.assertEqual(metrics['Variação de volume necessária'], '+11,61%')
        self.assertEqual(self.app.session_state['analysis_result'][
            'evaluated_price_brl'], 12)
        self.assertEqual(self.rtc_mock.call_count, 1)
        slider = next(iter(self.app.slider))
        slider.set_value(slider.min).run()
        self.assertFalse(self.app.exception)

    def test_summary_is_calculated_and_has_no_rewrite_button(self):
        """The diagnosis comes from the app; the AI is only in its own block."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key',
                                     'TAX_PRICING_LLM_MODEL': 'test-model'}), patch(
                'tax_pricing.ui.view.request_answer', return_value=None) as request:
            self.app.selectbox(key='regime').select('lucro_real').run()
            self.app.button(key='analyze').click().run()
            self.assertFalse(self.app.exception)
            request.assert_not_called()
            self.assertFalse([b for b in self.app.button if b.key == 'rewrite_summary'])
            self.assertEqual(sum(metric.label == 'Margem de contribuição'
                                 for metric in self.app.metric), 1)
            self.assertTrue(any('O ICMS-ST foi retido na compra' in item.value
                                for item in self.app.markdown))

    def test_sourced_answer_uses_secrets_and_falls_back(self):
        """A context question calls the model with the secrets; a failure
        leaves the calculated answer on screen."""
        config = {'OPENAI_API_KEY': 'secret-test-key',
                  'TAX_PRICING_LLM_MODEL': 'secret-test-model'}
        self.app.secrets.update(config)
        with patch.dict(os.environ, dict.fromkeys(config, '')), patch(
                'tax_pricing.ui.view.request_answer', return_value=None) as request:
            self.app.selectbox(key='regime').select('lucro_real').run()
            self.app.button(key='analyze').click().run()
            question = next(b for b in self.app.button
                            if b.label == 'Por que cada loja conta uma vez?')
            question.click().run()
            self.assertFalse(self.app.exception)
            request.assert_called_once()
            prompt = request.call_args.args[0][1]['content']
            self.assertIn('purchase_st:', prompt)
            self.assertIn('tax:', prompt)
            self.assertEqual(request.call_args.kwargs, {
                'api_key': config['OPENAI_API_KEY'],
                'model': config['TAX_PRICING_LLM_MODEL'], 'url': ''})

    def test_invalid_optional_bundle_keeps_main_result(self):
        """An incompatible history file must not remove the checked margin."""
        self.app.selectbox(key='regime').select('simples_nacional').run()
        with patch('tax_pricing.ui.app.market_extras',
                   side_effect=ValueError('wrong analytics contract')):
            self.app.button(key='analyze').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.metric)
        self.assertTrue(any('histórico e a comparação com similares estão indisponíveis' in w.value
                            for w in self.app.warning))


    def test_cost_slider_preserves_baseline_and_recalculates_without_rtc(self):
        """Both controls remain visible and cost changes leave the input untouched."""
        self.app.selectbox(key='regime').select('lucro_real').run()
        self.app.button(key='analyze').click().run()
        cost = next(slider for slider in self.app.slider if slider.label == 'Custo simulado (R$)')
        cost.set_value(8.0).run()
        self.assertFalse(self.app.exception)
        metrics = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(metrics['Contribuição simulada'], 'R$ 4,00')
        self.assertEqual(self.app.session_state['analysis_result'][
            'analysis']['personalized']['margin']['net_cost_brl'], 7)
        self.assertEqual(self.rtc_mock.call_count, 1)
        self.assertFalse(any('Simular outro preço' == item.label for item in self.app.expander))
        self.assertTrue(any('a cada 100 unidades' in item.value for item in self.app.markdown))

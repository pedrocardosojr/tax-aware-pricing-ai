"""The model may write the brief, but only the app's figures and caveats pass."""
import json
import unittest
from unittest.mock import patch

from datetime import date

from tax_pricing.ui.grounded_explanation import (
    PricingExplanation, rejection_reason, request_answer, request_explanation,
    season_fact, validated_explanation,
)
from tax_pricing.ui.price_brief import prioritize_brief


def _reply(contribution: str, position: str = '') -> str:
    return json.dumps({'contribution': contribution, 'position': position,
                       'action': '', 'season': ''}, ensure_ascii=False)


class GroundedExplanationTests(unittest.TestCase):
    """Written text is accepted only when every figure comes from the app."""

    def setUp(self):
        self.facts: PricingExplanation = {
            'contribution': ('Depois dessas deduções, sobram R$ 3,90 por '
                             'unidade (32,50%) para cobrir despesas fixas.'),
            'position': ('Em 01/10/2026, o preço avaliado está R$ 0,15 '
                         '(1,27%) acima da mediana observada.'),
            'action': 'Compare a contribuição nos cenários da faixa.',
            'season': '',
        }
        self.fallback = [text for text in self.facts.values() if text]

    def test_accepts_a_rewrite_that_keeps_the_figures(self):
        """Different words, same numbers, possibly written without zeros."""
        contribution = 'Sobram R$ 3,9 por unidade, ou 32,5% do preço.'
        position = r'Em 01/10/2026 você está R\$ 0,15 acima da mediana.'
        shown = contribution.replace('R$ 3,9', r'R\$ 3,9') + ' ' + position
        self.assertEqual(validated_explanation(
            self.facts, _reply(contribution, position)), ([shown], True))

    def test_rejects_figures_swapped_between_sections(self):
        """A market difference cannot become contribution per unit."""
        reply = _reply('Sobram R$ 0,15 (32,50%) por unidade.',
                       'O preço está R$ 3,90 acima da mediana.')
        self.assertEqual(validated_explanation(self.facts, reply),
                         (self.fallback, False))

    def test_model_keeps_the_warning_in_the_market_comparison(self):
        """A historical caveat in another section cannot qualify the comparison."""
        reply = json.dumps({
            'contribution': 'Sobram R$ 3,90 (32,50%).',
            'position': 'O preço está R$ 0,15 acima da mediana.',
            'action': 'Observe o histórico.',
        })
        self.assertEqual(validated_explanation(
            self.facts, reply, required=('histor',)), (self.fallback, False))

    def test_rejects_figures_the_app_did_not_calculate(self):
        """An invented, rounded or recomputed amount sends the fallback."""
        for text in ('Sobram R$ 3,90 (32,50%). Isso é R$ 39,00 a cada dez.',
                     'Sobram cerca de R$ 4,00 (32,50%) por unidade.',
                     'Sobram R$ 3,90 (32,50%), 1,3% acima do mercado.'):
            with self.subTest(text=text):
                self.assertEqual(rejection_reason(self.facts, text),
                                 'numero_fora_do_calculo')
                self.assertEqual(validated_explanation(
                    self.facts, _reply(text)), (self.fallback, False))

    def test_rejects_text_that_drops_the_contribution(self):
        """The margin is the reason the brief exists; it cannot be omitted."""
        text = 'Em 01/10/2026 você está R$ 0,15 acima da mediana observada.'
        self.assertEqual(rejection_reason(self.facts, text),
                         'omitiu_contribuicao')

    def test_rejects_claims_the_data_cannot_support(self):
        """Profit, guarantees and demand are outside what the app measures."""
        for text in ('Sobram R$ 3,90 (32,50%) de lucro garantido.',
                     'Sobram R$ 3,90 (32,50%); a demanda não deve cair.'):
            with self.subTest(text=text):
                self.assertEqual(rejection_reason(self.facts, text),
                                 'termo_proibido')

    def test_historical_reference_warning_must_survive(self):
        """Stale market data cannot be rewritten as a current comparison."""
        text = 'Sobram R$ 3,90 (32,50%). Você está acima da mediana.'
        self.assertEqual(rejection_reason(self.facts, text, ('histor',)),
                         'perdeu_aviso')
        kept = text + ' A referência é histórica.'
        self.assertIsNone(rejection_reason(self.facts, kept, ('histor',)))

    def test_malformed_replies_use_the_app_reading(self):
        """Malformed replies use the deterministic reading."""
        for reply in (None, '', 'Sobram R$ 3,90', '{"sections":["action"]}',
                      '{"text": 3}', '{"text": "ok", "extra": 1}',
                      _reply('x' * 700)):
            with self.subTest(reply=reply):
                self.assertEqual(validated_explanation(self.facts, reply),
                                 (self.fallback, False))

    def test_fallback_starts_with_the_priority_section(self):
        """A historical scenario opens with the market caveat."""
        paragraphs, written = validated_explanation(
            self.facts, None, priority='position')
        self.assertFalse(written)
        self.assertEqual(paragraphs[0], self.facts['position'])

    def test_api_and_fallback_contract(self):
        """Check the request payload and handle unavailable transport."""
        reply = _reply('Sobram R$ 3,90 (32,50%).')
        response = {'choices': [{'finish_reason': 'stop',
                                 'message': {'content': reply}}]}
        with patch('tax_pricing.ui.grounded_explanation.urlopen') as send:
            send.return_value.__enter__.return_value.read.return_value = (
                json.dumps(response).encode())
            self.assertEqual(request_explanation(
                self.facts, 'contribution', model='test-model',
                api_key='test-key', required=('histor',)), reply)
            body = json.loads(send.call_args.args[0].data)
            self.assertFalse(body['store'])
            self.assertEqual(json.loads(body['messages'][1]['content'])[
                'avisos_obrigatorios'], ['histor'])
            self.assertEqual(send.call_args.kwargs['timeout'], 10)
            self.assertEqual(send.call_args.args[0].full_url,
                             'https://api.openai.com/v1/chat/completions')
            gemini = ('https://generativelanguage.googleapis.com/v1beta/'
                      'openai/chat/completions')
            self.assertEqual(request_explanation(
                self.facts, 'contribution', model='gemini-test',
                api_key='test-key', url=gemini), reply)
            request = send.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, gemini)
            self.assertNotIn('store', body)
            self.assertEqual(body['max_completion_tokens'], 4000)
            self.assertEqual(send.call_args.kwargs['timeout'], 30)
            send.side_effect = TimeoutError
            self.assertIsNone(request_explanation(
                self.facts, 'contribution', model='test-model',
                api_key='test-key'))

    def test_optional_brief_order_waits_at_most_five_seconds(self):
        """A slow model only drops the suggested order of the summary."""
        gemini = ('https://generativelanguage.googleapis.com/v1beta/'
                  'openai/chat/completions')
        lines = {'Posicionamento': 'a', 'Promoção': 'b'}
        with patch('tax_pricing.ui.grounded_explanation.urlopen') as send:
            send.side_effect = TimeoutError
            self.assertEqual(prioritize_brief(
                lines, model='gemini-test', api_key='test-key', url=gemini), ())
            self.assertEqual(send.call_args.kwargs['timeout'], 5)
            request_answer([], model='gemini-test', api_key='test-key', url=gemini)
            self.assertEqual(send.call_args.kwargs['timeout'], 30)


class SeasonFactTests(unittest.TestCase):
    """The summary names a retail date only when its source cites the product."""

    def test_date_that_cites_the_product(self):
        """Black Friday sources cite coffee, as a sector suggestion."""
        text = season_fact('Café', date(2026, 11, 14))
        self.assertTrue(text.startswith('Black Friday, de 23/11 a 29/11'))
        self.assertIn('café', text)
        self.assertIn('não uma previsão', text)

    def test_ongoing_date_says_until_when(self):
        """A date already under way is not announced as if it were ahead."""
        text = season_fact('Refrigerante 2 L', date(2026, 11, 25))
        self.assertIn('Black Friday vai até 29/11', text)
        self.assertIn('a fonte cita refrigerante 2 L', text)
        self.assertNotIn('mais vendas', text)

    def test_month_signal_without_a_product_source(self):
        """Without a product source, only the IBGE month signal, when strong."""
        self.assertIn('21,2% acima', season_fact('Arroz', date(2026, 12, 5)))
        self.assertIn('7,7% abaixo', season_fact('Leite', date(2027, 2, 10)))
        self.assertEqual(season_fact('Arroz', date(2026, 10, 5)), '')

    def test_written_season_keeps_only_its_figures(self):
        """A season sentence with a new number falls back to the app text."""
        facts: PricingExplanation = {
            'contribution': 'Sobram R$ 3,90 por unidade (32,50%).',
            'position': '', 'action': '',
            'season': season_fact('Arroz', date(2026, 12, 5)),
        }
        good = json.dumps({'contribution': 'Sobram R$ 3,90, 32,50%.',
                           'position': '', 'action': '',
                           'season': 'Em dezembro o setor vende 21,2% acima '
                                     'da média, sugestão e não previsão.'})
        bad = good.replace('21,2%', '30%')
        self.assertTrue(validated_explanation(facts, good)[1])
        self.assertFalse(validated_explanation(facts, bad)[1])


if __name__ == '__main__':
    unittest.main()

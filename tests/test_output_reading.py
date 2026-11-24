"""Decision wording and visible chart arithmetic, without market invention."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.pricing_scenarios import volume_scenario
from tax_pricing.ui.formatting import brl_markdown, network_name, percent, product_name
from tax_pricing.ui.charts import price_tree
from tax_pricing.ui.price_questions import answer_question, direct_answer, match_topic
from tax_pricing.ui.reading import decision_text, observed_spread

ROOT = Path(__file__).resolve().parents[1]


class OutputReadingTests(unittest.TestCase):
    """Exercise loss, stale references and correct credit presentation."""

    def setUp(self):
        self.snapshot = json.loads((ROOT / 'evidencias/'
            'mvp_estimativa_2026-11-07/mercado_coca_2l.json').read_text())

    def scenario(self, cost='7', regime='simples_nacional', market=None):
        """Use the real snapshot and demo arithmetic without network calls."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   side_effect=RuntimeError('offline test')):
            return analyze_mvp({'ean': '7894900027013', 'regime': regime,
                                'acquisition_cost': cost, 'selling_price': '12'},
                               market if market is not None else self.snapshot)

    def test_spread_uses_only_observed_network_values(self):
        """Seven network prices are not treated as a larger historical sample."""
        spread = observed_spread(self.snapshot)
        self.assertEqual(spread['count'], 7)
        self.assertEqual(spread['range'], Decimal('1.13'))
        self.assertIsNone(observed_spread({**self.snapshot, 'kind': 'estimated'}))
        self.assertIsNone(observed_spread({'status': 'unavailable'}))

    def test_negative_contribution_is_not_described_as_money_left(self):
        """A loss points to reviewing cost/price, not guaranteed earnings."""
        reading = decision_text(self.scenario(cost='20'))
        self.assertIn('faltam', reading['contribution'])
        self.assertIn('Reveja', reading['action'])
        self.assertNotIn('sobram', reading['contribution'])

    def test_historical_data_does_not_generate_current_price_advice(self):
        """The next action is refreshing evidence, not blindly repricing."""
        old = deepcopy(self.snapshot)
        old['date'] = '2025-10-01'
        reading = decision_text(self.scenario(market=old))
        self.assertIn('Atualize', reading['action'])
        self.assertIn('01/10/2025', reading['position'])

    def test_credit_is_a_separate_bar_and_composition_reconciles(self):
        """Show gross purchase minus credit once, preserving contribution."""
        result = self.scenario(regime='lucro_real')
        margin = result['analysis']['personalized']['margin']
        trace = price_tree(margin, credit=Decimal('.35')).data[0]
        self.assertIn('Crédito do cenário', trace.x)
        self.assertAlmostEqual(sum(trace.y[:-1]),
                               float(margin['contribution_brl']), places=8)
        # The explicit retail-ST beverage case has no recoverable credit.
        self.assertEqual(trace.text[-1], 'R$ 5,00')

    def test_question_retrieval_handles_paraphrases_and_abstains(self):
        """Rank supported topics and skip weak or ambiguous questions."""
        queries = {
            'Estou caro?': 'market',
            'Como ficou meu posicionamento frente às redes?': 'market',
            'Quanto eu teria de vender a mais se baixasse o preço?': 'promotion',
            'Quero reduzir o preco': 'promotion',
            'Quanto sobra por unidade?': 'margin',
            'Qual minha margem de contribuição?': 'margin',
            'Por que o ICMS aparece zerado?': 'tax',
            'Quanto pago de imposto?': 'tax',
            'Qual é a previsão do tempo?': None,
            'Preço?': None,
            'Margem e imposto?': None,
            '   ': None,
        }
        for question, expected in queries.items():
            with self.subTest(question=question):
                self.assertEqual(match_topic(question), expected)

    def test_promotion_answer_respects_current_market_and_contribution(self):
        """Compute the volume trade-off and suppress unsupported scenarios."""
        question = 'Quanto eu teria de vender a mais se baixasse o preço?'
        answer = answer_question(question, self.scenario())
        self.assertIn('a mais', answer)
        self.assertIn('não sabe quanto as vendas subiriam', answer)
        old = {**self.snapshot, 'date': '2025-10-01'}
        answer = answer_question(question, self.scenario(market=old))
        self.assertIn('preços recentes de lojas suficientes', answer)
        self.assertNotIn('a mais', answer)
        answer = answer_question(question, self.scenario(cost='20'))
        self.assertIn('vender mais não ajuda', answer)

    def test_zero_tax_answer_mentions_the_configured_icms_st_assumption(self):
        """Read the scenario instead of equating zero at sale with no tax."""
        answer = answer_question('Por que o imposto zerou?',
                                 self.scenario(regime='lucro_real'))
        self.assertIn('0,00', answer)
        self.assertIn('ICMS-ST retido na compra', answer)
        self.assertIn('perfil de exemplo', answer)

    def test_explicit_price_question_reuses_simulator(self):
        """The question and the slider agree on the proposed contribution."""
        result = self.scenario()
        simulated = volume_scenario(result, Decimal('11.48'))
        answer = answer_question('E se eu vender a Coca-Cola 2 L por R$ 11,48?', result)
        self.assertIn(brl_markdown(simulated['contribution_brl']), answer)
        self.assertIn(percent(simulated['volume_change_percent']), answer)
        self.assertIn(percent(abs(simulated['position']['gap_percent'])), answer)
        self.assertIn('preço do meio das lojas', answer)

    def test_explicit_price_question_declines_ambiguous_or_invalid_amounts(self):
        """A missing or ambiguous amount never becomes a fabricated price."""
        for question in ('E se eu vender?', 'Simule R$ 12,00 ou R$ 13,00',
                         'E se eu vender por R$ 0,00?', 'E se eu vender por -10?',
                         'E se eu vender por 15%?', 'E se eu vender por 15 %?',
                         'Simule um desconto de R$ 2,00'):
            with self.subTest(question=question):
                self.assertIn('Informe um único preço', answer_question(
                    question, self.scenario()))

    def test_explicit_scenario_with_historical_market_or_negative_contribution(self):
        """Calculate the scenario while withholding unsupported comparisons."""
        old = {**self.snapshot, 'date': '2025-10-01'}
        answer = answer_question('E se eu vender por 11,48?', self.scenario(market=old))
        self.assertIn('Ainda não há preços de mercado recentes', answer)
        answer = answer_question('E se eu vender por 1,00?', self.scenario())
        self.assertIn('perde dinheiro em cada venda', answer)

    def test_price_changes_use_the_current_price(self):
        """Distinguish relative changes from a new selling price."""
        result = self.scenario()
        for question, expected in (
                ('E se eu baixar R$ 1?', '11,00'),
                ('Baixar o preço em R$ 0,50', '11,50'),
                ('Subir R$ 1,00', '13,00'),
                ('Baixar para R$ 11,48', '11,48'),
                ('E se eu vender por 11.48?', '11,48'),
                ('Vale a pena dar R$ 2 de desconto?', '10,00')):
            with self.subTest(question=question):
                self.assertIn(f'A R\\$ {expected}', answer_question(question, result))

    def test_promotion_paraphrase_uses_the_promotion_topic(self):
        """The short promotion question should reach the existing analysis."""
        self.assertEqual(match_topic('Vale a pena fazer promoção?'), 'promotion')

    def test_tax_question_uses_the_simulated_price(self):
        """The requested tax comes from the repriced scenario."""
        result = self.scenario()
        expected = volume_scenario(result, Decimal('11.48'))['tax_brl']
        answer = answer_question('Quanto de imposto pago se vender por R$ 11,48?', result)
        self.assertIn('imposto estimado na venda', answer)
        self.assertIn(brl_markdown(expected), answer)

    def test_seasonal_promotion_requests_price_or_runs_the_simulator(self):
        """Ask for a selling price before simulating a seasonal promotion."""
        result = self.scenario()
        question = 'Vale a pena promoção no Natal?'
        self.assertIn('Informe um único preço', answer_question(question, result))
        answer = answer_question('Vale a pena promoção por R$ 11,48 no Natal?', result)
        self.assertIn(brl_markdown(Decimal('11.48')), answer)
        self.assertIn('preço do meio das lojas', answer)

    def test_percent_discount_and_raise_are_simulated(self):
        """A percentage change becomes a price on the evaluated price."""
        result = self.scenario()
        self.assertIn('para R\\$ 10,80', answer_question('Faz sentido dar desconto de 10%?',
                                                         result))
        self.assertIn('para R\\$ 12,60', answer_question('E se eu subir 5%?', result))

    def test_plain_answers_settled_by_the_scenario(self):
        """Common lay questions get the scenario's own numbers in plain words."""
        result = self.scenario()
        market = result['market']
        expected = {
            'Quando foi a última coleta?': 'última coleta de preços',
            'Quantas lojas foram pesquisadas?': f"{market['network_count']} redes",
            'Qual rede é mais barata?': 'Ver preços por rede',
            'O que é a mediana?': 'preço do meio',
            'Por que a margem é essa?': ' = R\\$ 4,66',
            'Posso subir o preço?': 'Subindo para',
            'Qual o melhor preço?': 'não calcula um preço ideal',
        }
        for question, fragment in expected.items():
            with self.subTest(question=question):
                self.assertIn(fragment, direct_answer(question, result) or '')
        for question in ('Estou caro?', 'E se eu vender a R$ 11,00?', 'Quanto pago de imposto?'):
            with self.subTest(question=question):
                self.assertIsNone(direct_answer(question, result))

    def test_display_names_restore_accents_and_units(self):
        """Labels read naturally while catalog and network keys stay unchanged."""
        self.assertEqual(product_name('CAFE VACUO - PILAO - 500 GR'),
                         'Café a Vácuo · Pilão · 500 g')
        self.assertEqual(product_name('REFRIGERANTE - COCA COLA - 2 LITRO'),
                         'Refrigerante · Coca-Cola · 2 L')
        self.assertEqual(network_name('SACOLÃO POPULAR'), 'Sacolão Popular')
        self.assertEqual(network_name('MIG ATACADO E VAREJO'), 'Mig Atacado e Varejo')
        self.assertEqual(network_name('Armazem da Maria'), 'Armazém da Maria')

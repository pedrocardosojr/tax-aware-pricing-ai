"""Minimal-input demonstration flow, with no hidden fiscal personalization."""
from decimal import Decimal
import unittest
from unittest.mock import patch

from tax_pricing.catalog import load_catalog
from tax_pricing.demo_profile import ROOT
from tax_pricing.demo_profile import build_demo_profile
from tax_pricing.mvp_analysis import analyze_mvp


class MvpAnalysisTests(unittest.TestCase):
    """The regime changes the scenario without asking for extra tax fields."""

    def setUp(self):
        self.inputs = {'ean': '7894900027013', 'regime': 'simples_nacional',
                       'acquisition_cost': Decimal(20),
                       'selling_price': Decimal(30)}
        self.market = {'ean': self.inputs['ean'], 'date': '2026-10-01',
                       'median': Decimal(30), 'p25': Decimal(28),
                       'p75': Decimal(32), 'network_count': 7,
                       'source': 'fictional test market summary',
                       'kind': 'observed'}
        self.rtc = patch('tax_pricing.product_analysis.calculate_current_tax',
                         side_effect=RuntimeError('offline test'))
        self.rtc.start()
        self.addCleanup(self.rtc.stop)

    def test_regime_selects_labeled_product_scenarios(self):
        """All rates, revenue, credit and fees are internal demo assumptions."""
        expected = {'simples_nacional': '9.1440250',
                    'lucro_presumido': '10.000000', 'lucro_real': '10.000000'}
        for regime, margin in expected.items():
            result = analyze_mvp({**self.inputs, 'regime': regime}, self.market)
            self.assertEqual(result['mode'], 'demonstration')
            self.assertEqual(result['labels']['margin'],
                             'Margem de contribuição')
            self.assertEqual(result['labels']['tax'], 'Tributação estimada')
            self.assertEqual(result['analysis']['personalized']['margin'][
                'contribution_brl'], Decimal(margin))
            self.assertEqual(result['market_position']['price_index'],
                             Decimal(100))

    def test_no_price_uses_market_scenarios_without_a_margin_target(self):
        """Observed quartiles give a provisional band, not an optimum claim."""
        result = analyze_mvp({**self.inputs, 'selling_price': None}, self.market)
        self.assertEqual(result['price_origin'], 'corridor_scenario')
        self.assertEqual(result['evaluated_price_brl'], Decimal(30))
        self.assertEqual([p['price_brl'] for p in result['corridor_points']],
                         [Decimal(28), Decimal(30), Decimal(32)])
        self.assertNotIn('target_margin', result)

    def test_no_market_does_not_ask_for_more_user_inputs(self):
        """Missing data is an internal market dependency, not a fake price."""
        result = analyze_mvp({**self.inputs, 'selling_price': None})
        self.assertEqual(result['status'], 'pending_market_data')
        self.assertIsNone(result['analysis'])
        self.assertIn('market', result['pending_internal_data'])

    def test_duplicate_quartile_does_not_move_reference_to_upper_price(self):
        """When P25 equals median, the main scenario stays on the median."""
        result = analyze_mvp({**self.inputs, 'selling_price': None},
                             {**self.market, 'p25': Decimal(30)})
        self.assertEqual(result['evaluated_price_brl'], Decimal(30))
        self.assertEqual(len(result['corridor_points']), 2)

    def test_stale_or_sparse_market_does_not_suggest_a_current_band(self):
        """Beer history or a single network cannot masquerade as current band."""
        for change in ({'date': '2026-02-01'}, {'network_count': 1},
                       {'kind': 'estimated'}):
            result = analyze_mvp({**self.inputs, 'selling_price': None},
                                 {**self.market, **change})
            self.assertEqual(result['status'], 'pending_market_data')
            self.assertEqual(result['corridor_points'], [])

    def test_market_identity_and_quartiles_are_checked(self):
        """Do not compare another SKU or invert the observed interval."""
        for change in ({'ean': 'other'}, {'p25': Decimal(33)},
                       {'date': '2027-01-01'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                analyze_mvp(self.inputs, {**self.market, **change})

    def test_estimated_reference_is_not_described_as_observed(self):
        """A forecast can be shown with its origin, without inventing a band."""
        result = analyze_mvp({**self.inputs, 'selling_price': Decimal(32)},
                             {**self.market, 'kind': 'estimated'})
        self.assertEqual(result['corridor_points'], [])
        self.assertTrue(any('referência estimada' in text
                            for text in result['insights']))

    def test_regime_is_required_and_unknown_sku_is_rejected(self):
        """The fixed demo never silently chooses a different company regime."""
        for change in ({'regime': None}, {'ean': 'unknown'},
                       {'group': 'Arroz'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                analyze_mvp({**self.inputs, **change})

    def test_simples_formula_and_credit_are_visible_in_assumptions(self):
        """The user can inspect the fictional revenue and credit premises."""
        result = build_demo_profile('simples_nacional', Decimal(20))
        self.assertEqual(result['taxpayer']['tax_components'][0]['rate'],
                         Decimal('.0565'))
        self.assertEqual(result['assumptions']['profile']['rbt12_brl'], '360000')
        real = build_demo_profile('lucro_real', Decimal(20))
        self.assertEqual(real['assumptions']['credit_brl'], Decimal('5.39'))

    def test_noncumulative_regimes_credit_the_purchase(self):
        """Charging ICMS on the sale without crediting it biases the compare."""
        fractions = {regime: build_demo_profile(regime, Decimal(100))[
            'assumptions']['credit_fraction']
            for regime in ('simples_nacional', 'lucro_presumido',
                           'lucro_real')}
        self.assertEqual(fractions['simples_nacional'], Decimal(0))
        self.assertGreater(fractions['lucro_presumido'], Decimal(0))
        self.assertGreater(fractions['lucro_real'], fractions['lucro_presumido'])

    def test_fixed_profitable_fixture_stays_profitable(self):
        """These inputs are profitable fixtures, not a universal guarantee."""
        for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
            with self.subTest(regime=regime):
                result = analyze_mvp({**self.inputs, 'regime': regime},
                                     self.market)
                self.assertGreater(result['analysis']['personalized'][
                    'margin']['contribution_brl'], Decimal(0))

    def test_all_catalog_skus_work_with_each_demo_regime(self):
        """The 50-SKU catalog and three internal profiles share one contract."""
        products = load_catalog(ROOT / 'dados/catalogo/skus_50.json')
        for product in products:
            for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
                with self.subTest(ean=product['ean'], regime=regime):
                    result = analyze_mvp({**self.inputs, 'ean': product['ean'],
                                          'group': product['group'],
                                          'regime': regime})
                    self.assertEqual(result['status'], 'ready')
                    self.assertEqual(result['product']['ean'], product['ean'])
                    self.assertIsNotNone(result['analysis'])

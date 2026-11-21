"""Commercial curve and floor checks against the existing demo engine."""
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.pricing_scenarios import scenario_analysis, volume_scenario
from tax_pricing.ui.data import LAB, market_snapshot


class ScenarioAnalysisTests(unittest.TestCase):
    """Price scenarios use the same demo engine without extra RTC calls."""

    def result(self, cost='12'):
        """Build one ready result while preserving RTC unavailability."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   side_effect=RuntimeError('offline')), patch.dict(
                       os.environ, {'TAX_PRICING_MARKET_DIR': str(LAB)}):
            return analyze_mvp({'ean': '7894900027013',
                                'regime': 'simples_nacional',
                                'acquisition_cost': cost,
                                'selling_price': '12'},
                               market_snapshot('7894900027013'))

    def test_floor_is_first_nonnegative_cent_and_band_is_not_profitable(self):
        """A central competitor range cannot override the user's economics."""
        result = scenario_analysis(self.result(cost='13'))
        self.assertEqual(result['zero_contribution_price_brl'], Decimal('13.39'))
        self.assertGreaterEqual(result['floor_contribution_brl'], 0)
        self.assertLess(result['previous_cent_contribution_brl'], 0)
        self.assertEqual(result['band_status'], 'all_negative')

    def test_sensitivity_includes_current_cost_and_price(self):
        """The baseline appears in the scenario grid for reconciliation."""
        result = scenario_analysis(self.result(cost='7'))
        self.assertIn(Decimal('7'), result['costs_brl'])
        self.assertTrue(any(p['price_brl'] == Decimal('12')
                            for p in result['curve']))

    def test_price_and_cost_match_a_fresh_analysis_in_each_regime(self):
        """A changed purchase cost rebuilds the same credits as a new scenario."""
        for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
            with self.subTest(regime=regime), patch(
                    'tax_pricing.product_analysis.calculate_current_tax',
                    side_effect=RuntimeError('offline')) as rtc:
                snapshot = market_snapshot('7896089011357')
                initial = analyze_mvp({
                    'ean': '7896089011357', 'regime': regime,
                    'acquisition_cost': '18', 'selling_price': '27.90'}, snapshot)
                expected = analyze_mvp({
                    'ean': '7896089011357', 'regime': regime,
                    'acquisition_cost': '20.50', 'selling_price': '26.70'}, snapshot)
                calls = rtc.call_count
                simulated = volume_scenario(initial, Decimal('26.70'),
                                            acquisition_cost=Decimal('20.50'))
                margin = expected['analysis']['personalized']['margin']
                self.assertEqual(simulated['contribution_brl'], margin['contribution_brl'])
                self.assertEqual(simulated['tax_brl'], margin['tax_brl'])
                self.assertEqual(rtc.call_count, calls)
                self.assertEqual(initial['evaluated_price_brl'], Decimal('27.90'))

    def test_units_round_up_and_require_positive_contributions(self):
        """Whole units cover the original contribution without understating it."""
        result = self.result(cost='7')
        simulated = volume_scenario(result, Decimal('11.48'))
        before = result['analysis']['personalized']['margin']['contribution_brl'] * 100
        after = simulated['contribution_brl']
        units = simulated['units_per_100']
        self.assertGreaterEqual(after * units, before)
        self.assertLess(after * (units - 1), before)
        loss = volume_scenario(result, Decimal('11.48'), acquisition_cost=Decimal('30'))
        self.assertIsNone(loss['units_per_100'])
        self.assertIsNone(loss['volume_change_percent'])

    def test_changed_cost_recalculates_the_floor_and_curve(self):
        """The expanded chart and its band use the same cost as the sliders."""
        baseline = self.result(cost='7')
        changed = scenario_analysis(baseline, acquisition_cost=Decimal('13'))
        fresh = scenario_analysis(self.result(cost='13'))
        self.assertEqual(changed['curve'], fresh['curve'])
        self.assertEqual(changed['band_status'], 'all_negative')
        self.assertEqual(changed['zero_contribution_price_brl'],
                         fresh['zero_contribution_price_brl'])

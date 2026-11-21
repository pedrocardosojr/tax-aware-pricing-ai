"""Integration contract for product, taxpayer calculation and RTC context."""
from decimal import Decimal
import unittest
from unittest.mock import patch

from tax_pricing.product_analysis import analyze_product


class ProductAnalysisTests(unittest.TestCase):
    """Missing or unavailable RTC evidence does not invent company taxes."""

    def setUp(self):
        self.product = {'ean': '7894900027013', 'ncm': '22021000'}
        self.context = {'year': 2026, 'fiscal_date': '2026-11-07',
                        'cst': '000', 'cclass': '000001'}
        self.taxpayer = {
            'regime': 'simples_nacional', 'competence': '2026-11',
            'scope': 'fictional sourced scenario', 'coverage_confirmed': True,
            'usable_purchase_credit_brl': Decimal(0),
            'purchase_credit_source': 'explicit fictional zero',
            'icms_outside_das': False,
            'tax_components': [{'name': 'DAS', 'rate': Decimal('.04'),
                                'basis': 'selling_price',
                                'source': 'hypothetical supplied rate'}]}
        self.pricing = {'selling_price': Decimal(30), 'gross_cost': Decimal(20),
                        'expenses': {'rate': Decimal(0),
                                     'per_unit_brl': Decimal(0)},
                        'price_origin': 'user_price'}

    def test_missing_fiscal_base_does_not_use_acquisition_cost(self):
        """The user's purchase cost is not the RTC sale tax base."""
        with patch('tax_pricing.product_analysis.calculate_current_tax') as api:
            result = analyze_product(self.product, self.context, self.taxpayer,
                                     self.pricing)
        api.assert_not_called()
        self.assertEqual(result['rtc']['status'], 'pending_fiscal_base')
        self.assertEqual(result['personalized']['tax_total_brl'], Decimal('1.2'))

    def test_rtc_amount_is_not_added_to_personalized_deductions(self):
        """A 0.30 RTC calculation does not turn the 1.20 DAS input into 1.50."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   return_value={'summary': {'total_ibs_cbs_brl': Decimal('.30')}}):
            result = analyze_product(self.product,
                                     {**self.context, 'tax_base_brl': Decimal(30)},
                                     self.taxpayer, self.pricing)
        self.assertEqual(result['personalized']['tax_total_brl'], Decimal('1.20'))
        self.assertEqual(result['personalized']['margin']['contribution_brl'],
                         Decimal('8.80'))

    def test_unavailable_rtc_keeps_the_personalized_result_and_status(self):
        """A failed panel cannot be shown as a successful zero-tax panel."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   side_effect=RuntimeError('offline')):
            result = analyze_product(self.product,
                                     {**self.context, 'tax_base_brl': Decimal(30)},
                                     self.taxpayer, self.pricing)
        self.assertEqual(result['rtc']['status'], 'unavailable')
        self.assertIsNone(result['rtc']['result'])
        self.assertEqual(result['personalized']['tax_total_brl'], Decimal('1.20'))

    def test_corridor_scenario_does_not_need_target_margin(self):
        """Scenario origin is explicit, without presenting it as actual price."""
        result = analyze_product(self.product, self.context, self.taxpayer,
                                 {**self.pricing, 'price_origin': 'corridor_scenario'})
        self.assertEqual(result['price_origin'], 'corridor_scenario')
        self.assertIsNotNone(result['personalized']['margin'])

    def test_mismatched_competence_and_missing_origin_fail(self):
        """Do not silently price with a different period or unknown origin."""
        with self.assertRaises(ValueError):
            analyze_product(self.product, self.context,
                            {**self.taxpayer, 'competence': '2026-10'}, self.pricing)
        with self.assertRaises(ValueError):
            analyze_product(self.product, self.context, self.taxpayer,
                            {**self.pricing, 'price_origin': None})

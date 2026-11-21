"""Regressions for catalogue retail scenarios, not tax certification."""
from decimal import Decimal
import unittest
from unittest.mock import patch

from tax_pricing.demo_profile import ROOT, build_demo_profile
from tax_pricing.demo_profile import demo_settings
from tax_pricing.catalog import load_catalog
from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.pricing_scenarios import scenario_analysis


class ProductTaxDemoTests(unittest.TestCase):
    """Prevent duplicate ST and credits prohibited in the chosen operation."""

    def setUp(self) -> None:
        self.products = {p['ean']: p for p in load_catalog(
            ROOT / 'dados/catalogo/skus_50.json')}

    def test_coke_retail_st_does_not_repeat_icms_or_purchase_credit(self):
        """Under stated retailer/ST conditions both regular profiles use zero."""
        for regime in ('lucro_presumido', 'lucro_real'):
            demo = build_demo_profile(regime, Decimal(8),
                                     product=self.products['7894900027013'])
            rates = {c['name']: c['rate']
                     for c in demo['taxpayer']['tax_components']}
            self.assertEqual(rates, {'ICMS': Decimal(0), 'PIS': Decimal(0),
                                     'COFINS': Decimal(0)})
            self.assertEqual(demo['assumptions']['credit_brl'], Decimal(0))
            self.assertIn('conditions', demo['assumptions']['product_tax'])

    def test_simples_product_segregation_is_not_a_blanket_zero_benefit(self):
        """Cold beverages have an explicit Simples rule; toothpaste does not."""
        for ean, expected in [('7894900027013', '.0285325'),
                              ('7891528029498', '.037290')]:
            demo = build_demo_profile('simples_nacional', Decimal(8),
                                     product=self.products[ean])
            self.assertEqual(demo['taxpayer']['tax_components'][0]['rate'],
                             Decimal(expected))

    def test_toothpaste_lc224_residual_is_not_full_standard_rate(self):
        """The November demo applies the sourced 10% benefit-reduction case."""
        for regime, pis, cofins in [('lucro_presumido', '.00065', '.003'),
                                    ('lucro_real', '.00165', '.0076')]:
            demo = build_demo_profile(regime, Decimal('1.50'),
                                     product=self.products['7891528029498'])
            rows = {r['name']: r for r in demo['taxpayer']['tax_components']}
            self.assertEqual(rows['PIS']['rate'], Decimal(pis))
            self.assertEqual(rows['COFINS']['rate'], Decimal(cofins))
            self.assertEqual(demo['assumptions']['credit_brl'], Decimal(0))

    def test_curves_and_sensitivity_keep_the_same_product_treatment(self):
        """Rebuilding a price/cost scenario must not restore generic credits."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   side_effect=RuntimeError('offline test')):
            result = analyze_mvp({'ean': '7894900027013',
                                  'regime': 'lucro_real',
                                  'acquisition_cost': '8', 'selling_price': '12'})
        margin = result['analysis']['personalized']['margin']
        self.assertEqual(margin['contribution_brl'], Decimal('4.000000'))
        curve = scenario_analysis(result)
        point = next(r for r in curve['curve'] if r['price_brl'] == Decimal(12))
        self.assertEqual(point['contribution_brl'], margin['contribution_brl'])
        row = curve['costs_brl'].index(Decimal(8))
        col = curve['grid_prices_brl'].index(Decimal(12))
        self.assertEqual(curve['contribution_grid_brl'][row][col],
                         margin['contribution_brl'])

    def test_unreviewed_skus_remain_explicit_and_ncm_mismatch_fails(self):
        """Unknown products remain unreviewed; changed NCM fails visibly."""
        rice = build_demo_profile('lucro_real', Decimal(8),
                                 product={'ean': 'unknown', 'ncm': '00000000'})
        self.assertEqual(rice['assumptions']['product_tax']['status'],
                         'generic_illustrative_unreviewed')
        wrong = {**self.products['7894900027013'], 'ncm': '33061000'}
        with self.assertRaises(ValueError):
            build_demo_profile('lucro_real', Decimal(8), product=wrong)

    def test_reviewed_rules_do_not_silently_extend_to_another_month(self):
        """A new competence requires a dated product-rule review."""
        future = {**demo_settings(), 'fiscal_date': '2027-01-01'}
        with patch('tax_pricing.demo_profile.demo_settings', return_value=future):
            with self.assertRaises(ValueError):
                build_demo_profile('lucro_real', Decimal(8),
                                   product=self.products['7894900027013'])

    def test_generic_credit_does_not_apply_pis_cofins_on_icms(self):
        """The fictional eligible normal purchase excludes ICMS from credits."""
        demo = build_demo_profile('lucro_real', Decimal(100))
        expected = Decimal('.195') + (1 - Decimal('.195')) * Decimal('.0925')
        self.assertEqual(demo['assumptions']['credit_fraction'], expected)
        self.assertEqual(demo['assumptions']['credit_brl'], Decimal('26.95'))

    def test_st_base_exclusion_is_not_a_second_purchase_credit(self):
        """An assumed ST amount changes the PIS base, not the acquisition cost."""
        with patch('tax_pricing.product_analysis.calculate_current_tax',
                   side_effect=RuntimeError('offline test')):
            result = analyze_mvp({'ean': '7891528029498',
                                  'regime': 'lucro_real',
                                  'acquisition_cost': '1.50',
                                  'selling_price': '3.99'})
        analysis = result['analysis']['personalized']
        pis = next(c for c in analysis['tax_components'] if c['name'] == 'PIS')
        self.assertEqual(pis['base_brl'], Decimal('3.84'))
        self.assertEqual(analysis['margin']['net_cost_brl'], Decimal('1.50'))
        self.assertEqual(analysis['margin']['contribution_brl'],
                         Decimal('2.4544800'))
        curve = scenario_analysis(result)
        self.assertGreaterEqual(curve['floor_contribution_brl'], 0)
        self.assertLess(curve['previous_cent_contribution_brl'], 0)


    def test_all_catalogue_products_have_dated_explicit_recipes(self):
        """Every EAN has its own NCM guard and source-backed conditions."""
        for product in self.products.values():
            for regime in ('simples_nacional', 'lucro_presumido', 'lucro_real'):
                with self.subTest(ean=product['ean'], regime=regime):
                    result = build_demo_profile(regime, Decimal('8'),
                                                product=product)
                    tax = result['assumptions']['product_tax']
                    self.assertEqual(
                        tax['status'],
                        'source_based_demonstration_conditions_assumed')
                    self.assertTrue(tax['source_urls'])
                    self.assertEqual(result['assumptions']['credit_brl'], 0)
                    wrong = {**product, 'ncm': '00000000'}
                    with self.assertRaises(ValueError):
                        build_demo_profile(regime, Decimal(8), product=wrong)

    def test_food_basket_is_distinct_from_soybean_oil(self):
        """Protected food zero and oil residual must not share one rate."""
        for product in self.products.values():
            if product['group'] not in ('Arroz', 'Feijão', 'Macarrão',
                                        'Açúcar', 'Café', 'Leite',
                                        'Óleo de soja'):
                continue
            profile = build_demo_profile('lucro_real', Decimal(8),
                                         product=product)
            rates = {r['name']: r['rate'] for r in
                     profile['taxpayer']['tax_components']}
            expected = (Decimal('.00165')
                        if product['group'] == 'Óleo de soja' else 0)
            self.assertEqual(rates['PIS'], expected)
            self.assertEqual(rates['ICMS'], 0)
            simple = build_demo_profile('simples_nacional', Decimal(8),
                                        product=product)
            self.assertEqual(simple['taxpayer']['tax_components'][0]['rate'],
                             Decimal('.03729'))

    def test_beverage_family_uses_retail_zero_and_segregation(self):
        """Beer shares the conditional retail rule with soda."""
        for product in self.products.values():
            if product['group'] not in ('Cerveja', 'Refrigerante 2 L'):
                continue
            regular = build_demo_profile('lucro_real', Decimal(8),
                                          product=product)
            self.assertTrue(all(r['rate'] == 0 for r in
                                regular['taxpayer']['tax_components']))
            simple = build_demo_profile('simples_nacional', Decimal(8),
                                        product=product)
            self.assertEqual(simple['taxpayer']['tax_components'][0]['rate'],
                             Decimal('.0285325'))


    def test_soap_residual_and_st_are_conditioned_on_toilet_soap(self):
        """NCM alone cannot prove the Ex01 toilet-soap description."""
        demo = build_demo_profile('lucro_real', Decimal('2'),
                                 product=self.products['7891024035047'])
        rows = {r['name']: r for r in demo['taxpayer']['tax_components']}
        self.assertEqual(rows['PIS']['rate'], Decimal('.00165'))
        self.assertEqual(rows['COFINS']['rate'], Decimal('.0076'))
        self.assertEqual(demo['assumptions']['purchase_icms_st_exclusion_brl'],
                         Decimal('.20'))
        self.assertIn('Ex01', ' '.join(
            demo['assumptions']['product_tax']['conditions']))


    def test_natural_mineral_water_does_not_inherit_cold_beverage_zero(self):
        """Art14 excludes Ex01/Ex02 natural mineral water, despite the NCM."""
        water = [p for p in self.products.values()
                 if p['group'] == 'Água mineral']
        self.assertEqual(len(water), 2)
        for product in water:
            for regime, pis in [('lucro_presumido', '.0065'),
                                ('lucro_real', '.0165')]:
                demo = build_demo_profile(regime, Decimal(8), product=product)
                rows = {r['name']: r for r in demo['taxpayer']['tax_components']}
                self.assertEqual(rows['PIS']['rate'], Decimal(pis))
            demo = build_demo_profile('simples_nacional', Decimal(8),
                                      product=product)
            self.assertEqual(demo['taxpayer']['tax_components'][0]['rate'],
                             Decimal('.03729'))

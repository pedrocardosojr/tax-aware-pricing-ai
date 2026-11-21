"""Personalized margin from explicit taxpayer components, not regime guesses."""
from copy import deepcopy
from decimal import Decimal
import unittest

from tax_pricing.personalized_tax import personalized_margin


class PersonalizedTaxTests(unittest.TestCase):
    """Reconcile distinct tax bases, credits and incomplete taxpayer data."""

    def setUp(self):
        self.profile = {
            'regime': 'lucro_presumido', 'competence': '2026-11',
            'coverage_confirmed': True, 'scope': 'fictional retail scenario',
            'usable_purchase_credit_brl': Decimal(0),
            'purchase_credit_source': 'explicit zero for arithmetic test',
            'tax_components': [
                self.rule('ICMS', '.18', 'selling_price'),
                self.rule('PIS', '.0065', 'selling_price_less_icms'),
                self.rule('COFINS', '.03', 'selling_price_less_icms')],
        }
        self.expenses = {'rate': Decimal('.05'), 'per_unit_brl': Decimal(1)}

    @staticmethod
    def rule(name, rate, basis):
        """Build sourced fictional data; these are not prescribed rates."""
        return {'name': name, 'rate': Decimal(rate), 'basis': basis,
                'source': 'fictional supplied taxpayer rule'}

    def test_distinct_bases_and_amount_reconciliation(self):
        """A supplied 18% ICMS leaves an 82-real base for the other rules."""
        result = personalized_margin(Decimal(100), Decimal(50), self.profile,
                                     expenses=self.expenses)
        self.assertEqual(result['status'], 'calculated_from_supplied_profile')
        self.assertEqual(result['tax_total_brl'], Decimal('20.993'))
        self.assertEqual(result['margin']['contribution_brl'],
                         Decimal('23.007'))
        self.assertEqual(result['margin']['contribution_percent'],
                         Decimal('23.007'))

    def test_three_regimes_use_their_explicit_components(self):
        """Simples uses supplied DAS, while Real uses supplied credit/rules."""
        simples = {**self.profile, 'regime': 'simples_nacional',
                   'icms_outside_das': False,
                   'tax_components': [self.rule('DAS', '.0565',
                                                'selling_price')]}
        result = personalized_margin(Decimal(100), Decimal(50), simples,
                                     expenses=self.expenses)
        self.assertEqual(result['tax_total_brl'], Decimal('5.6500'))
        real = {**self.profile, 'regime': 'lucro_real',
                'usable_purchase_credit_brl': Decimal(5)}
        result = personalized_margin(Decimal(100), Decimal(50), real,
                                     expenses=self.expenses)
        self.assertEqual(result['margin']['net_cost_brl'], Decimal(45))
        self.assertEqual(result['margin']['contribution_brl'],
                         Decimal('28.007'))

    def test_missing_component_or_source_does_not_become_zero(self):
        """A partial profile never produces an apparently complete margin."""
        for key in ('component', 'source', 'credit', 'coverage'):
            profile = deepcopy(self.profile)
            if key == 'component':
                profile['tax_components'].pop()
            elif key == 'source':
                profile['tax_components'][0]['source'] = ''
            elif key == 'credit':
                profile['usable_purchase_credit_brl'] = None
            else:
                profile['coverage_confirmed'] = False
            result = personalized_margin(Decimal(100), Decimal(50), profile,
                                         expenses=self.expenses)
            self.assertEqual(result['status'], 'pending_taxpayer_data')
            self.assertIsNone(result['margin'])
            self.assertTrue(result['missing_fields'])

    def test_zero_tax_with_source_is_valid(self):
        """Explicit zero rates can represent the user's sourced treatment."""
        for rule in self.profile['tax_components']:
            rule['rate'] = Decimal(0)
        result = personalized_margin(Decimal(100), Decimal(50), self.profile,
                                     expenses=self.expenses)
        self.assertEqual(result['tax_total_brl'], Decimal(0))
        self.assertEqual(result['margin']['contribution_brl'], Decimal(44))

    def test_simples_icms_cannot_be_counted_twice(self):
        """Outside-DAS ICMS requires an explicit exclusion in the DAS rule."""
        profile = {**self.profile, 'regime': 'simples_nacional',
                   'icms_outside_das': True,
                   'tax_components': [self.rule('DAS', '.05', 'selling_price'),
                                      self.rule('ICMS', '.10', 'selling_price')]}
        result = personalized_margin(Decimal(100), Decimal(50), profile,
                                     expenses=self.expenses)
        self.assertIsNone(result['margin'])
        profile['tax_components'][0]['excludes_icms'] = True
        result = personalized_margin(Decimal(100), Decimal(50), profile,
                                     expenses=self.expenses)
        self.assertEqual(result['tax_total_brl'], Decimal(15))

    def test_invalid_or_duplicate_rules_fail_explicitly(self):
        """Do not permit duplicate deductions or unsupported base recipes."""
        for key in ('duplicate', 'negative', 'basis', 'credit'):
            profile = deepcopy(self.profile)
            if key == 'duplicate':
                profile['tax_components'].append(profile['tax_components'][0])
            elif key == 'negative':
                profile['tax_components'][0]['rate'] = Decimal('-1')
            elif key == 'basis':
                profile['tax_components'][0]['basis'] = 'selling_price_less_icms'
            else:
                profile['usable_purchase_credit_brl'] = Decimal(51)
            with self.subTest(key=key), self.assertRaises(ValueError):
                personalized_margin(Decimal(100), Decimal(50), profile,
                                    expenses=self.expenses)

    def test_scenario_prices_recompute_amounts_without_a_margin_target(self):
        """The same declared rate recipes apply to each corridor candidate."""
        for price in (Decimal(10), Decimal(20)):
            result = personalized_margin(price, Decimal(5), self.profile,
                                         expenses=self.expenses)
            self.assertEqual(result['tax_total_brl'], price * Decimal('.20993'))

    def test_total_tax_above_price_remains_a_visible_loss(self):
        """An extreme explicit deduction cannot wrap into a positive margin."""
        for rule in self.profile['tax_components']:
            rule.update(rate=Decimal('.90'), basis='selling_price')
        result = personalized_margin(Decimal(100), Decimal(50), self.profile,
                                     expenses=self.expenses)
        self.assertLess(result['margin']['contribution_brl'], Decimal(0))

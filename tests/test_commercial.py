"""Contracts for current-price arithmetic with declared fiscal inputs."""
from decimal import Decimal
import unittest

from tax_pricing.commercial import (margin_breakdown, market_position,
                                    net_acquisition_cost,
                                    required_selling_price)


class CommercialTests(unittest.TestCase):
    """Check reconciliation, losses, inverse pricing and missing inputs."""

    def setUp(self):
        self.rates = {'tax_rate': Decimal('.10'),
                      'expense_rate': Decimal('.05'),
                      'expense_per_unit': Decimal('.50')}

    def test_price_tree_reconciles_and_margin_is_on_sales(self):
        """Ten reais less six cost, one tax and one expense leaves two."""
        result = margin_breakdown(Decimal('10'), Decimal('6'), **self.rates)
        self.assertEqual(result['contribution_brl'], Decimal('2'))
        self.assertEqual(result['contribution_percent'], Decimal('20'))
        self.assertEqual(result['tax_brl'], Decimal('1'))
        self.assertEqual(result['expense_brl'], Decimal('1'))
        self.assertEqual(sum(result[k] for k in (
            'net_cost_brl', 'tax_brl', 'expense_brl', 'contribution_brl')),
            result['selling_price_brl'])

    def test_credit_is_explicit_and_applied_once(self):
        """A declared fifty-cent usable credit reduces cost to 5.50."""
        cost = net_acquisition_cost(Decimal('6'), Decimal('.50'))
        result = margin_breakdown(Decimal('10'), cost, **self.rates)
        self.assertEqual(result['contribution_brl'], Decimal('2.50'))
        self.assertEqual(result['contribution_percent'], Decimal('25'))

    def test_negative_margin_remains_visible(self):
        """An unprofitable selling price is valid evidence, not an error."""
        result = margin_breakdown(Decimal('5'), Decimal('6'), **self.rates)
        self.assertEqual(result['contribution_brl'], Decimal('-2.25'))
        self.assertEqual(result['contribution_percent'], Decimal('-45'))

    def test_target_price_is_minimum_cent_and_round_trips(self):
        """The first cent meets the target and the preceding cent fails."""
        price = required_selling_price(Decimal('6'), Decimal('.25'),
                                       **self.rates)
        self.assertEqual(price, Decimal('10.84'))
        result = margin_breakdown(price, Decimal('6'), **self.rates)
        self.assertGreaterEqual(result['contribution_percent'], Decimal('25'))
        prior = margin_breakdown(price - Decimal('.01'), Decimal('6'),
                                 **self.rates)
        self.assertLess(prior['contribution_percent'], Decimal('25'))

    def test_market_reference_and_direction(self):
        """Index 100 equals reference; values above and below keep sign."""
        for sale, index, gap in [('10', '100', '0'), ('12', '120', '2'),
                                 ('8', '80', '-2')]:
            result = market_position(Decimal(sale), Decimal('10'))
            self.assertEqual(result['price_index'], Decimal(index))
            self.assertEqual(result['gap_brl'], Decimal(gap))
            self.assertEqual(result['gap_percent'], Decimal(index) - 100)

    def test_invalid_cost_credit_and_price(self):
        """Reject absent, nonfinite, negative and oversized credits."""
        for credit in ('-1', '7', 'NaN', 'Infinity'):
            with self.subTest(credit=credit), self.assertRaises(ValueError):
                net_acquisition_cost(Decimal('6'), Decimal(credit))
        for sale in ('0', '-1', 'NaN', 'Infinity'):
            with self.subTest(sale=sale), self.assertRaises(ValueError):
                margin_breakdown(Decimal(sale), Decimal('6'), **self.rates)
        for reference in ('0', '-1', 'NaN', 'Infinity'):
            with self.subTest(reference=reference), self.assertRaises(
                    ValueError):
                market_position(Decimal('10'), Decimal(reference))

    def test_invalid_rates_expenses_and_target(self):
        """Reject impossible rate totals and nonfinite parameters."""
        for key, value in [('tax_rate', '-.1'), ('tax_rate', '1'),
                           ('expense_rate', 'NaN'),
                           ('expense_rate', '.9'),
                           ('expense_per_unit', '-1')]:
            inputs = {**self.rates, key: Decimal(value)}
            with self.subTest(key=key, value=value), self.assertRaises(
                    ValueError):
                margin_breakdown(Decimal('10'), Decimal('6'), **inputs)
        for target in ('-.1', '.85', 'NaN', 'Infinity'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                required_selling_price(Decimal('6'), Decimal(target),
                                       **self.rates)

    def test_missing_tax_is_not_zero(self):
        """An unknown tax input must not silently become tax-free."""
        with self.assertRaises(TypeError):
            # Deliberately omit a mandatory fiscal assumption.
            # pylint: disable-next=missing-kwoa
            margin_breakdown(Decimal('10'), Decimal('6'),
                             expense_rate=Decimal(0),
                             expense_per_unit=Decimal(0))

    def test_zero_cost_and_full_credit_are_explicit(self):
        """Zero net cost is supported, but cannot produce a zero sale."""
        self.assertEqual(net_acquisition_cost(Decimal('6'), Decimal('6')),
                         Decimal(0))
        with self.assertRaises(ValueError):
            required_selling_price(Decimal(0), Decimal('.25'),
                                   tax_rate=Decimal(0),
                                   expense_rate=Decimal(0),
                                   expense_per_unit=Decimal(0))

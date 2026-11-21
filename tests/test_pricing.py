"""Commercial contracts independent of a fiscal service."""
from decimal import Decimal
import unittest

from tax_pricing.economics import contribution_margin
from tax_pricing.pricing import commercial_quote


class PricingTests(unittest.TestCase):
    """Protect explicit commercial assumptions."""

    def test_declared_credit_and_inverse_margin(self):
        """Use the explicit credit rather than inferring it from NCM."""
        quote = commercial_quote(*map(Decimal, ('2.30', '.22', '.05', '.20')),
                                 regime='regular', unified_rate=Decimal(0))
        self.assertEqual(quote['net_cost'], Decimal('2.08'))
        self.assertEqual(quote['base'], Decimal('2.78'))
        self.assertGreaterEqual(quote['achieved_margin'], Decimal('.20'))
        self.assertLess(contribution_margin(quote['base'] - Decimal('.01'),
                                           quote['net_cost'],
                                           quote['deduction']), Decimal('.20'))

    def test_simples_is_declared_arithmetic(self):
        """Effective rate is a premise, not a regime-geral API response."""
        quote = commercial_quote(*map(Decimal, ('2.30', '0', '.05', '.20')),
                                 regime='simples', unified_rate=Decimal('.04'))
        self.assertEqual(quote['base'], Decimal('3.24'))
        self.assertEqual(quote['net_cost'], Decimal('2.30'))

    def test_invalid_or_incompatible_inputs(self):
        """Reject hidden credits, double taxes and infeasible margin."""
        cases = [('-1', '0', '.05', '.2', 'regular', '0'),
                 ('2', '2', '.05', '.2', 'regular', '0'),
                 ('2', '.01', '.05', '.2', 'simples', '.04'),
                 ('2', '0', '.05', '.2', 'regular', '.04'),
                 ('2', '0', '.9', '.2', 'simples', '.04'),
                 ('2', '0', 'NaN', '.2', 'regular', '0')]
        for gross, credit, expense, target, regime, rate in cases:
            with self.subTest(regime=regime, cost=gross), (
                    self.assertRaises(ValueError)):
                commercial_quote(Decimal(gross), Decimal(credit),
                                 Decimal(expense), Decimal(target),
                                 regime=regime, unified_rate=Decimal(rate))

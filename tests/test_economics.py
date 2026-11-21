"""Behavioral checks for the explicitly declared contribution model."""
from decimal import Decimal
import unittest

from tax_pricing.economics import contribution_margin, required_base


class EconomicsTests(unittest.TestCase):
    """Check target feasibility and minimal cent rounding."""

    def test_required_base_and_inverse(self):
        """The returned cent covers the target; the previous cent does not."""
        cost, expense, target = map(Decimal, ('2.30', '.05', '.20'))
        base = required_base(cost, expense, target)
        self.assertEqual(base, Decimal('3.07'))
        self.assertGreaterEqual(
            contribution_margin(base, cost, expense), target)
        self.assertLess(
            contribution_margin(base - Decimal('.01'), cost, expense),
            target)

    def test_zero_cost_is_valid(self):
        """A zero acquisition cost is valid but zero revenue has no margin."""
        self.assertEqual(required_base(Decimal(0), Decimal(0), Decimal(0)),
                         Decimal('0.00'))
        with self.assertRaises(ValueError):
            contribution_margin(Decimal(0), Decimal(0), Decimal(0))

    def test_invalid_inputs(self):
        """Reject non-finite, infeasible and negative inputs explicitly."""
        cases = [('-1', '.05', '.20'), ('2', '-.1', '.2'),
                 ('2', '.05', '-.1'), ('2', '.8', '.2'),
                 ('2', '1', '0'), ('NaN', '.05', '.2'),
                 ('Infinity', '.05', '.2')]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                required_base(*map(Decimal, values))

    def test_margin_can_be_negative(self):
        """A loss-making scenario must remain visible."""
        self.assertEqual(contribution_margin(
            Decimal('2'), Decimal('3'), Decimal('.1')), Decimal('-.6'))

    def test_invalid_revenue_and_expenses(self):
        """Reject unusable revenue and expense fractions."""
        for base, cost, expense in [('-1', '2', '.1'), ('NaN', '2', '.1'),
                                    ('2', '-1', '.1'), ('2', '1', '1')]:
            with self.subTest(base=base, cost=cost, expense=expense):
                with self.assertRaises(ValueError):
                    contribution_margin(*map(Decimal, (base, cost, expense)))

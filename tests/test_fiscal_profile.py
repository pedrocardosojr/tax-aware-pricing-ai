"""Contracts between fiscal coverage, scenario provenance and margin."""
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import unittest

from tax_pricing.fiscal_profile import FiscalProfile, REGIMES
from tax_pricing.profile_calculation import (profile_margin,
                                            simples_effective_rate)
from tax_pricing.tax_summary import summarize_tax


class FiscalProfileTests(unittest.TestCase):
    """Unknown fiscal components stay pending even when RTC returns zero."""

    def setUp(self):
        self.profile = FiscalProfile(
            'simples_nacional', '2026-11', Decimal('.10'), Decimal(0),
            'fictional test tax', 'explicit test credit of zero',
            'illustrative constant deductions on selling price',
            'illustrative')
        self.expenses = {'expense_rate': Decimal('.05'),
                         'expense_per_unit': Decimal('.50')}

    def test_complete_illustrative_profile_computes_conditional_margin(self):
        """Profile assumptions drive arithmetic, not the company regime key."""
        for regime in REGIMES:
            result = profile_margin(Decimal('10'), Decimal('6'),
                                    replace(self.profile, regime=regime),
                                    **self.expenses)
            self.assertEqual(result['status'], 'illustrative')
            self.assertEqual(result['margin']['contribution_brl'],
                             Decimal('2'))
            self.assertEqual(result['business_regime'], regime)

    def test_regime_alone_cannot_produce_margin(self):
        """Every regime needs fiscal inputs and provenance."""
        for regime in REGIMES:
            result = profile_margin(Decimal('10'), Decimal('6'),
                                    FiscalProfile(regime, '2026-11'),
                                    **self.expenses)
            self.assertIsNone(result['margin'])
            self.assertEqual(result['status'], 'pending_profile')
            self.assertIn('tax_rate', result['missing_fields'])

    def test_zero_rate_requires_explicit_provenance(self):
        """A deliberate zero can calculate; unknown or unsourced cannot."""
        profile = replace(self.profile, tax_rate=Decimal(0))
        result = profile_margin(Decimal('10'), Decimal('6'), profile,
                                **self.expenses)
        self.assertEqual(result['margin']['tax_brl'], Decimal(0))
        for changes in ({'tax_rate': None}, {'tax_source': ' '},
                        {'credit_source': ''}, {'status': 'pending'}):
            result = profile_margin(Decimal('10'), Decimal('6'),
                                    replace(profile, **changes),
                                    **self.expenses)
            self.assertIsNone(result['margin'])

    def test_explicit_credit_is_used_once(self):
        """A purchase credit changes cost only by its declared BRL amount."""
        profile = replace(self.profile, usable_credit_brl=Decimal('.50'))
        result = profile_margin(Decimal('10'), Decimal('6'), profile,
                                **self.expenses)
        self.assertEqual(result['margin']['net_cost_brl'], Decimal('5.50'))
        self.assertEqual(result['margin']['contribution_brl'], Decimal('2.50'))

    def test_actual_rtc_evidence_never_completes_company_profile(self):
        """Both zero rice and nonzero soda leave taxpayer data unresolved."""
        fixtures = json.loads((Path(__file__).parent / 'fixtures'
                               / 'rtc_2026_examples.json').read_text())
        totals = []
        for fixture in fixtures[:2]:
            tax = summarize_tax(fixture['call']['body'])
            totals.append(tax['total_ibs_cbs_brl'])
            result = profile_margin(Decimal('30'), Decimal('20'),
                                    FiscalProfile('lucro_real', '2026-11'),
                                    **self.expenses)
            self.assertIsNone(result['margin'])
            self.assertFalse(tax['total_tax_burden_calculated'])
        self.assertEqual(totals, [Decimal('0'), Decimal('.30')])

    def test_invalid_regime_date_status_and_parameters(self):
        """Reject unsupported identifiers and invalid fiscal assumptions."""
        for change in ({'regime': 'regular'}, {'competence': '2026-13'},
                       {'competence': '2026-1'}, {'status': 'certified'},
                       {'tax_rate': Decimal('NaN')},
                       {'tax_rate': Decimal('1')},
                       {'usable_credit_brl': Decimal('-1')}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.profile, **change)

    def test_supplied_simples_formula(self):
        """Declared bracket values produce 5.65%, before revenue treatment."""
        self.assertEqual(simples_effective_rate(
            Decimal('360000'), Decimal('.073'), Decimal('5940')),
            Decimal('.0565'))
        self.assertEqual(simples_effective_rate(
            Decimal('180000'), Decimal('.04'), Decimal(0)), Decimal('.04'))

    def test_invalid_simples_inputs(self):
        """Zero revenue, inconsistent deduction and nonfinite values fail."""
        for values in [('0', '.04', '0'), ('100', '.04', '10'),
                       ('NaN', '.04', '0'), ('100', '1', '0'),
                       ('100', '.04', '-1')]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                simples_effective_rate(*map(Decimal, values))

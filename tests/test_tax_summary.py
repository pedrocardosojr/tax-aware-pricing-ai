"""Verify UI facts against recorded RTC examples and error cases."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from tax_pricing.tax_summary import summarize_tax


class TaxSummaryTests(unittest.TestCase):
    """Expose calculated tax details with explicit coverage."""

    def setUp(self):
        """Load actual local RTC responses for four catalog products."""
        path = Path(__file__).parent / 'fixtures/rtc_2026_examples.json'
        self.cases = json.loads(path.read_text())

    def test_rice_zero_explains_the_full_reduction(self):
        """A zero amount still carries the rate and reduction evidence."""
        result = summarize_tax(self.cases[0]['call']['body'])
        self.assertEqual(result['tax_base_brl'], Decimal('30.00'))
        cbs = result['components'][0]
        self.assertEqual(cbs['reference_rate_percent'], Decimal('.90'))
        self.assertEqual(cbs['reduction_percent'], Decimal('100'))
        self.assertEqual(cbs['effective_rate_percent'], Decimal(0))
        self.assertEqual(result['total_ibs_cbs_brl'], Decimal(0))
        self.assertEqual(result['coverage'], 'IBS/CBS calculated by RTC')
        self.assertFalse(result['total_tax_burden_calculated'])

    def test_full_rate_without_reduction_group(self):
        """The refrigerant result exposes 1% combined effective rates."""
        result = summarize_tax(self.cases[1]['call']['body'])
        self.assertEqual(result['total_ibs_cbs_brl'], Decimal('.30'))
        self.assertEqual(result['components'][0]['reduction_percent'], 0)
        self.assertEqual(result['components'][0]['effective_rate_percent'],
                         Decimal('.90'))

    def test_reduced_oil_and_soap(self):
        """The 60% reduction produces the recorded nonzero amounts."""
        for case in self.cases[2:]:
            with self.subTest(product=case['product']):
                result = summarize_tax(case['call']['body'])
                self.assertEqual(result['total_ibs_cbs_brl'], Decimal('.12'))
                self.assertEqual(
                    result['components'][0]['effective_rate_percent'],
                    Decimal('.36'))

    def test_missing_or_invalid_fields_are_rejected(self):
        """Missing details and invalid rates must fail explicitly."""
        for value in ('NaN', '-1', '101'):
            body = deepcopy(self.cases[0]['call']['body'])
            group = body['objetos'][0]['tribCalc']['IBSCBS']['gIBSCBS']
            group['gCBS']['pCBS'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize_tax(body)
        body = deepcopy(self.cases[0]['call']['body'])
        del body['objetos'][0]['tribCalc']['IBSCBS']['gIBSCBS']['gIBSUF']
        with self.assertRaises(ValueError):
            summarize_tax(body)

    def test_preserves_official_ibs_aggregate(self):
        """Rounded component amounts do not replace the engine aggregate."""
        body = deepcopy(self.cases[2]['call']['body'])
        group = body['objetos'][0]['tribCalc']['IBSCBS']['gIBSCBS']
        group['vIBS'] = '.23'
        group['gIBSUF']['vIBSUF'] = '.12'
        group['gIBSMun']['vIBSMun'] = '.12'
        result = summarize_tax(body)
        self.assertEqual(result['ibs_official_total_brl'], Decimal('.23'))
        self.assertEqual(result['total_ibs_cbs_brl'], Decimal('.34'))

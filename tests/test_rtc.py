"""Contract tests without requiring a running RTC server."""
from decimal import Decimal
import unittest

from tax_pricing.rtc import build_operation, read_tax


class RtcTests(unittest.TestCase):
    """Validate transport and tax extraction independently of HTTP."""

    def setUp(self):
        """Use an explicit hypothetical future scenario."""
        self.product = {'ean': '7891528029498', 'ncm': '33061000'}
        self.scenario = {
            'year': 2033, 'cst': '200', 'cclass': '200035',
            'nominal_rates': {'cbs': 8.8, 'ibsEstadual': 8.85,
                              'ibsMunicipal': 8.85}}

    def test_future_rates_are_explicit(self):
        """A future year cannot silently select presumed legal rates."""
        del self.scenario['nominal_rates']
        with self.assertRaises(ValueError):
            build_operation(self.product, self.scenario, Decimal('3.07'))

    def test_invalid_or_fractional_cent_base(self):
        """Reject invalid bases before making any HTTP request."""
        for value in ('-1', '0', 'NaN', 'Infinity', '2.301'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_operation(self.product, self.scenario, Decimal(value))

    def test_preserve_leading_zero_ncm(self):
        """Fiscal codes must stay textual in the payload."""
        self.product['ncm'] = '07133319'
        payload = build_operation(self.product, self.scenario, Decimal('3'))
        self.assertEqual(payload['itens'][0]['ncm'], '07133319')
        self.assertEqual(payload['tpDoc'], 65)

    def test_missing_classification_is_rejected(self):
        """NCM alone must not silently choose a classification."""
        self.scenario['cclass'] = ''
        with self.assertRaises(ValueError):
            build_operation(self.product, self.scenario, Decimal('3'))

    def test_aggregate_tax_is_preserved(self):
        """Rounded IBS components need not sum to the official aggregate."""
        response = {'objetos': [{'calculoSimulado': True, 'tribCalc': {
            'IBSCBS': {'gIBSCBS': {'vIBS': '.23',
                                  'gCBS': {'vCBS': '.12'}}}}}]}
        self.assertEqual(read_tax(response), Decimal('.35'))

    def test_negative_or_missing_tax_fails_closed(self):
        """Malformed tax cannot become an apparent zero-tax quote."""
        for response in ({}, {'objetos': []}, {'objetos': [{
                'tribCalc': {'IBSCBS': {'gIBSCBS': {
                    'vIBS': '-1', 'gCBS': {'vCBS': '0'}}}}}]}):
            with self.subTest(response=response), (
                    self.assertRaises(ValueError)):
                read_tax(response)

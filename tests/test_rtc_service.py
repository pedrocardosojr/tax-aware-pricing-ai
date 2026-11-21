"""Current-scenario service contracts against saved official responses."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tax_pricing.rtc_service import calculate_current_tax


class CurrentTaxTests(unittest.TestCase):
    """Validate dates, compatibility and response identity before use."""

    def setUp(self):
        fixtures = json.loads((Path(__file__).parent / 'fixtures'
                               / 'rtc_2026_examples.json').read_text())
        self.body = fixtures[1]['call']['body']
        self.product = {'ean': '7894900027013', 'ncm': '22021000'}
        self.scenario = {'year': 2026, 'cst': '000', 'cclass': '000001',
                         'fiscal_date': '2026-11-07'}
        self.version = {'versaoApp': '1.5.4', 'versaoDb': 'V0059',
                        'ambiente': 'offline'}

    def responses(self, body=None):
        """Supply three independent RTC calls in transport order."""
        return [{'status': 200, 'body': self.version},
                {'status': 200, 'body': {'valido': True}},
                {'status': 200, 'body': self.body if body is None else body}]

    def test_explicit_date_base_and_scope(self):
        """Use the requested fiscal base/date and preserve IBS/CBS scope."""
        with patch('tax_pricing.rtc_service.call_rtc',
                   side_effect=self.responses()) as call:
            result = calculate_current_tax(self.product, self.scenario,
                                           Decimal('30'))
        self.assertEqual(result['summary']['total_ibs_cbs_brl'],
                         Decimal('.30'))
        self.assertEqual(result['request']['dhFatoGerador'],
                         '2026-11-07T12:00:00-03:00')
        self.assertIn('2026-11-07', call.call_args_list[1].args[0])
        self.assertEqual(result['company_tax_assessment'], 'not_calculated')
        self.assertEqual(result['classification_review'], 'pending')

    def test_invalid_dates_fail_before_transport(self):
        """Do not silently replace an absent, future or invalid date."""
        for day in (None, '2026-02-30', '2027-01-01', '20261107'):
            with self.subTest(day=day), patch(
                    'tax_pricing.rtc_service.call_rtc') as call:
                with self.assertRaises(ValueError):
                    calculate_current_tax(self.product,
                                          {**self.scenario, 'fiscal_date': day},
                                          Decimal('30'))
                call.assert_not_called()

    def test_new_engine_requires_the_matching_database(self):
        """Accept the evaluated release, not arbitrary application/db pairs."""
        self.version = {'versaoApp': '1.6.2', 'versaoDb': 'V0066',
                        'ambiente': 'offline'}
        with patch('tax_pricing.rtc_service.call_rtc',
                   side_effect=self.responses()):
            result = calculate_current_tax(self.product, self.scenario,
                                           Decimal('30'))
        self.assertEqual(result['engine']['versaoDb'], 'V0066')
        self.version['versaoDb'] = 'V0059'
        with patch('tax_pricing.rtc_service.call_rtc',
                   side_effect=self.responses()), self.assertRaises(
                       RuntimeError):
            calculate_current_tax(self.product, self.scenario, Decimal('30'))

    def test_response_must_match_request(self):
        """Reject another base, classification or simulation flag."""
        for key in ('base', 'class', 'simulated'):
            body = deepcopy(self.body)
            item = body['objetos'][0]
            group = item['tribCalc']['IBSCBS']
            if key == 'base':
                group['gIBSCBS']['vBC'] = '31.00'
            elif key == 'class':
                group['cClassTrib'] = '200003'
            else:
                item['calculoSimulado'] = True
            with self.subTest(key=key), patch(
                    'tax_pricing.rtc_service.call_rtc',
                    side_effect=self.responses(body)):
                with self.assertRaises(ValueError):
                    calculate_current_tax(self.product, self.scenario,
                                          Decimal('30'))

    def test_incompatible_classification_or_http_error_stops_calculation(self):
        """No fallback to zero when compatibility or HTTP checks fail."""
        for second in ({'status': 200, 'body': {'valido': False}},
                       {'status': 422, 'body': {'message': 'invalid'}}):
            responses = self.responses()
            responses[1] = second
            with self.subTest(second=second), patch(
                    'tax_pricing.rtc_service.call_rtc',
                    side_effect=responses) as call:
                with self.assertRaises((ValueError, RuntimeError)):
                    calculate_current_tax(self.product, self.scenario,
                                          Decimal('30'))
                self.assertEqual(call.call_count, 2)

    def test_version_and_service_failures_are_explicit(self):
        """An untested motor version or an outage cannot produce a quote."""
        for effect in ([{'status': 200, 'body': {'versaoApp': 'changed'}}],
                       RuntimeError('service unavailable')):
            with self.subTest(effect=effect), patch(
                    'tax_pricing.rtc_service.call_rtc', side_effect=effect):
                with self.assertRaises(RuntimeError):
                    calculate_current_tax(self.product, self.scenario,
                                          Decimal('30'))

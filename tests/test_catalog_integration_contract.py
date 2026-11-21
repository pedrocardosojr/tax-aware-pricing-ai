"""Batch behavior when fiscal inputs or the RTC service are unavailable."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.test_catalog_rtc import run_catalog
from tax_pricing.rtc import call_rtc


class CatalogIntegrationContractTests(unittest.TestCase):
    """A blocked scenario must never acquire an apparent consumer price."""

    def test_missing_is_remains_blocked_with_evidence(self):
        """Preserve the engine's IS refusal rather than force zero tax."""
        version = {'versaoApp': '1.5.4', 'versaoDb': 'V0059',
                   'ambiente': 'offline'}
        refusal = {'type': '/errors/dados-imposto-seletivo-nao-informados'}
        responses = [
            {'status': 200, 'body': version},
            {'status': 200, 'body': {'valido': True}},
            {'status': 422, 'body': refusal},
            {'status': 200, 'body': {'valido': True}},
            {'status': 422, 'body': refusal}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog, profiles = root / 'catalog.json', root / 'profiles.json'
            catalog.write_text(json.dumps({'products': [
                {'ean': '7894900027013', 'ncm': '22021000'}]}))
            profiles.write_text(json.dumps({'22021000': {
                'cst': '000', 'cclass': '000001'}}))
            with patch('scripts.test_catalog_rtc.call_rtc',
                       side_effect=responses):
                result = run_catalog(catalog, profiles, root / 'evidence',
                                     years=(2026, 2033))
            self.assertEqual(result['blocked'], 2)
            self.assertEqual(result['errors'], 0)
            self.assertTrue((root / 'evidence/calls.json').exists())
            for row in result['rows']:
                self.assertNotIn('experimental_total', row)
            with self.assertRaises(FileExistsError):
                run_catalog(catalog, profiles, root / 'evidence')

    def test_default_scope_is_only_2026(self):
        """The agreed delivery must not require future nominal rates."""
        version = {'versaoApp': '1.5.4', 'versaoDb': 'V0059',
                   'ambiente': 'offline'}
        examples = Path(__file__).parent / 'fixtures/rtc_2026_examples.json'
        tax = json.loads(examples.read_text())[1]['call']['body']
        responses = [{'status': 200, 'body': version},
                     {'status': 200, 'body': {'valido': True}},
                     {'status': 200, 'body': tax}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog, profiles = root / 'catalog.json', root / 'profiles.json'
            catalog.write_text(json.dumps({'products': [
                {'ean': '7894900027013', 'ncm': '22021000'}]}))
            profiles.write_text(json.dumps({'22021000': {
                'cst': '000', 'cclass': '000001'}}))
            with patch('scripts.test_catalog_rtc.call_rtc',
                       side_effect=responses) as mocked:
                result = run_catalog(catalog, profiles, root / 'evidence')
            self.assertEqual(result['scenario_years'], [2026])
            self.assertEqual(result['passed'], 1)
            self.assertEqual(len(result['rows']), 1)
            payload = mocked.call_args_list[-1].args[1]
            self.assertNotIn('aliquotasNominais', payload['itens'][0])

    def test_offline_service_does_not_return_zero_tax(self):
        """Connectivity failure is explicit rather than a made-up estimate."""
        with patch('tax_pricing.rtc.urlopen', side_effect=URLError('offline')):
            with self.assertRaises(RuntimeError):
                call_rtc('/calculadora/dados-abertos/versao')

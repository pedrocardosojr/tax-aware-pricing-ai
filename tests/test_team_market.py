"""Contract checks for importing the team's observed market reference."""
from copy import deepcopy
import unittest

from tax_pricing.team_market import adapt_team_reference


class TeamMarketTests(unittest.TestCase):
    """Prevent invented sources, inconsistent coverage and hidden estimates."""

    def setUp(self) -> None:
        self.reference = {
            'id_produto': '7894900027013', 'janela': ['2026-08', '2026-09',
                                                    '2026-10'],
            'camada': 'observado', 'mediana': 10, 'p25': 9, 'p75': 11,
            'n_redes': 3, 'n_obs': 9, 'n_lojas': 6,
            'ultima_obs': '2026-10-01', 'cobertura_ok': True,
        }
        self.networks = {'A': 8, 'B': 10, 'C': 12}

    def adapt(self) -> dict:
        """Use the same observed payload for each contract scenario."""
        return adapt_team_reference(
            self.reference, self.networks, source='team:revision-123')

    def test_preserves_window_source_and_equal_network_prices(self) -> None:
        """Do not replace the team's reference with the old laboratory."""
        snapshot = self.adapt()
        self.assertEqual(snapshot['ean'], self.reference['id_produto'])
        self.assertEqual(snapshot['window'], self.reference['janela'])
        self.assertEqual(snapshot['source'], 'team:revision-123')
        self.assertEqual(snapshot['median'], '10')
        self.assertEqual(snapshot['kind'], 'observed')
        self.assertEqual(snapshot['network_count'], 3)

    def test_rejects_estimated_layer_and_inconsistent_counts(self) -> None:
        """An estimate or extra network cannot masquerade as observed data."""
        self.reference['camada'] = 'estimado'
        with self.assertRaises(ValueError):
            self.adapt()
        self.reference['camada'] = 'observado'
        self.reference['n_redes'] = 4
        with self.assertRaises(ValueError):
            self.adapt()

    def test_rejects_bad_money_dates_and_empty_source(self) -> None:
        """Fail visibly on corrupted data instead of silently using zero."""
        original = deepcopy(self.reference)
        for field, value in [('p25', 12), ('mediana', 'NaN'),
                             ('ultima_obs', '2026-02-30'),
                             ('janela', ['2026-10', '2026-08'])]:
            self.reference = {**original, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.adapt()
        with self.assertRaises(ValueError):
            adapt_team_reference(original, self.networks, source=' ')

    def test_insufficient_coverage_does_not_expose_a_band(self) -> None:
        """Keep the reference and source while withholding a current band."""
        self.reference['cobertura_ok'] = False
        result = self.adapt()
        self.assertIsNone(result['p25'])
        self.assertIsNone(result['p75'])
        self.assertEqual(result['median'], '10')

    def test_original_payload_is_not_changed(self) -> None:
        """The app adapter must not mutate the statistics owned by Edu."""
        original = deepcopy(self.reference)
        self.adapt()
        self.assertEqual(self.reference, original)

    def test_network_prices_must_describe_the_same_reference(self) -> None:
        """A same-size price list from another window is not interchangeable."""
        self.networks['B'] = 100
        with self.assertRaises(ValueError):
            self.adapt()

    def test_store_reference_may_differ_from_the_network_median(self) -> None:
        """Import store quartiles alongside the separately grouped network points."""
        self.reference.update(aggregation='median_across_stores', mediana=11)
        snapshot = self.adapt()
        self.assertEqual(snapshot['median'], '11')
        self.assertEqual(snapshot['aggregation'], 'median_across_stores')
        self.assertEqual(snapshot['per_network_brl'], {'A': '8', 'B': '10', 'C': '12'})

    def test_unknown_aggregation_is_rejected(self) -> None:
        """A misspelled method cannot bypass network consistency checks."""
        self.reference['aggregation'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unknown team reference aggregation'):
            self.adapt()

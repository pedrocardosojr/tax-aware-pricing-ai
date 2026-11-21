"""Extra price charts read the public monthly base without inventing values."""
import unittest

from tax_pricing.price_history import (
    monthly_band, network_by_month, similar_unit_prices, unit_factor,
)

COCA = '7894900027013'


class PriceHistoryTests(unittest.TestCase):
    """Monthly band, network table and category comparison."""

    def test_unit_factor_reads_packages(self):
        """Packages become kg or litres; unknown formats are skipped."""
        self.assertEqual(unit_factor('500 g'), (0.5, 'kg'))
        self.assertEqual(unit_factor('2 L'), (2.0, 'L'))
        quantity, unit = unit_factor('350 ml') or (0.0, '')
        self.assertAlmostEqual(quantity, 0.35)
        self.assertEqual(unit, 'L')
        self.assertIsNone(unit_factor('cx 12 un'))

    def test_monthly_band_is_ordered_and_consistent(self):
        """Quartiles surround the median in every month."""
        band = monthly_band(COCA)
        self.assertLessEqual(len(band), 12)
        self.assertEqual(list(band['mes']), sorted(band['mes']))
        self.assertTrue(((band['p25'] <= band['mediana']) &
                         (band['mediana'] <= band['p75'])).all())

    def test_network_table_keeps_gaps(self):
        """A month without collection stays empty, never zero."""
        table = network_by_month(COCA)
        self.assertLessEqual(len(table), 12)
        self.assertFalse((table.fillna(1) == 0).any().any())

    def test_category_is_ranked_by_unit_price(self):
        """Similars are sorted by price per litre and include the product."""
        similars = similar_unit_prices('Refrigerante 2 L')
        self.assertIn(COCA, set(similars['ean']))
        self.assertEqual(list(similars['preco_unidade']),
                         sorted(similars['preco_unidade']))
        self.assertTrue((similars['unidade'] == 'L').all())


if __name__ == '__main__':
    unittest.main()

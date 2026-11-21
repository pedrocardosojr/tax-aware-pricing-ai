"""Market aggregation, comparable samples and economic scenario contracts."""
from decimal import Decimal
import unittest

from tax_pricing.market_statistics import (
    comparable_matrix, paired_history, price_rank, summarize_quotes)


def quote(network, store, price, day='2026-10-01'):
    """Return an explicit regular observed quote for the selected SKU."""
    return {'ean': '7894900027013', 'date': day, 'network': network,
            'store': store, 'price': str(price), 'price_kind': 'regular'}


class MarketStatisticsTests(unittest.TestCase):
    """Keep store counts, network weights and comparable populations distinct."""

    def summary(self, rows):
        """Aggregate one declared SKU/date without automatic identity matching."""
        return summarize_quotes(rows, '7894900027013', '2026-10-01',
                                source='test fixture')

    def test_network_weight_is_independent_of_number_of_stores(self):
        """Three stores of one network must not dominate the main median."""
        rows = [quote('A', str(i), 10) for i in range(3)]
        rows += [quote('B', 'b', 20), quote('C', 'c', 30)]
        summary = self.summary(rows)
        self.assertEqual(summary['median'], Decimal('20'))
        self.assertEqual(summary['store_count'], 5)
        self.assertEqual(summary['network_count'], 3)
        self.assertEqual(summary['p25'], Decimal('15'))

    def test_duplicate_quote_is_not_an_additional_store(self):
        """Identical repeated rows have no additional statistical weight."""
        q = quote('A', 'a', 10)
        summary = self.summary([q, q])
        self.assertEqual(summary['store_count'], 1)
        self.assertEqual(summary['duplicate_count'], 1)

    def test_conflicting_store_quotes_are_not_silently_averaged(self):
        """The same store/date/SKU with different prices requires review."""
        with self.assertRaises(ValueError):
            self.summary([quote('A', 'a', 10), quote('A', 'a', 20)])

    def test_rank_keeps_ties_and_counts_explicit(self):
        """Equal values are ties, not evidence of a cheaper competitor."""
        snapshot = self.summary([quote('A', 'a', 10), quote('B', 'b', 12),
                                 quote('C', 'c', 14)])
        rank = price_rank(snapshot, Decimal('12'))
        self.assertEqual((rank['cheaper'], rank['equal'], rank['dearer']),
                         (1, 1, 1))

    def test_one_common_network_is_insufficient_for_paired_change(self):
        """Rotating the sample must not create a broad market growth claim."""
        rows = [quote(n, n, 10, '2026-09-01') for n in ('A', 'B', 'C')]
        rows += [quote(n, n, 12) for n in ('A', 'D', 'E')]
        last = paired_history(rows, '7894900027013', 'fixture')[-1]
        self.assertEqual(last['common_network_count'], 1)
        self.assertIsNone(last['paired_change_percent'])

    def test_pairing_requires_the_same_stores_not_only_network_names(self):
        """New branches do not count as repeated comparable establishments."""
        rows = [quote(n, n+'old', 10, '2026-09-01') for n in ('A', 'B', 'C')]
        rows += [quote(n, n+'new', 12) for n in ('A', 'B', 'C')]
        last = paired_history(rows, '7894900027013', 'fixture')[-1]
        self.assertEqual(last['common_network_count'], 0)
        self.assertIsNone(last['paired_change_percent'])

    def test_three_repeated_networks_produce_the_checked_change(self):
        """An adequate matched panel has a separately labeled change."""
        rows = [quote(n, n, 10, '2026-09-01') for n in ('A', 'B', 'C')]
        rows += [quote(n, n, 11) for n in ('A', 'B', 'C')]
        last = paired_history(rows, '7894900027013', 'fixture')[-1]
        self.assertEqual(last['paired_change_percent'], Decimal('10'))

    def test_group_contract_rejects_different_presentations(self):
        """A price heatmap must not silently join different product cohorts."""
        product = {'ean': 'a', 'group': 'Refri', 'type': 'cola', 'package': '2 L',
                   'description': 'A', 'date': '2026-10-01',
                   'kind': 'observed',
                   'median': '10', 'per_network_brl': {'X': '10'}}
        with self.assertRaises(ValueError):
            comparable_matrix([product, {**product, 'ean': 'b',
                                         'package': '350 ml'}])

    def test_heatmap_preserves_missing_cells(self):
        """No observation is a blank cell, never a zero price."""
        a = {'ean': 'a', 'group': 'Refri', 'type': 'cola', 'package': '2 L',
             'description': 'A', 'date': '2026-10-01',
             'kind': 'observed',
             'median': '10', 'per_network_brl': {'X': '10'}}
        b = {**a, 'ean': 'b', 'description': 'B', 'median': '12',
             'per_network_brl': {'Y': '12'}}
        matrix = comparable_matrix([a, b])
        self.assertIsNone(matrix['indices'][0][1])
        self.assertIsNone(matrix['indices'][1][0])
        self.assertEqual(matrix['common_basket_networks'], [])

    def test_missing_month_does_not_get_a_monthly_change(self):
        """Repeating stores after a gap do not imply a one-month price change."""
        rows = [quote(n, n, 10, '2026-08-01') for n in ('A', 'B', 'C')]
        rows += [quote(n, n, 11) for n in ('A', 'B', 'C')]
        last = paired_history(rows, '7894900027013', 'fixture')[-1]
        self.assertEqual(last['common_network_count'], 3)
        self.assertIsNone(last['paired_change_percent'])

    def test_period_uses_last_quote_per_store_and_preserves_date_range(self):
        """Multiple collection days do not create several historical months."""
        rows = [quote('A', 'a', 10, '2026-09-30'), quote('A', 'a', 11)]
        for row in rows:
            row['period'] = '2026-10'
        history = paired_history(rows, '7894900027013', 'fixture')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['median'], Decimal('11'))
        self.assertEqual(history[0]['store_count'], 1)

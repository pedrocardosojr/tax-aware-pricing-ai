"""Catalog contract tests."""
import json
from pathlib import Path
import tempfile
import unittest

from tax_pricing.catalog import load_catalog


class CatalogTests(unittest.TestCase):
    """Protect catalog expansion and uniqueness."""

    def test_catalog_is_not_limited_to_37_products(self):
        """Expanding to 50 is data input, with no pricing code change."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog.json'
            products = [{'ean': str(7890000000000 + i), 'ncm': '07133319'}
                        for i in range(50)]
            path.write_text(json.dumps({'products': products}))
            self.assertEqual(len(load_catalog(path)), 50)
            products.append(products[0])
            path.write_text(json.dumps({'products': products}))
            with self.assertRaises(ValueError):
                load_catalog(path)

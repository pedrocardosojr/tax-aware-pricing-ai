"""Load replaceable experimental catalogs without assuming a SKU count."""
import json
from pathlib import Path


def load_catalog(path: Path) -> list[dict[str, str]]:
    """Load products while rejecting duplicate EANs or malformed codes.

    Parameters
    ----------
    path : Path
        JSON with a products list; fiscal approval remains independent.

    Returns
    -------
    list
        Product dictionaries ready for explicit scenario construction.
    """
    products = json.loads(path.read_text())['products']
    if not isinstance(products, list) or not products:
        raise ValueError('Catalog must have a nonempty products list.')
    seen = set()
    for product in products:
        for field, lengths in (('ean', (8, 12, 13, 14)), ('ncm', (8,))):
            value = product.get(field)
            if (not isinstance(value, str) or not value.isascii()
                    or not value.isdigit() or len(value) not in lengths):
                raise ValueError(f'Invalid textual {field}.')
        if product['ean'] in seen:
            raise ValueError('Duplicate EAN in catalog.')
        seen.add(product['ean'])
    return products

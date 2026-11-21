"""Integrity and temporal checks for the isolated price experiments."""

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.benchmark_price_estimates import NUMERIC, panel
from scripts.pilot_description_prices import candidate_pairs, quantity
from scripts.pilot_daily_prices import (
    KEY,
    OUT,
    ROOT,
    additional_quotes,
    unique_quotes,
)


class ResearchTests(unittest.TestCase):
    """Protect source identity, missing store IDs and past-only features."""

    def test_description_guards_different_variant_and_volume(self) -> None:
        """Same brand cannot merge different pasta cuts, sugar or bottle."""
        catalog = pd.DataFrame(
            [
                {
                    "ean": "pasta",
                    "description": "MACARRAO COM OVOS PENA -ORQUIDEA -500 GR",
                    "group": "Macarrão",
                },
                {
                    "ean": "sugar",
                    "description": "ACUCAR REFINADO -UNIAO -5 KG",
                    "group": "Açúcar",
                },
                {
                    "ean": "cola",
                    "description": "REFRIGERANTE -COCA COLA -2 LITRO",
                    "group": "Refrigerante 2 L",
                },
                {
                    "ean": "milk",
                    "description": "LEITE LONGA VIDA INTEGRAL -TIROL -1 LITRO",
                    "group": "Leite",
                },
            ]
        )
        source = pd.DataFrame(
            [
                {
                    "id_produto": "1",
                    "descricao": (
                        "MACARRAO COM OVOS ESPAGUETE -ORQUIDEA -500 GR"
                    ),
                },
                {
                    "id_produto": "2",
                    "descricao": "ACUCAR CRISTAL -UNIAO -5 KG",
                },
                {
                    "id_produto": "3",
                    "descricao": "REFRIGERANTE -COCA COLA SEM ACUCAR -2 LITRO",
                },
                {
                    "id_produto": "4",
                    "descricao": "REFRIGERANTE -COCA COLA -600 ML",
                },
                {
                    "id_produto": "5",
                    "descricao": "REFRIGERANTE COCA COLA PET -2 LITRO",
                },
                {
                    "id_produto": "6",
                    "descricao": "LEITE PASTEURIZADO INTEGRAL -TIROL -1 LITRO",
                },
            ]
        )
        result = candidate_pairs(source, catalog)
        self.assertEqual(result.source_product_id.tolist(), ["5"])
        self.assertEqual(quantity("2 LITRO"), quantity("2000 ML"))
        self.assertNotEqual(quantity("1 KG"), quantity("1 LITRO"))

    def test_conflicting_key_is_excluded(self) -> None:
        """Exclude both prices when a source key has conflicting values."""
        data = pd.DataFrame(
            {
                "id_produto": ["a", "a", "b", "b"],
                "id_empresa": ["x", "x", "y", "y"],
                "endereco_completo": ["A", "A", "B", "B"],
                "data_pesquisa": ["2026-10-01"] * 4,
                "preco_regular": [4.0, 5.0, 6.0, 6.0],
            }
        )
        result, conflicts = unique_quotes(data)
        self.assertEqual(conflicts, 1)
        self.assertEqual(result.id_produto.tolist(), ["b"])

    def test_missing_store_id_still_matches_address(self) -> None:
        """A repeated null ID must not create an artificial new observation."""
        data = pd.DataFrame(
            {
                "id_produto": ["a", "a"],
                "id_empresa": [None, None],
                "endereco_completo": ["A", "B"],
                "data_pesquisa": ["2026-10-01"] * 2,
                "preco_regular": [4.0, 5.0],
            }
        )
        result = additional_quotes(data, data.iloc[:1])
        self.assertEqual(result.endereco_completo.tolist(), ["B"])

    def test_published_additions_are_disjoint_and_valid(self) -> None:
        """Keep real additions unique, positive and absent from old keys."""
        added = pd.read_parquet(OUT / "daily_added_exact_skus.parquet")
        old = pd.read_parquet(
            ROOT / "dados/clique_economia_mensal_2024_2026.parquet"
        )
        self.assertFalse(added.duplicated(KEY).any())
        self.assertTrue(added.merge(old[KEY], on=KEY).empty)
        self.assertTrue(np.isfinite(added.preco_regular).all())
        self.assertTrue(added.preco_regular.gt(0).all())
        self.assertTrue(added.date.between("2026-10-01", "2026-10-31").all())

    def test_future_prices_do_not_change_past_features(self) -> None:
        """Changing October prices cannot change October inputs or old rows."""
        original, _ = panel()
        raw = pd.read_parquet(
            ROOT / "dados/clique_economia_mensal_2024_2026.parquet"
        )
        prices = pd.to_numeric(raw.preco_regular, errors="coerce")
        raw["preco_regular"] = prices.where(
            raw["__mes"].lt("2026-10"), prices * 2
        )
        with patch(
            "scripts.benchmark_price_estimates.pd.read_parquet",
            return_value=raw,
        ):
            changed, _ = panel()
        columns = ["id_produto", "__mes"] + NUMERIC
        pd.testing.assert_frame_equal(original[columns], changed[columns])

    def test_published_predictions_train_before_target(self) -> None:
        """All methods use the same targets and strictly earlier training."""
        result = pd.read_csv(OUT / "model_predictions.csv")
        self.assertTrue((result.training_through < result.month).all())
        self.assertTrue(np.isfinite(result.estimated).all())
        self.assertTrue(result.estimated.gt(0).all())
        for _, phase in result.groupby("phase"):
            keys = [
                set(zip(group.id_produto, group.month))
                for _, group in phase.groupby("method")
            ]
            self.assertTrue(all(key == keys[0] for key in keys))


if __name__ == "__main__":
    unittest.main()

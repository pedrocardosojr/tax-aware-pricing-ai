"""Temporal pilot of monthly SKU forecasts, never new observed quotes."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pesquisas/ampliacao_modelos_2026-11-07"
KEY = ["id_produto", "id_empresa", "endereco_completo", "data_pesquisa"]
NUMERIC = [
    "log_lag1",
    "log_lag2",
    "log_lag3",
    "trend_log",
    "t",
    "sin_m",
    "cos_m",
]
CATEGORICAL = ["id_produto", "grupo"]


def panel() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reproduce exact-code cleaning and aggregate by network.

    Returns
    -------
    tuple
        Eligible monthly targets with past-only features, and source metadata.
    """
    path = ROOT / "dados/clique_economia_mensal_2024_2026.parquet"
    raw = pd.read_parquet(path)
    products = json.loads((ROOT / "dados/catalogo/skus_50.json").read_text())[
        "products"
    ]
    catalog: pd.DataFrame = pd.DataFrame(products).rename(
        columns={"ean": "id_produto", "group": "grupo"}
    )
    raw["preco_regular"] = pd.to_numeric(
        raw.preco_regular.astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    obs = raw[
        raw.id_produto.isin(catalog.id_produto) & (raw.preco_regular > 0)
    ]
    obs = obs.sort_values("__mes").drop_duplicates(KEY)
    net = obs.groupby(["id_produto", "__mes", "rede"]).preco_regular.median()
    monthly = (
        net.groupby(["id_produto", "__mes"])
        .agg(price="median", networks="size")
        .reset_index()
    )
    monthly = monthly[monthly.networks >= 3].merge(
        catalog.filter(items=["id_produto", "grupo"]), on="id_produto"
    )
    monthly = monthly.sort_values(["id_produto", "__mes"]).reset_index(
        drop=True
    )
    monthly["serial"] = pd.PeriodIndex(monthly["__mes"], freq="M").asi8
    group = monthly.groupby("id_produto")
    for lag in (1, 2, 3):
        monthly[f"lag{lag}"] = group.price.shift(lag)
        monthly[f"log_lag{lag}"] = np.log(monthly[f"lag{lag}"])
    monthly["prior_serial"] = group.serial.shift(1)
    monthly["mean3"] = group.price.transform(
        lambda s: s.shift(1).rolling(3).mean()
    )
    monthly["median3"] = group.price.transform(
        lambda s: s.shift(1).rolling(3).median()
    )
    monthly["trend_log"] = monthly.log_lag1 - monthly.log_lag3
    monthly["t"] = monthly.serial - monthly.serial.min()
    month_number = pd.to_datetime(monthly["__mes"]).dt.month
    monthly["sin_m"] = np.sin(2 * np.pi * month_number / 12)
    monthly["cos_m"] = np.cos(2 * np.pi * month_number / 12)
    possible_2026 = int((monthly["__mes"] >= "2026-01").sum())
    data = monthly.dropna(subset=NUMERIC + ["mean3", "median3"]).copy()
    data = data[data.serial - data.prior_serial == 1]
    assert len(obs) == 15739 and obs.id_produto.nunique() == 50
    return data, {
        "source_sha256": sha256(path.read_bytes()).hexdigest(),
        "clean_rows": len(obs),
        "monthly_observed_targets": len(monthly),
        "possible_2026_targets": possible_2026,
    }


def model(name: str) -> Pipeline:
    """Build a model with preprocessing fitted on past rows only.

    Parameters
    ----------
    name : str
        Ridge or random_forest selection from the fixed experiment design.

    Returns
    -------
    sklearn.pipeline.Pipeline
        Unfitted preprocessing and regression model.
    """
    transform = ColumnTransformer(
        [
            ("numbers", StandardScaler(), NUMERIC),
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL,
            ),
        ]
    )
    estimator = (
        Ridge(alpha=1.0)
        if name == "ridge"
        else RandomForestRegressor(
            n_estimators=120,
            max_depth=8,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=2,
        )
    )
    return make_pipeline(transform, estimator)


# Research orchestration keeps the measured stages visible together.
# pylint: disable=too-many-locals
def main() -> None:
    """Compare past-only baselines and models with a separate final window."""
    OUT.mkdir(parents=True, exist_ok=True)
    data, metadata = panel()
    records = []
    for month in sorted(
        data.loc[data["__mes"] >= "2026-01", "__mes"].unique()
    ):
        train = data[data["__mes"] < month]
        test = data[data["__mes"] == month]
        assert train["__mes"].max() < test["__mes"].min()
        predictions = {
            "last_month": test.lag1.to_numpy(),
            "mean_previous_3": test.mean3.to_numpy(),
            "median_previous_3": test.median3.to_numpy(),
        }
        for name in ("ridge", "random_forest"):
            fitted = model(name).fit(
                train[NUMERIC + CATEGORICAL], np.log(train.price)
            )
            predictions[name] = np.exp(
                fitted.predict(test[NUMERIC + CATEGORICAL])
            )
        for name, values in predictions.items():
            for row, value in zip(test.to_dict("records"), values):
                records.append(
                    {
                        "month": month,
                        "id_produto": row["id_produto"],
                        "grupo": row["grupo"],
                        "method": name,
                        "observed": row["price"],
                        "estimated": float(value),
                        "networks": row["networks"],
                        "phase": (
                            "development" if month <= "2026-06" else "holdout"
                        ),
                        "training_through": train["__mes"].max(),
                    }
                )
    predictions = pd.DataFrame(records)
    predictions["abs_error_brl"] = (
        predictions.estimated - predictions.observed
    ).abs()
    predictions["ape_percent"] = (
        predictions.abs_error_brl / predictions.observed * 100
    )
    per_sku = (
        predictions.groupby(["phase", "method", "id_produto"])
        .agg(
            mae_brl=("abs_error_brl", "mean"),
            mape_percent=("ape_percent", "mean"),
            evaluated_months=("month", "nunique"),
        )
        .reset_index()
    )
    summary = (
        per_sku.groupby(["phase", "method"])
        .agg(
            macro_mae_brl=("mae_brl", "mean"),
            macro_mape_percent=("mape_percent", "mean"),
            sku_count=("id_produto", "nunique"),
            sku_months=("evaluated_months", "sum"),
        )
        .reset_index()
    )
    dev = summary[summary.phase == "development"].sort_values(
        "macro_mape_percent"
    )
    winner = dev.iloc[0]["method"]
    holdout = summary[summary.phase == "holdout"].sort_values(
        "macro_mape_percent"
    )
    metadata.update(
        {
            "sklearn": sklearn.__version__,
            "protocol": "Expanding training; Jan-Jun 2026 development; "
            "Jul-Oct 2026 holdout. "
            "Targets: observed SKU monthly network medians, >=3 networks. "
            "Lag features use prior observations only; "
            "lag1 must be previous calendar month. "
            "Fixed model parameters; no random split or future-filled values.",
            "selected_on_development": winner,
            "holdout_results": holdout.to_dict("records"),
            "development_results": dev.to_dict("records"),
            "limitations": "Forecast of aggregate reference, not inference "
            "of individual store quotes, cold-start SKUs, "
            "9-month beer extrapolation or additional real observations.",
        }
    )
    predictions.to_csv(OUT / "model_predictions.csv", index=False)
    per_sku.to_csv(OUT / "model_metrics_by_sku.csv", index=False)
    summary.to_csv(OUT / "model_comparison.csv", index=False)
    (OUT / "model_summary.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(metadata, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

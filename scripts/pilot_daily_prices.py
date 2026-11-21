"""Bounded October pilot of Clique Economia; no alias inference."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import gettempdir
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pesquisas/ampliacao_modelos_2026-11-07"
CACHE = Path(gettempdir()) / "tax-pricing-review-20261107/daily"
URL = "https://dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia/"
KEY = ["id_produto", "id_empresa", "endereco_completo", "data_pesquisa"]


def download(name: str) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Cache a listed public file and record its size and hash.

    Parameters
    ----------
    name : str
        Data filename present in the public index.

    Returns
    -------
    tuple
        Parsed quotes (or None for empty files) and source manifest entry.
    """
    path = CACHE / name
    if not path.exists():
        response = requests.get(URL + name, timeout=40)
        response.raise_for_status()
        path.write_bytes(response.content)
    content = path.read_bytes()
    info = {
        "url": URL + name,
        "bytes": len(content),
        "sha256": sha256(content).hexdigest(),
    }
    if not content.strip():
        return None, {**info, "status": "empty"}
    try:
        data = pd.read_csv(
            BytesIO(content), sep=";", dtype=str, encoding="utf-8-sig"
        )
    except UnicodeError:
        data = pd.read_csv(
            BytesIO(content), sep=";", dtype=str, encoding="latin1"
        )
    data["source_file"] = name
    return data, {**info, "status": "read", "rows": len(data)}


def unique_quotes(selected: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove ambiguous quote keys before keeping a single copy.

    Parameters
    ----------
    selected : pandas.DataFrame
        Positive quotes with the four source identity columns.

    Returns
    -------
    tuple
        Unambiguous quotes and number of excluded conflicting keys.
    """
    conflicts = selected.groupby(KEY, dropna=False).preco_regular.nunique()
    bad = conflicts[conflicts > 1].reset_index()[KEY]
    if not bad.empty:
        selected = selected.merge(
            bad.assign(conflict=True), on=KEY, how="left"
        )
        selected = selected[selected.conflict.isna()].drop(columns="conflict")
    return selected.drop_duplicates(KEY), len(bad)


def additional_quotes(new: pd.DataFrame, old: pd.DataFrame) -> pd.DataFrame:
    """Return source keys absent from the baseline, including missing IDs.

    Parameters
    ----------
    new, old : pandas.DataFrame
        Unique quotes and baseline quotes, using the same key definition.

    Returns
    -------
    pandas.DataFrame
        New quotes; null store IDs match when address and other keys match.
    """
    merged = new.merge(
        old[KEY].assign(already_present=True), on=KEY, how="left"
    )
    return merged[merged.already_present.isna()].drop(
        columns="already_present"
    )


def coverage_shape(data: pd.DataFrame) -> dict[str, int]:
    """Measure temporal and store coverage without equating rows to stores.

    Parameters
    ----------
    data : pandas.DataFrame
        Source quotes with network names and establishment addresses.

    Returns
    -------
    dict
        Counts; network/address pairs are a store proxy, not verified IDs.
    """
    return {
        "rows": len(data),
        "products": data.id_produto.nunique(),
        "dates": data.data_pesquisa.nunique(),
        "source_network_names": data.rede.nunique(),
        "network_address_pairs": len(
            data[["rede", "endereco_completo"]].drop_duplicates()
        ),
        "product_network_address_pairs": len(
            data[["id_produto", "rede", "endereco_completo"]].drop_duplicates()
        ),
    }


# Research orchestration keeps the measured stages visible together.
# pylint: disable=too-many-locals
def main() -> None:
    """Measure positive exact-code additions against the monthly base.

    Returns
    -------
    None
        Write source manifest, additions and coverage in the research folder.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    index = requests.get(URL, timeout=30)
    index.raise_for_status()
    names = sorted(
        n
        for n in re.findall(r'href="([^"]+)"', index.text)
        if n.startswith("2026-10")
        and n.endswith("Cotacoes_-_Base_de_Dados.csv")
    )
    assert 1 <= len(names) <= 31
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(download, names))
    manifest = [info for _, info in results]
    daily = pd.concat(
        [d for d, _ in results if d is not None], ignore_index=True
    )
    products = json.loads((ROOT / "dados/catalogo/skus_50.json").read_text())[
        "products"
    ]
    catalog = pd.DataFrame(products)
    daily["preco_regular"] = pd.to_numeric(
        daily.preco_regular.str.replace(",", ".", regex=False), errors="coerce"
    )
    selected = daily[
        daily.id_produto.isin(catalog.ean)
        & (daily.preco_regular > 0)
        & np.isfinite(daily.preco_regular)
    ].copy()
    selected["date"] = pd.to_datetime(selected.data_pesquisa, errors="coerce")
    invalid_dates = int(selected.date.isna().sum())
    selected = selected[selected.date.notna()].copy()
    unique, conflicting_keys = unique_quotes(
        selected.sort_values("source_file")
    )
    old = pd.read_parquet(
        ROOT / "dados/clique_economia_mensal_2024_2026.parquet"
    )
    old["preco_regular"] = pd.to_numeric(
        old.preco_regular.astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    old = old[old.id_produto.isin(catalog.ean) & (old.preco_regular > 0)]
    old = old.sort_values("__mes").drop_duplicates(KEY)
    added = additional_quotes(unique, old)
    output = catalog[["ean", "description", "group"]].rename(
        columns={"ean": "id_produto"}
    )
    for label, data in [
        ("old_all_months", old),
        ("daily_pilot", unique),
        ("added", added),
    ]:
        counts = data.groupby("id_produto").agg(
            **{
                label + "_rows": ("preco_regular", "size"),
                label + "_networks": ("rede", "nunique"),
                label + "_dates": ("data_pesquisa", "nunique"),
            }
        )
        output = output.merge(counts, on="id_produto", how="left")
    old_oct = old[old["__mes"] == "2026-10"]
    combined_oct = pd.concat([old_oct, added], ignore_index=True)
    summary = {
        "source": URL,
        "scope": "October 2026 pilot; exact catalog codes only",
        "listed_files": len(names),
        "read_files": sum(m["status"] == "read" for m in manifest),
        "download_bytes": sum(m["bytes"] for m in manifest),
        "raw_rows": len(daily),
        "invalid_dates": invalid_dates,
        "conflicting_keys_excluded": conflicting_keys,
        "positive_selected_rows_before_dedup": len(selected),
        "unique_pilot_rows": len(unique),
        "distinct_pilot_dates": unique.data_pesquisa.nunique(),
        "old_october_rows": len(old_oct),
        "october_snapshot_coverage": coverage_shape(old_oct),
        "october_expanded_coverage": coverage_shape(combined_oct),
        "old_all_months_rows": len(old),
        "additional_unique_rows": len(added),
        "combined_rows": len(old) + len(added),
        "products_with_additions": added.id_produto.nunique(),
        "observation_date_min": str(unique.date.min().date()),
        "observation_date_max": str(unique.date.max().date()),
        "limitations": "One-month pilot, not full-history download; "
        "observed regular prices, "
        "not independent demand samples. Aliases remain pending team review.",
    }
    output.fillna(0).to_csv(OUT / "daily_coverage_by_sku.csv", index=False)
    added.to_parquet(OUT / "daily_added_exact_skus.parquet", index=False)
    for name, obj in [
        ("daily_summary.json", summary),
        ("daily_manifest.json", manifest),
    ]:
        (OUT / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

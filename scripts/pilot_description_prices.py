"""Generate review candidates using descriptions, never approve aliases."""

from decimal import Decimal
import json
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from scripts.pilot_daily_prices import (
    KEY,
    OUT,
    ROOT,
    additional_quotes,
    download,
    unique_quotes,
)

GROUP_WORDS = {
    "Arroz": "ARROZ",
    "Feijão": "FEIJAO",
    "Macarrão": "MACARRAO",
    "Açúcar": "ACUCAR",
    "Café": "CAFE",
    "Refrigerante 2 L": "REFRIGERANTE",
    "Creme dental": "CREME DENTAL",
    "Sabonete": "SABONETE",
    "Água mineral": "AGUA MINERAL",
    "Leite": "LEITE",
    "Óleo de soja": "OLEO DE SOJA",
    "Cerveja": "CERVEJA",
}
VARIANTS = (
    "ZERO ALCOOL",
    "SEM ACUCAR",
    "EXTRA FORTE",
    "SUBZERO",
    "ORIGINAL",
    "PARBOILIZADO",
    "POLIDO",
    "PRETO",
    "CARIOCA",
    "SEMIDESNATADO",
    "DESNATADO",
    "INTEGRAL",
    "REFINADO",
    "CRISTAL",
    "PENA",
    "ESPAGUETE",
    "PARAFUSO",
    "NINHO",
    "CONCHINHA",
    "FITILHOS DE OURO",
    "COM GAS",
    "SEM GAS",
    "PASTEURIZADO",
    "LONGA VIDA",
)


def normalize(text: pd.Series) -> pd.Series:
    """Normalize spelling while retaining words and numeric attributes.

    Parameters
    ----------
    text : pandas.Series
        Original descriptions.

    Returns
    -------
    pandas.Series
        Accent-free uppercase words with standard whitespace.
    """
    return (
        text.fillna("")
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
        .str.upper()
        .str.replace(r"[^A-Z0-9.,]+", " ", regex=True)
        .str.replace(r"\bPENNE\b", "PENA", regex=True)
        .str.strip()
    )


def quantity(text: str) -> tuple[str, Decimal] | None:
    """Extract the final explicit weight or volume without guessing units.

    Parameters
    ----------
    text : str
        Normalized product description or package.

    Returns
    -------
    tuple or None
        Dimension and quantity in grams or millilitres; None if absent.
    """
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(LITROS?|KG|ML|GR|G|L)\b", text)
    if not matches:
        return None
    number, unit = matches[-1]
    amount = Decimal(number.replace(",", "."))
    if unit in ("KG", "L", "LITRO", "LITROS"):
        amount *= 1000
    return ("weight" if unit in ("KG", "GR", "G") else "volume", amount)


# Ranking retains intermediate source attributes for the review report.
# pylint: disable=too-many-locals
def candidate_pairs(
    descriptions: pd.DataFrame,
    catalog: pd.DataFrame,
) -> pd.DataFrame:
    """Rank only same-brand, same-quantity, non-conflicting candidates.

    Parameters
    ----------
    descriptions : pandas.DataFrame
        Unique source code/description pairs outside selected catalogue IDs.
    catalog : pandas.DataFrame
        Selected products, including brand in the source description.

    Returns
    -------
    pandas.DataFrame
        Review queue. No similarity score constitutes identity approval.
    """
    source = descriptions.copy().reset_index(drop=True)
    source["normalized"] = normalize(source.descricao)
    targets = normalize(catalog.description)
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    features = vectorizer.fit_transform(
        pd.concat([targets, source.normalized], ignore_index=True)
    )
    scores = cosine_similarity(
        features[len(targets) :], features[: len(targets)]
    )
    records = []
    target_info = []
    for target_index, product in catalog.iterrows():
        target = targets.iloc[target_index]
        brand = normalize(pd.Series([product.description.split("-")[1]]))
        target_info.append(
            (target_index, product, target, brand.iloc[0], quantity(target))
        )
    for index, row in source.iterrows():
        source_quantity = quantity(row.normalized)
        for (
            target_index,
            product,
            target,
            brand,
            target_quantity,
        ) in target_info:
            if not re.search(r"\b" + re.escape(brand) + r"\b", row.normalized):
                continue
            if GROUP_WORDS[product["group"]] not in row.normalized:
                continue
            if source_quantity != target_quantity:
                continue
            if target_quantity is None:
                continue
            if any(
                bool(re.search(r"\b" + word + r"\b", row.normalized))
                != bool(re.search(r"\b" + word + r"\b", target))
                for word in VARIANTS
            ):
                continue
            records.append(
                {
                    "source_product_id": row.id_produto,
                    "source_description": row.descricao,
                    "catalog_id": product.ean,
                    "catalog_description": product.description,
                    "tfidf_cosine": float(scores[index, target_index]),
                    "status": "candidate_requires_identity_and_package_review",
                }
            )
    return pd.DataFrame(
        records,
        columns=[
            "source_product_id",
            "source_description",
            "catalog_id",
            "catalog_description",
            "tfidf_cosine",
            "status",
        ],
    )


# Keep the measured stages of the isolated experiment visible together.
# pylint: disable=too-many-locals
def main() -> None:
    """Compare description recovery in old snapshots and the daily pilot."""
    catalog = pd.DataFrame(
        json.loads((ROOT / "dados/catalogo/skus_50.json").read_text())[
            "products"
        ]
    )
    old = pd.read_parquet(
        ROOT / "dados/clique_economia_mensal_2024_2026.parquet"
    )
    old["origin"] = "monthly"
    frames = []
    for entry in json.loads((OUT / "daily_manifest.json").read_text()):
        frame, _ = download(entry["url"].rsplit("/", 1)[-1])
        if frame is not None:
            frames.append(frame)
    daily = pd.concat(frames, ignore_index=True)
    daily["origin"] = "daily"
    all_quotes = pd.concat([old, daily], ignore_index=True)
    all_quotes["preco_regular"] = pd.to_numeric(
        all_quotes.preco_regular.astype(str).str.replace(
            ",", ".", regex=False
        ),
        errors="coerce",
    )
    all_quotes = all_quotes[all_quotes.preco_regular.gt(0)].copy()
    outside = all_quotes[~all_quotes.id_produto.isin(catalog.ean)]
    pairs = candidate_pairs(
        outside[["id_produto", "descricao"]].drop_duplicates(), catalog
    )
    candidates = outside.rename(
        columns={
            "id_produto": "source_product_id",
            "descricao": "source_description",
        }
    ).merge(pairs, on=["source_product_id", "source_description"])
    ambiguity = pairs.groupby(
        ["source_product_id", "source_description"]
    ).catalog_id.nunique()
    # Exclude source descriptions with more than one possible target.
    ambiguous = ambiguity[ambiguity.gt(1)].reset_index()
    candidates = candidates.merge(
        ambiguous[["source_product_id", "source_description"]].assign(
            ambiguous=True
        ),
        on=["source_product_id", "source_description"],
        how="left",
    )
    candidates = candidates[candidates.ambiguous.isna()].copy()
    candidates["id_produto"] = candidates.catalog_id
    baseline = all_quotes[all_quotes.id_produto.isin(catalog.ean)]
    baseline = baseline.drop_duplicates(KEY)
    stats = []
    for origin, frame in candidates.groupby("origin"):
        unique, conflicts = unique_quotes(frame)
        novel = additional_quotes(unique, baseline)
        stats.append(
            {
                "origin": origin,
                "candidate_rows": len(frame),
                "unique_candidate_keys": len(unique),
                "conflicting_keys_excluded": conflicts,
                "potential_additional_keys": len(novel),
                "products": novel.id_produto.nunique(),
            }
        )
    pairs.to_csv(OUT / "description_candidate_pairs.csv", index=False)
    candidates.to_parquet(
        OUT / "description_candidate_quotes.parquet", index=False
    )
    result = {
        "method": "TF-IDF char 3-5 ranking after brand, quantity, group and "
        "explicit variant guards; no automatic identity approval.",
        "comparison": "Potential additions against exact-code monthly plus "
        "daily observations, excluding same-store/date overlap.",
        "ambiguous_source_descriptions": len(ambiguous),
        "stats": stats,
        "limitations": "Candidates only. Packaging and source code reuse need "
        "team review. This does not replace Rodrigo mappings.",
    }
    (OUT / "description_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    print(pairs.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()

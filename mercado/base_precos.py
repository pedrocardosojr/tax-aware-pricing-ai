"""Limpeza da base de precos do Clique Economia para os SKUs do catalogo.

Regras (verificadas em 07/11/2026 sobre os 50 SKUs do catalogo):
1. Filtro: preco_regular > 0 (preco zerado = condicao inexistente, nao e preco).
2. Deduplicacao pela chave id_produto + id_empresa + endereco_completo + data_pesquisa,
   mantendo a linha do primeiro arquivo (__mes mais antigo). Nos 281 pares encontrados,
   todos os precos (regular, promocao, fidelidade, atacado, atacado_qtd) eram identicos
   e os arquivos eram consecutivos.
3. __mes e o eixo da serie (cada arquivo e uma rodada de coleta de 0 a 1 dia);
   data_pesquisa e a data real da observacao.
4. Meses de cobertura = __mes distintos apos deduplicar. Nao usar contagem de datas.
5. Exclusoes por produto diferente sob o mesmo EAN: Sorriso 90 GR gravado no EAN do
   Sorriso 70 g (7891528029498), 9 linhas em 2026-05.
"""
from pathlib import Path

import pandas as pd

CHAVE_DUP = ["id_produto", "id_empresa", "endereco_completo", "data_pesquisa"]
EXCLUSOES = [("7891528029498", r"90\s*GR")]


def carregar_base(caminho: str = "dados/clique_economia_mensal_2024_2026.parquet") -> pd.DataFrame:
    """Le o parquet, mantem codigos como texto e converte preco_regular para numero."""
    raw = pd.read_parquet(Path(caminho))
    raw["id_produto"] = raw["id_produto"].astype(str)
    raw["preco_regular"] = pd.to_numeric(
        raw["preco_regular"].astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )
    return raw


def carregar_catalogo(
    caminho_37: str = "dados/ncm_rastreabilidade_37.csv",
    caminho_13: str = "dados/catalogo_expansao_13.csv",
) -> pd.DataFrame:
    """Une os 37 SKUs originais e os 13 da expansao (colunas grupo, id_produto, descricao)."""
    c37 = pd.read_csv(caminho_37, dtype=str)
    c13 = pd.read_csv(caminho_13, dtype=str)
    cols = ["grupo", "id_produto", "descricao"]
    return pd.concat([c37[cols], c13[cols]], ignore_index=True)


def limpar(raw: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:
    """Vinculo exato por EAN, preco regular positivo, deduplicacao e exclusoes.

    Retorna observacoes unicas.
    """
    x = raw[raw["id_produto"].isin(catalogo["id_produto"])]
    pos = x[x["preco_regular"] > 0].copy()
    for ean, padrao in EXCLUSOES:
        desc = pos["descricao"].astype(str).str.upper()
        fora = (pos["id_produto"] == ean) & desc.str.contains(padrao, regex=True, na=False)
        pos = pos[~fora]
    pos["data"] = pd.to_datetime(pos["data_pesquisa"], errors="coerce")
    unicas = pos.sort_values("__mes").drop_duplicates(CHAVE_DUP, keep="first")
    return unicas.merge(catalogo[["id_produto", "grupo"]], on="id_produto", how="left")


if __name__ == "__main__":
    base = carregar_base()
    cat = carregar_catalogo()
    obs = limpar(base, cat)
    print("observacoes unicas:", len(obs))

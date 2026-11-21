"""Referencia do Cafe Pilao 500 g sem e com as coletas diarias de outubro.

Loja = endereco_completo; rodada = __mes (no diario, mes da data real, adaptacao de teste).
Um ponto por loja por mes, mediana por loja, IC95% por bootstrap com semente fixa.
Le o diario versionado em pesquisas/ e grava dados/pilao_sem_e_com_diario.csv.
"""
import zlib
import numpy as np
import pandas as pd
from mercado.base_precos import carregar_base, carregar_catalogo, limpar

EAN = "7896089011357"
DIARIO = "pesquisas/ampliacao_modelos_2026-11-07/daily_added_exact_skus.parquet"
SAIDA = "dados/pilao_sem_e_com_diario.csv"
REGRA = ("loja=endereco_completo; mes=__mes na base mensal e mes da data real no diario; "
         "1 ponto por loja por mes (mediana das coletas do mes); mediana por loja")
COLS = ["__mes", "endereco_completo", "rede", "data_coleta", "preco_regular"]

base = limpar(carregar_base(), carregar_catalogo())
m = base[base["id_produto"] == EAN].copy()
m["data_coleta"] = pd.to_datetime(m["data_pesquisa"])
m = m[COLS].copy()
m["camada"] = "mensal"

d = pd.read_parquet(DIARIO)
d = d[(d["id_produto"].astype(str) == EAN) & (d["preco_regular"] > 0)].copy()
d["__mes"] = d["date"].dt.strftime("%Y-%m")
d["data_coleta"] = d["date"]
d = d[COLS].copy()
d["camada"] = "diario"

def ic(dados, n_meses):
    """Mediana por loja, P25-P75, IC95% da mediana e cobertura nos ultimos n_meses."""
    meses = sorted(dados["__mes"].unique())[-n_meses:]
    w = dados[dados["__mes"].isin(meses)]
    por_loja = (w.groupby(["__mes", "endereco_completo"])["preco_regular"].median()
                 .groupby("endereco_completo").median())
    v = por_loja.to_numpy()
    rng = np.random.default_rng(zlib.crc32(EAN.encode()))
    boot = [np.median(rng.choice(v, len(v))) for _ in range(1000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    med = float(np.median(v))
    return {"janela_meses": n_meses, "mes_ini": meses[0], "mes_fim": meses[-1],
            "lojas": len(v), "mediana_loja": round(med, 2),
            "p25": round(float(np.percentile(v, 25)), 2),
            "p75": round(float(np.percentile(v, 75)), 2),
            "ic_lo": round(float(lo), 2), "ic_hi": round(float(hi), 2),
            "largura_pct": round((hi - lo) / med * 100, 2),
            "observacoes": len(w),
            "coletas_datas": int(w["data_coleta"].nunique()),
            "redes": int(w["rede"].nunique()),
            "ultima_coleta": w["data_coleta"].max().date().isoformat(),
            "regra_loja_mes": REGRA}

linhas = []
for nome, df in [("sem_diario", m), ("com_diario", pd.concat([m, d]))]:
    for n in (3, 6):
        r = ic(df, n)
        r["cenario"] = nome
        linhas.append(r)
out = pd.DataFrame(linhas)[["cenario", "janela_meses", "mes_ini", "mes_fim", "lojas",
                            "mediana_loja", "p25", "p75", "ic_lo", "ic_hi", "largura_pct",
                            "observacoes", "coletas_datas", "redes", "ultima_coleta",
                            "regra_loja_mes"]]
out.to_csv(SAIDA, index=False)
print(out.drop(columns=["regra_loja_mes"]).to_string(index=False))

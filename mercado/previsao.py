"""Previsão do preço do mês seguinte por rede: modelo híbrido do notebook 04.

Regra do modelo híbrido:
- a rede tinha preço do produto no mês anterior -> repete esse preço;
- não tinha -> regressão Ridge: referência de mercado do mês anterior
  ajustada pelo nível típico do produto, do grupo e da rede.

O script refaz a avaliação do notebook (validação mai-jul, teste ago-out/2026,
bootstrap por loja) na base mensal complementada pelo diário de outubro,
treina com todos os meses e grava a previsão do mês
seguinte à última rodada. A aba "Previsão" do app só lê o JSON gerado.

Uso: python -m mercado.previsao
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from mercado.exportar_cafe import bases

SAIDA = Path("evidencias/previsao_2026-11-14/previsao.json")
CATEGORIAS = ["id_produto", "grupo", "rede"]
ETAPAS = {"validacao": ("2026-04", "2026-07"), "teste": ("2026-07", "2026-10")}
ALPHA = 1.0
SEMENTE = 42


def tabela_mensal(obs):
    """Uma linha por loja e mês, com a referência e o preço da rede do mês anterior."""
    loja = (obs.groupby(["id_produto", "grupo", "rede", "endereco_completo", "__mes"],
                        as_index=False)["preco_regular"].median())
    meses = sorted(loja["__mes"].unique())
    loja["mes_ant"] = loja["__mes"].map(dict(zip(meses[1:], meses[:-1])))

    por_rede = (loja.groupby(["id_produto", "rede", "__mes"])["preco_regular"]
                .median().rename("preco_rede_ant").reset_index())
    ref = (por_rede.groupby(["id_produto", "__mes"])["preco_rede_ant"].median()
           .rename("ref_produto_ant").reset_index())

    tab = (loja.merge(ref.rename(columns={"__mes": "mes_ant"}),
                      on=["id_produto", "mes_ant"], how="left")
           .merge(por_rede.rename(columns={"__mes": "mes_ant"}),
                  on=["id_produto", "rede", "mes_ant"], how="left"))
    tab = tab.dropna(subset=["ref_produto_ant"]).copy()
    tab["rede_tinha_preco"] = tab["preco_rede_ant"].notna().astype(int)
    tab["preco_rede_ant"] = tab["preco_rede_ant"].fillna(tab["ref_produto_ant"])
    for coluna, origem in (("log_preco", "preco_regular"),
                           ("log_ref_ant", "ref_produto_ant"),
                           ("log_rede_ant", "preco_rede_ant")):
        tab[coluna] = np.log(tab[origem])
    return tab, por_rede, ref


class NivelRede:
    """Ridge com one-hot de produto, grupo e rede + log da referência anterior.

    Mesma conta do Ridge do scikit-learn (intercepto sem penalidade), feita com
    numpy para não acrescentar dependência ao projeto.
    """

    def __init__(self, alpha=ALPHA):
        self.alpha = alpha
        self.colunas = []
        self.coef = np.zeros(0)
        self.media_x = np.zeros(0)
        self.intercepto = 0.0

    def _matriz(self, df):
        """One-hot das categorias conhecidas no treino; categoria nova vira zeros."""
        dummies = pd.get_dummies(df[CATEGORIAS].astype(str), dtype=float)
        dummies["log_ref_ant"] = df["log_ref_ant"].to_numpy()
        if not self.colunas:
            self.colunas = list(dummies.columns)
        return dummies.reindex(columns=self.colunas, fill_value=0.0).to_numpy()

    def fit(self, df, alvo):
        """Resolve (X'X + alpha I) b = X'y com X e y centrados."""
        self.colunas = []
        x = self._matriz(df)
        y = np.asarray(alvo, dtype=float)
        self.media_x = x.mean(axis=0)
        xc = x - self.media_x
        penal = self.alpha * np.eye(xc.shape[1])
        self.coef = np.linalg.solve(xc.T @ xc + penal, xc.T @ (y - y.mean()))
        self.intercepto = float(y.mean() - self.media_x @ self.coef)
        return self

    def predict(self, df):
        """Log do preço previsto."""
        return self._matriz(df) @ self.coef + self.intercepto


def hibrido(treino, alvo_df):
    """Preço da rede quando existe; nível da rede quando não existe (em log)."""
    modelo = NivelRede().fit(treino, treino["log_preco"])
    return np.where(alvo_df["rede_tinha_preco"] == 1, alvo_df["log_rede_ant"],
                    modelo.predict(alvo_df))


def metricas(log_real, log_prev):
    """MAE em reais, MdAPE e % de previsões com erro de até 5%."""
    real, prev = np.exp(np.asarray(log_real)), np.exp(np.asarray(log_prev))
    erro_pct = np.abs(prev / real - 1) * 100
    return {"mae_brl": round(float(np.mean(np.abs(prev - real))), 3),
            "mdape_pct": round(float(np.median(erro_pct)), 2),
            "erro_ate_5_pct": round(float(np.mean(erro_pct <= 5) * 100), 1)}


def avaliar(tab, fim_treino, fim_aval):
    """Baselines e híbrido num corte temporal: treino até fim_treino."""
    treino = tab[tab["__mes"] <= fim_treino]
    aval = tab[(tab["__mes"] > fim_treino) & (tab["__mes"] <= fim_aval)]
    y = aval["log_preco"]
    return aval, [
        {"modelo": "baseline 1: referência do mês anterior",
         **metricas(y, aval["log_ref_ant"])},
        {"modelo": "baseline 2: preço da rede no mês anterior",
         **metricas(y, aval["log_rede_ant"])},
        {"modelo": "híbrido", **metricas(y, hibrido(treino, aval))},
    ]


def bootstrap_ganho(tab, fim_treino, n=2000):
    """Ganho do híbrido sobre o baseline 2 (p.p. de erro), IC 95% sorteando lojas."""
    aval = tab[tab["__mes"] > fim_treino].copy()
    real = np.exp(aval["log_preco"])
    prev = np.exp(hibrido(tab[tab["__mes"] <= fim_treino], aval))
    aval["ganho"] = ((np.exp(aval["log_rede_ant"]) / real - 1).abs() * 100
                     - (prev / real - 1).abs() * 100)
    por_loja = aval.groupby("endereco_completo")["ganho"].agg(["sum", "count"])
    lojas = por_loja.index.to_numpy()
    rng = np.random.default_rng(SEMENTE)
    amostras = []
    for _ in range(n):
        sorteio = por_loja.loc[rng.choice(lojas, len(lojas), replace=True)]
        amostras.append(sorteio["sum"].sum() / sorteio["count"].sum())
    baixo, alto = np.percentile(amostras, [2.5, 97.5])
    return {"ganho_medio_pp": round(float(aval["ganho"].mean()), 2),
            "ic95_pp": [round(float(baixo), 2), round(float(alto), 2)],
            "linhas_melhor_pct": round(float((aval["ganho"] > 0).mean() * 100), 1),
            "linhas_iguais_pct": round(float((aval["ganho"] == 0).mean() * 100), 1),
            "linhas_pior_pct": round(float((aval["ganho"] < 0).mean() * 100), 1),
            "reamostragens": n, "semente": SEMENTE}


def mes_seguinte(mes):
    """'2026-10' -> '2026-11'; '2026-12' -> '2027-01'."""
    ano, numero = map(int, mes.split("-"))
    return f"{ano + numero // 12}-{numero % 12 + 1:02d}"


def _base_previsao(obs, por_rede, ref, ultimo):
    """Redes vistas nos últimos 6 meses, com a referência e o preço da rede no mês base."""
    recentes = sorted(obs["__mes"].unique())[-6:]
    base = (obs[obs["__mes"].isin(recentes)][["id_produto", "grupo", "rede"]]
            .drop_duplicates()
            .merge(ref[ref["__mes"] == ultimo], on="id_produto", how="inner")
            .merge(por_rede.loc[por_rede["__mes"] == ultimo,
                                ["id_produto", "rede", "preco_rede_ant"]],
                   on=["id_produto", "rede"], how="left"))
    base["log_ref_ant"] = np.log(base["ref_produto_ant"])
    return base


def previsoes(tab, por_rede, ref, obs):
    """Preço previsto por rede para o mês seguinte à última rodada."""
    ultimo = sorted(obs["__mes"].unique())[-1]
    base = _base_previsao(obs, por_rede, ref, ultimo)
    tem_preco = base["preco_rede_ant"].notna()
    nivel = np.exp(NivelRede().fit(tab, tab["log_preco"]).predict(base))
    base["previsto"] = np.where(tem_preco, base["preco_rede_ant"], nivel)
    base["origem"] = np.where(tem_preco, "preco_rede", "nivel_rede")

    resultado = {}
    for ean, sku in base.groupby("id_produto"):
        resultado[str(ean)] = {
            "mes_base": ultimo, "mes_previsto": mes_seguinte(ultimo),
            "referencia_mes_base": round(float(sku["ref_produto_ant"].iloc[0]), 2),
            "mediana_prevista": round(float(sku["previsto"].median()), 2),
            "redes": [{"rede": r.rede, "previsto": round(float(r.previsto), 2),
                       "origem": r.origem,
                       "preco_mes_base": (None if pd.isna(r.preco_rede_ant)
                                          else round(float(r.preco_rede_ant), 2))}
                      for r in sku.sort_values("previsto").itertuples()]}
    return resultado


def segmentos(tab, fim_treino):
    """Teste separado por rede com e sem preço no mês anterior."""
    treino = tab[tab["__mes"] <= fim_treino]
    aval = tab[tab["__mes"] > fim_treino].assign(prev=lambda d: hibrido(treino, d))
    linhas = []
    for flag, parte in aval.groupby("rede_tinha_preco"):
        linhas.append({"rede_tinha_preco": bool(flag), "linhas": len(parte),
                       "baseline_2": metricas(parte["log_preco"], parte["log_rede_ant"]),
                       "hibrido": metricas(parte["log_preco"], parte["prev"])})
    return linhas


def gerar(obs, commit):
    """Monta o conteúdo do JSON lido pela aba Previsão."""
    tab, por_rede, ref = tabela_mensal(obs)
    avaliacao = {etapa: avaliar(tab, *cortes)[1] for etapa, cortes in ETAPAS.items()}
    return {
        "schema_version": 1,
        "metodo": ("híbrido: preço da rede no mês anterior quando existe; "
                   "senão Ridge (alpha=1) com produto, grupo, rede e log da referência"),
        "fonte": f"Clique Economia (mensal + diário de outubro); mercado/previsao.py@{commit}",
        "cortes": {etapa: {"treino_ate": t, "avaliacao_ate": a}
                   for etapa, (t, a) in ETAPAS.items()},
        "avaliacao": avaliacao,
        "segmentos_teste": segmentos(tab, ETAPAS["teste"][0]),
        "bootstrap_teste": bootstrap_ganho(tab, ETAPAS["teste"][0]),
        "previsoes": previsoes(tab, por_rede, ref, obs),
    }


def main():
    """Gera evidencias/previsao_2026-11-14/previsao.json."""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    obs = bases()["mensal_diario"]
    conteudo = gerar(obs, commit)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    for etapa, linhas in conteudo["avaliacao"].items():
        print(etapa)
        print(pd.DataFrame(linhas).to_string(index=False))
    print("bootstrap:", conteudo["bootstrap_teste"])
    print(len(conteudo["previsoes"]), "SKUs com previsão ->", SAIDA)


if __name__ == "__main__":
    main()

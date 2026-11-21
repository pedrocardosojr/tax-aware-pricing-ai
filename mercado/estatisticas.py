"""Estatísticas de mercado sobre a base limpa (obs) de mercado.base_precos.
Responsável: Edu. Regras de limpeza e vínculo ficam em base_precos.py (Rodrigo)."""

import zlib
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Regra:
    """Parâmetros do método, iguais para todos os SKUs.

    n_rodadas: tamanho da janela; camada: camada de dados aceita;
    min_redes: mínimo de redes para cobertura_ok.
    """
    n_rodadas: int = 3
    camada: str = "observado"
    min_redes: int = 3


PADRAO = Regra()


def reais(valor):
    """Arredonda dinheiro em 2 casas, meio centavo para cima (12,235 -> 12,24).

    round(..., 6) remove o ruído de ponto flutuante antes do Decimal:
    24.065 calculado vira 24.064999999999998 e seria arredondado para baixo.
    """
    limpo = Decimal(str(round(float(valor), 6)))
    return float(limpo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def referencia_mercado(obs, id_produto, mes_final, regra=PADRAO):
    """Referência de mercado de um SKU numa janela de rodadas que termina em mes_final.

    Regras:
    - cada loja vale um valor por rodada (mediana das coletas dela), para coletas
      diárias não darem peso extra a quem foi visitado várias vezes;
    - mediana por rede, depois entre redes: cada rede vale um voto;
    - status diz se houve coleta na rodada final ou só em rodadas anteriores.
    """
    base = obs
    if "camada" in obs.columns:
        base = obs[obs["camada"] == regra.camada]

    rodadas = sorted(obs["__mes"].unique())
    if mes_final not in rodadas:
        raise ValueError(f"rodada {mes_final} não existe na base")
    fim = rodadas.index(mes_final)
    janela = rodadas[max(0, fim - regra.n_rodadas + 1): fim + 1]

    sel = base[(base["id_produto"] == id_produto) & (base["__mes"].isin(janela))]
    if sel.empty:
        raise LookupError(f"sem observações de {id_produto} em {janela}")

    # 1. uma observação por loja por rodada
    por_loja = (sel.groupby(["rede", "endereco_completo", "__mes"], as_index=False)["preco_regular"]
                   .median())
    # 2. mediana por rede, depois entre redes
    por_rede = por_loja.groupby("rede")["preco_regular"].median()

    coletado_no_final = bool((sel["__mes"] == mes_final).any())
    return {
        "id_produto": id_produto,
        "janela": janela,
        "camada": regra.camada,
        "mediana": reais(por_rede.median()),
        "p25": reais(por_rede.quantile(0.25)),
        "p75": reais(por_rede.quantile(0.75)),
        "n_obs": len(sel),
        "n_obs_loja_rodada": len(por_loja),
        "n_lojas": sel["endereco_completo"].nunique(),
        "n_redes": len(por_rede),
        "ultima_obs": sel["data"].max().strftime("%Y-%m-%d"),
        "ultima_rodada_com_coleta": sel["__mes"].max(),
        "coleta_na_rodada_final": coletado_no_final,
        "status": "atual" if coletado_no_final else "recente_sem_coleta_final",
        "cobertura_ok": len(por_rede) >= regra.min_redes,
        "precos_por_rede": {rede: reais(v) for rede, v in por_rede.items()},
    }


def historico_referencia(obs, id_produto, regra=PADRAO):
    """Uma linha por rodada: a referência da janela móvel que termina nela.
    Rodada sem observação do produto vira lacuna (NaN), nunca zero."""
    linhas = []
    for mes in sorted(obs["__mes"].unique()):
        try:
            r = referencia_mercado(obs, id_produto, mes, regra)
            linhas.append({"mes": mes, "mediana": r["mediana"], "p25": r["p25"], "p75": r["p75"],
                           "n_lojas": r["n_lojas"], "n_redes": r["n_redes"],
                           "cobertura_ok": r["cobertura_ok"]})
        except LookupError:
            linhas.append({"mes": mes, "mediana": None, "p25": None, "p75": None,
                           "n_lojas": 0, "n_redes": 0, "cobertura_ok": False})
    return pd.DataFrame(linhas).set_index("mes")


def similares(obs, id_produto, mes_final, regra=PADRAO):
    """Referência de todos os SKUs do mesmo grupo, com índice base 100 no SKU escolhido."""
    grupo = obs.loc[obs["id_produto"] == id_produto, "grupo"].iloc[0]
    ids_grupo = obs.loc[obs["grupo"] == grupo, "id_produto"].unique()

    linhas = []
    for pid in ids_grupo:
        try:
            r = referencia_mercado(obs, pid, mes_final, regra)
        except LookupError:
            continue  # SKU sem preço na janela: fica fora da comparação
        descricao = obs.loc[obs["id_produto"] == pid, "descricao"].mode().iloc[0]
        linhas.append({"id_produto": pid, "descricao": descricao, "mediana": r["mediana"],
                       "p25": r["p25"], "p75": r["p75"], "n_redes": r["n_redes"],
                       "cobertura_ok": r["cobertura_ok"]})

    tabela = pd.DataFrame(linhas).set_index("id_produto")
    if id_produto not in tabela.index:
        raise LookupError(f"{id_produto} sem preço na janela que termina em {mes_final}")
    base = tabela.loc[id_produto, "mediana"]
    tabela["indice"] = (tabela["mediana"] / base * 100).round(0).astype(int)
    tabela["escolhido"] = tabela.index == id_produto
    return tabela.sort_values("mediana", ascending=False)


def referencia_com_status(obs, id_produto, mes_final, regra=PADRAO):
    """Como referencia_mercado, mas nunca falha por falta de dado recente:
    - 'atual' / 'recente_sem_coleta_final': janela que termina em mes_final;
    - 'historica': janela que termina na última rodada em que o SKU foi coletado;
    - 'ausente': o SKU nunca foi coletado até mes_final."""
    try:
        return referencia_mercado(obs, id_produto, mes_final, regra)
    except LookupError:
        base = obs[obs["camada"] == regra.camada] if "camada" in obs.columns else obs
        meses = sorted(base.loc[base["id_produto"] == id_produto, "__mes"].unique())
        anteriores = [m for m in meses if m <= mes_final]
        if not anteriores:
            return {"id_produto": id_produto, "status": "ausente", "camada": regra.camada}
        r = referencia_mercado(obs, id_produto, anteriores[-1], regra)
        r["status"] = "historica"
        return r


def referencia_loja_e_rede(obs, id_produto, janela):
    """Mesma cadeia nas duas unidades: loja-mês -> loja -> rede.

    Cada loja vale um voto dentro da rede, mesmo pesquisada em vários meses.
    """
    sel = obs[(obs["id_produto"] == id_produto) & (obs["__mes"].isin(janela))]
    if sel.empty:
        raise LookupError(f"{id_produto} sem observação na janela {janela}")

    loja_mes = sel.groupby(["rede", "endereco_completo", "__mes"])["preco_regular"].median()
    por_loja = loja_mes.groupby(level=["rede", "endereco_completo"]).median()
    por_rede = por_loja.groupby(level="rede").median()

    def resumo(precos):
        """Mediana e quartis, em reais, de uma série de preços."""
        p25, p50, p75 = precos.quantile([0.25, 0.5, 0.75])
        return {"mediana": reais(p50), "p25": reais(p25), "p75": reais(p75)}

    return {
        "janela": list(janela),
        "n_obs": len(sel),
        "n_lojas": len(por_loja),
        "n_redes": len(por_rede),
        "ultima_obs": sel["data"].max().strftime("%Y-%m-%d"),
        "por_loja": resumo(por_loja),
        "por_rede": resumo(por_rede),
        "precos_por_rede": {rede: reais(v) for rede, v in por_rede.items()},
    }


def ic95_mediana_lojas(obs, id_produto, janela, reamostragens=1000):
    """IC95% da mediana por loja, por bootstrap de lojas (comparativo do Rodrigo).

    Mesma conta de mercado/pilao_referencia.py: um preço por loja e mês
    (mediana das coletas), mediana por loja, 1000 sorteios de lojas com
    reposição e semente fixa pelo EAN. largura_pct = (sup - inf) / mediana * 100.
    """
    sel = obs[(obs["id_produto"] == id_produto) & (obs["__mes"].isin(janela))]
    if sel.empty:
        raise LookupError(f"{id_produto} sem observação na janela {janela}")
    valores = (sel.groupby(["__mes", "endereco_completo"])["preco_regular"].median()
               .groupby("endereco_completo").median().to_numpy())
    rng = np.random.default_rng(zlib.crc32(id_produto.encode()))
    medianas = [np.median(rng.choice(valores, len(valores))) for _ in range(reamostragens)]
    inferior, superior = np.percentile(medianas, [2.5, 97.5])
    return {"ic_inf": reais(inferior), "ic_sup": reais(superior),
            "largura_pct": round(float((superior - inferior) / np.median(valores) * 100), 2)}

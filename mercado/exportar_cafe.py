"""Exporta o Café Pilão 500 g, mensal e mensal + diário, no mesmo recorte.

Uso: python -m mercado.exportar_cafe
"""
import json
import subprocess
from pathlib import Path

import pandas as pd

from mercado.base_precos import carregar_base, carregar_catalogo, limpar
from mercado.estatisticas import referencia_loja_e_rede

EAN = "7896089011357"
JANELA = ["2026-08", "2026-09", "2026-10"]
DIARIO = "pesquisas/ampliacao_modelos_2026-11-07/daily_added_exact_skus.parquet"
SAIDA = Path("evidencias/cafe_pilao_2026-11-14")


def bases():
    """Mesma limpeza do Rodrigo nas duas bases; no diário, rodada = mês da data real."""
    catalogo = carregar_catalogo()
    mensal = carregar_base().assign(origem="mensal")
    diario = carregar_base(DIARIO).assign(origem="diario")
    diario["__mes"] = pd.to_datetime(diario["data_pesquisa"]).dt.strftime("%Y-%m")
    return {
        "mensal": limpar(mensal, catalogo),
        "mensal_diario": limpar(pd.concat([mensal, diario], ignore_index=True), catalogo),
    }


def payload(r, cenario, commit):
    """Formato por loja do adaptador do Pedro: cartão por loja, pontos por rede."""
    reference = {
        "id_produto": EAN, "camada": "observado", "janela": r["janela"],
        "aggregation": "median_across_stores",
        **r["por_loja"],
        "n_obs": r["n_obs"], "n_lojas": r["n_lojas"], "n_redes": r["n_redes"],
        "ultima_obs": r["ultima_obs"], "cobertura_ok": r["n_redes"] >= 3,
    }
    return {
        "cenario": cenario,
        "reference": reference,
        "per_network_brl": r["precos_por_rede"],
        "por_rede": r["por_rede"],
        "source": (f"Clique Economia ({cenario}); janela {r['janela'][0]}..{r['janela'][-1]}; "
                   f"loja-mes -> loja -> rede; mercado/estatisticas.py@{commit}"),
    }


def main():
    """Gera os dois JSONs e o resumo.csv; o commit atual entra no source."""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    SAIDA.mkdir(parents=True, exist_ok=True)
    linhas = []
    for cenario, obs in bases().items():
        r = referencia_loja_e_rede(obs, EAN, JANELA)
        (SAIDA / f"{cenario}.json").write_text(
            json.dumps(payload(r, cenario, commit), ensure_ascii=False, indent=2) + "\n")
        for unidade in ("por_loja", "por_rede"):
            linhas.append({"cenario": cenario, "unidade": unidade, **r[unidade],
                           "n_obs": r["n_obs"], "n_lojas": r["n_lojas"],
                           "n_redes": r["n_redes"], "ultima_obs": r["ultima_obs"]})
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(SAIDA / "resumo.csv", index=False)
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    main()

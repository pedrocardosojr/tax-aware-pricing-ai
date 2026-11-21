"""Exporta a referência dos 50 SKUs no formato por loja do app (PR #26).

Base: mensal + diário de outubro, limpos por mercado/base_precos.py
(mercado.exportar_cafe.bases). Loja = endereco_completo; no diário, a rodada
é o mês real da coleta.

Janela por SKU (comparativo do Rodrigo, IC95% da mediana sorteando lojas):
- referência atual começa em 3 meses (ago-out/2026); largura <= 10% -> 3 meses;
- senão testa 6 meses (mai-out/2026); largura <= 10% -> 6 meses;
- senão "baixa_precisao", adotando 3 meses (o recorte mais recente);
- SKU sem coleta em ago-out/2026 -> "historica": 3 meses que terminam na
  última coleta real, com essa data em ultima_obs.

Uso, na raiz do projeto:
    python -m mercado.exportar
"""
import json
import subprocess
from pathlib import Path

import pandas as pd

from mercado.base_precos import carregar_catalogo
from mercado.estatisticas import ic95_mediana_lojas, referencia_loja_e_rede
from mercado.exportar_cafe import bases

FIM = "2026-10"
LIMITE_PCT = 10.0
SAIDA = Path("evidencias/referencias_edu_2026-11-10")


def janela(fim, meses):
    """Meses do calendário que terminam em fim: janela('2026-10', 3) -> ago..out."""
    return [p.strftime("%Y-%m") for p in pd.period_range(end=fim, periods=meses, freq="M")]


def escolher(obs, ean):
    """Aplica a regra de janela a um SKU e devolve janela, status e os ICs avaliados."""
    meses_sku = sorted(obs.loc[(obs["id_produto"] == ean) & (obs["__mes"] <= FIM),
                               "__mes"].unique())
    if not meses_sku:
        return {"status": "ausente", "motivo": f"sem coleta até {FIM}", "ics": {}}
    if meses_sku[-1] < janela(FIM, 3)[0]:
        recorte = janela(meses_sku[-1], 3)
        return {"status": "historica", "janela": recorte, "meses": 3,
                "motivo": f"última coleta em {meses_sku[-1]}",
                "ics": {3: ic95_mediana_lojas(obs, ean, recorte)}}
    ics = {3: ic95_mediana_lojas(obs, ean, janela(FIM, 3))}
    if ics[3]["largura_pct"] <= LIMITE_PCT:
        return {"status": "atual", "janela": janela(FIM, 3), "meses": 3, "motivo": "",
                "ics": ics}
    ics[6] = ic95_mediana_lojas(obs, ean, janela(FIM, 6))
    if ics[6]["largura_pct"] <= LIMITE_PCT:
        return {"status": "atual", "janela": janela(FIM, 6), "meses": 6, "motivo": "",
                "ics": ics}
    return {"status": "baixa_precisao", "janela": janela(FIM, 3), "meses": 3,
            "motivo": "IC95% acima de 10% com 3 e 6 meses; adotado o recorte de 3 meses",
            "ics": ics}


def payload(ean, ref, source):
    """JSON por SKU no formato de evidencias/cafe_pilao_2026-11-14/mensal_diario.json."""
    reference = {
        "id_produto": ean, "camada": "observado", "janela": ref["janela"],
        "aggregation": "median_across_stores", **ref["por_loja"],
        "n_obs": ref["n_obs"], "n_lojas": ref["n_lojas"], "n_redes": ref["n_redes"],
        "ultima_obs": ref["ultima_obs"], "cobertura_ok": ref["n_redes"] >= 3,
    }
    return {"reference": reference, "per_network_brl": ref["precos_por_rede"],
            "por_rede": ref["por_rede"], "source": source}


def linha_status(produto, escolha, ref, source):
    """Uma linha do status_50.csv: janela escolhida, cobertura e os ICs avaliados."""
    linha = {"id_produto": produto.id_produto, "descricao": produto.descricao,
             "grupo": produto.grupo, "status": escolha["status"],
             "janela_meses": escolha.get("meses"), "motivo": escolha["motivo"]}
    if ref is not None:
        linha.update({"mes_ini": ref["janela"][0], "mes_fim": ref["janela"][-1],
                      "ultima_obs": ref["ultima_obs"], "n_lojas": ref["n_lojas"],
                      "n_redes": ref["n_redes"], "n_obs": ref["n_obs"],
                      **ref["por_loja"], "cobertura_ok": ref["n_redes"] >= 3})
    for meses in (3, 6):
        ic = escolha["ics"].get(meses, {})
        linha.update({f"ic{meses}_inf": ic.get("ic_inf"), f"ic{meses}_sup": ic.get("ic_sup"),
                      f"ic{meses}_largura_pct": ic.get("largura_pct")})
    linha["source"] = source
    return linha


def exportar(obs, catalogo, commit):
    """Grava saida/inputs/<ean>.json e saida/status_50.csv; devolve o status."""
    (SAIDA / "inputs").mkdir(parents=True, exist_ok=True)
    linhas = []
    for produto in catalogo.sort_values("id_produto").itertuples():
        escolha = escolher(obs, produto.id_produto)
        ref, source = None, ""
        if escolha["status"] != "ausente":
            ref = referencia_loja_e_rede(obs, produto.id_produto, escolha["janela"])
            source = (f"Clique Economia (mensal + diário); janela {ref['janela'][0]}.."
                      f"{ref['janela'][-1]}; loja-mes -> loja -> rede; "
                      f"status {escolha['status']}; mercado/exportar.py@{commit}")
            (SAIDA / "inputs" / f"{produto.id_produto}.json").write_text(
                json.dumps(payload(produto.id_produto, ref, source),
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        linhas.append(linha_status(produto, escolha, ref, source))
    status = pd.DataFrame(linhas)
    status.to_csv(SAIDA / "status_50.csv", index=False)
    return status


def main():
    """Exporta o lote e resume quantos SKUs ficaram em cada situação."""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    status = exportar(bases()["mensal_diario"], carregar_catalogo(), commit)
    resumo = status["status"] + " " + status["janela_meses"].astype("Int64").astype(str)
    print(resumo.str.replace(" <NA>", "").value_counts().to_string())
    print(f"{len(list((SAIDA / 'inputs').glob('*.json')))} arquivos em {SAIDA / 'inputs'}")


if __name__ == "__main__":
    main()

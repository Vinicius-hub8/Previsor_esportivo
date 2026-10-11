#!/usr/bin/env python3
"""Roda o modelo da NBA e grava web/public/dados/nba.json (mesmo formato do nfl.json, com pequenas extensões)."""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import previsor_nba as N

RAIZ = Path(__file__).resolve().parent
CURTO = {"Play-in": "PI", "Primeira rodada": "R1", "Semifinais de conferência": "R2",
         "Finais de conferência": "R3", "Finais da NBA": "Final", "Playoffs": "PO"}
CHAVE_FASE = {"Play-in": "PI", "Primeira rodada": "R1", "Semifinais de conferência": "R2",
              "Finais de conferência": "R3", "Finais da NBA": "F", "Playoffs": "PO"}
FAIXAS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def agrupar(sub):
    """Divide a temporada em 'semanas' (seg-dom) na fase regular, mais Play-in e cada rodada dos playoffs.
    Devolve {chave: info} e {game_id: chave}."""
    reg = sub[sub["tipo"] == "REG"]
    inicio = pd.to_datetime(reg["dia"]).dt.to_period("W-SUN").dt.start_time
    ordem = {d: i + 1 for i, d in enumerate(sorted(inicio.unique()))}  # numeração corrida (pula a semana do All-Star)
    chave_de = {gid: str(ordem[d]) for gid, d in zip(reg["game_id"], inicio)}
    grupos = {}
    for k in sorted(set(chave_de.values()), key=int):
        grupos[k] = {"rotulo": f"Semana {k}", "curto": k, "tipo": "REG", "jogos": []}
    for g in sub[sub["tipo"] != "REG"].itertuples():
        k = CHAVE_FASE.get(g.rodada, "PO")
        chave_de[g.game_id] = k
        grupos.setdefault(k, {"rotulo": g.rodada, "curto": CURTO.get(g.rodada, "PO"), "tipo": g.tipo, "jogos": []})
    return grupos, chave_de


def main(saida=None, temporadas=2):
    saida = Path(saida) if saida else RAIZ / "web" / "public" / "dados" / "nba.json"
    saida.parent.mkdir(parents=True, exist_ok=True)

    S = N.construir(N.carregar())
    jg, bt, atual = S["jogos"], S["bt"].set_index("game_id"), S["atual"]
    hoje = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")

    out = {"meta": {}, "times": {}, "semanas": {}, "projecoes": {}}
    semana_de = {}
    chave_atual = rotulo_atual = None

    # --- Jogos por semana (temporada atual e anterior) -------------------------
    for temp in range(atual, atual - temporadas, -1):
        sub = jg[jg["season"] == temp].sort_values(["dt", "game_id"])
        if sub.empty:
            continue
        grupos, chave_de = agrupar(sub)
        fut = N.prever_futuros(S, sub[~sub["jogado"]])
        fut_p = dict(zip(fut["game_id"], fut["p"])) if len(fut) else {}
        for g in sub.itertuples():
            item = {"id": str(g.game_id), "data": g.dia, "hora": g.hora if isinstance(g.hora, str) else None,
                    "v": g.v, "m": g.m, "spread": None, "linha": False,
                    "placar": [int(g.pts_v), int(g.pts_m)] if g.jogado else None,
                    "p": None, "ok": None, "elo": int(round(g.dif_elo)), "pf": None,
                    # [visitante, mandante]: saldo médio dos últimos jogos, quantos jogos entraram, dias de descanso
                    "forma": [r(g.a_forma, 1), r(g.h_forma, 1)], "nj": [int(g.a_nf), int(g.h_nf)], "desc": [int(g.a_desc), int(g.h_desc)]}
            if g.jogado and g.game_id in bt.index:
                item["p"] = r(bt.loc[g.game_id, "p"])
                item["ok"] = bool(bt.loc[g.game_id, "ok"])
            elif not g.jogado and g.game_id in fut_p:
                item["p"] = r(fut_p[g.game_id])
            grupos[chave_de[g.game_id]]["jogos"].append(item)
        out["semanas"][str(temp)] = grupos
        if temp == atual:
            semana_de = {gid: int(k) for gid, k in chave_de.items() if k.isdigit()}
            prox = sub[sub["dia"] >= hoje]
            chave_atual = chave_de[(prox.iloc[0] if len(prox) else sub.iloc[-1])["game_id"]]
            rotulo_atual = grupos[chave_atual]["rotulo"]

    # --- Times: metadados, forma recente, Elo, acerto histórico ------------------
    ids = {**dict(zip(jg["id_m"], jg["m"])), **dict(zip(jg["id_v"], jg["v"]))}
    elo_sigla = {ids[i]: e for i, e in S["elo"].items() if i in ids}
    rank = {t: i + 1 for i, (t, _) in enumerate(sorted(elo_sigla.items(), key=lambda x: -x[1]))}
    ref = S["bt"][S["bt"]["season"] >= N.ANOS_REF[0]]
    jogados = jg[jg["jogado"]]
    for t, (nome, apelido, conf, div) in N.TIMES.items():
        ult = jogados[(jogados["m"] == t) | (jogados["v"] == t)].tail(5)
        forma = ["V" if ((g.pts_m > g.pts_v) == (g.m == t)) else "D" for g in ult.itertuples()]
        b = ref[(ref["m"] == t) | (ref["v"] == t)]
        out["times"][t] = {"nome": nome, "apelido": apelido, "conf": conf, "div": div,
                           "elo": r(elo_sigla.get(t), 0), "elo_rank": rank.get(t), "forma": forma,
                           "acc": r(b["ok"].mean()), "acc_n": int(len(b))}

    # --- Projeção de recorde (temporada regular atual) ----------------------------
    for t in N.TIMES:
        p = N.projecao(S, t)
        if not p["n_rest"]:
            out["projecoes"][t] = {"v": p["v"], "d": p["d"], "e": 0, "n_rest": 0, "n_sem_data": 0, "dist": [], "jogos": []}
            continue
        fut = p["fut"].sort_values("dt")
        out["projecoes"][t] = {
            "v": p["v"], "d": p["d"], "e": 0, "n_rest": p["n_rest"], "n_sem_data": p["n_sem_data"],
            "esperado": r(p["esperado"], 1), "moda": [p["v"] + p["moda"], p["d"] + p["n_rest"] - p["moda"]],
            "faixa": [p["v"] + p["lo"], p["v"] + p["hi"]], "dist": [r(x, 4) for x in p["dist"]],
            "jogos": [{"sem": semana_de.get(g.game_id), "data": g.dia, "casa": g.m == t,
                       "adv": g.v if g.m == t else g.m, "p": r(g.p_time), "linha": False} for g in fut.itertuples()],
        }

    # --- Simulação da temporada: classificação, play-in, playoffs e título ---------
    sim = N.simular(S)
    out["simulacao"] = {
        "n": sim["n"],
        "times": {s: {"v": r(sim["v"][i], 1), **{k: r(sim[k][i], 3) for k in ("dir", "playin", "pof", "r2", "r3", "fin", "tit")}}
                  for i, s in enumerate(sim["siglas"])},
    }

    # --- Meta -----------------------------------------------------------------
    conf = ref[["p", "ok"]].assign(c=lambda d: d["p"].where(d["p"] >= 0.5, 1 - d["p"]))
    faixas = []
    for lo, hi in FAIXAS:
        x = conf[(conf["c"] >= lo) & (conf["c"] < hi)]
        faixas.append({"de": lo, "ate": min(hi, 1.0), "n": int(len(x)), "acc": r(x["ok"].mean())})
    out["meta"] = {
        "esporte": "NBA", "temporada": atual, "temporada_rotulo": N.rotulo_temporada(atual),
        "rotulos_temporada": {str(t): N.rotulo_temporada(int(t)) for t in out["semanas"]},
        "semana_atual": chave_atual, "semana_rotulo": rotulo_atual,
        "atualizado": date.today().isoformat(), "usa_linha": False,
        "acc": r(S["acc"]), "acc_mandante": r(S["acc_mandante"]), "n_ref": S["n_ref"], "faixas": faixas,
        "anos_ref": [N.rotulo_temporada(N.ANOS_REF[0]), N.rotulo_temporada(N.ANOS_REF[1])],
        "acc_temporada": r(S["acc_atual"]), "n_temporada": S["n_atual"],
        "fonte": "hoopR / ESPN (dados abertos)", "avisos": N.AVISOS,
        "grupos": [f"{c} {d}" for c in ("Leste", "Oeste") for d in
                   {"Leste": ("Atlântico", "Central", "Sudeste"), "Oeste": ("Noroeste", "Pacífico", "Sudoeste")}[c]],
    }

    with open(saida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK:", saida, f"({saida.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main(*(sys.argv[1:2]))

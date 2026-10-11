#!/usr/bin/env python3
"""Gera web/public/dados/nfl.json a partir do modelo (previsor_nfl.py) para alimentar o site."""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import previsor_nfl as P

TIMES = {
    "ARI": ("Arizona Cardinals", "NFC", "Oeste"), "ATL": ("Atlanta Falcons", "NFC", "Sul"),
    "BAL": ("Baltimore Ravens", "AFC", "Norte"), "BUF": ("Buffalo Bills", "AFC", "Leste"),
    "CAR": ("Carolina Panthers", "NFC", "Sul"), "CHI": ("Chicago Bears", "NFC", "Norte"),
    "CIN": ("Cincinnati Bengals", "AFC", "Norte"), "CLE": ("Cleveland Browns", "AFC", "Norte"),
    "DAL": ("Dallas Cowboys", "NFC", "Leste"), "DEN": ("Denver Broncos", "AFC", "Oeste"),
    "DET": ("Detroit Lions", "NFC", "Norte"), "GB": ("Green Bay Packers", "NFC", "Norte"),
    "HOU": ("Houston Texans", "AFC", "Sul"), "IND": ("Indianapolis Colts", "AFC", "Sul"),
    "JAX": ("Jacksonville Jaguars", "AFC", "Sul"), "KC": ("Kansas City Chiefs", "AFC", "Oeste"),
    "LA": ("Los Angeles Rams", "NFC", "Oeste"), "LAC": ("Los Angeles Chargers", "AFC", "Oeste"),
    "LV": ("Las Vegas Raiders", "AFC", "Oeste"), "MIA": ("Miami Dolphins", "AFC", "Leste"),
    "MIN": ("Minnesota Vikings", "NFC", "Norte"), "NE": ("New England Patriots", "AFC", "Leste"),
    "NO": ("New Orleans Saints", "NFC", "Sul"), "NYG": ("New York Giants", "NFC", "Leste"),
    "NYJ": ("New York Jets", "AFC", "Leste"), "PHI": ("Philadelphia Eagles", "NFC", "Leste"),
    "PIT": ("Pittsburgh Steelers", "AFC", "Norte"), "SEA": ("Seattle Seahawks", "NFC", "Oeste"),
    "SF": ("San Francisco 49ers", "NFC", "Oeste"), "TB": ("Tampa Bay Buccaneers", "NFC", "Sul"),
    "TEN": ("Tennessee Titans", "AFC", "Sul"), "WAS": ("Washington Commanders", "NFC", "Leste"),
}
ROTULO_FASE = {"WC": "Wild Card", "DIV": "Divisional", "CON": "Final de conferência", "SB": "Super Bowl"}


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


RAIZ = Path(__file__).resolve().parent


def main(saida=None, temporadas=2):
    saida = Path(saida) if saida else RAIZ / "web" / "public" / "dados" / "nfl.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    S = P.construir(P.carregar())
    jogos, bt, modelo = S["jogos"], S["bt"].set_index("game_id"), S["modelo"].set_index("game_id")
    atual = S["atual"]
    prox_sem = P._proxima_semana(S)

    out = {
        "meta": {
            "esporte": "NFL", "temporada": atual, "semana_atual": prox_sem,
            "atualizado": date.today().isoformat(),
            "acc_com_linha": r(S["acc_full"]), "acc_sem_linha": r(S["acc_base"]),
            "anos_ref": list(S["anos_ref"]),
            "acc_temporada": r(S["acc_atual"]), "n_temporada": S["n_atual"],
            "fonte": "nflverse (dados abertos)",
        },
        "times": {}, "semanas": {}, "projecoes": {},
    }

    # --- Jogos por semana (temporada atual e anterior) -------------------------
    for temp in range(atual, atual - temporadas, -1):
        sub = jogos[jogos["season"] == temp].sort_values("gameday")
        fut = P.prever_futuros(S, sub[sub["home_score"].isna()])
        fut_i = fut.set_index("game_id") if len(fut) else None
        sem_dict = {}
        for g in sub.itertuples():
            jogado = pd.notna(g.home_score)
            item = {
                "id": g.game_id, "espn": str(int(g.espn)) if pd.notna(g.espn) else None, "data": g.gameday.strftime("%Y-%m-%d"), "hora": g.gametime if isinstance(g.gametime, str) else None,
                "v": g.away_team, "m": g.home_team, "spread": r(g.spread_line, 1),
                "placar": [int(g.away_score), int(g.home_score)] if jogado else None,
                "p": None, "linha": bool(pd.notna(g.spread_line)), "ok": None,
                "elo": None, "pf": None,
            }
            if jogado:
                if g.game_id in bt.index:
                    p = float(bt.loc[g.game_id, "p_full"])
                    item["p"] = r(p)
                    if g.home_score != g.away_score:
                        item["ok"] = bool((p >= .5) == (g.home_score > g.away_score))
                if g.game_id in modelo.index:
                    m = modelo.loc[g.game_id]
                    item["elo"] = r(m["dif_elo"], 0)
                    item["pf"] = [r(m["a_pf"], 1), r(m["a_pa"], 1), r(m["h_pf"], 1), r(m["h_pa"], 1)]
            elif fut_i is not None and g.game_id in fut_i.index:
                f = fut_i.loc[g.game_id]
                item["p"] = r(f["prob_casa"])
                item["linha"] = bool(f["tem_linha"])
                item["elo"] = r(f["dif_elo"], 0)
                u = S["ult"]
                if g.away_team in u.index and g.home_team in u.index:
                    item["pf"] = [r(u.loc[g.away_team, "pf"], 1), r(u.loc[g.away_team, "pa"], 1),
                                  r(u.loc[g.home_team, "pf"], 1), r(u.loc[g.home_team, "pa"], 1)]
            sem_dict.setdefault(str(int(g.week)), {"rotulo": ROTULO_FASE.get(g.game_type, f"Semana {int(g.week)}"),
                                                    "tipo": g.game_type, "jogos": []})["jogos"].append(item)
        out["semanas"][str(temp)] = sem_dict

    # --- Times: metadados, forma recente, Elo, acerto histórico ------------------
    elo_rank = {t: i + 1 for i, (t, _) in enumerate(sorted(S["elo"].items(), key=lambda x: -x[1]))}
    bt_j = S["bt"].merge(jogos[["game_id", "home_team", "away_team"]], on="game_id")
    bt_j = bt_j[bt_j["season"] >= 2016]
    jogados = jogos.dropna(subset=["home_score"]).sort_values("gameday")
    for t, (nome, conf, div) in TIMES.items():
        mt = jogados[(jogados["home_team"] == t) | (jogados["away_team"] == t)].tail(5)
        forma = []
        for g in mt.itertuples():
            meu, opp = (g.home_score, g.away_score) if g.home_team == t else (g.away_score, g.home_score)
            forma.append("V" if meu > opp else ("D" if meu < opp else "E"))
        b = bt_j[(bt_j["home_team"] == t) | (bt_j["away_team"] == t)]
        out["times"][t] = {
            "nome": nome, "apelido": nome.split()[-1] if t not in ("LA", "LAC") else nome.replace("Los Angeles ", ""),
            "conf": conf, "div": div, "elo": r(S["elo"].get(t), 0), "elo_rank": elo_rank.get(t),
            "forma": forma, "acc": r(b["ac_full"].mean()), "acc_n": int(len(b)),
        }

    # --- Projeção de recorde de cada time (temporada regular atual) -------------
    reg = jogos[(jogos["season"] == atual) & (jogos["game_type"] == "REG")]
    for t in TIMES:
        todos = reg[(reg["home_team"] == t) | (reg["away_team"] == t)]
        jog, resta = todos[todos["home_score"].notna()], todos[todos["home_score"].isna()].sort_values("gameday")
        v = d = e = 0
        for g in jog.itertuples():
            meu, opp = (g.home_score, g.away_score) if g.home_team == t else (g.away_score, g.home_score)
            v += meu > opp; d += meu < opp; e += meu == opp
        fut = P.prever_futuros(S, resta).dropna(subset=["prob_casa"]) if len(resta) else resta
        if len(fut):
            fut = fut.assign(p_time=np.where(fut["home_team"] == t, fut["prob_casa"], 1 - fut["prob_casa"]))
            dist = P._dist_vitorias(fut["p_time"].values)
            cum = np.cumsum(dist)
            lo, hi = int(np.searchsorted(cum, 0.10)), int(np.searchsorted(cum, 0.90))
            moda = int(np.argmax(dist))
            esperado = v + float((np.arange(len(dist)) * dist).sum())
            jg = [{"sem": int(g.week), "data": g.gameday.strftime("%Y-%m-%d"),
                   "casa": g.home_team == t, "adv": g.away_team if g.home_team == t else g.home_team,
                   "p": r(g.p_time), "linha": bool(g.tem_linha)} for g in fut.itertuples()]
            out["projecoes"][t] = {
                "v": int(v), "d": int(d), "e": int(e), "n_rest": len(fut),
                "esperado": r(esperado, 1), "moda": [int(v + moda), int(d + len(fut) - moda)],
                "faixa": [int(v + lo), int(v + hi)], "dist": [r(x, 4) for x in dist], "jogos": jg,
            }
        else:
            out["projecoes"][t] = {"v": int(v), "d": int(d), "e": int(e), "n_rest": 0, "dist": [], "jogos": []}

    with open(saida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK:", saida, f"({len(json.dumps(out)) / 1024:.0f} KB)")


if __name__ == "__main__":
    main(*(sys.argv[1:2]))

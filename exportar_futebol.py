#!/usr/bin/env python3
"""Roda o modelo de futebol e grava, em web/public/dados/:
     futebol.json            (resumo das ligas, usado na página inicial)
     futebol/<liga>.json     (uma por liga: jogos por rodada, tabela atual, tabela prevista)
Se uma liga falhar (ex.: sem internet), o JSON antigo dela é mantido e as outras seguem."""
import json
import sys
import traceback
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import noticias
import previsor_futebol as F

RAIZ = Path(__file__).resolve().parent
PASTA = RAIZ / "web" / "public" / "dados"
FAIXAS = [(0.33, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 1.01)]


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def rotulo_temp(d_atual):
    return d_atual["temp"].iloc[0]


def rodada_atual(cur, hoje_br):
    """Rodada que está acontecendo ou a próxima: a de data mediana mais perto de hoje, sem olhar para trás mais que 2 dias."""
    meds = cur.groupby("rodada")["dia_br"].apply(lambda s: pd.to_datetime(s).sort_values().iloc[len(s) // 2])
    alvo = pd.Timestamp(hoje_br) - pd.Timedelta(days=2)
    futuras = meds[meds >= alvo]
    return int(futuras.index[0]) if len(futuras) else int(meds.index[-1])


def exportar_liga(lid, pasta):
    cfg = F.LIGAS[lid]
    hoje_br = pd.Timestamp.now(tz=F.TZ_BR).strftime("%Y-%m-%d")
    S = F.montar(lid)
    d, bt = S["d"], S["bt"]
    cur = d[d["ano"] == S["atual"]].copy()
    rot = rotulo_temp(cur)
    acc = F.resumo_acuracia(S)

    # --- times -------------------------------------------------------------------
    tab = F.tabela_atual(S, cfg)
    nomes = [L["t"] for L in tab]
    usadas = {}
    cod = {n: F.sigla(n, usadas) for n in sorted(nomes)}
    elo = {n: S["elo"].get(n, F.ELO_INICIAL) for n in nomes}
    rank_elo = {n: i + 1 for i, n in enumerate(sorted(nomes, key=lambda n: -elo[n]))}
    times = {cod[L["t"]]: {"nome": L["t"], "elo": r(elo[L["t"]], 0), "elo_rank": rank_elo[L["t"]], "forma": L["forma"]} for L in tab}

    # --- jogos por rodada ----------------------------------------------------------
    fut = F.prever_jogos(S, cur[~cur["jogado"]])
    fut_i = {i: g for i, g in zip(fut.index, fut.itertuples())}
    bt_i = {i: g for i, g in zip(bt.index, bt.itertuples())} if len(bt) else {}
    rodadas = {}
    cur["_h"] = cur["hora_br"].fillna("99:99")
    for i, g in cur.sort_values(["rodada", "dia_br", "_h", "casa"]).iterrows():
        item = {"id": f"{lid}-{g.rodada}-{cod[g.casa]}-{cod[g.fora]}", "d": g.dia_br, "h": g.hora_br, "c": cod[g.casa], "f": cod[g.fora],
                "pl": [int(g.gc), int(g.gf)] if g.jogado else None, "p": None, "g": None, "es": None, "ok": None}
        if g.adiado and not g.jogado:
            item["adiado"] = True
        if not g.jogado:
            nt = noticias.para_json(S["adj"], [(cod[g.casa], g.casa, g.dia_br), (cod[g.fora], g.fora, g.dia_br)])
            if nt:
                item["nt"] = nt
        src = bt_i.get(i) if g.jogado else fut_i.get(i)
        if src is not None:
            item["p"] = [r(src.p_c, 3), r(src.p_e, 3), r(src.p_f, 3)]
            item["g"] = [r(src.lc, 2), r(src.lf, 2)]
            item["es"] = [int(src.pl_c), int(src.pl_f)]
            if g.jogado:
                item["ok"] = bool(src.ok)
        rodadas.setdefault(str(int(g.rodada)), []).append(item)
    rodadas = dict(sorted(rodadas.items(), key=lambda kv: int(kv[0])))
    atual = rodada_atual(cur, hoje_br)

    # --- tabela prevista -----------------------------------------------------------
    sim = F.simular(S, cfg)
    base = {L["t"]: L for L in tab}
    resto_df = cur[~cur["jogado"]]
    rest_por_time = pd.concat([resto_df["casa"], resto_df["fora"]]).value_counts().to_dict()
    prev = []
    for i, n in enumerate(sim["times"]):
        prev.append({"t": cod[n], "pts": base[n]["pts"], "j": base[n]["j"], "n_rest": int(rest_por_time.get(n, 0)),
                     "esp": r(sim["pts"][i], 1), "faixa": [int(round(sim["pts_lo"][i])), int(round(sim["pts_hi"][i]))],
                     "pos": r(sim["pos_media"][i], 1), "pos_prov": int(sim["dist"][i].argmax()) + 1,
                     "tit": r(sim["tit"][i], 3), "topo": r(sim["topo"][i], 3), "reb": r(sim["rebaixa"][i], 3),
                     "dist": [r(x, 4) for x in sim["dist"][i]]})
    prev.sort(key=lambda x: (-x["esp"], x["pos"]))

    tabela = [{"t": cod[L["t"]], **{k: L[k] for k in ("j", "v", "e", "d", "gp", "gc", "sg", "pts")}, "forma": L["forma"]} for L in tab]

    # --- meta ------------------------------------------------------------------------
    ref = bt[bt["ano"] < S["atual"]] if len(bt) else bt
    faixas = []
    for lo, hi in FAIXAS:
        conf = ref[["p_c", "p_e", "p_f"]].max(axis=1)
        x = ref[(conf >= lo) & (conf < hi)]
        faixas.append({"de": lo, "ate": min(hi, 1.0), "n": int(len(x)), "acc": r(x["ok"].mean()) if len(x) else None})
    anos = acc["anos_ref"]
    rotulo_ano = (lambda y: f"{y}-{str(y + 1)[2:]}") if "eu" in cfg else str
    out = {
        "meta": {
            "esporte": "Futebol", "liga": lid, "nome": cfg["nome"], "pais": cfg["pais"],
            "temporada": int(S["atual"]), "temporada_rotulo": rot, "rotulos_temporada": {str(S["atual"]): rot},
            "semana_atual": str(atual), "semana_rotulo": f"Rodada {atual}", "n_rodadas": len(rodadas),
            "atualizado": date.today().isoformat(), "usa_linha": False, "fuso": "Horário de Brasília",
            "acc": r(acc["acc"]), "acc_mandante": r(acc["acc_mandante"]), "freq_empate": r(acc["freq_empate"]), "n_ref": acc["n_ref"],
            "log_loss": r(acc["log_loss"], 4), "log_loss_base": r(acc["log_loss_base"], 4),
            "anos_ref": [rotulo_ano(anos[0]), rotulo_ano(anos[1])], "faixas": faixas,
            "acc_temporada": r(acc["acc_atual"]), "n_temporada": acc["n_atual"],
            "fonte": "openfootball (domínio público) e ESPN", "avisos": F.AVISOS,
            "topo": cfg["topo"], "rebaixa": cfg["rebaixa"], "repescagem": bool(cfg.get("repescagem")),
            "desempate_vitorias": bool(cfg.get("desempate_vitorias")),
            "como_ler": ("Para cada temporada de {a} a {b}, o modelo aprendeu só com os anos anteriores e previu os jogos daquele ano. "
                         "O palpite é o resultado mais provável entre vitória do mandante, empate e vitória do visitante. "
                         "Com três resultados possíveis, chutar “mandante” sempre acerta {m:.0%} e o acaso puro, 33%.")
            .format(a=rotulo_ano(anos[0]), b=rotulo_ano(anos[1]), m=acc["acc_mandante"]),
        },
        "times": times, "rodadas": rodadas, "tabela": tabela,
        "previsao": {"n": sim["n"], "sigma": r(sim["sigma"], 0), "n_rest": sim["n_rest"], "times": prev},
    }
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{lid}.json"
    arq.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("OK:", arq, f"({arq.stat().st_size / 1024:.0f} KB)")
    return out


def indice(pasta_ligas):
    """Resumo de todas as ligas que têm JSON gravado (usa os arquivos, então uma liga que falhou hoje continua aparecendo)."""
    ligas, metas = [], []
    for lid, cfg in F.LIGAS.items():
        arq = pasta_ligas / f"{lid}.json"
        if not arq.exists():
            continue
        j = json.loads(arq.read_text(encoding="utf-8"))
        m = j["meta"]
        metas.append(m)
        lider = j["tabela"][0]
        fav = max(j["previsao"]["times"], key=lambda x: x["tit"])
        ligas.append({"id": lid, "nome": m["nome"], "pais": m["pais"], "temporada_rotulo": m["temporada_rotulo"], "rodada": m["semana_rotulo"],
                      "acc": m["acc"], "acc_mandante": m["acc_mandante"], "n_ref": m["n_ref"], "atualizado": m["atualizado"],
                      "lider": {"nome": j["times"][lider["t"]]["nome"], "pts": lider["pts"], "j": lider["j"]},
                      "favorito": {"nome": j["times"][fav["t"]]["nome"], "tit": fav["tit"]}})
    n = sum(m["n_ref"] for m in metas)
    ponderar = lambda k: r(sum(m[k] * m["n_ref"] for m in metas) / n)
    return {"meta": {
        "esporte": "Futebol", "temporada_rotulo": "2026", "semana_rotulo": f"{len(ligas)} ligas", "atualizado": max(m["atualizado"] for m in metas),
        "acc": ponderar("acc"), "acc_mandante": ponderar("acc_mandante"), "n_ref": n,
        "anos_ref": [min(m["anos_ref"][0][:4] for m in metas), max(m["anos_ref"][1][:4] for m in metas)],
        "fonte": "openfootball (domínio público) e ESPN", "usa_linha": False, "avisos": F.AVISOS,
    }, "ligas": ligas}


def main(pasta=None, ligas=None):
    pasta = Path(pasta) if pasta else PASTA
    falhas = []
    for lid in ligas or F.LIGAS:
        print(f"-- {F.LIGAS[lid]['nome']}")
        try:
            exportar_liga(lid, pasta / "futebol")
        except Exception:
            traceback.print_exc()
            print(f"::warning::Falha em {F.LIGAS[lid]['nome']}; mantendo o JSON anterior.")
            falhas.append(lid)
    if len(falhas) == len(ligas or F.LIGAS):
        raise RuntimeError("nenhuma liga de futebol foi atualizada")
    (pasta / "futebol.json").write_text(json.dumps(indice(pasta / "futebol"), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("OK:", pasta / "futebol.json")


if __name__ == "__main__":
    main(ligas=[a.lower() for a in sys.argv[1:]] or None)

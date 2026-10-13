#!/usr/bin/env python3
"""
Previsor NFL
============
Duas funções:
  1) Previsões de uma semana (temporada + rodada), com acurácia do modelo.
  2) Projeção de recorde de um time até o fim da temporada regular.

Uso (terminal):
    python previsor_nfl.py                 -> menu interativo
    python previsor_nfl.py semana 6        -> previsões da semana 6 da temporada atual
    python previsor_nfl.py semana 10 2025  -> semana 10 de 2025
    python previsor_nfl.py time KC         -> recorde projetado do Kansas City

No Google Colab: rode o arquivo/célula e chame  menu()
Requisitos: pandas, numpy, scikit-learn (já vêm no Colab).
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

import noticias
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

URL = os.environ.get(
    "NFL_CSV",
    "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
)
FEATS_FULL = ["spread_line", "dif_elo", "dif_pf", "dif_pa", "dif_rest"]  # com linha de aposta
FEATS_BASE = ["dif_elo", "dif_pf", "dif_pa", "dif_rest"]                 # sem linha de aposta
FRANQUIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA"}                      # mudanças de cidade
ALIAS = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "LVR": "LV", "OAK": "LV", "SD": "LAC", "STL": "LA"}

AVISOS = [
    "Lesões, troca de quarterback, clima e suspensões NÃO entram no modelo.",
    "Elo e médias de pontos ficam 'congelados' no estado atual: quanto mais distante o jogo, menos confiável.",
    "Jogos sem linha de aposta usam o modelo sem ela (acurácia histórica menor, ~64% contra ~66%).",
    "A acurácia histórica é uma média de várias temporadas; numa rodada isolada o resultado varia muito.",
    "Isto é um estudo estatístico, não uma recomendação de aposta.",
]


# ----------------------------------------------------------------------------
# Dados e modelo
# ----------------------------------------------------------------------------
def _modelo_lr():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def calcular_elo(jg, k=20, vantagem_casa=48):
    """Elo ANTES de cada jogo (sem vazamento). Devolve também o Elo atual de cada time."""
    elo, h_elo, a_elo, ultima = {}, [], [], None
    for r in jg.itertuples():
        if ultima is not None and r.season != ultima:  # regressão à média entre temporadas
            for t in elo:
                elo[t] = 0.67 * elo[t] + 0.33 * 1500
        ultima = r.season
        eh, ea = elo.get(r.home_team, 1500), elo.get(r.away_team, 1500)
        h_elo.append(eh)
        a_elo.append(ea)
        esperado = 1 / (1 + 10 ** (-((eh + vantagem_casa) - ea) / 400))
        margem = r.home_score - r.away_score
        resultado = 1.0 if margem > 0 else 0.0
        ajuste = k * np.log(abs(margem) + 1) * (resultado - esperado)
        elo[r.home_team] = eh + ajuste
        elo[r.away_team] = ea - ajuste
    return np.array(h_elo), np.array(a_elo), elo


def carregar():
    print("Baixando dados da NFL (nflverse)...")
    jogos = pd.read_csv(URL)
    jogos = jogos[jogos["season"] >= 2006].copy()
    jogos["gameday"] = pd.to_datetime(jogos["gameday"])
    for c in ("home_team", "away_team"):
        jogos[c] = jogos[c].replace(FRANQUIAS)
    return _completar_com_espn(jogos.reset_index(drop=True))


def _completar_com_espn(jogos):
    """O nflverse demora horas para publicar o placar; a ESPN costuma ter minutos depois do jogo."""
    import espn
    finais = espn.finais("nfl")
    if not finais or "espn" not in jogos.columns:
        return jogos
    n = 0
    for i in jogos.index[jogos["home_score"].isna() & jogos["espn"].notna()]:
        r = finais.get(str(int(jogos.at[i, "espn"])))
        if r:
            jogos.at[i, "away_score"], jogos.at[i, "home_score"] = r
            n += 1
    if n:
        print(f"ESPN: {n} placar(es) completado(s)")
    return jogos


def construir(jogos):
    """Treina tudo e devolve um dicionário com o 'estado' do previsor."""
    futuros = jogos[jogos["home_score"].isna()].copy()
    jogados = (jogos.dropna(subset=["home_score", "away_score"])
                    .sort_values("gameday").reset_index(drop=True))
    jogados = jogados[jogados["home_score"] != jogados["away_score"]].reset_index(drop=True)
    jogados["home_win"] = (jogados["home_score"] > jogados["away_score"]).astype(int)

    h_elo, a_elo, elo_atual = calcular_elo(jogados)
    jogados["dif_elo"] = h_elo - a_elo

    casa = jogados[["game_id", "gameday", "home_team", "home_score", "away_score"]].rename(
        columns={"home_team": "team", "home_score": "pf", "away_score": "pa"})
    fora = jogados[["game_id", "gameday", "away_team", "away_score", "home_score"]].rename(
        columns={"away_team": "team", "away_score": "pf", "home_score": "pa"})
    longo = pd.concat([casa, fora]).sort_values(["team", "gameday"])
    for c in ("pf", "pa"):
        longo[c + "_med5"] = longo.groupby("team")[c].transform(
            lambda s: s.shift(1).rolling(5, min_periods=3).mean())
    feat = longo[["game_id", "team", "pf_med5", "pa_med5"]]
    h = feat.rename(columns={"team": "home_team", "pf_med5": "h_pf", "pa_med5": "h_pa"})
    a = feat.rename(columns={"team": "away_team", "pf_med5": "a_pf", "pa_med5": "a_pa"})
    modelo = jogados.merge(h, on=["game_id", "home_team"]).merge(a, on=["game_id", "away_team"])
    modelo["dif_pf"] = modelo["h_pf"] - modelo["a_pf"]
    modelo["dif_pa"] = modelo["h_pa"] - modelo["a_pa"]
    modelo["dif_rest"] = modelo["home_rest"] - modelo["away_rest"]
    modelo = modelo.dropna(subset=FEATS_FULL).reset_index(drop=True)

    # Backtest: para cada temporada, treina só com as anteriores (nenhum vazamento)
    partes = []
    for ano in range(2012, int(modelo["season"].max()) + 1):
        tr, te = modelo[modelo["season"] < ano], modelo[modelo["season"] == ano]
        if te.empty:
            continue
        p_full = _modelo_lr().fit(tr[FEATS_FULL], tr["home_win"]).predict_proba(te[FEATS_FULL])[:, 1]
        p_base = _modelo_lr().fit(tr[FEATS_BASE], tr["home_win"]).predict_proba(te[FEATS_BASE])[:, 1]
        partes.append(te[["game_id", "season", "home_win"]].assign(p_full=p_full, p_base=p_base))
    bt = pd.concat(partes)
    bt["ac_full"] = ((bt["p_full"] >= .5).astype(int) == bt["home_win"]).astype(int)
    bt["ac_base"] = ((bt["p_base"] >= .5).astype(int) == bt["home_win"]).astype(int)

    # Acurácia de referência: temporadas completas desde 2016
    cont = bt.groupby("season").size()
    completas = [s for s in cont.index if s >= 2016 and cont[s] >= 250]
    ref = bt[bt["season"].isin(completas)]
    atual = int(jogos["season"].max())
    bt_atual = bt[bt["season"] == atual]

    return {
        "jogos": jogos, "futuros": futuros, "modelo": modelo, "bt": bt, "elo": elo_atual,
        "ult": longo.groupby("team").tail(5).groupby("team")[["pf", "pa"]].mean(),
        "m_full": _modelo_lr().fit(modelo[FEATS_FULL], modelo["home_win"]),
        "m_base": _modelo_lr().fit(modelo[FEATS_BASE], modelo["home_win"]),
        "acc_full": ref["ac_full"].mean(), "acc_base": ref["ac_base"].mean(),
        "anos_ref": (min(completas), max(completas)),
        "acc_atual": bt_atual["ac_full"].mean() if len(bt_atual) else None,
        "n_atual": len(bt_atual), "atual": atual,
        "times": sorted(set(jogos["home_team"]) | set(jogos["away_team"])),
    }


_NOT = {}


def prever_futuros(S, fut):
    """Probabilidade de vitória do mandante para jogos que ainda não aconteceram."""
    fut = fut.copy()
    fut["dif_elo"] = fut["home_team"].map(S["elo"]) - fut["away_team"].map(S["elo"])
    fut["dif_pf"] = fut["home_team"].map(S["ult"]["pf"]) - fut["away_team"].map(S["ult"]["pf"])
    fut["dif_pa"] = fut["home_team"].map(S["ult"]["pa"]) - fut["away_team"].map(S["ult"]["pa"])
    fut["dif_rest"] = (fut["home_rest"] - fut["away_rest"]).fillna(0)
    fut["tem_linha"] = fut["spread_line"].notna()
    # ajustes por notícia (lesões etc.): só em jogos SEM linha de aposta, porque a linha já embute a notícia
    if "adj" not in _NOT:
        _NOT["adj"] = noticias.carregar("nfl")
    if _NOT["adj"]:
        dias = fut["gameday"].dt.strftime("%Y-%m-%d")
        aj = [0.0 if tl else noticias.delta(_NOT["adj"], h, d) - noticias.delta(_NOT["adj"], a, d)
              for h, a, d, tl in zip(fut["home_team"], fut["away_team"], dias, fut["tem_linha"])]
        fut["dif_elo"] = fut["dif_elo"] + aj
    fut["prob_casa"] = np.nan
    ok_base = fut[FEATS_BASE].notna().all(axis=1)
    ok_full = ok_base & fut["tem_linha"]
    if ok_full.any():
        fut.loc[ok_full, "prob_casa"] = S["m_full"].predict_proba(fut.loc[ok_full, FEATS_FULL])[:, 1]
    so_base = ok_base & ~fut["tem_linha"]
    if so_base.any():
        fut.loc[so_base, "prob_casa"] = S["m_base"].predict_proba(fut.loc[so_base, FEATS_BASE])[:, 1]
    return fut


# ----------------------------------------------------------------------------
# Saída
# ----------------------------------------------------------------------------
def _avisos():
    print("\n⚠  AVISOS E NUANCES")
    for a in AVISOS:
        print("  - " + a)


def _cabecalho_acuracia(S):
    a0, a1 = S["anos_ref"]
    print(f"Acurácia histórica do modelo ({a0}-{a1}, teste fora da amostra):")
    print(f"  com linha de aposta: {S['acc_full']:.1%}   |   sem linha de aposta: {S['acc_base']:.1%}")
    if S["acc_atual"] is not None:
        print(f"  temporada {S['atual']} até agora ({S['n_atual']} jogos): {S['acc_atual']:.1%}")


def semana(S, week, season=None):
    season = season or S["atual"]
    jg = S["jogos"][(S["jogos"]["season"] == season) & (S["jogos"]["week"] == week)].sort_values("gameday")
    print("\n" + "=" * 70)
    print(f"PREVISÕES - TEMPORADA {season}, SEMANA {week}")
    print("=" * 70)
    if jg.empty:
        print("Não encontrei jogos para essa temporada/semana.")
        return
    _cabecalho_acuracia(S)
    print()

    linhas, acertos, n_jogados = [], 0, 0
    bt = S["bt"].set_index("game_id")
    fut = prever_futuros(S, jg[jg["home_score"].isna()])
    fut_idx = fut.set_index("game_id") if len(fut) else None

    for r in jg.itertuples():
        data = r.gameday.strftime("%d/%m")
        jogo = f"{r.away_team:>3} @ {r.home_team:<3}"
        if pd.notna(r.home_score):
            placar = f"{int(r.away_score)}-{int(r.home_score)}"
            if r.game_id in bt.index:
                p = bt.loc[r.game_id, "p_full"]
                palpite = r.home_team if p >= .5 else r.away_team
                venc = r.home_team if r.home_score > r.away_score else (r.away_team if r.away_score > r.home_score else "EMP")
                ok = palpite == venc
                acertos += ok
                n_jogados += 1
                linhas.append((data, jogo, palpite, f"{max(p, 1 - p):.0%}", placar, "✓" if ok else "✗"))
            else:
                linhas.append((data, jogo, "-", "-", placar, "(sem backtest)"))
        else:
            p = fut_idx.loc[r.game_id, "prob_casa"] if fut_idx is not None else np.nan
            if pd.isna(p):
                linhas.append((data, jogo, "-", "-", "a jogar", "dados insuficientes"))
                continue
            sem = "" if fut_idx.loc[r.game_id, "tem_linha"] else "*"
            palpite = r.home_team if p >= .5 else r.away_team
            linhas.append((data, jogo, palpite, f"{max(p, 1 - p):.0%}{sem}", "a jogar", ""))

    print(f"{'Data':<6}{'Jogo':<11}{'Palpite':<9}{'Conf.':<7}{'Placar(V-M)':<13}")
    print("-" * 52)
    for l in linhas:
        print(f"{l[0]:<6}{l[1]:<11}{l[2]:<9}{l[3]:<7}{l[4]:<13}{l[5]}")
    if n_jogados:
        print(f"\nAcertos nesta semana: {acertos}/{n_jogados} ({acertos / n_jogados:.0%}) "
              "- previsões feitas só com dados anteriores a cada jogo.")
    if any("*" in l[3] for l in linhas):
        print("* sem linha de aposta disponível (modelo menos preciso).")
    _avisos()


def _dist_vitorias(probs):
    """Distribuição do número de vitórias (soma de Bernoullis independentes)."""
    dist = np.array([1.0])
    for p in probs:
        dist = np.convolve(dist, [1 - p, p])
    return dist


def recorde(S, sigla):
    sigla = ALIAS.get(sigla.upper().strip(), sigla.upper().strip())
    if sigla not in S["times"]:
        print(f"Time '{sigla}' não encontrado. Siglas válidas:\n  " + ", ".join(S["times"]))
        return
    season = S["atual"]
    todos = S["jogos"][(S["jogos"]["season"] == season) & (S["jogos"]["game_type"] == "REG")
                       & ((S["jogos"]["home_team"] == sigla) | (S["jogos"]["away_team"] == sigla))]
    jogados = todos[todos["home_score"].notna()]
    resta = todos[todos["home_score"].isna()].sort_values("gameday")

    v = d = e = 0
    for r in jogados.itertuples():
        meu, opp = (r.home_score, r.away_score) if r.home_team == sigla else (r.away_score, r.home_score)
        v += meu > opp
        d += meu < opp
        e += meu == opp

    print("\n" + "=" * 70)
    print(f"PROJEÇÃO DE RECORDE - {sigla} - TEMPORADA {season}")
    print("=" * 70)
    _cabecalho_acuracia(S)
    bt = S["bt"].merge(S["jogos"][["game_id", "home_team", "away_team"]], on="game_id")
    bt_t = bt[(bt["home_team"] == sigla) | (bt["away_team"] == sigla)]
    bt_t = bt_t[bt_t["season"] >= 2016]
    if len(bt_t):
        print(f"  acerto do modelo nos jogos do {sigla} desde 2016: {bt_t['ac_full'].mean():.1%} ({len(bt_t)} jogos)")
    print(f"\nRecorde atual: {v}-{d}" + (f"-{e}" if e else ""))

    if resta.empty:
        print("A temporada regular deste time já terminou.")
        _avisos()
        return

    fut = prever_futuros(S, resta)
    fut["p_time"] = np.where(fut["home_team"] == sigla, fut["prob_casa"], 1 - fut["prob_casa"])
    fut = fut.dropna(subset=["p_time"])

    print(f"\nJogos restantes ({len(fut)}):")
    print(f"{'Sem.':<6}{'Data':<7}{'Jogo':<12}{'Chance de vencer':<18}")
    for r in fut.itertuples():
        onde = f"vs {r.away_team}" if r.home_team == sigla else f"@ {r.home_team}"
        sem = "" if r.tem_linha else "*"
        print(f"{r.week:<6}{r.gameday.strftime('%d/%m'):<7}{onde:<12}{r.p_time:.0%}{sem}")

    dist = _dist_vitorias(fut["p_time"].values)
    esperado = v + (np.arange(len(dist)) * dist).sum()
    moda = int(np.argmax(dist))
    cum = np.cumsum(dist)
    lo, hi = int(np.searchsorted(cum, 0.10)), int(np.searchsorted(cum, 0.90))
    n_rest = len(dist) - 1
    print(f"\nVitórias esperadas no fim: {esperado:.1f}")
    print(f"Recorde mais provável:     {v + moda}-{d + n_rest - moda}" + (f"-{e}" if e else ""))
    print(f"Faixa provável (80%):      {v + lo} a {v + hi} vitórias")
    print("\nDistribuição do total de vitórias:")
    for k, pk in enumerate(dist):
        if pk >= 0.01:
            print(f"  {v + k:>2} vitórias: {pk:>5.1%} {'█' * int(round(pk * 60))}")
    if (~fut["tem_linha"]).any():
        print("\n* sem linha de aposta disponível (usa o modelo sem ela, menos preciso).")
    print("\nObs.: a projeção trata os jogos como independentes e não considera playoffs.")
    _avisos()


# ----------------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------------
def _proxima_semana(S):
    f = S["futuros"]
    f = f[f["season"] == S["atual"]].sort_values("gameday")
    return int(f["week"].iloc[0]) if len(f) else None


def menu(S=None):
    S = S or construir(carregar())
    prox = _proxima_semana(S)
    print(f"\nDados prontos. Temporada atual: {S['atual']} | próxima semana: {prox}")
    while True:
        print("\n--- PREVISOR NFL ---")
        print("1) Previsões de uma semana")
        print("2) Projeção de recorde de um time")
        print("3) Sair")
        op = input("Escolha: ").strip()
        if op == "1":
            w = input(f"Semana [ENTER = {prox}]: ").strip()
            s = input(f"Temporada [ENTER = {S['atual']}]: ").strip()
            try:
                semana(S, int(w) if w else prox, int(s) if s else None)
            except ValueError:
                print("Digite apenas números.")
        elif op == "2":
            t = input("Sigla do time (ex.: KC, SF, DAL, GB): ").strip()
            if t:
                recorde(S, t)
        elif op == "3":
            print("Até mais!")
            break
        else:
            print("Opção inválida.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return menu()
    S = construir(carregar())
    cmd = argv[0].lower()
    if cmd == "semana" and len(argv) >= 2:
        semana(S, int(argv[1]), int(argv[2]) if len(argv) > 2 else None)
    elif cmd == "time" and len(argv) >= 2:
        recorde(S, argv[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

"""Testes da parte de tempo real. Rodar:  python tests/test_tempo_real.py   (ou: python -m pytest tests)"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import espn  # noqa: E402
import verificar_novos as V  # noqa: E402

AMOSTRA = {"events": [
    {"id": "100", "status": {"type": {"state": "post", "completed": True, "shortDetail": "Final"}},
     "competitions": [{"competitors": [{"homeAway": "home", "score": "16", "team": {"abbreviation": "DAL"}},
                                       {"homeAway": "away", "score": "24", "team": {"abbreviation": "TB"}}]}]},
    {"id": "101", "status": {"type": {"state": "in", "completed": False, "shortDetail": "8:12 - 3rd"}},
     "competitions": [{"competitors": [{"homeAway": "home", "score": "7", "team": {"abbreviation": "KC"}},
                                       {"homeAway": "away", "score": "3", "team": {"abbreviation": "LV"}}]}]},
    {"id": "102", "status": {"type": {"state": "pre", "completed": False, "shortDetail": "Sun 8:20 PM"}},
     "competitions": [{"competitors": [{"homeAway": "home", "team": {"abbreviation": "GB"}},
                                       {"homeAway": "away", "team": {"abbreviation": "CHI"}}]}]},
    {"id": "103", "status": {"type": {}}, "competitions": [{"competitors": []}]},  # incompleto: ignorado
]}


def test_interpretar():
    j = {x["id"]: x for x in espn.interpretar(AMOSTRA)}
    assert set(j) == {"100", "101", "102"}
    assert j["100"]["final"] and (j["100"]["pts_fora"], j["100"]["pts_casa"]) == (24, 16)
    assert j["101"]["estado"] == "in" and j["101"]["detalhe"] == "8:12 - 3rd"
    assert j["102"]["pts_casa"] is None and not j["102"]["final"]


def test_finais_so_terminados(monkeypatch=None):
    original = espn.jogos_do_periodo
    espn.jogos_do_periodo = lambda esporte, dias=3, hoje=None: espn.interpretar(AMOSTRA)
    try:
        assert espn.finais("nfl") == {"100": (24, 16)}
    finally:
        espn.jogos_do_periodo = original


def test_pendentes():
    site = {"semanas": {"2026": {"5": {"jogos": [
        {"id": "2026_05_TB_DAL", "espn": "100", "placar": None},   # acabou na ESPN, site sem placar -> pendente
        {"id": "2026_05_LV_KC", "espn": "101", "placar": None},    # ainda em andamento -> não conta
        {"id": "2026_05_A_B", "espn": "104", "placar": [10, 3]},   # já publicado
    ]}}}}
    assert V.pendentes({"100": (24, 16), "104": (3, 10), "999": (1, 2)}, site, "nfl") == ["100"]  # 999 não está no site: ignorado
    nba = {"semanas": {"2027": {"1": {"jogos": [{"id": "401", "placar": None}]}}}}
    assert V.pendentes({"401": (100, 90)}, nba, "nba") == ["401"]
    assert V.pendentes({}, nba, "nba") == []


def test_completar_nfl_e_nba():
    import previsor_nba as N
    import previsor_nfl as P
    original = espn.finais
    espn.finais = lambda esporte, dias=3: {"555": (20, 27)}
    try:
        nfl = pd.DataFrame({"espn": [555.0, 556.0], "home_score": [np.nan, np.nan], "away_score": [np.nan, np.nan]})
        out = P._completar_com_espn(nfl.copy())
        assert (out.loc[0, "away_score"], out.loc[0, "home_score"]) == (20, 27) and pd.isna(out.loc[1, "home_score"])
        nba = pd.DataFrame({"game_id": [555, 556], "home_score": [np.nan, np.nan], "away_score": [np.nan, np.nan],
                            "status_type_completed": [False, False]})
        out = N._completar_com_espn(nba.copy())
        assert bool(out.loc[0, "status_type_completed"]) and out.loc[0, "home_score"] == 27 and not out.loc[1, "status_type_completed"]
    finally:
        espn.finais = original


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)

"""Testes do futebol. Rodar:  python -m pytest tests   (ou: python tests/test_futebol.py). Não usam internet."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import previsor_futebol as F  # noqa: E402

TXT = """= Brasiléiro Série A 2026

▪ Matchday 1
  Wed Jan 28 2026
    19:00  CA Mineiro              v SE Palmeiras             2-2 (1-1)
           Coritiba FBC            v RB Bragantino            0-1 (0-0)
  Thu Jan 29
    20:00  Mirassol FC             v CR Vasco da Gama
▪ Matchday 2
  Wed Feb 4
           Chapecoense AF          v CR Vasco da Gama         [postponed]
"""


def test_parser_brasil():
    j = list(F._linhas_brasil(TXT, 2026, "America/Sao_Paulo"))
    assert len(j) == 4
    assert (j[0]["gc"], j[0]["gf"], j[0]["hora"]) == (2, 2, "19:00")
    assert j[1]["hora"] == "19:00"                      # o horário vale até a próxima data
    assert np.isnan(j[2]["gc"]) and j[2]["dia"] == "2026-01-29"
    assert j[3]["adiado"] and j[3]["fora_raw"] == "CR Vasco da Gama" and j[3]["hora"] is None


def test_fuso_brasilia():
    utc, dia, hora = F._para_brasilia("2026-09-20", "16:30", "Europe/London")   # horário de verão: UTC+1
    assert (dia, hora) == ("2026-09-20", "12:30")
    _, dia, hora = F._para_brasilia("2026-09-20", "00:30", "Europe/Paris")        # vira o dia anterior em Brasília
    assert (dia, hora) == ("2026-09-19", "19:30")
    assert F._para_brasilia("2026-09-20", None, "Europe/Rome")[2] is None


def test_apelidos():
    assert F.apelido("Manchester City FC") == F.apelido("Manchester City") == "Man City"
    assert F.apelido("SC Corinthians Paulista") == F.apelido("Corinthians SP") == "Corinthians"
    assert F.apelido("FC Bayern München") == F.apelido("Bayern München") == "Bayern de Munique"


def test_chances_somam_1_e_forca_importa():
    p, plac = F.chances(np.array([1.5, 2.5, 0.8]), np.array([1.2, 0.7, 2.0]))
    assert np.allclose(p.sum(1), 1)
    assert p[1, 0] > p[0, 0] > p[2, 0] and p[2, 2] > p[2, 0]


def _liga_fake():
    rng = np.random.default_rng(1)
    times = [f"T{i}" for i in range(14)]
    forca = dict(zip(times, np.linspace(1.6, 0.3, 14)))
    linhas, dia = [], pd.Timestamp("2024-08-01")
    for ano in (2023, 2024, 2025, 2026):
        for a in times:
            for b in times:
                if a == b:
                    continue
                dia += pd.Timedelta(days=1)
                jog = not (ano == 2026 and rng.random() < 0.4)
                gc, gf = rng.poisson(forca[a] * 0.9 + 0.3), rng.poisson(forca[b] * 0.7 + 0.2)
                linhas.append(dict(temp=str(ano), rodada=1, dia=dia.strftime("%Y-%m-%d"), hora="20:00", tz="America/Sao_Paulo",
                                   casa_raw=a, fora_raw=b, gc=gc if jog else np.nan, gf=gf if jog else np.nan, adiado=False))
    return F.preparar(pd.DataFrame(linhas))


def test_modelo_tabela_e_simulacao():
    S = F.construir(_liga_fake())
    cfg = dict(topo=2, rebaixa=1)
    tab = F.tabela_atual(S, cfg)
    assert sum(L["pts"] for L in tab) > 0 and [L["pts"] for L in tab] == sorted((L["pts"] for L in tab), reverse=True)
    sim = F.simular(S, cfg, n=2000)
    assert np.allclose(sim["dist"].sum(0), 1) and np.allclose(sim["dist"].sum(1), 1)   # cada posição e cada time somam 100%
    assert np.isclose(sim["tit"].sum(), 1)
    assert sim["tit"][sim["times"].index("T0")] > sim["tit"][sim["times"].index("T13")]
    assert (sim["pts"] >= np.array([L["pts"] for L in tab])).all()                       # ninguém perde pontos
    assert F.resumo_acuracia(S)["acc"] > 0.35


def test_espn_completa_resultado():
    d = _liga_fake()
    i = d.index[~d["jogado"]][0]
    g = d.loc[i]
    ev = [{"final": True, "pts_casa": 3, "pts_fora": 1, "nome_casa": g.casa_raw, "nome_fora": g.fora_raw, "data": g["dt"].isoformat()}]
    assert F.casar_espn(d, ev) == 1
    assert (d.at[i, "gc"], d.at[i, "gf"], d.at[i, "jogado"]) == (3, 1, True)


def test_espn_nomes_diferentes():
    d = F.preparar(pd.DataFrame([dict(temp="2026", rodada=1, dia="2026-10-03", hora="15:00", tz="Europe/Berlin", casa_raw="FC Bayern München",
                                      fora_raw="Borussia Mönchengladbach", gc=np.nan, gf=np.nan, adiado=False),
                                 dict(temp="2026", rodada=1, dia="2026-10-03", hora="15:00", tz="Europe/Berlin", casa_raw="RB Leipzig",
                                      fora_raw="1. FC Köln", gc=np.nan, gf=np.nan, adiado=False)]))
    ev = [{"final": True, "pts_casa": 2, "pts_fora": 0, "nome_casa": "Bayern Munich", "nome_fora": "Borussia Mönchengladbach",
           "data": "2026-10-03T13:30Z"},
          {"final": True, "pts_casa": 1, "pts_fora": 1, "nome_casa": "RB Leipzig", "nome_fora": "FC Cologne", "data": "2026-10-03T13:30Z"}]
    assert F.casar_espn(d, ev) == 2
    assert d.loc[d["casa"] == "Bayern de Munique", "gc"].iloc[0] == 2


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn()
            print("ok", nome)

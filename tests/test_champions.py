"""Testes da Champions League (mesmo fluxo das ligas de futebol). Rodar:  python -m pytest tests   (ou: python tests/test_champions.py).
Não usam internet."""
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import espn  # noqa: E402
import historico_previsoes as H  # noqa: E402
import previsor_futebol as F  # noqa: E402

TIMES = [f"Clube {chr(65 + i)}{chr(65 + j)}x" for i in range(6) for j in range(6)]   # 36 clubes ("x": evita sufixos como "BA")


def _jogo(i, dia, casa, fora, fase="league-phase", placar=None, nota=None):
    return {"id": str(i), "data": dia.isoformat(), "hora": "17:00", "mandante": casa, "visitante": fora, "estado": "post" if placar else "pre",
            "finalizado": placar is not None, "placar": placar, "fase": fase, "nota": nota, "temporada": dia.year if dia.month >= 7 else dia.year - 1}


def _temporada(ano, rng, rodadas_jogadas=8, mata=False):
    """Fase de liga com 8 rodadas (terças), 18 jogos cada; opcionalmente o mata-mata já disputado."""
    jogos, i = [], ano * 1000
    for r in range(8):
        dia = date(ano, 9, 16) + timedelta(weeks=2 * r)
        ordem = rng.permutation(36)
        for k in range(18):
            casa, fora = TIMES[ordem[2 * k]], TIMES[ordem[2 * k + 1]]
            pl = [int(rng.poisson(1.5)), int(rng.poisson(1.2))] if r < rodadas_jogadas else None
            jogos.append(_jogo(i, dia, casa, fora, placar=pl))
            i += 1
    if mata:
        for fase, semanas, n in (("knockout-round-playoffs", (0, 1), 8), ("round-of-16", (3, 4), 8), ("quarterfinals", (7, 8), 4),
                                 ("semifinals", (11, 12), 2), ("final", (16,), 1)):
            for perna, s in enumerate(semanas):
                dia = date(ano + 1, 2, 10) + timedelta(weeks=s)
                for k in range(n):
                    a, b = TIMES[2 * k], TIMES[2 * k + 1]
                    casa, fora = (a, b) if perna == 0 else (b, a)
                    jogos.append(_jogo(i, dia, casa, fora, fase=fase, placar=[1, 0]))
                    i += 1
    return jogos


def _pasta_fake():
    rng = np.random.default_rng(7)
    pasta = Path(tempfile.mkdtemp())
    for ano in range(2022, 2026):
        F._gravar_temporada(F._arquivo_champions(ano, pasta), ano, {j["id"]: j for j in _temporada(ano, rng, mata=True)})
    F._gravar_temporada(F._arquivo_champions(2026, pasta), 2026, {j["id"]: j for j in _temporada(2026, rng, rodadas_jogadas=4)})
    return pasta


def _montar(pasta):
    d = F.preparar(pd.DataFrame(F.linhas_champions(date(2026, 11, 15), pasta=pasta, atualizar=False)))
    return F.construir(d)


def test_rodadas_e_tabela_so_da_fase_de_liga():
    S = _montar(_pasta_fake())
    cur = S["d"][S["d"]["ano"] == 2026]
    assert sorted(cur["rodada"].unique()) == list(range(1, 9)) and cur["na_tabela"].all()
    old = S["d"][S["d"]["ano"] == 2025]
    assert old["rodada"].max() == 8 + 9 and (old["na_tabela"] == (old["fase"] == "league-phase")).all()   # 8 de liga + 9 do mata-mata
    tab = F.tabela_atual(S, F.LIGAS["champions"])
    assert len(tab) == 36 and all(L["j"] == 4 for L in tab)


def test_rotulos_do_mata_mata():
    S = _montar(_pasta_fake())
    rot = F.rotulos_rodada(S["d"][S["d"]["ano"] == 2025])
    assert rot["9"] == {"nome": "Playoff (ida)", "curto": "PO1"} and rot["10"]["nome"] == "Playoff (volta)"
    assert rot["17"] == {"nome": "Final", "curto": "F"} and "1" not in rot


def test_simulacao_com_titulo():
    S = _montar(_pasta_fake())
    cfg = F.LIGAS["champions"]
    sim = F.simular(S, cfg, n=2000)
    assert np.isclose(sim["tit"].sum(), 1) and np.allclose(sim["topo"] + sim["meio"] + sim["rebaixa"], 1)
    assert (sim["tit"][sim["rebaixa"] > 0.999] == 0).all()        # quem é sempre eliminado na fase de liga nunca é campeão


def test_confrontos_reais_usam_a_nota_da_espn():
    rng = np.random.default_rng(1)
    jogos = _temporada(2026, rng)
    jogos += [_jogo(1, date(2027, 2, 16), "Clube AAx", "Clube ABx", fase="knockout-round-playoffs", placar=[2, 0], nota="1st Leg"),
              _jogo(2, date(2027, 2, 23), "Clube ABx", "Clube AAx", fase="knockout-round-playoffs", placar=[3, 0],
                    nota="2nd Leg - Clube ABx advance 3-2 on aggregate"),
              _jogo(3, date(2027, 2, 16), "Clube ACx", "Clube ADx", fase="knockout-round-playoffs", placar=[1, 1], nota="1st Leg")]
    pasta = Path(tempfile.mkdtemp())
    F._gravar_temporada(F._arquivo_champions(2026, pasta), 2026, {j["id"]: j for j in jogos})
    d = F.preparar(pd.DataFrame(F.linhas_champions(date(2027, 2, 20), pasta=pasta, atualizar=False)))
    S = dict(d=d, atual=2026)
    ix = {t: i for i, t in enumerate(sorted(set(d["casa"]) | set(d["fora"])))}
    reais = {(a, b): (ja, pernas, v) for a, b, ja, pernas, v in F._confrontos_reais(S, "knockout-round-playoffs", ix)}
    assert reais[(ix["Clube ABx"], ix["Clube AAx"])] == ((3, 2), [], "A")        # AB recebeu a volta e passou
    assert reais[(ix["Clube ADx"], ix["Clube ACx"])] == ((1, 1), ["A"], None)     # só a ida: falta a volta na casa de AD


def test_coleta_junta_sem_apagar_resultado():
    pasta = Path(tempfile.mkdtemp())
    ev = {"id": "9", "data": "2026-11-25T20:00Z", "nome_casa": "Arsenal", "nome_fora": "Bayern Munich", "final": True, "estado": "post",
          "pts_casa": 2, "pts_fora": 1, "fase": "league-phase", "temporada": 2026}
    original = espn.jogos_dos_dias
    try:
        espn.jogos_dos_dias = lambda esporte, dias, tolerante=True: [ev]
        assert F.coletar_champions(2026, date(2026, 11, 25), date(2026, 11, 25), pasta) == 1
        espn.jogos_dos_dias = lambda esporte, dias, tolerante=True: [dict(ev, final=False, pts_casa=None, pts_fora=None, estado="in")]
        F.coletar_champions(2026, date(2026, 11, 25), date(2026, 11, 25), pasta)
        espn.jogos_dos_dias = lambda esporte, dias, tolerante=True: [dict(ev, id="8", fase="qualifying-third-round")]
        F.coletar_champions(2026, date(2026, 8, 5), date(2026, 8, 5), pasta)
    finally:
        espn.jogos_dos_dias = original
    jogos = F._ler_temporada(F._arquivo_champions(2026, pasta))
    assert list(jogos) == ["9"] and jogos["9"]["placar"] == [2, 1] and jogos["9"]["data"] == "2026-11-25"   # 17:00 em Brasília


def test_historico_le_champions_como_as_ligas():
    pasta = Path(tempfile.mkdtemp())
    (pasta / "futebol").mkdir()
    liga = {"meta": {"temporada": 2026}, "times": {"ARS": {"nome": "Arsenal"}, "BAY": {"nome": "Bayern de Munique"}},
            "rodadas": {"5": [{"id": "champions-5-ARS-BAY", "d": "2026-11-25", "h": "17:00", "c": "ARS", "f": "BAY", "pl": None,
                               "p": [0.5, 0.25, 0.25], "espn": "9"}]}}
    (pasta / "futebol" / "champions.json").write_text(json.dumps(liga), encoding="utf-8")
    jogos = list(H.ler_jogos(pasta))
    assert len(jogos) == 1 and jogos[0]["liga"] == "champions" and jogos[0]["probabilidades"]["empate"] == 0.25


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn()
            print("ok", nome)

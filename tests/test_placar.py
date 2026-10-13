"""Testes do placar previsto e do horário de Brasília. Rodar: python tests/test_placar.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import placar as PL  # noqa: E402


def test_placar_respeita_o_palpite():
    for p in (0.5, 0.55, 0.7, 0.9, 0.3, 0.1):
        v, m = PL.placar_previsto(p, 44.0, 12.6)
        assert (m > v) == (p >= 0.5) and m != v


def test_favorito_forte_ganha_por_mais():
    a = PL.placar_previsto(0.6, 220, 12)
    b = PL.placar_previsto(0.85, 220, 12)
    assert (b[1] - b[0]) > (a[1] - a[0]) and abs(sum(b) - 220) <= 1


def test_inclinacao_recupera_k():
    ps = [0.2, 0.35, 0.5, 0.65, 0.8] * 20
    margens = [12 * PL.z(p) for p in ps]
    assert abs(PL.inclinacao(ps, margens) - 12) < 1e-6
    assert PL.erro_medio(ps, margens, 12) < 1e-6


def test_brasilia():
    assert PL.para_brasilia("2026-10-18", "13:00") == ("2026-10-18", "14:00")   # EDT (UTC-4) -> BRT (UTC-3)
    assert PL.para_brasilia("2026-12-06", "13:00") == ("2026-12-06", "15:00")   # EST (UTC-5) -> BRT
    assert PL.para_brasilia("2026-10-18", "23:30") == ("2026-10-19", "00:30")   # vira o dia
    assert PL.para_brasilia("2026-10-18", None) == ("2026-10-18", None)


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn()
            print("ok", nome)

"""Testes dos ajustes por notícias. Rodar: python tests/test_noticias.py"""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import noticias  # noqa: E402

CSV = """# comentário
esporte,liga,time,delta_elo,motivo,fonte,inicio,valido_ate
nba,,BOS,-40,Astro fora,https://x.com/a,2026-10-10,2026-10-20
nba,,BOS,-30,Outro fora,https://x.com/b,,2026-10-15
nba,,LAL,-20,Vencida,,,2026-09-01
futebol,premier,Man City,-25,Goleiro fora,,,2026-11-01
futebol,laliga,Barcelona,-10,Outra liga,,,2026-11-01
nba,,XXX,abc,linha ruim,,,2026-11-01
"""


def _arq():
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(CSV)
    f.close()
    return f.name


def test_carregar_e_janela():
    a = noticias.carregar("nba", hoje=date(2026, 10, 12), arquivo=_arq())
    assert {x["time"] for x in a} == {"BOS"}                      # LAL venceu; a linha ruim foi ignorada
    assert noticias.delta(a, "BOS", "2026-10-12") == -70           # duas notícias valem
    assert noticias.delta(a, "BOS", "2026-10-18") == -40           # a segunda já venceu
    assert noticias.delta(a, "BOS", "2026-10-09") == -30           # a primeira ainda não começou
    assert noticias.delta(a, "BOS", "2026-10-25") == 0
    assert noticias.delta(a, "MIA", "2026-10-12") == 0


def test_filtro_de_liga_e_limite():
    a = noticias.carregar("futebol", "premier", hoje=date(2026, 10, 12), arquivo=_arq())
    assert [x["time"] for x in a] == ["Man City"]
    assert noticias.carregar("futebol", "seriea", hoje=date(2026, 10, 12), arquivo=_arq()) == []
    muitos = [{"time": "A", "delta": -100, "motivo": "", "fonte": "", "inicio": "0000-00-00", "ate": "2099-01-01"}] * 3
    assert noticias.delta(muitos, "A", "2026-10-12") == -noticias.LIMITE


def test_json_e_desconhecidos():
    a = noticias.carregar("nba", hoje=date(2026, 10, 12), arquivo=_arq())
    j = noticias.para_json(a, [("BOS", "BOS", "2026-10-12"), ("MIA", "MIA", "2026-10-12")])
    assert len(j) == 2 and j[0]["t"] == "BOS" and j[0]["f"].startswith("https")
    assert noticias.desconhecidos(a, ["MIA"]) == ["BOS"]


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn()
            print("ok", nome)

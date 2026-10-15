
from datetime import datetime
from zoneinfo import ZoneInfo

from champions.previsor import processar_jogos

FUSO = ZoneInfo("America/Sao_Paulo")


def criar_jogo(identificador, casa, fora, placar):
    return {
        "id": identificador,
        "data": "2025-10-01",
        "hora": "16:00",
        "mandante": casa,
        "visitante": fora,
        "placar": placar,
        "finalizado": True,
        "temporada": "2025-2026",
    }


def test_jogos_simultaneos_independentes():
    agora = datetime(
        2025, 10, 2, tzinfo=FUSO
    )

    primeiro = criar_jogo(
        "1", "Arsenal", "Barcelona", [3, 0]
    )

    segundo = criar_jogo(
        "2", "Arsenal", "Real Madrid", [1, 0]
    )

    resultado_a = processar_jogos(
        [primeiro, segundo], agora
    )

    resultado_b = processar_jogos(
        [segundo, primeiro], agora
    )

    assert resultado_a["elo"] == resultado_b["elo"]

    assert (
        resultado_a["avaliacoes"]
        == resultado_b["avaliacoes"]
    )


def test_resultado_futuro_nao_altera_elo():
    agora = datetime(
        2025, 10, 1, 12, 0, tzinfo=FUSO
    )

    jogo = criar_jogo(
        "3", "Liverpool", "Chelsea", [4, 0]
    )

    resultado = processar_jogos(
        [jogo], agora
    )

    assert resultado["elo"]["Liverpool"] == 1500
    assert resultado["elo"]["Chelsea"] == 1500
    assert len(resultado["avaliacoes"]) == 0

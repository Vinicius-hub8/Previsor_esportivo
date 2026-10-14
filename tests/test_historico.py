
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from historico_previsoes import (
    conectar,
    registrar_previsoes,
    atualizar_resultados,
)

FUSO = ZoneInfo("America/Sao_Paulo")


def criar_jogo(inicio, placar=None):
    return {
        "esporte": "futebol",
        "liga": "teste",
        "jogo_id": "partida-001",
        "temporada": "2026",
        "data_jogo": inicio.strftime("%Y-%m-%d"),
        "hora_jogo": inicio.strftime("%H:%M"),
        "mandante": "Time A",
        "visitante": "Time B",
        "probabilidades": {
            "mandante": 0.60,
            "empate": 0.25,
            "visitante": 0.15,
        },
        "placar": placar,
    }


def test_registrar_previsao(tmp_path):
    banco = tmp_path / "historico.db"
    agora = datetime.now(FUSO)
    inicio = agora + timedelta(days=1)

    with conectar(banco) as conexao:
        novos = registrar_previsoes(
            conexao, [criar_jogo(inicio)], agora
        )

        assert novos == 1

        registro = conexao.execute(
            "SELECT probabilidades FROM previsoes"
        ).fetchone()

        assert json.loads(registro[0])["mandante"] == 0.60


def test_nao_duplicar_previsao(tmp_path):
    banco = tmp_path / "historico.db"
    agora = datetime.now(FUSO)
    jogo = criar_jogo(agora + timedelta(days=1))

    with conectar(banco) as conexao:
        primeiro = registrar_previsoes(
            conexao, [jogo], agora
        )
        segundo = registrar_previsoes(
            conexao, [jogo], agora
        )

        assert primeiro == 1
        assert segundo == 0


def test_nao_registrar_apos_inicio(tmp_path):
    banco = tmp_path / "historico.db"
    agora = datetime.now(FUSO)
    jogo = criar_jogo(agora - timedelta(hours=2))

    with conectar(banco) as conexao:
        novos = registrar_previsoes(
            conexao, [jogo], agora
        )

        assert novos == 0


def test_atualizar_sem_modificar_previsao(tmp_path):
    banco = tmp_path / "historico.db"
    agora = datetime.now(FUSO)
    inicio = agora + timedelta(days=1)

    jogo = criar_jogo(inicio)

    with conectar(banco) as conexao:
        registrar_previsoes(conexao, [jogo], agora)

        original = conexao.execute(
            "SELECT probabilidades FROM previsoes"
        ).fetchone()[0]

        depois = inicio + timedelta(hours=3)

        resultado = criar_jogo(inicio, placar=(2, 1))

        atualizados = atualizar_resultados(
            conexao, [resultado], depois
        )

        assert atualizados == 1

        registro = conexao.execute("""
            SELECT probabilidades,
                   placar_mandante,
                   placar_visitante,
                   finalizado_em
            FROM previsoes
        """).fetchone()

        assert registro[0] == original
        assert registro[1] == 2
        assert registro[2] == 1
        assert registro[3] is not None


def test_nao_sobrescrever_resultado(tmp_path):
    banco = tmp_path / "historico.db"
    agora = datetime.now(FUSO)
    inicio = agora + timedelta(days=1)

    with conectar(banco) as conexao:
        registrar_previsoes(
            conexao, [criar_jogo(inicio)], agora
        )

        depois = inicio + timedelta(hours=3)

        primeiro = atualizar_resultados(
            conexao,
            [criar_jogo(inicio, placar=(2, 1))],
            depois,
        )

        segundo = atualizar_resultados(
            conexao,
            [criar_jogo(inicio, placar=(4, 0))],
            depois,
        )

        placar = conexao.execute("""
            SELECT placar_mandante, placar_visitante
            FROM previsoes
        """).fetchone()

        assert primeiro == 1
        assert segundo == 0
        assert placar == (2, 1)

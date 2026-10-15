
import json
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from historico_previsoes import (
    executar,
    conectar,
)

FUSO = ZoneInfo("America/Sao_Paulo")


def test_champions_preserva_previsao_apos_resultado(tmp_path):
    # Banco e arquivos temporarios:
    # o historico original nunca sera alterado.
    banco = tmp_path / "teste.db"
    pasta = tmp_path / "dados"
    champions = pasta / "champions"

    champions.mkdir(parents=True)

    # Partida marcada para daqui a dois dias.
    inicio = datetime.now(FUSO) + timedelta(days=2)

    data = inicio.strftime("%Y-%m-%d")
    hora = inicio.strftime("%H:%M")

    previsao = {
        "id": "teste-champions-001",
        "data": data,
        "hora": hora,
        "mandante": "Time A",
        "visitante": "Time B",
        "temporada": "2026-2027",
        "probabilidades": {
            "mandante": 55.0,
            "empate": 25.0,
            "visitante": 20.0,
        },
    }

    arquivo_previsoes = pasta / "champions.json"

    arquivo_previsoes.write_text(
        json.dumps({"jogos": [previsao]}),
        encoding="utf-8",
    )

    # Primeiro: registrar o palpite.
    executar(banco=banco, pasta=pasta)

    with conectar(banco) as conexao:
        antes = conexao.execute("""
            SELECT probabilidades, placar_mandante
            FROM previsoes
            WHERE jogo_id = ?
        """, ("teste-champions-001",)).fetchone()

    assert antes is not None
    probabilidades_originais = antes[0]
    assert antes[1] is None

    # Agora simulamos um jogo ja finalizado,
    # com data no passado.
    passado = datetime.now(FUSO) - timedelta(days=2)

    resultado = {
        "id": "teste-champions-001",
        "data": passado.strftime("%Y-%m-%d"),
        "hora": passado.strftime("%H:%M"),
        "mandante": "Time A",
        "visitante": "Time B",
        "finalizado": True,
        "placar": [2, 1],
    }

    (champions / "2026-2027.json").write_text(
        json.dumps({"jogos": [resultado]}),
        encoding="utf-8",
    )

    # O jogo nao aparece mais entre as
    # previsoes futuras.
    arquivo_previsoes.write_text(
        json.dumps({"jogos": []}),
        encoding="utf-8",
    )

    executar(banco=banco, pasta=pasta)

    with sqlite3.connect(banco) as conexao:
        depois = conexao.execute("""
            SELECT
                probabilidades,
                placar_mandante,
                placar_visitante,
                finalizado_em
            FROM previsoes
            WHERE jogo_id = ?
        """, ("teste-champions-001",)).fetchone()

    assert depois is not None

    # O palpite deve continuar exatamente igual.
    assert depois[0] == probabilidades_originais

    # O resultado deve ter sido preenchido.
    assert depois[1] == 2
    assert depois[2] == 1
    assert depois[3] is not None

    # Executar outra vez nao pode duplicar
    # registros nem alterar o resultado.
    executar(banco=banco, pasta=pasta)

    with sqlite3.connect(banco) as conexao:
        quantidade = conexao.execute("""
            SELECT COUNT(*)
            FROM previsoes
            WHERE jogo_id = ?
        """, ("teste-champions-001",)).fetchone()[0]

    assert quantidade == 1

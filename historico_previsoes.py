
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "web" / "public" / "dados"
BANCO = RAIZ / "historico.db"
FUSO = ZoneInfo("America/Sao_Paulo")


def conectar(banco=BANCO):
    conexao = sqlite3.connect(banco)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS previsoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            esporte TEXT NOT NULL,
            liga TEXT NOT NULL,
            jogo_id TEXT NOT NULL,
            temporada TEXT NOT NULL,
            data_jogo TEXT NOT NULL,
            mandante TEXT NOT NULL,
            visitante TEXT NOT NULL,
            probabilidades TEXT NOT NULL,
            registrado_em TEXT NOT NULL,
            placar_mandante INTEGER,
            placar_visitante INTEGER,
            finalizado_em TEXT,
            UNIQUE(esporte, liga, jogo_id)
        )
    """)

    colunas = {
        linha[1]
        for linha in conexao.execute(
            "PRAGMA table_info(previsoes)"
        )
    }

    novas_colunas = {
        "placar_mandante": "INTEGER",
        "placar_visitante": "INTEGER",
        "finalizado_em": "TEXT",
    }

    for nome, tipo in novas_colunas.items():
        if nome not in colunas:
            conexao.execute(
                f"ALTER TABLE previsoes ADD COLUMN {nome} {tipo}"
            )

    conexao.commit()
    return conexao


def carregar_json(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def ler_jogos(pasta=DADOS):
    """
    Retorna partidas de NFL, NBA e futebol,
    independentemente de estarem finalizadas.
    """
    for esporte in ("nfl", "nba"):
        caminho = pasta / f"{esporte}.json"

        if not caminho.exists():
            continue

        dados = carregar_json(caminho)
        times = dados["times"]

        for temporada, semanas in dados["semanas"].items():
            for grupo in semanas.values():
                jogos = (
                    grupo
                    if isinstance(grupo, list)
                    else grupo["jogos"]
                )

                for jogo in jogos:
                    placar = jogo.get("placar")

                    yield {
                        "esporte": esporte,
                        "liga": esporte,
                        "jogo_id": str(jogo["id"]),
                        "temporada": str(temporada),
                        "data_jogo": jogo.get("db") or jogo["data"],
                        "hora_jogo": jogo.get("hb"),
                        "mandante": times[jogo["m"]]["nome"],
                        "visitante": times[jogo["v"]]["nome"],
                        "probabilidades": (
                            None if jogo.get("p") is None else {
                                "mandante": jogo["p"],
                                "visitante": 1 - jogo["p"],
                            }
                        ),
                        # O JSON usa visitante, mandante
                        "placar": (
                            None if placar is None else (
                                placar[1], placar[0]
                            )
                        ),
                    }

    pasta_futebol = pasta / "futebol"

    if not pasta_futebol.exists():
        return

    for caminho in sorted(pasta_futebol.glob("*.json")):
        dados = carregar_json(caminho)
        times = dados["times"]
        liga = caminho.stem

        for jogos in dados["rodadas"].values():
            for jogo in jogos:
                placar = jogo.get("pl")
                prob = jogo.get("p")

                yield {
                    "esporte": "futebol",
                    "liga": liga,
                    "jogo_id": str(jogo["id"]),
                    "temporada": str(
                        dados["meta"]["temporada"]
                    ),
                    "data_jogo": jogo["d"],
                    "hora_jogo": jogo.get("h"),
                    "mandante": times[jogo["c"]]["nome"],
                    "visitante": times[jogo["f"]]["nome"],
                    "probabilidades": (
                        None if prob is None else {
                            "mandante": prob[0],
                            "empate": prob[1],
                            "visitante": prob[2],
                        }
                    ),
                    # O JSON usa mandante, visitante
                    "placar": (
                        None if placar is None else (
                            placar[0], placar[1]
                        )
                    ),
                    "adiado": jogo.get("adiado", False),
                }


def inicio_partida(jogo):
    """
    Converte data e hora do jogo para
    um datetime com fuso de Brasilia.
    """
    hora = jogo.get("hora_jogo")

    if not hora:
        return None

    try:
        return datetime.fromisoformat(
            f"{jogo['data_jogo']}T{hora}"
        ).replace(tzinfo=FUSO)
    except (ValueError, TypeError):
        return None


def registrar_previsoes(conexao, jogos, agora):
    total = 0

    for jogo in jogos:
        if jogo.get("adiado"):
            continue

        if jogo["placar"] is not None:
            continue

        probabilidades = jogo["probabilidades"]

        if not probabilidades:
            continue

        inicio = inicio_partida(jogo)

        # Sem horario confirmado, nao registra
        if inicio is None or inicio <= agora:
            continue

        cursor = conexao.execute("""
            INSERT OR IGNORE INTO previsoes (
                esporte, liga, jogo_id, temporada,
                data_jogo, mandante, visitante,
                probabilidades, registrado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jogo["esporte"],
            jogo["liga"],
            jogo["jogo_id"],
            jogo["temporada"],
            jogo["data_jogo"],
            jogo["mandante"],
            jogo["visitante"],
            json.dumps(
                probabilidades, ensure_ascii=False
            ),
            agora.isoformat(timespec="seconds"),
        ))

        total += cursor.rowcount

    return total


def atualizar_resultados(conexao, jogos, agora):
    total = 0

    for jogo in jogos:
        placar = jogo["placar"]

        # Sem resultado final no JSON
        if placar is None:
            continue

        # Confirma que a partida ja comecou
        inicio = inicio_partida(jogo)

        if inicio is None or inicio > agora:
            continue

        # Nao altera probabilidades nem
        # registros com resultado ja salvo
        cursor = conexao.execute("""
            UPDATE previsoes
            SET
                placar_mandante = ?,
                placar_visitante = ?,
                finalizado_em = ?
            WHERE esporte = ?
              AND liga = ?
              AND jogo_id = ?
              AND placar_mandante IS NULL
              AND placar_visitante IS NULL
              AND finalizado_em IS NULL
        """, (
            int(placar[0]),
            int(placar[1]),
            agora.isoformat(timespec="seconds"),
            jogo["esporte"],
            jogo["liga"],
            jogo["jogo_id"],
        ))

        total += cursor.rowcount

    return total


def executar(banco=BANCO, pasta=DADOS):
    agora = datetime.now(FUSO)

    # Carrega os dados apenas uma vez
    jogos = list(ler_jogos(pasta))

    with conectar(banco) as conexao:
        novos = registrar_previsoes(
            conexao, jogos, agora
        )

        finalizados = atualizar_resultados(
            conexao, jogos, agora
        )

        conexao.commit()

        total = conexao.execute("""
            SELECT COUNT(*) FROM previsoes
        """).fetchone()[0]

        total_finalizados = conexao.execute("""
            SELECT COUNT(*) FROM previsoes
            WHERE finalizado_em IS NOT NULL
        """).fetchone()[0]

    print("=== HISTORICO DE PREVISOES ===")
    print(f"Novas previsoes: {novos}")
    print(f"Novos resultados: {finalizados}")
    print(f"Total de previsoes: {total}")
    print(f"Total finalizados: {total_finalizados}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--banco",
        type=Path,
        default=BANCO,
        help="Caminho do banco SQLite"
    )

    args = parser.parse_args()
    executar(banco=args.banco)

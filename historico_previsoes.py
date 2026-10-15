
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


def ler_esportes_americanos(pasta):
    """
    Le NFL e NBA preservando o formato
    original das probabilidades e placares.
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
                        "data_jogo": (
                            jogo.get("db") or jogo["data"]
                        ),
                        "hora_jogo": jogo.get("hb"),
                        "mandante": times[jogo["m"]]["nome"],
                        "visitante": times[jogo["v"]]["nome"],
                        "probabilidades": (
                            None
                            if jogo.get("p") is None
                            else {
                                "mandante": jogo["p"],
                                "visitante": 1 - jogo["p"],
                            }
                        ),
                        # O JSON usa visitante, mandante.
                        "placar": (
                            None
                            if placar is None
                            else (placar[1], placar[0])
                        ),
                    }


def ler_futebol(pasta):
    """
    Le as ligas nacionais de futebol.
    """
    pasta_futebol = pasta / "futebol"

    if not pasta_futebol.exists():
        return

    for caminho in sorted(
        pasta_futebol.glob("*.json")
    ):
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
                        None
                        if prob is None
                        else {
                            "mandante": prob[0],
                            "empate": prob[1],
                            "visitante": prob[2],
                        }
                    ),
                    # O JSON usa mandante, visitante.
                    "placar": (
                        None
                        if placar is None
                        else (placar[0], placar[1])
                    ),
                    "adiado": jogo.get(
                        "adiado", False
                    ),
                }


def ler_champions(pasta):
    """
    Le previsoes futuras e resultados
    historicos da Champions League.

    Mesmo que uma partida desapareca de
    champions.json, seu resultado continua
    disponivel nos arquivos por temporada.

    Nunca cria previsoes retroativas.
    """
    arquivo_previsoes = pasta / "champions.json"
    pasta_champions = pasta / "champions"

    resultados = {}
    ids_exportados = set()

    # 1. Carregar os resultados confirmados
    # dos arquivos historicos.
    if pasta_champions.exists():
        for caminho in sorted(
            pasta_champions.glob("20??-20??.json")
        ):
            dados_temporada = carregar_json(caminho)

            for jogo in dados_temporada.get("jogos", []):
                if not jogo.get("finalizado"):
                    continue

                placar = jogo.get("placar")

                if (
                    not isinstance(
                        placar, (list, tuple)
                    )
                    or len(placar) != 2
                    or placar[0] is None
                    or placar[1] is None
                ):
                    continue

                identificador = str(jogo["id"])

                resultados[identificador] = {
                    "jogo": jogo,
                    "temporada": caminho.stem,
                    "placar": (
                        int(placar[0]),
                        int(placar[1]),
                    ),
                }

    # 2. Ler previsoes exportadas.
    if arquivo_previsoes.exists():
        dados = carregar_json(
            arquivo_previsoes
        )

        for jogo in dados.get("jogos", []):
            identificador = str(jogo["id"])
            ids_exportados.add(identificador)

            p = jogo.get("probabilidades")
            probabilidades = None

            if isinstance(p, dict):
                try:
                    # champions.json armazena
                    # porcentagens de 0 a 100.
                    probabilidades = {
                        "mandante": float(
                            p["mandante"]
                        ) / 100.0,
                        "empate": float(
                            p["empate"]
                        ) / 100.0,
                        "visitante": float(
                            p["visitante"]
                        ) / 100.0,
                    }
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    pass

            resultado = resultados.get(
                identificador
            )

            yield {
                "esporte": "futebol",
                "liga": "champions",
                "jogo_id": identificador,
                "temporada": str(
                    jogo["temporada"]
                ),
                "data_jogo": jogo["data"],
                "hora_jogo": jogo.get("hora"),
                "mandante": jogo["mandante"],
                "visitante": jogo["visitante"],
                "probabilidades": probabilidades,
                "placar": (
                    resultado["placar"]
                    if resultado else None
                ),
            }

    # 3. Ler resultados de partidas que
    # nao estao mais no JSON de previsoes.
    for identificador, resultado in resultados.items():
        if identificador in ids_exportados:
            continue

        jogo = resultado["jogo"]

        yield {
            "esporte": "futebol",
            "liga": "champions",
            "jogo_id": identificador,
            "temporada": resultado[
                "temporada"
            ],
            "data_jogo": jogo["data"],
            "hora_jogo": jogo.get("hora"),
            "mandante": jogo["mandante"],
            "visitante": jogo["visitante"],
            # Nunca gerar probabilidades
            # depois do resultado conhecido.
            "probabilidades": None,
            "placar": resultado["placar"],
        }


def ler_jogos(pasta=DADOS):
    """
    Retorna as partidas de todos
    os esportes disponiveis.
    """
    yield from ler_esportes_americanos(pasta)
    yield from ler_futebol(pasta)
    yield from ler_champions(pasta)


def inicio_partida(jogo):
    """
    Converte a data e o horario da partida
    para o fuso horario de Brasilia.
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
    """
    Registra apenas previsoes anteriores
    ao inicio das partidas.

    Nunca substitui probabilidades antigas.
    """
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

        if inicio is None or inicio <= agora:
            continue

        cursor = conexao.execute("""
            INSERT OR IGNORE INTO previsoes (
                esporte,
                liga,
                jogo_id,
                temporada,
                data_jogo,
                mandante,
                visitante,
                probabilidades,
                registrado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jogo["esporte"],
            jogo["liga"],
            jogo["jogo_id"],
            jogo["temporada"],
            jogo["data_jogo"],
            jogo["mandante"],
            jogo["visitante"],
            json.dumps(
                probabilidades,
                ensure_ascii=False
            ),
            agora.isoformat(
                timespec="seconds"
            ),
        ))

        total += cursor.rowcount

    return total


def atualizar_resultados(conexao, jogos, agora):
    """
    Atualiza somente o resultado
    das previsoes ja registradas.

    As probabilidades permanecem intactas.
    """
    total = 0

    for jogo in jogos:
        placar = jogo["placar"]

        if placar is None:
            continue

        inicio = inicio_partida(jogo)

        if inicio is None or inicio > agora:
            continue

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
            agora.isoformat(
                timespec="seconds"
            ),
            jogo["esporte"],
            jogo["liga"],
            jogo["jogo_id"],
        ))

        total += cursor.rowcount

    return total


def executar(banco=BANCO, pasta=DADOS):
    agora = datetime.now(FUSO)

    # Carrega os dados uma unica vez.
    jogos = list(
        ler_jogos(pasta)
    )

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

        total_champions = conexao.execute("""
            SELECT COUNT(*) FROM previsoes
            WHERE esporte = 'futebol'
              AND liga = 'champions'
        """).fetchone()[0]

    print("=== HISTORICO DE PREVISOES ===")
    print(f"Novas previsoes: {novos}")
    print(f"Novos resultados: {finalizados}")
    print(f"Total de previsoes: {total}")
    print(
        f"Total finalizados: {total_finalizados}"
    )
    print(
        f"Previsoes Champions: {total_champions}"
    )


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

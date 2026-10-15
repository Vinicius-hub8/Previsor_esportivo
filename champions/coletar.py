
import argparse
import json
import time
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

URL = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/soccer/uefa.champions/scoreboard"
)

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "web" / "public" / "dados" / "champions"
SAIDA = PASTA / "temporada.json"
FUSO = ZoneInfo("America/Sao_Paulo")


def baixar_partidas(dia):
    parametro = dia.strftime("%Y%m%d")
    requisicao = urllib.request.Request(
        f"{URL}?dates={parametro}",
        headers={"User-Agent": "FatorCasa/1.0"},
    )

    with urllib.request.urlopen(
        requisicao, timeout=20
    ) as resposta:
        return json.load(resposta)


def converter_partida(evento):
    competicoes = evento.get("competitions") or []

    if not competicoes:
        return None

    competicao = competicoes[0]
    participantes = competicao.get("competitors") or []

    times = {
        p.get("homeAway"): p
        for p in participantes
    }

    casa = times.get("home")
    fora = times.get("away")

    if not casa or not fora:
        return None

    def nome(participante):
        equipe = participante.get("team") or {}
        return (
            equipe.get("displayName")
            or equipe.get("name")
            or "Desconhecido"
        )

    data_original = evento.get("date")
    identificador = evento.get("id")

    if not data_original or identificador is None:
        return None

    inicio = datetime.fromisoformat(
        data_original.replace("Z", "+00:00")
    ).astimezone(FUSO)

    status = (evento.get("status") or {}).get(
        "type"
    ) or {}

    estado = status.get("state", "pre")
    finalizado = bool(status.get("completed", False))

    def gols(participante):
        valor = participante.get("score")
        try:
            return int(valor)
        except (ValueError, TypeError):
            return None

    placar = None

    if finalizado:
        gc = gols(casa)
        gf = gols(fora)

        if gc is not None and gf is not None:
            placar = [gc, gf]

    return {
        "id": str(identificador),
        "data": inicio.strftime("%Y-%m-%d"),
        "hora": inicio.strftime("%H:%M"),
        "mandante": nome(casa),
        "visitante": nome(fora),
        "estado": estado,
        "finalizado": finalizado,
        "placar": placar,
    }


def carregar_anteriores():
    if not SAIDA.exists():
        return {}

    with open(SAIDA, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    return {
        jogo["id"]: jogo
        for jogo in dados.get("jogos", [])
    }


def combinar(antigo, novo):
    # Nao substitui um resultado final
    # por uma informacao incompleta.
    if antigo and antigo.get("finalizado"):
        if not novo.get("finalizado"):
            return antigo

        if novo.get("placar") is None:
            return antigo

    return novo


def coletar_periodo(inicio, fim):
    jogos = carregar_anteriores()
    consultados = 0

    # Consulta um dia extra: partidas perto da
    # meia-noite UTC podem cair no dia anterior
    # no horario de Brasilia.
    dia = inicio
    ultimo_dia = fim + timedelta(days=1)

    while dia <= ultimo_dia:
        dados = baixar_partidas(dia)
        consultados += 1

        for evento in dados.get("events", []):
            jogo = converter_partida(evento)

            if jogo is None:
                continue

            data_br = date.fromisoformat(
                jogo["data"]
            )

            if not inicio <= data_br <= fim:
                continue

            identificador = jogo["id"]
            jogos[identificador] = combinar(
                jogos.get(identificador),
                jogo
            )

        print(f"Consultado: {dia.isoformat()}")

        dia += timedelta(days=1)

        if dia <= ultimo_dia:
            time.sleep(0.2)

    return jogos, consultados


def salvar(jogos, inicio, fim):
    PASTA.mkdir(parents=True, exist_ok=True)

    lista = sorted(
        jogos.values(),
        key=lambda j: (
            j["data"],
            j["hora"],
            j["id"]
        )
    )

    resultado = {
        "meta": {
            "competicao": "UEFA Champions League",
            "fonte": "ESPN",
            "ultima_consulta": datetime.now(
                FUSO
            ).isoformat(timespec="seconds"),
            "intervalo_consultado": {
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
            },
            "fuso": "America/Sao_Paulo",
            "quantidade": len(lista),
        },
        "jogos": lista,
    }

    temporario = SAIDA.with_suffix(".tmp")

    with open(
        temporario, "w", encoding="utf-8"
    ) as arquivo:
        json.dump(
            resultado,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    temporario.replace(SAIDA)

    return lista


def main():
    parser = argparse.ArgumentParser(
        description="Coletor da Champions League"
    )

    parser.add_argument(
        "--inicio",
        required=True,
        help="Data inicial: AAAA-MM-DD"
    )

    parser.add_argument(
        "--fim",
        required=True,
        help="Data final: AAAA-MM-DD"
    )

    args = parser.parse_args()

    inicio = date.fromisoformat(args.inicio)
    fim = date.fromisoformat(args.fim)

    if fim < inicio:
        parser.error(
            "A data final deve ser igual ou posterior "
            "a data inicial."
        )

    if (fim - inicio).days > 30:
        parser.error(
            "Consulte no maximo 31 dias por execucao."
        )

    print("=== COLETOR CHAMPIONS LEAGUE ===")

    jogos, consultas = coletar_periodo(
        inicio, fim
    )

    lista = salvar(jogos, inicio, fim)

    finalizados = sum(
        1 for j in lista if j["finalizado"]
    )

    futuros = sum(
        1 for j in lista if j["estado"] == "pre"
    )

    print("\n=== RESULTADO ===")
    print(f"Consultas realizadas: {consultas}")
    print(f"Partidas armazenadas: {len(lista)}")
    print(f"Finalizadas: {finalizados}")
    print(f"Agendadas: {futuros}")
    print(f"Arquivo: {SAIDA}")


if __name__ == "__main__":
    main()

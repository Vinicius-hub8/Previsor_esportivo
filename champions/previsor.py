
import json
import math
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "web" / "public" / "dados" / "champions"

FUSO = ZoneInfo("America/Sao_Paulo")

ELO_INICIAL = 1500.0
K_ELO = 28.0
VANTAGEM_CASA = 75.0
MEDIA_GOLS = 1.65
MAX_GOLS = 10

RESULTADOS = ("mandante", "empate", "visitante")


def carregar_jogos(pasta=PASTA):
    jogos = []
    ids = set()

    for arquivo in sorted(pasta.glob("20??-20??.json")):
        with open(arquivo, encoding="utf-8") as f:
            dados = json.load(f)

        for jogo in dados["jogos"]:
            identificador = str(jogo["id"])

            if identificador in ids:
                raise ValueError(
                    f"Partida duplicada: {identificador}"
                )

            ids.add(identificador)

            item = jogo.copy()
            item["temporada"] = arquivo.stem
            jogos.append(item)

    return sorted(
        jogos,
        key=lambda j: (
            j["data"],
            j["hora"] or "00:00",
            j["id"]
        )
    )


def horario_partida(jogo):
    if not jogo.get("hora"):
        return None

    return datetime.fromisoformat(
        f"{jogo['data']}T{jogo['hora']}"
    ).replace(tzinfo=FUSO)


def poisson(media, gols):
    return (
        math.exp(-media)
        * media ** gols
        / math.factorial(gols)
    )


def probabilidades(elo_casa, elo_fora):
    diferenca = (
        elo_casa - elo_fora + VANTAGEM_CASA
    )

    fator = max(
        -2.0,
        min(2.0, diferenca / 500.0)
    )

    gols_casa = MEDIA_GOLS * math.exp(fator / 2)
    gols_fora = MEDIA_GOLS * math.exp(-fator / 2)

    chances = {
        "mandante": 0.0,
        "empate": 0.0,
        "visitante": 0.0
    }

    placar_provavel = [0, 0]
    maior_prob = -1.0

    for gc in range(MAX_GOLS + 1):
        for gf in range(MAX_GOLS + 1):
            p = (
                poisson(gols_casa, gc)
                * poisson(gols_fora, gf)
            )

            if gc > gf:
                chances["mandante"] += p
            elif gc == gf:
                chances["empate"] += p
            else:
                chances["visitante"] += p

            if p > maior_prob:
                maior_prob = p
                placar_provavel = [gc, gf]

    total = sum(chances.values())

    for resultado in RESULTADOS:
        chances[resultado] /= total

    chances["gols_esperados"] = [
        round(gols_casa, 2),
        round(gols_fora, 2)
    ]

    chances["placar_provavel"] = placar_provavel

    return chances


def resultado_real(placar):
    gc, gf = placar

    if gc > gf:
        return "mandante"

    if gc < gf:
        return "visitante"

    return "empate"


def variacao_elo(elo_casa, elo_fora, placar):
    gc, gf = placar

    esperado = 1 / (
        1 + 10 ** (
            (elo_fora - elo_casa - VANTAGEM_CASA)
            / 400
        )
    )

    resultado = (
        1.0 if gc > gf
        else 0.5 if gc == gf
        else 0.0
    )

    peso = min(
        2.0,
        1 + 0.25 * abs(gc - gf)
    )

    return K_ELO * peso * (resultado - esperado)


def processar_jogos(jogos, agora=None):
    """
    Processa partidas cronologicamente.

    Todos os jogos com o mesmo horario sao previstos
    usando o mesmo estado anterior do ranking Elo.

    Apenas depois sao aplicadas as atualizacoes.
    """

    if agora is None:
        agora = datetime.now(FUSO)

    elo = defaultdict(lambda: ELO_INICIAL)

    avaliacoes = []
    futuras = []

    jogos = sorted(
        jogos,
        key=lambda j: (
            j["data"],
            j["hora"] or "00:00",
            j["id"]
        )
    )

    for _, grupo in groupby(
        jogos,
        key=lambda j: (j["data"], j["hora"])
    ):
        grupo = list(grupo)

        previsoes_grupo = []

        # ETAPA A:
        # Prever todas as partidas antes de
        # atualizar qualquer resultado do grupo.
        for jogo in grupo:
            casa = jogo["mandante"]
            fora = jogo["visitante"]

            p = probabilidades(
                elo[casa],
                elo[fora]
            )

            previsoes_grupo.append((jogo, p))

        atualizacoes = []

        # ETAPA B:
        # Avaliar e preparar as atualizacoes.
        for jogo, p in previsoes_grupo:
            placar = jogo.get("placar")
            finalizado = jogo.get(
                "finalizado", False
            )

            inicio = horario_partida(jogo)

            if inicio is None:
                continue

            # Nunca aproveitar resultados de partidas
            # cujo horario ainda esta no futuro.
            if inicio > agora:
                continue

            if finalizado and placar is not None:
                real = resultado_real(placar)

                palpite = max(
                    RESULTADOS,
                    key=lambda resultado: p[resultado]
                )

                if jogo["temporada"] >= "2025-2026":
                    avaliacoes.append({
                        "id": jogo["id"],
                        "temporada": jogo["temporada"],
                        "acertou": palpite == real,
                        "prob_real": p[real],
                    })

                atualizacoes.append((
                    jogo["mandante"],
                    jogo["visitante"],
                    placar,
                ))

            elif not finalizado and inicio > agora:
                # Este ramo nao e usado porque
                # jogos futuros sao tratados abaixo.
                pass

        # ETAPA C:
        # Atualizar todos os Elo simultaneamente,
        # usando os valores anteriores ao grupo.
        deltas = defaultdict(float)

        for casa, fora, placar in atualizacoes:
            delta = variacao_elo(
                elo[casa],
                elo[fora],
                placar
            )

            deltas[casa] += delta
            deltas[fora] -= delta

        for time, delta in deltas.items():
            elo[time] += delta

        # ETAPA D:
        # Preparar as partidas futuras.
        # Estas probabilidades sao recalculadas
        # com os Elo disponiveis no momento atual.
        for jogo, _ in previsoes_grupo:
            inicio = horario_partida(jogo)

            if inicio is None or inicio <= agora:
                continue

            if jogo.get("finalizado"):
                continue

            casa = jogo["mandante"]
            fora = jogo["visitante"]

            p = probabilidades(
                elo[casa],
                elo[fora]
            )

            futuras.append({
                "id": jogo["id"],
                "data": jogo["data"],
                "hora": jogo["hora"],
                "mandante": casa,
                "visitante": fora,
                "temporada": jogo["temporada"],
                "probabilidades": p,
                "elo_mandante": round(elo[casa], 1),
                "elo_visitante": round(elo[fora], 1),
            })

    return dict(
        elo=dict(elo),
        avaliacoes=avaliacoes,
        futuras=futuras
    )


def prever():
    jogos = carregar_jogos()
    return processar_jogos(jogos)


def avaliar(avaliacoes):
    temporadas = sorted({
        j["temporada"]
        for j in avaliacoes
    })

    for temporada in temporadas:
        amostra = [
            j for j in avaliacoes
            if j["temporada"] == temporada
        ]

        n = len(amostra)
        acertos = sum(
            j["acertou"] for j in amostra
        )

        log_loss = -sum(
            math.log(
                max(j["prob_real"], 1e-12)
            )
            for j in amostra
        ) / n

        print(
            f"{temporada}: "
            f"{acertos}/{n} "
            f"({acertos / n:.1%}) "
            f"| Log Loss: {log_loss:.4f}"
        )


def main():
    resultado = prever()

    ranking = sorted(
        resultado["elo"].items(),
        key=lambda x: x[1],
        reverse=True
    )

    print("=== FATOR CASA | CHAMPIONS LEAGUE ===")

    print("\nRANKING ELO")

    for pos, (time, pontos) in enumerate(
        ranking[:15], start=1
    ):
        print(
            f"{pos:2}. {time:25} {pontos:.1f}"
        )

    print("\nAVALIACAO HISTORICA")
    avaliar(resultado["avaliacoes"])

    futuras = resultado["futuras"]

    print(
        f"\nPARTIDAS FUTURAS: {len(futuras)}"
    )

    for jogo in futuras:
        p = jogo["probabilidades"]

        print(
            f"\n{jogo['data']} {jogo['hora']} | "
            f"{jogo['mandante']} x "
            f"{jogo['visitante']}"
        )

        print(
            f"Casa: {p['mandante']:.1%} | "
            f"Empate: {p['empate']:.1%} | "
            f"Fora: {p['visitante']:.1%}"
        )


if __name__ == "__main__":
    main()

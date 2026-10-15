
import math
from collections import defaultdict
from itertools import groupby

from previsor import carregar_jogos, poisson, MAX_GOLS


# Temporadas usadas na calibracao
TEMP_VALIDACAO = "2024-2025"
TEMP_TESTE = "2025-2026"

# Configuracoes que vamos comparar
VALORES_K = [12, 20, 28]
VANTAGENS_CASA = [35, 55, 75]
MEDIAS_GOLS = [1.25, 1.45, 1.65]

ELO_INICIAL = 1500.0


def calcular_probabilidades(
    elo_casa,
    elo_fora,
    vantagem,
    media_gols
):
    diferenca = elo_casa - elo_fora + vantagem

    fator = max(
        -2.0,
        min(2.0, diferenca / 500.0)
    )

    gols_casa = media_gols * math.exp(fator / 2)
    gols_fora = media_gols * math.exp(-fator / 2)

    chances = [0.0, 0.0, 0.0]

    for gc in range(MAX_GOLS + 1):
        for gf in range(MAX_GOLS + 1):
            p = (
                poisson(gols_casa, gc)
                * poisson(gols_fora, gf)
            )

            if gc > gf:
                chances[0] += p
            elif gc == gf:
                chances[1] += p
            else:
                chances[2] += p

    total = sum(chances)

    return [p / total for p in chances]


def resultado_real(placar):
    gc, gf = placar

    if gc > gf:
        return 0
    if gc == gf:
        return 1
    return 2


def calcular_delta(
    elo_casa,
    elo_fora,
    placar,
    k,
    vantagem
):
    gc, gf = placar

    esperado = 1 / (
        1 + 10 ** (
            (elo_fora - elo_casa - vantagem) / 400
        )
    )

    resultado = (
        1.0 if gc > gf
        else 0.5 if gc == gf
        else 0.0
    )

    peso = min(2.0, 1 + 0.25 * abs(gc - gf))

    return k * peso * (resultado - esperado)


def avaliar_configuracao(
    jogos,
    k,
    vantagem,
    media_gols,
    temporada_alvo
):
    elo = defaultdict(lambda: ELO_INICIAL)

    acertos = 0
    total = 0
    perda = 0.0

    # Processar somente ate a temporada avaliada.
    historico = sorted(
        (
            j for j in jogos
            if j["temporada"] <= temporada_alvo
            and j.get("finalizado")
            and j.get("placar") is not None
            and j.get("hora")
        ),
        key=lambda j: (
            j["data"],
            j["hora"],
            j["id"]
        )
    )

    # Os jogos do mesmo horario usam
    # os mesmos Elo anteriores.
    for _, grupo_iter in groupby(
        historico,
        key=lambda j: (j["data"], j["hora"])
    ):
        grupo = list(grupo_iter)

        deltas = defaultdict(float)

        for jogo in grupo:
            casa = jogo["mandante"]
            fora = jogo["visitante"]

            ec = elo[casa]
            ef = elo[fora]

            if jogo["temporada"] == temporada_alvo:
                chances = calcular_probabilidades(
                    ec, ef, vantagem, media_gols
                )

                real = resultado_real(jogo["placar"])
                palpite = max(
                    range(3), key=lambda i: chances[i]
                )

                acertos += int(palpite == real)
                perda -= math.log(
                    max(chances[real], 1e-12)
                )
                total += 1

            delta = calcular_delta(
                ec, ef, jogo["placar"],
                k, vantagem
            )

            deltas[casa] += delta
            deltas[fora] -= delta

        for time, delta in deltas.items():
            elo[time] += delta

    if total == 0:
        raise ValueError(
            f"Nenhuma partida avaliada: {temporada_alvo}"
        )

    return {
        "k": k,
        "vantagem": vantagem,
        "media_gols": media_gols,
        "jogos": total,
        "acertos": acertos,
        "acuracia": acertos / total,
        "log_loss": perda / total,
    }


def main():
    jogos = carregar_jogos()

    print("=== CALIBRACAO CHAMPIONS LEAGUE ===")
    print(f"Partidas carregadas: {len(jogos)}")

    resultados = []

    for k in VALORES_K:
        for vantagem in VANTAGENS_CASA:
            for media in MEDIAS_GOLS:
                resultado = avaliar_configuracao(
                    jogos,
                    k,
                    vantagem,
                    media,
                    TEMP_VALIDACAO
                )
                resultados.append(resultado)

    resultados.sort(key=lambda r: r["log_loss"])

    print("\nMELHORES CONFIGURACOES - 2024/25")

    for pos, r in enumerate(resultados[:5], 1):
        print(
            f"{pos}. K={r['k']}, "
            f"Casa={r['vantagem']}, "
            f"Gols={r['media_gols']:.2f} | "
            f"Acerto={r['acuracia']:.1%} | "
            f"Log Loss={r['log_loss']:.4f}"
        )

    melhor = resultados[0]

    print("\nTESTE INDEPENDENTE - 2025/26")

    teste = avaliar_configuracao(
        jogos,
        melhor["k"],
        melhor["vantagem"],
        melhor["media_gols"],
        TEMP_TESTE
    )

    print(f"Jogos avaliados: {teste['jogos']}")
    print(f"Acertos: {teste['acertos']}")
    print(f"Acuracia: {teste['acuracia']:.1%}")
    print(f"Log Loss: {teste['log_loss']:.4f}")

    print("\nCOMPARACAO COM PARAMETROS ORIGINAIS")

    original = avaliar_configuracao(
        jogos,
        20,
        55,
        1.45,
        TEMP_TESTE
    )

    print(
        f"Original: {original['acuracia']:.1%} | "
        f"Log Loss: {original['log_loss']:.4f}"
    )

    print(
        f"Calibrado: {teste['acuracia']:.1%} | "
        f"Log Loss: {teste['log_loss']:.4f}"
    )

    print("\nNenhum parametro foi alterado automaticamente.")


if __name__ == "__main__":
    main()

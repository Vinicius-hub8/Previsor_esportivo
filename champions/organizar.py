
import json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "web" / "public" / "dados" / "champions"
ORIGEM = PASTA / "temporada.json"


def identificar_temporada(data):
    ano, mes, _ = map(int, data.split("-"))

    # Temporada europeia comeca no segundo semestre
    inicio = ano if mes >= 7 else ano - 1

    return f"{inicio}-{inicio + 1}"


def organizar():
    with open(ORIGEM, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    temporadas = defaultdict(list)

    for jogo in dados["jogos"]:
        temporada = identificar_temporada(jogo["data"])
        temporadas[temporada].append(jogo)

    for temporada, jogos in sorted(temporadas.items()):
        jogos.sort(
            key=lambda j: (
                j["data"],
                j["hora"],
                j["id"]
            )
        )

        saida = PASTA / f"{temporada}.json"

        conteudo = {
            "meta": {
                "competicao": "UEFA Champions League",
                "temporada": temporada,
                "quantidade": len(jogos),
                "finalizadas": sum(
                    bool(j.get("finalizado"))
                    for j in jogos
                ),
                "fonte": "ESPN"
            },
            "jogos": jogos
        }

        with open(
            saida, "w", encoding="utf-8"
        ) as arquivo:
            json.dump(
                conteudo,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"{temporada}: {len(jogos)} partidas "
            f"({conteudo['meta']['finalizadas']} finalizadas)"
        )

    print("\nTemporadas organizadas com sucesso!")


if __name__ == "__main__":
    organizar()

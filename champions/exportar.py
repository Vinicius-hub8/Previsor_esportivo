
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from previsor import (
    carregar_jogos,
    processar_jogos,
    probabilidades,
)

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = (
    RAIZ / "web" / "public" / "dados"
    / "champions.json"
)
FUSO = ZoneInfo("America/Sao_Paulo")


def main():
    agora = datetime.now(FUSO)

    jogos = carregar_jogos()
    resultado = processar_jogos(jogos, agora)

    previsoes = []
    elo = resultado["elo"]

    for jogo in jogos:
        if jogo.get("finalizado"):
            continue

        data_hora = datetime.fromisoformat(
            f"{jogo['data']}T{jogo['hora']}"
        ).replace(tzinfo=FUSO)

        if data_hora <= agora:
            continue

        mandante = jogo["mandante"]
        visitante = jogo["visitante"]

        p = probabilidades(
            elo.get(mandante, 1500),
            elo.get(visitante, 1500),
        )

        previsoes.append({
            "id": jogo["id"],
            "data": jogo["data"],
            "hora": jogo["hora"],
            "mandante": mandante,
            "visitante": visitante,
            "temporada": jogo["temporada"],
            "probabilidades": {
                "mandante": round(
                    p["mandante"] * 100, 1
                ),
                "empate": round(
                    p["empate"] * 100, 1
                ),
                "visitante": round(
                    p["visitante"] * 100, 1
                ),
            },
            "placar_provavel": p["placar_provavel"],
            "gols_esperados": p["gols_esperados"],
        })

    previsoes.sort(
        key=lambda j: (
            j["data"], j["hora"], j["id"]
        )
    )

    conteudo = {
        "meta": {
            "competicao": "UEFA Champions League",
            "gerado_em": agora.isoformat(),
            "total": len(previsoes),
            "modelo": "Elo + Poisson experimental",
        },
        "jogos": previsoes,
    }

    SAIDA.parent.mkdir(
        parents=True, exist_ok=True
    )

    with open(
        SAIDA, "w", encoding="utf-8"
    ) as arquivo:
        json.dump(
            conteudo,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    print("=== EXPORTACAO CHAMPIONS ===")
    print(f"Previsoes exportadas: {len(previsoes)}")
    print(f"Arquivo: {SAIDA}")

    for jogo in previsoes[:5]:
        print(
            f"{jogo['data']} | "
            f"{jogo['mandante']} x "
            f"{jogo['visitante']}"
        )


if __name__ == "__main__":
    main()

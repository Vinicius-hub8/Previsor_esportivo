
#!/usr/bin/env python3
"""
Atualizador do Fator Casa.

Comandos:
    python atualizar.py
    python atualizar.py nfl
    python atualizar.py nba
    python atualizar.py futebol
    python atualizar.py champions

A Champions League segue o mesmo fluxo das ligas de futebol (previsor_futebol.py):
`python atualizar.py champions` atualiza so ela. No fim, as previsoes entram no historico (historico_previsoes.py).
"""

import sys
import traceback
from pathlib import Path

import exportar_dados
import exportar_futebol
import exportar_nba
import historico_previsoes
import previsor_futebol as F


RAIZ = Path(__file__).resolve().parent


def atualizar_futebol():
    exportar_futebol.main(ligas=[l for l in F.LIGAS if l != "champions"])


def atualizar_champions():
    exportar_futebol.main(ligas=["champions"])


def registrar_historico():
    """Guarda as previsoes e os resultados no banco local (historico.db). Falhar aqui nao derruba a atualizacao."""
    try:
        historico_previsoes.executar()
    except Exception:
        traceback.print_exc()
        print("Aviso: o historico de previsoes nao foi atualizado.", flush=True)


ESPORTES = {
    "nfl": exportar_dados.main,
    "nba": exportar_nba.main,
    "futebol": atualizar_futebol,
    "champions": atualizar_champions,
}


def main():
    pedidos = (
        [a.lower() for a in sys.argv[1:]]
        or list(ESPORTES)
    )

    desconhecidos = [
        nome
        for nome in pedidos
        if nome not in ESPORTES
    ]

    if desconhecidos:
        sys.exit(
            "Esporte desconhecido: "
            + ", ".join(desconhecidos)
            + ". Opcoes: "
            + ", ".join(ESPORTES)
        )

    falhas = []

    for nome in pedidos:
        print(
            f"\n========== {nome.upper()} ==========",
            flush=True,
        )

        try:
            ESPORTES[nome]()

        except Exception:
            traceback.print_exc()

            print(
                f"\nFalha ao atualizar {nome.upper()}. "
                "As outras modalidades continuarao.",
                flush=True,
            )

            falhas.append(nome)

    print("\n========== RESUMO ==========")

    if falhas:
        print(
            "Falharam: " + ", ".join(falhas)
        )
    else:
        print(
            "Todas as atualizacoes solicitadas "
            "foram concluidas."
        )

    print(
        "\nPara abrir o site: "
        "cd web  e  npm run dev"
    )

    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()

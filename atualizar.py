
#!/usr/bin/env python3
"""
Atualizador do Fator Casa.

Comandos:
    python atualizar.py
    python atualizar.py nfl
    python atualizar.py nba
    python atualizar.py futebol
    python atualizar.py champions

A Champions possui seu proprio fluxo:
coleta -> organizacao -> previsoes -> historico.
"""

import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import exportar_dados
import exportar_futebol
import exportar_nba


RAIZ = Path(__file__).resolve().parent
FUSO = ZoneInfo("America/Sao_Paulo")


def executar_script(caminho, *argumentos):
    comando = [
        sys.executable,
        str(RAIZ / caminho),
        *map(str, argumentos),
    ]

    subprocess.run(
        comando,
        cwd=RAIZ,
        check=True,
    )


def atualizar_champions():
    print("\n--- CHAMPIONS: COLETA ---", flush=True)

    hoje = datetime.now(FUSO).date()

    # Reconsulta alguns dias anteriores para
    # encontrar resultados recem-finalizados
    # e busca as partidas dos proximos 14 dias.
    inicio = hoje - timedelta(days=3)
    fim = hoje + timedelta(days=14)

    executar_script(
        "champions/coletar.py",
        "--inicio",
        inicio.isoformat(),
        "--fim",
        fim.isoformat(),
    )

    print(
        "\n--- CHAMPIONS: ORGANIZACAO ---",
        flush=True,
    )

    executar_script("champions/organizar.py")

    print(
        "\n--- CHAMPIONS: PREVISOES ---",
        flush=True,
    )

    executar_script("champions/exportar.py")

    print(
        "\n--- CHAMPIONS: HISTORICO ---",
        flush=True,
    )

    executar_script("historico_previsoes.py")


ESPORTES = {
    "nfl": exportar_dados.main,
    "nba": exportar_nba.main,
    "futebol": exportar_futebol.main,
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

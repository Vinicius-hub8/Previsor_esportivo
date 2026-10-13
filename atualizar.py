#!/usr/bin/env python3
"""Atualiza os dados de todos os esportes com um comando:

    python atualizar.py            # NFL, NBA e futebol (6 ligas)
    python atualizar.py nba        # só a NBA (ou nfl, futebol)

Grava web/public/dados/<esporte>.json. Depois, em outro terminal:  cd web  e  npm run dev
Se um esporte falhar (ex.: sem internet), o JSON antigo dele é mantido e os outros seguem.
"""
import sys
import traceback

import exportar_dados
import exportar_futebol
import exportar_nba

ESPORTES = {"nfl": exportar_dados.main, "nba": exportar_nba.main, "futebol": exportar_futebol.main}

if __name__ == "__main__":
    pedidos = [a.lower() for a in sys.argv[1:]] or list(ESPORTES)
    falhas = []
    for nome in pedidos:
        if nome not in ESPORTES:
            sys.exit(f"Esporte desconhecido: {nome}. Opções: {', '.join(ESPORTES)}")
        print(f"\n== {nome.upper()} ==")
        try:
            ESPORTES[nome]()
        except Exception:
            traceback.print_exc()
            print(f"::warning::Falha ao atualizar {nome.upper()}; mantendo o JSON anterior.")
            falhas.append(nome)
    if falhas and len(falhas) == len(pedidos):
        sys.exit(1)
    print("\nPronto. Para ver o site:  cd web  e  npm run dev")

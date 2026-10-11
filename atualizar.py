#!/usr/bin/env python3
"""Atualiza os dados do site com um comando:

    python atualizar.py

Baixa os resultados mais recentes, roda o modelo e grava web/public/dados/nfl.json.
Depois, em outro terminal:  cd web  e  npm run dev
"""
import exportar_dados

if __name__ == "__main__":
    exportar_dados.main()
    print("\nPronto. Para ver o site:  cd web  e  npm run dev")

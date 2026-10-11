#!/usr/bin/env python3
"""Decide se o site precisa ser refeito: terminou algum jogo na ESPN que o site publicado ainda não mostra?

Roda a cada 15 minutos no GitHub Actions (.github/workflows/ao-fim-do-jogo.yml). Não guarda estado:
compara a ESPN com o JSON que está no ar. Só jogos que já existem no JSON publicado contam, então jogos
fora do nosso calendário (pré-temporada, por exemplo) nunca causam republicação em loop.

Saída: imprime e grava `atualizar=true|false` em $GITHUB_OUTPUT.
Variável SITE_URL (opcional): endereço do site, ex.: https://usuario.github.io/repositorio/
"""
import json
import os
import sys
import urllib.request

import espn

ESPORTES = ["nfl", "nba"]


def ids_do_site(dados, esporte):
    """(ids que existem no JSON, ids que já têm placar). NFL usa o campo 'espn'; NBA, o próprio 'id' (que é da ESPN)."""
    todos, com_placar = set(), set()
    for semana in dados.get("semanas", {}).values():
        for info in semana.values():
            for g in info["jogos"]:
                chave = g.get("espn") if esporte == "nfl" else g.get("id")
                if not chave:
                    continue
                todos.add(str(chave))
                if g.get("placar"):
                    com_placar.add(str(chave))
    return todos, com_placar


def pendentes(finais_espn, dados, esporte):
    """Jogos que a ESPN diz que acabaram, estão no calendário do site e ainda não têm placar publicado."""
    todos, com_placar = ids_do_site(dados, esporte)
    return sorted(i for i in finais_espn if i in todos and i not in com_placar)


def _url_site():
    if os.environ.get("SITE_URL"):
        return os.environ["SITE_URL"].rstrip("/") + "/"
    dono, _, repo = os.environ.get("GITHUB_REPOSITORY", "").partition("/")
    return f"https://{dono.lower()}.github.io/{repo}/" if repo else None


def main():
    base = _url_site()
    if not base:
        sys.exit("Defina SITE_URL ou GITHUB_REPOSITORY.")
    achados = []
    for esp in ESPORTES:
        try:
            with urllib.request.urlopen(f"{base}dados/{esp}.json", timeout=30) as r:
                dados = json.load(r)
        except Exception as e:
            print(f"{esp}: não consegui ler o JSON publicado ({e}); ignorando.")
            continue
        novos = pendentes(espn.finais(esp), dados, esp)
        print(f"{esp}: {len(novos)} jogo(s) terminado(s) ainda sem placar no site {novos}")
        achados += novos
    saida = "true" if achados else "false"
    print("atualizar=" + saida)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"atualizar={saida}\n")


if __name__ == "__main__":
    main()

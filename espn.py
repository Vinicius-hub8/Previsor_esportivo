#!/usr/bin/env python3
"""Placares da ESPN (endereço público e NÃO oficial: pode mudar sem aviso).

Serve a duas coisas:
  - completar os placares que as bases abertas (nflverse, hoopR) ainda não têm, logo após o fim do jogo;
  - detectar se terminou algum jogo que o site publicado ainda não mostra (verificar_novos.py).

Só usa a biblioteca padrão. Se a ESPN falhar, devolve vazio e o resto do projeto segue normalmente.
"""
import json
import os
import time
import urllib.request
from datetime import date, timedelta

BASE = "https://site.api.espn.com/apis/site/v2/sports/{esporte}/scoreboard"
ESPORTES = {"nfl": "football/nfl", "nba": "basketball/nba"}


def _baixar(url, tentativas=3):
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fator-casa/1.0 (projeto de estudo)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:  # rede, JSON inválido, 5xx...
            erro = e
            time.sleep(2 * (i + 1))
    raise erro


def interpretar(dados):
    """JSON da ESPN -> lista de jogos [{id, estado, final, casa, fora, pts_casa, pts_fora, detalhe}].
    estado: 'pre' (não começou), 'in' (em andamento) ou 'post' (terminou)."""
    saida = []
    for ev in dados.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        tipo = (ev.get("status") or {}).get("type") or {}
        lados = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        if "home" not in lados or "away" not in lados:
            continue

        def pts(c):
            try:
                return int(c.get("score"))
            except (TypeError, ValueError):
                return None

        saida.append({
            "id": str(ev.get("id")), "estado": tipo.get("state"), "final": bool(tipo.get("completed")),
            "casa": lados["home"].get("team", {}).get("abbreviation"), "fora": lados["away"].get("team", {}).get("abbreviation"),
            "pts_casa": pts(lados["home"]), "pts_fora": pts(lados["away"]), "detalhe": tipo.get("shortDetail"),
            # usados pelo futebol, onde o jogo é achado pelo nome dos times e pela data
            "nome_casa": lados["home"].get("team", {}).get("displayName"), "nome_fora": lados["away"].get("team", {}).get("displayName"),
            "data": ev.get("date"),
        })
    return saida


def jogos_do_periodo(esporte, dias=3, hoje=None):
    hoje = hoje or date.today()
    ini, fim = hoje - timedelta(days=dias), hoje + timedelta(days=1)
    url = BASE.format(esporte=ESPORTES.get(esporte, esporte)) + f"?dates={ini:%Y%m%d}-{fim:%Y%m%d}&limit=500"
    return interpretar(_baixar(url))


def finais(esporte, dias=3):
    """{id_espn: (pontos_visitante, pontos_mandante)} dos jogos terminados nos últimos dias. Vazio se a ESPN falhar."""
    if os.environ.get("SEM_ESPN"):
        return {}
    try:
        return {j["id"]: (j["pts_fora"], j["pts_casa"]) for j in jogos_do_periodo(esporte, dias)
                if j["final"] and j["pts_fora"] is not None and j["pts_casa"] is not None}
    except Exception as e:
        print(f"::warning::ESPN indisponível ({e}); seguindo só com as bases abertas.")
        return {}

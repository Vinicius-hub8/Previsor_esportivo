#!/usr/bin/env python3
"""Placares da ESPN (endereço público e NÃO oficial: pode mudar sem aviso).

Serve a três coisas:
  - completar os placares que as bases abertas (nflverse, hoopR, openfootball) ainda não têm;
  - baixar os jogos da Champions League (a ESPN é a fonte dela);
  - detectar se terminou algum jogo que o site publicado ainda não mostra (verificar_novos.py).

A ESPN deixou de aceitar intervalos de datas (`dates=AAAAMMDD-AAAAMMDD` responde 400), então cada dia é consultado
separadamente, em paralelo.

Só usa a biblioteca padrão. Se a ESPN falhar, devolve vazio e o resto do projeto segue normalmente.
"""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

BASE = "https://site.api.espn.com/apis/site/v2/sports/{esporte}/scoreboard"
ESPORTES = {"nfl": "football/nfl", "nba": "basketball/nba"}
PARALELO = 8


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
    """JSON da ESPN -> lista de jogos [{id, estado, final, casa, fora, pts_casa, pts_fora, detalhe, ...}].
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

        temporada = ev.get("season") or {}
        saida.append({
            "id": str(ev.get("id")), "estado": tipo.get("state"), "final": bool(tipo.get("completed")),
            "casa": lados["home"].get("team", {}).get("abbreviation"), "fora": lados["away"].get("team", {}).get("abbreviation"),
            "pts_casa": pts(lados["home"]), "pts_fora": pts(lados["away"]), "detalhe": tipo.get("shortDetail"),
            # usados pelo futebol, onde o jogo é achado pelo nome dos times e pela data
            "nome_casa": lados["home"].get("team", {}).get("displayName"), "nome_fora": lados["away"].get("team", {}).get("displayName"),
            "data": ev.get("date"),
            # usados pela Champions: ano de início da temporada e fase ('league-phase', 'round-of-16', 'final'...)
            "temporada": temporada.get("year"), "fase": temporada.get("slug"),
            # ex.: "2nd Leg - Arsenal advance 2-1 on aggregate" (diz quem passou no mata-mata)
            "nota": next((n.get("headline") or n.get("text") for n in comp.get("notes") or [] if n.get("headline") or n.get("text")), None),
        })
    return saida


def _url(esporte, dia):
    return BASE.format(esporte=ESPORTES.get(esporte, esporte)) + f"?dates={dia:%Y%m%d}&limit=500"


def jogos_dos_dias(esporte, dias, tolerante=True):
    """Jogos de cada dia pedido (um pedido por dia, em paralelo), sem repetição.
    tolerante=True: um dia que falhar é ignorado (com aviso), desde que algum dia tenha dado certo."""
    dias = sorted(set(dias))
    if not dias:
        return []

    def um(dia):
        try:
            return interpretar(_baixar(_url(esporte, dia)))
        except Exception as e:
            return e

    with ThreadPoolExecutor(max_workers=min(PARALELO, len(dias))) as ex:
        resultados = list(ex.map(um, dias))
    falhas = [(d, r) for d, r in zip(dias, resultados) if isinstance(r, Exception)]
    if falhas and (not tolerante or len(falhas) == len(dias)):
        raise falhas[0][1]
    if falhas:
        print(f"::warning::ESPN falhou em {len(falhas)} de {len(dias)} dia(s) de {esporte} (ex.: {falhas[0][0]}: {falhas[0][1]})")
    vistos, saida = set(), []
    for r in resultados:
        if isinstance(r, Exception):
            continue
        for j in r:
            if j["id"] not in vistos:
                vistos.add(j["id"])
                saida.append(j)
    return saida


def dias_entre(ini, fim):
    return [ini + timedelta(days=i) for i in range((fim - ini).days + 1)]


def jogos_do_periodo(esporte, dias=3, hoje=None, adiante=1):
    """Jogos de `dias` dias atrás até `adiante` dias à frente."""
    hoje = hoje or date.today()
    return jogos_dos_dias(esporte, dias_entre(hoje - timedelta(days=dias), hoje + timedelta(days=adiante)))


def finais(esporte, dias=3, datas=None):
    """{id_espn: (pontos_visitante, pontos_mandante)} dos jogos terminados nos últimos dias (ou nas `datas` pedidas).
    Vazio se a ESPN falhar."""
    if os.environ.get("SEM_ESPN"):
        return {}
    try:
        jogos = jogos_dos_dias(esporte, datas) if datas is not None else jogos_do_periodo(esporte, dias)
        return {j["id"]: (j["pts_fora"], j["pts_casa"]) for j in jogos
                if j["final"] and j["pts_fora"] is not None and j["pts_casa"] is not None}
    except Exception as e:
        print(f"::warning::ESPN indisponível ({e}); seguindo só com as bases abertas.")
        return {}

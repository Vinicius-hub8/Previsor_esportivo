#!/usr/bin/env python3
"""
Previsor de Futebol
===================
Seis ligas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e Brasileirão.

Para cada liga:
  1) Chance de vitória do mandante, empate e vitória do visitante em cada jogo (e o placar mais provável).
  2) Tabela atual.
  3) Tabela prevista: simulamos o resto da temporada 10 mil vezes (chance de título, vaga continental e rebaixamento).
  4) Todos os horários convertidos para Brasília.

Modelo (simples e explicável):
  - Força de cada time pelo Elo, atualizado jogo a jogo (peso maior para goleadas, vantagem de casa, regressão à média
    a cada temporada nova).
  - A diferença de Elo entra numa regressão de Poisson que dá os gols esperados de cada lado. Dos gols esperados saem as
    chances de vitória, empate e derrota.
  - Cada temporada é prevista só com o que existia antes dela (walk-forward), então a acurácia não "olha o futuro".

Dados: calendários e placares abertos do projeto openfootball (domínio público), completados com a ESPN quando o
openfootball ainda não tem o resultado.

Uso (terminal):
    python previsor_futebol.py                 -> resumo e acurácia de cada liga
    python previsor_futebol.py premier         -> só uma liga (premier, laliga, seriea, bundesliga, ligue1, brasileirao)

Requisitos: pandas, numpy, scikit-learn.
"""
import hashlib
import math
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import warnings
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import noticias
from sklearn.linear_model import PoissonRegressor

warnings.filterwarnings("ignore")

TZ_BR = ZoneInfo("America/Sao_Paulo")
BASE_EU = os.environ.get("FUT_BASE_EU", "https://raw.githubusercontent.com/openfootball/football.json/master")
BASE_BR = os.environ.get("FUT_BASE_BR", "https://raw.githubusercontent.com/openfootball/brazil/master/brazil")
PRIMEIRO_ANO = 2018          # primeira temporada baixada (a primeira serve só para "aquecer" o Elo)
CACHE = Path(tempfile.gettempdir()) / "fatorcasa_cache"

# topo = quantos times entram na faixa "vaga continental" (simplificado); rebaixa = rebaixamento direto.
LIGAS = {
    "premier": dict(nome="Premier League", pais="Inglaterra", eu="en.1", tz="Europe/London", espn="eng.1", topo=4, rebaixa=3),
    "laliga": dict(nome="La Liga", pais="Espanha", eu="es.1", tz="Europe/Madrid", espn="esp.1", topo=4, rebaixa=3),
    "seriea": dict(nome="Serie A", pais="Itália", eu="it.1", tz="Europe/Rome", espn="ita.1", topo=4, rebaixa=3),
    "bundesliga": dict(nome="Bundesliga", pais="Alemanha", eu="de.1", tz="Europe/Berlin", espn="ger.1", topo=4, rebaixa=2, repescagem=True),
    "ligue1": dict(nome="Ligue 1", pais="França", eu="fr.1", tz="Europe/Paris", espn="fra.1", topo=3, rebaixa=2, repescagem=True),
    "brasileirao": dict(nome="Brasileirão Série A", pais="Brasil", br="br1", tz="America/Sao_Paulo", espn="bra.1", topo=6, rebaixa=4, desempate_vitorias=True),
}

# Elo: em teste com as seis ligas, K de 14 a 32, vantagem de casa de 55 a 75 e reversão de 0,75 a 0,88 dão praticamente o mesmo
# resultado (platô). Ficaram valores do meio.
ELO_INICIAL, ELO_NOVATO, K_ELO, VANT_CASA, REVERSAO = 1500.0, 1460.0, 16.0, 60.0, 0.85
SIGMA_ELO_TEMPORADA = 50.0   # incerteza da força dos times no início da temporada (pontos de Elo); calibrada em backtest
N_SIM = 10000
MAX_GOLS = 10

AVISOS = [
    "Lesões, suspensões, escalação, mercado da bola e troca de técnico não entram no modelo.",
    "Em futebol o empate é comum (cerca de 1 jogo em cada 4). Por isso o palpite acerta bem menos que no basquete ou no futebol americano.",
    "Os horários são de Brasília. Quando a liga ainda não divulgou o horário de um jogo, aparece “horário a definir”.",
    "A tabela prevista é um cenário: sorteamos os resultados dos jogos restantes e também uma variação na força de cada time.",
    "Desempate da tabela: pontos, saldo de gols e gols marcados (no Brasileirão, vitórias primeiro). Confronto direto não é considerado.",
    "As vagas continentais e o rebaixamento são simplificados (a regra pode mudar de um ano para o outro).",
    "É um estudo estatístico, não uma recomendação de aposta.",
]

# ----------------------------------------------------------------------------
# Nomes: cada fonte escreve o nome do clube de um jeito. Aqui tudo vira um apelido único.
# ----------------------------------------------------------------------------
_PREF = {"fc", "afc", "cf", "sc", "ec", "cr", "se", "ca", "ud", "cd", "rc", "rcd", "ac", "as", "ss", "ssc", "us", "sv", "vfb", "vfl",
         "tsg", "fsv", "ogc", "aj", "es", "ea", "sm", "1.", "spvgg", "ssd", "acf", "rb", "club", "real", "sd"}
_SUF = {"fc", "afc", "cf", "sc", "ec", "fbc", "fbpa", "sco", "hsc", "fco", "estac", "calcio", "balompie", "bc", "cfc", "bsc", "fr",
        "mg", "rj", "sp", "rs", "pr", "go", "ba", "pe", "ce", "mt", "al", "pa", "de"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def limpar(raw):
    t = sem_acento(str(raw)).replace("&", "and").split()
    t = [w for w in t if not re.fullmatch(r"\d{2,4}", w)]
    while len(t) > 1 and t[0].lower() in _PREF:
        t = t[1:]
    while len(t) > 1 and t[-1].lower() in _SUF:
        t = t[:-1]
    return " ".join(t)


# chave = limpar(nome da fonte) -> apelido exibido
APELIDOS = {
    # Inglaterra
    "Brighton and Hove Albion": "Brighton", "Cardiff City": "Cardiff", "Coventry City": "Coventry", "Huddersfield Town": "Huddersfield",
    "Hull City": "Hull City", "Ipswich Town": "Ipswich", "Leeds United": "Leeds", "Leicester City": "Leicester", "Luton Town": "Luton",
    "Manchester City": "Man City", "Manchester United": "Man United", "Newcastle United": "Newcastle", "Norwich City": "Norwich",
    "Nottingham Forest": "Nott'm Forest", "Tottenham Hotspur": "Tottenham", "West Bromwich Albion": "West Brom",
    "West Ham United": "West Ham", "Wolverhampton Wanderers": "Wolves", "Aston Villa": "Aston Villa", "Crystal Palace": "Crystal Palace",
    "Sheffield United": "Sheffield Utd",
    # Espanha
    "Alaves": "Alavés", "Deportivo Alaves": "Alavés", "Almeria": "Almería", "Atletico Madrid": "Atlético de Madrid",
    "Atletico de Madrid": "Atlético de Madrid", "Barcelona": "Barcelona", "Betis": "Betis", "Cadiz": "Cádiz", "Celta": "Celta de Vigo",
    "Celta de Vigo": "Celta de Vigo", "Deportivo La Coruna": "Deportivo", "Espanyol Barcelona": "Espanyol", "Espanyol de Barcelona": "Espanyol",
    "Leganes": "Leganés", "Madrid": "Real Madrid", "Malaga": "Málaga", "Racing Club de Santander": "Racing Santander",
    "Rayo Vallecano de Madrid": "Rayo Vallecano", "Sociedad": "Real Sociedad", "Sociedad de Futbol": "Real Sociedad", "Levante UD": "Levante",
    "Athletic Club": "Athletic Bilbao", "Valladolid": "Valladolid", "Las Palmas": "Las Palmas",
    # Itália
    "Internazionale Milano": "Inter", "Inter": "Inter", "Milan": "Milan", "Lazio": "Lazio", "Lazio Roma": "Lazio", "Chievo Verona": "Chievo",
    "SPAL Ferrara": "SPAL", "UC Sampdoria": "Sampdoria", "Salernitana": "Salernitana", "Hellas Verona": "Verona", "Cremonese": "Cremonese",
    "Parma": "Parma", "Pisa": "Pisa",
    # Alemanha
    "Bayern Munchen": "Bayern de Munique", "Bayer Leverkusen": "Leverkusen", "Bor. Monchengladbach": "Gladbach",
    "Borussia Monchengladbach": "Gladbach", "Borussia Dortmund": "Dortmund", "Eintracht Frankfurt": "Eintracht Frankfurt",
    "Fortuna Dusseldorf": "Fortuna Düsseldorf", "Freiburg": "Freiburg", "Greuther Furth": "Greuther Fürth", "Hamburger SV": "Hamburgo",
    "Hannover": "Hannover", "Hertha": "Hertha Berlim", "Hoffenheim": "Hoffenheim", "Koln": "Colônia", "Leipzig": "RB Leipzig", "Mainz": "Mainz",
    "Nurnberg": "Nürnberg", "Schalke": "Schalke 04", "St. Pauli": "St. Pauli", "Union Berlin": "Union Berlim", "Werder Bremen": "Werder Bremen",
    "Heidenheim": "Heidenheim", "Darmstadt": "Darmstadt", "Elversberg": "Elversberg", "Augsburg": "Augsburg", "Bochum": "Bochum",
    "Stuttgart": "Stuttgart", "Wolfsburg": "Wolfsburg", "Paderborn": "Paderborn", "Arminia Bielefeld": "Bielefeld", "Holstein Kiel": "Holstein Kiel",
    # França
    "Paris Saint-Germain": "PSG", "Paris": "Paris FC", "Olympique Lyonnais": "Lyon", "Olympique Marseille": "Marseille",
    "Olympique de Marseille": "Marseille", "Lille OSC": "Lille", "Racing Club de Lens": "Lens", "Lens": "Lens", "Stade Brestois": "Brest",
    "Stade Rennais": "Rennes", "Stade de Reims": "Reims", "Strasbourg": "Strasbourg", "Strasbourg Alsace": "Strasbourg", "ESTAC Troyes": "Troyes",
    "Troyes AC": "Troyes", "Girondins Bordeaux": "Bordeaux", "Clermont Foot": "Clermont", "Saint-Etienne": "Saint-Étienne",
    "Nimes Olympique": "Nîmes", "Le Havre AC": "Le Havre", "Nice": "Nice", "Monaco": "Monaco", "Angers": "Angers", "Auxerre": "Auxerre",
    "Lorient": "Lorient", "Toulouse": "Toulouse", "Le Mans": "Le Mans", "Metz": "Metz", "Nantes": "Nantes", "Montpellier": "Montpellier",
    "Caen": "Caen", "Dijon": "Dijon", "Amiens": "Amiens", "Ajaccio": "Ajaccio", "Guingamp": "Guingamp",
    # Brasil
    "America": "América-MG", "America Mineiro": "América-MG", "Athletico Paranaense": "Athletico-PR", "Paranaense": "Athletico-PR",
    "Atletico Goianiense": "Atlético-GO", "Goianiense": "Atlético-GO", "Atletico Mineiro": "Atlético-MG", "Mineiro": "Atlético-MG",
    "Avai": "Avaí", "Bragantino": "Bragantino", "Red Bull Bragantino": "Bragantino", "CSA": "CSA", "Ceara": "Ceará",
    "Chapecoense AF": "Chapecoense", "Clube do Remo": "Remo", "Corinthians Paulista": "Corinthians", "Criciuma": "Criciúma", "Cuiaba": "Cuiabá",
    "Goias": "Goiás", "Gremio": "Grêmio", "Gremio Porto Alegre": "Grêmio", "Parana Clube": "Paraná", "Recife": "Sport", "Sport Recife": "Sport",
    "Sao Paulo": "São Paulo", "Vasco da Gama": "Vasco", "Vitoria": "Vitória", "Internacional": "Internacional",
}
SIGLAS = {  # só onde a sigla automática ficaria estranha ou repetida
    "Man City": "MCI", "Man United": "MUN", "Nott'm Forest": "NFO", "Tottenham": "TOT", "West Ham": "WHU", "West Brom": "WBA",
    "Newcastle": "NEW", "Wolves": "WOL", "Sheffield Utd": "SHU", "Leicester": "LEI", "Leeds": "LEE", "Liverpool": "LIV", "Brighton": "BHA",
    "Barcelona": "BAR", "Real Madrid": "RMA", "Atlético de Madrid": "ATM", "Athletic Bilbao": "ATH", "Real Sociedad": "RSO", "Celta de Vigo": "CEL",
    "Rayo Vallecano": "RAY", "Racing Santander": "RAC", "Deportivo": "DEP", "Espanyol": "ESP", "Valencia": "VAL", "Villarreal": "VIL",
    "Inter": "INT", "Milan": "MIL", "Juventus": "JUV", "Napoli": "NAP", "Roma": "ROM", "Lazio": "LAZ", "Atalanta": "ATA", "Fiorentina": "FIO",
    "Bayern de Munique": "BAY", "Dortmund": "BVB", "Leverkusen": "B04", "Gladbach": "BMG", "RB Leipzig": "RBL", "Colônia": "KOL",
    "Eintracht Frankfurt": "SGE", "Union Berlim": "FCU", "Hamburgo": "HSV", "Schalke 04": "S04", "Werder Bremen": "SVW", "Hertha Berlim": "BSC",
    "PSG": "PSG", "Lyon": "OL", "Marseille": "OM", "Lille": "LIL", "Paris FC": "PFC", "Rennes": "REN", "Strasbourg": "STR", "Lens": "RCL",
    "Nice": "NIC", "Monaco": "ASM", "Brest": "BRE", "Auxerre": "AUX", "Angers": "ANG", "Toulouse": "TFC", "Lorient": "LOR", "Le Havre": "HAC",
    "Flamengo": "FLA", "Palmeiras": "PAL", "Corinthians": "COR", "São Paulo": "SAO", "Santos": "SAN", "Fluminense": "FLU", "Botafogo": "BOT",
    "Vasco": "VAS", "Grêmio": "GRE", "Internacional": "INT", "Atlético-MG": "CAM", "Cruzeiro": "CRU", "Bahia": "BAH", "Fortaleza": "FOR",
    "Athletico-PR": "CAP", "Bragantino": "RBB", "Vitória": "VIT", "Mirassol": "MIR", "Coritiba": "CFC", "Chapecoense": "CHA", "Remo": "REM",
    "Juventude": "JUV", "Ceará": "CEA", "Sport": "SPO", "Goiás": "GOI", "Cuiabá": "CUI", "Criciúma": "CRI",
}


def apelido(raw):
    k = limpar(raw)
    return APELIDOS.get(k, k)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s).lower()).strip("-")


def sigla(ap, usadas):
    s = SIGLAS.get(ap)
    if not s:
        palavras = re.findall(r"[A-Za-zÀ-ú]+", sem_acento(ap))
        s = (("".join(p[0] for p in palavras[:3]) if len(palavras) >= 3 else "".join(palavras)[:3]) or "XXX").upper()
    base, i = s, 1
    while s in usadas and usadas[s] != ap:
        s = base[:2] + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i % 26]
        i += 1
    usadas[s] = ap
    return s


# ----------------------------------------------------------------------------
# Download e leitura dos calendários
# ----------------------------------------------------------------------------
def baixar(url, cache_ok=False, tentativas=5):
    """Texto de uma URL. Repete se o GitHub pedir calma (429). cache_ok guarda temporadas já encerradas."""
    arq = CACHE / hashlib.md5(url.encode()).hexdigest()
    if cache_ok and arq.exists():
        return arq.read_text(encoding="utf-8")
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fator-casa/1.0 (projeto de estudo)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8")
            if cache_ok:
                CACHE.mkdir(parents=True, exist_ok=True)
                arq.write_text(txt, encoding="utf-8")
            return txt
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            erro = e
        except Exception as e:  # rede
            erro = e
        time.sleep(2 * (i + 1))
    raise erro


def _linhas_europa(txt, rotulo, tz):
    import json
    for m in json.loads(txt)["matches"]:
        sc = m.get("score")
        ft = sc.get("ft") if isinstance(sc, dict) else sc if isinstance(sc, list) and len(sc) == 2 else None
        r = re.search(r"(\d+)", m.get("round", ""))
        yield dict(temp=rotulo, rodada=int(r.group(1)) if r else 0, dia=m["date"], hora=m.get("time"), tz=tz,
                   casa_raw=m["team1"], fora_raw=m["team2"], gc=ft[0] if ft else np.nan, gf=ft[1] if ft else np.nan, adiado=False)


_DIA = re.compile(r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
_JOGO = re.compile(r"^\s+(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s*(?:(\d+)-(\d+)(?:\s*\(\d+-\d+\))?)?\s*$")


def _linhas_brasil(txt, ano, tz):
    """Formato Football.TXT do openfootball (rodadas, datas e horários). O horário vale até a próxima data."""
    rodada, dia, hora = 0, None, None
    for ln in txt.splitlines():
        m = re.match(r"^[▪»]\s*Matchday\s+(\d+)", ln)
        if m:
            rodada, dia, hora = int(m.group(1)), None, None
            continue
        m = _DIA.match(ln)
        if m:
            dia = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3) or ano}", "%b %d %Y").strftime("%Y-%m-%d")
            hora = None
            continue
        adiado = bool(re.search(r"\[\s*postponed\s*\]", ln))
        m = _JOGO.match(re.sub(r"\s*\[[^\]]*\]\s*$", "", ln))
        if m and dia:
            hora = m.group(1) or hora
            yield dict(temp=str(ano), rodada=rodada, dia=dia, hora=hora, tz=tz, casa_raw=m.group(2).strip(), fora_raw=m.group(3).strip(),
                       gc=float(m.group(4)) if m.group(4) else np.nan, gf=float(m.group(5)) if m.group(5) else np.nan, adiado=adiado)


def temporada_atual_europa(hoje):
    return hoje.year if hoje.month >= 7 else hoje.year - 1


def carregar_liga(lid, hoje=None, ate_ano=None):
    """DataFrame com todos os jogos (jogados ou não) das temporadas desde PRIMEIRO_ANO, já com horário de Brasília."""
    cfg = LIGAS[lid]
    hoje = hoje or date.today()
    linhas = []
    if "eu" in cfg:
        atual = ate_ano or temporada_atual_europa(hoje)
        for y in range(PRIMEIRO_ANO, atual + 1):
            rot = f"{y}-{str(y + 1)[2:]}"
            txt = baixar(f"{BASE_EU}/{rot}/{cfg['eu']}.json", cache_ok=y < atual)
            if txt:
                linhas += list(_linhas_europa(txt, rot, cfg["tz"]))
    else:
        atual = ate_ano or hoje.year
        for y in range(PRIMEIRO_ANO, atual + 1):
            txt = baixar(f"{BASE_BR}/{y}_{cfg['br']}.txt", cache_ok=y < atual)
            if txt:
                linhas += list(_linhas_brasil(txt, y, cfg["tz"]))
    return preparar(pd.DataFrame(linhas))


def _para_brasilia(dia, hora, tz):
    """('2026-09-20', '16:30', 'Europe/London') -> (UTC, data BRT, hora BRT ou None). Sem horário, só a data."""
    if pd.isna(hora) or not hora:
        return pd.Timestamp(dia + " 12:00", tz="UTC"), dia, None
    loc = datetime.strptime(f"{dia} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(tz))
    br = loc.astimezone(TZ_BR)
    return pd.Timestamp(loc.astimezone(ZoneInfo("UTC"))), br.strftime("%Y-%m-%d"), br.strftime("%H:%M")


def preparar(d):
    conv = [_para_brasilia(a, b, c) for a, b, c in zip(d["dia"], d["hora"], d["tz"])]
    d["dt"] = [c[0] for c in conv]
    d["dia_br"] = [c[1] for c in conv]
    d["hora_br"] = [c[2] for c in conv]
    d["hora_br"] = d["hora_br"].astype(object).where(d["hora_br"].notna(), None)
    d["casa"] = d["casa_raw"].map(apelido)
    d["fora"] = d["fora_raw"].map(apelido)
    d["jogado"] = d["gc"].notna() & d["gf"].notna()
    d["ano"] = d["temp"].str[:4].astype(int)
    return d.sort_values(["dt", "casa"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# ESPN: completa resultados que o openfootball ainda não tem
# ----------------------------------------------------------------------------
def _sim_nome(a, b):
    a, b = limpar(a).lower(), limpar(b).lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.85
    ta, tb = set(a.split()), set(b.split())
    if ta & tb and len(ta & tb) >= min(len(ta), len(tb)):
        return 0.8
    return SequenceMatcher(None, a, b).ratio()


def casar_espn(d, eventos, folga_dias=2):
    """Preenche gc/gf dos jogos ainda sem placar usando eventos da ESPN já terminados. Devolve quantos casou."""
    n = 0
    pend = d.index[~d["jogado"]]
    for ev in eventos:
        if not ev.get("final") or ev.get("pts_casa") is None or ev.get("pts_fora") is None or not ev.get("data"):
            continue
        dia = pd.Timestamp(ev["data"]).tz_convert("UTC")
        melhor, nota = None, 0.0
        for i in pend:
            folga = 365 if d.at[i, "adiado"] else folga_dias   # jogo adiado: a nova data ainda não está na base
            if d.at[i, "jogado"] or abs((d.at[i, "dt"] - dia).total_seconds()) > folga * 86400:
                continue
            s = _sim_nome(ev["nome_casa"], d.at[i, "casa_raw"]) + _sim_nome(ev["nome_fora"], d.at[i, "fora_raw"])
            s = max(s, _sim_nome(ev["nome_casa"], d.at[i, "casa"]) + _sim_nome(ev["nome_fora"], d.at[i, "fora"]))
            if s > nota:
                melhor, nota = i, s
        if melhor is not None and nota >= 1.5:
            d.at[melhor, "gc"], d.at[melhor, "gf"], d.at[melhor, "jogado"] = float(ev["pts_casa"]), float(ev["pts_fora"]), True
            n += 1
    return n


def completar_com_espn(d, lid, dias=45):
    if os.environ.get("SEM_ESPN"):
        return d
    try:
        import espn
        eventos = espn.jogos_do_periodo(f"soccer/{LIGAS[lid]['espn']}", dias=dias)
    except Exception as e:
        print(f"::warning::ESPN indisponível para {lid} ({e}); seguindo só com o openfootball.")
        return d
    n = casar_espn(d, eventos)
    if n:
        print(f"ESPN: {n} placar(es) de {LIGAS[lid]['nome']} completado(s)")
    return d


# ----------------------------------------------------------------------------
# Elo
# ----------------------------------------------------------------------------
def calcular_elo(d, k=K_ELO, h=VANT_CASA, rev=REVERSAO):
    """Elo de cada time ANTES de cada jogo (sem olhar o resultado). Devolve (elo_casa, elo_fora, elo_final)."""
    r, ec, ef = {}, np.zeros(len(d)), np.zeros(len(d))
    ano_ant, primeiro_ano = None, d["ano"].min()
    for pos, g in enumerate(d.itertuples()):
        if g.ano != ano_ant:
            if ano_ant is not None:
                r = {t: ELO_INICIAL + rev * (x - ELO_INICIAL) for t, x in r.items()}
            ano_ant = g.ano
        for t in (g.casa, g.fora):
            if t not in r:
                r[t] = ELO_INICIAL if g.ano == primeiro_ano else ELO_NOVATO
        ec[pos], ef[pos] = r[g.casa], r[g.fora]
        if g.jogado:
            esp = 1 / (1 + 10 ** (-(r[g.casa] - r[g.fora] + h) / 400))
            res = 1.0 if g.gc > g.gf else 0.5 if g.gc == g.gf else 0.0
            gd = abs(g.gc - g.gf)
            mult = 1.0 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8
            delta = k * mult * (res - esp)
            r[g.casa] += delta
            r[g.fora] -= delta
    return ec, ef, r


# ----------------------------------------------------------------------------
# Gols (Poisson) -> chances de vitória / empate / derrota
# ----------------------------------------------------------------------------
class ModeloGols:
    """log(gols do mandante) = a + b*x + c ;  log(gols do visitante) = a - b*x ;  x = (Elo casa - Elo fora)/100."""

    def __init__(self):
        self.m = PoissonRegressor(alpha=0.0, max_iter=500)

    def ajustar(self, x, gc, gf):
        X = np.r_[np.c_[x, np.ones(len(x))], np.c_[-x, np.zeros(len(x))]]
        self.m.fit(X, np.r_[gc, gf])
        return self

    def lambdas(self, x):
        x = np.asarray(x, dtype=float)
        a, (b, c) = self.m.intercept_, self.m.coef_
        return np.exp(a + b * x + c), np.exp(a - b * x)


def _pmf(lam, n=MAX_GOLS):
    k = np.arange(n + 1)
    lg = np.array([math.lgamma(i + 1) for i in k])
    lam = np.asarray(lam, dtype=float)[:, None]
    return np.exp(-lam + k * np.log(lam) - lg)


def matriz_placares(lc, lf):
    """(N, 11, 11): chance de cada placar casa x fora."""
    m = _pmf(lc)[:, :, None] * _pmf(lf)[:, None, :]
    return m / m.sum(axis=(1, 2), keepdims=True)


def chances(lc, lf):
    """Devolve p (N,3) = [casa, empate, fora] e o placar mais provável de cada jogo."""
    m = matriz_placares(lc, lf)
    ij = np.arange(m.shape[1])
    ganha = ij[:, None] > ij[None, :]
    empata = ij[:, None] == ij[None, :]
    p = np.c_[(m * ganha).sum((1, 2)), (m * empata).sum((1, 2)), (m * ganha.T).sum((1, 2))]
    plac = [np.unravel_index(x.argmax(), x.shape) for x in m]
    return p, np.array(plac)


def resultado(gc, gf):
    return np.where(gc > gf, 0, np.where(gc == gf, 1, 2))


# ----------------------------------------------------------------------------
# Construção: Elo + backtest walk-forward + modelo final
# ----------------------------------------------------------------------------
def construir(d, k=K_ELO, h=VANT_CASA, rev=REVERSAO):
    d = d.copy()
    d["elo_c"], d["elo_f"], elo_final = calcular_elo(d, k, h, rev)
    d["x"] = (d["elo_c"] - d["elo_f"]) / 100
    anos = sorted(d["ano"].unique())
    atual = anos[-1]
    bt = []                                   # previsões "às cegas" de cada temporada (treino só com as anteriores)
    for ano in anos[2:]:                      # a 1ª temporada aquece o Elo; a 2ª é só treino
        tr = d[(d["ano"] > anos[0]) & (d["ano"] < ano) & d["jogado"]]
        te = d[(d["ano"] == ano) & d["jogado"]]
        if len(tr) < 300 or te.empty:
            continue
        mod = ModeloGols().ajustar(tr["x"].values, tr["gc"].values, tr["gf"].values)
        lc, lf = mod.lambdas(te["x"].values)
        p, plac = chances(lc, lf)
        bt.append(te.assign(p_c=p[:, 0], p_e=p[:, 1], p_f=p[:, 2], lc=lc, lf=lf, pl_c=plac[:, 0], pl_f=plac[:, 1]))
    bt = pd.concat(bt) if bt else d.iloc[0:0]
    bt["real"] = resultado(bt["gc"].values, bt["gf"].values) if len(bt) else []
    bt["palpite"] = bt[["p_c", "p_e", "p_f"]].values.argmax(1) if len(bt) else []
    bt["ok"] = bt["palpite"] == bt["real"]

    # modelo final: todos os jogos já disputados (menos a temporada de aquecimento)
    tr = d[(d["ano"] > anos[0]) & d["jogado"]]
    modelo = ModeloGols().ajustar(tr["x"].values, tr["gc"].values, tr["gf"].values)
    return dict(d=d, bt=bt, modelo=modelo, elo=elo_final, atual=atual, anos=anos)


def log_loss(bt):
    p = bt[["p_c", "p_e", "p_f"]].values[np.arange(len(bt)), bt["real"].values]
    return float(-np.log(np.clip(p, 1e-9, 1)).mean())


def resumo_acuracia(S):
    bt = S["bt"]
    ref = bt[bt["ano"] < S["atual"]]
    if ref.empty:
        ref = bt
    atual = bt[bt["ano"] == S["atual"]]
    freq = np.bincount(ref["real"].values.astype(int), minlength=3) / len(ref)
    return dict(acc=float(ref["ok"].mean()), acc_mandante=float(freq[0]), freq_empate=float(freq[1]), n_ref=int(len(ref)),
                log_loss=log_loss(ref), log_loss_base=float(-np.log(freq[ref["real"].values]).mean()),
                acc_atual=float(atual["ok"].mean()) if len(atual) else None, n_atual=int(len(atual)),
                anos_ref=(int(ref["ano"].min()), int(ref["ano"].max())))


# ----------------------------------------------------------------------------
# Tabela atual e simulação do resto da temporada
# ----------------------------------------------------------------------------
def chave_ordem(pts, v, sg, gp, vitorias_primeiro):
    """Número que ordena a tabela (maior = melhor posição). pts, v, sg e gp podem ser arrays."""
    return (((pts * 100 + (v if vitorias_primeiro else 0)) * 1000 + (sg + 300)) * 1000) + gp


def tabela_atual(S, cfg):
    d = S["d"]
    t = d[(d["ano"] == S["atual"]) & d["jogado"]]
    times = sorted(set(d[d["ano"] == S["atual"]]["casa"]) | set(d[d["ano"] == S["atual"]]["fora"]))
    linhas = {x: dict(t=x, j=0, v=0, e=0, d=0, gp=0, gc=0, forma=[]) for x in times}
    for g in t.sort_values("dt").itertuples():
        for time_, gp, gc in ((g.casa, g.gc, g.gf), (g.fora, g.gf, g.gc)):
            L = linhas[time_]
            L["j"] += 1
            L["gp"] += int(gp)
            L["gc"] += int(gc)
            r = "V" if gp > gc else "E" if gp == gc else "D"
            L[{"V": "v", "E": "e", "D": "d"}[r]] += 1
            L["forma"].append(r)
    for L in linhas.values():
        L["sg"], L["pts"], L["forma"] = L["gp"] - L["gc"], 3 * L["v"] + L["e"], L["forma"][-5:]
    vp = bool(cfg.get("desempate_vitorias"))
    return sorted(linhas.values(), key=lambda L: -chave_ordem(L["pts"], L["v"], L["sg"], L["gp"], vp))


def sigma_incerteza(S):
    """Quanto a força dos times ainda pode mudar: cai conforme a temporada avança."""
    d = S["d"][S["d"]["ano"] == S["atual"]]
    resta = 1 - d["jogado"].mean() if len(d) else 1
    return SIGMA_ELO_TEMPORADA * math.sqrt(max(resta, 0.0))


def simular(S, cfg, n=N_SIM, semente=2026, sigma=None):
    """Simula o resto da temporada n vezes. Devolve, por time, pontos esperados e chance de cada posição final."""
    d = S["d"]
    cur = d[d["ano"] == S["atual"]]
    resto = cur[~cur["jogado"]]
    atual = tabela_atual(S, cfg)
    times = [L["t"] for L in atual]
    ix = {t: i for i, t in enumerate(times)}
    T = len(times)
    base = {k: np.array([L[k] for L in atual], dtype=float) for k in ("pts", "v", "sg", "gp")}
    rng = np.random.default_rng(semente)
    sigma = sigma_incerteza(S) if sigma is None else sigma
    choque = rng.normal(0, sigma, (n, T))
    pts, vit, sg, gp = (np.tile(base[k], (n, 1)) for k in ("pts", "v", "sg", "gp"))
    if len(resto):
        ci = resto["casa"].map(ix).values
        fi = resto["fora"].map(ix).values
        elo = np.array([S["elo"].get(t, ELO_INICIAL) for t in times])
        adj = S.get("adj") or []   # notícias: ajuste de força só nos jogos dentro da janela de cada notícia
        dn = np.array([noticias.delta(adj, c, dd) - noticias.delta(adj, f, dd) for c, f, dd in zip(resto["casa"], resto["fora"], resto["dia_br"])])
        x = (elo[ci] + choque[:, ci] - elo[fi] - choque[:, fi] + dn) / 100     # (n, M)
        a, (b, c) = S["modelo"].m.intercept_, S["modelo"].m.coef_
        gc = rng.poisson(np.exp(a + b * x + c))
        gf = rng.poisson(np.exp(a - b * x))
        for t in range(T):
            h, v_ = np.where(ci == t)[0], np.where(fi == t)[0]
            gh, ga = gc[:, h], gf[:, h]
            gv, gva = gf[:, v_], gc[:, v_]
            vit[:, t] += (gh > ga).sum(1) + (gv > gva).sum(1)
            pts[:, t] += 3 * ((gh > ga).sum(1) + (gv > gva).sum(1)) + (gh == ga).sum(1) + (gv == gva).sum(1)
            sg[:, t] += (gh - ga).sum(1) + (gv - gva).sum(1)
            gp[:, t] += gh.sum(1) + gv.sum(1)
    chave = chave_ordem(pts, vit, sg, gp, bool(cfg.get("desempate_vitorias"))) + rng.random((n, T)) * 0.5
    pos = (-chave).argsort(1).argsort(1)                                     # 0 = campeão
    dist = np.stack([(pos == p).mean(0) for p in range(T)], axis=1)          # (T, T): time x posição
    topo, baixo = cfg["topo"], cfg["rebaixa"]
    return dict(n=n, times=times, sigma=sigma, pts=pts.mean(0), pts_lo=np.percentile(pts, 10, axis=0), pts_hi=np.percentile(pts, 90, axis=0),
                pos_media=pos.mean(0) + 1, dist=dist, tit=dist[:, 0], topo=dist[:, :topo].sum(1), rebaixa=dist[:, T - baixo:].sum(1),
                n_rest=int(len(resto)))


def prever_jogos(S, jogos):
    """Chances dos jogos ainda não disputados (com o Elo de hoje)."""
    if len(jogos) == 0:
        return jogos.assign(p_c=[], p_e=[], p_f=[])
    elo, adj = S["elo"], S.get("adj") or []
    x = np.array([(elo.get(g.casa, ELO_INICIAL) + noticias.delta(adj, g.casa, g.dia_br) - elo.get(g.fora, ELO_INICIAL)
                   - noticias.delta(adj, g.fora, g.dia_br)) / 100 for g in jogos.itertuples()])
    lc, lf = S["modelo"].lambdas(x)
    p, plac = chances(lc, lf)
    return jogos.assign(p_c=p[:, 0], p_e=p[:, 1], p_f=p[:, 2], lc=lc, lf=lf, pl_c=plac[:, 0], pl_f=plac[:, 1])


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def montar(lid, hoje=None):
    d = completar_com_espn(carregar_liga(lid, hoje), lid)
    S = construir(d)
    S["adj"] = noticias.carregar("futebol", lid, hoje)
    ruins = noticias.desconhecidos(S["adj"], set(d["casa"]) | set(d["fora"]))
    if ruins:
        print(f"::warning::ajustes_noticias.csv: time(s) sem correspondência em {LIGAS[lid]['nome']}: {', '.join(ruins)}")
    return S


def main(argv):
    pedidas = argv or list(LIGAS)
    for lid in pedidas:
        if lid not in LIGAS:
            sys.exit(f"Liga desconhecida: {lid}. Opções: {', '.join(LIGAS)}")
        S = montar(lid)
        a = resumo_acuracia(S)
        cfg = LIGAS[lid]
        print(f"\n== {cfg['nome']} {S['d'][S['d']['ano'] == S['atual']]['temp'].iloc[0]} ==")
        print(f"Acerto do palpite 1X2 ({a['anos_ref'][0]}-{a['anos_ref'][1]}, {a['n_ref']} jogos): {a['acc']:.1%}"
              f"  | sempre mandante: {a['acc_mandante']:.1%}  | empates: {a['freq_empate']:.1%}")
        for i, L in enumerate(tabela_atual(S, cfg)[:5], 1):
            print(f"{i}. {L['t']:<20} {L['pts']} pts ({L['j']} jogos)")
        sim = simular(S, cfg)
        top = np.argsort(-sim["tit"])[:3]
        print("Favoritos ao título:", ", ".join(f"{sim['times'][i]} {sim['tit'][i]:.0%}" for i in top))


if __name__ == "__main__":
    main([a.lower() for a in sys.argv[1:]])

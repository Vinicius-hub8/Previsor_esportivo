#!/usr/bin/env python3
"""
Previsor de Futebol
===================
Seis ligas (Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e Brasileirão) e a Champions League.

Para cada competição:
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
openfootball ainda não tem o resultado. A Champions vem só da ESPN (guardada em web/public/dados/champions/<temporada>.json).

Uso (terminal):
    python previsor_futebol.py                 -> resumo e acurácia de cada liga
    python previsor_futebol.py premier         -> só uma liga (premier, laliga, seriea, bundesliga, ligue1, brasileirao, champions)
    python previsor_futebol.py coletar-champions 2018 2021   -> baixa da ESPN temporadas antigas da Champions

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
    # Champions: fase de liga com 36 clubes (1º-8º direto às oitavas, 9º-24º playoff, 25º-36º eliminados) e depois mata-mata.
    "champions": dict(nome="Champions League", pais="Europa", fonte="espn", espn="uefa.champions", tz="America/Sao_Paulo",
                      topo=8, rebaixa=12, mata_mata=True, europeu=True),
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
AVISOS_CHAMPIONS = [
    "Lesões, suspensões, escalação, mercado da bola e troca de técnico não entram no modelo.",
    "A força (Elo) de cada clube vem só dos jogos de Champions desde 2018-19. Clube que jogou pouco a competição tem força menos precisa.",
    "Fase de liga: 36 clubes, 8 jogos cada. Do 1º ao 8º vão direto às oitavas, do 9º ao 24º disputam o playoff e do 25º ao 36º são eliminados.",
    "Desempate da tabela: pontos, saldo de gols e gols marcados (a UEFA usa mais critérios, como gols fora de casa e vitórias).",
    "Chance de título: depois da fase de liga, simulamos o mata-mata (ida e volta, final em jogo único) com chaveamento simplificado; os confrontos reais saem de sorteio.",
    "Os horários são de Brasília.",
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
    # Champions (nomes da ESPN)
    "Bayern Munich": "Bayern de Munique", "Internazionale": "Inter", "Feyenoord Rotterdam": "Feyenoord", "PSV Eindhoven": "PSV",
    "Slavia Prague": "Slavia Praga", "Sparta Prague": "Sparta Praga", "Sabah FK": "Sabah", "Viking FK": "Viking", "Bodo/Glimt": "Bodø/Glimt",
    "LASK Linz": "LASK", "Fenerbahce": "Fenerbahçe", "Sporting CP": "Sporting", "Shakhtar Donetsk": "Shakhtar", "Brugge": "Club Brugge",
    "Red Star Belgrade": "Estrela Vermelha", "Red Bull Salzburg": "Salzburg", "Dinamo Zagreb": "Dínamo Zagreb", "Benfica": "Benfica",
    "FC Copenhagen": "Copenhague", "Copenhagen": "Copenhague", "Besiktas": "Beşiktaş", "Olympiacos": "Olympiacos",
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


def temporada_europeia(cfg):
    return "br" not in cfg


def carregar_liga(lid, hoje=None, ate_ano=None):
    """DataFrame com todos os jogos (jogados ou não) das temporadas desde PRIMEIRO_ANO, já com horário de Brasília."""
    cfg = LIGAS[lid]
    hoje = hoje or date.today()
    linhas = []
    if cfg.get("fonte") == "espn":
        linhas = linhas_champions(hoje, ate_ano)
    elif "eu" in cfg:
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
    for col, padrao in (("na_tabela", True), ("fase", None), ("nota", None), ("espn", None)):
        if col not in d.columns:
            d[col] = padrao
    d["na_tabela"] = d["na_tabela"].astype(bool)
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
    """Acha cada evento da ESPN no calendário (nome dos times + data). Guarda o id da ESPN na coluna 'espn' e, se o evento
    já terminou e o jogo ainda não tem placar, preenche gc/gf. Devolve quantos placares completou."""
    if "espn" not in d.columns:
        d["espn"] = None
    d["espn"] = d["espn"].astype(object)
    n = 0
    dts = pd.to_datetime(d["dt"], utc=True).values.astype("datetime64[s]").astype(np.int64)
    pend_adiado = (d["adiado"] & ~d["jogado"]).values
    for ev in eventos:
        if not ev.get("data"):
            continue
        final = bool(ev.get("final")) and ev.get("pts_casa") is not None and ev.get("pts_fora") is not None
        dia = int(pd.Timestamp(ev["data"]).tz_convert("UTC").timestamp())
        perto = np.abs(dts - dia) <= folga_dias * 86400
        if final:
            perto |= pend_adiado & (np.abs(dts - dia) <= 365 * 86400)   # jogo adiado: a nova data ainda não está na base
        def procurar(mascara):
            melhor, nota = None, 0.0
            for i in d.index[mascara]:
                if d.at[i, "espn"] is not None and d.at[i, "espn"] != ev.get("id"):
                    continue
                s = _sim_nome(ev["nome_casa"], d.at[i, "casa_raw"]) + _sim_nome(ev["nome_fora"], d.at[i, "fora_raw"])
                s = max(s, _sim_nome(ev["nome_casa"], d.at[i, "casa"]) + _sim_nome(ev["nome_fora"], d.at[i, "fora"]))
                if s > nota:
                    melhor, nota = i, s
            return melhor, nota

        melhor, nota = procurar(perto)
        if (melhor is None or nota < 1.5) and final:
            # jogo remarcado sem aviso na base (comum no Brasileirão): aceita até 30 dias de diferença, mas só com os dois
            # nomes batendo quase exatamente (no mesmo turno, o mesmo mando acontece uma vez só)
            melhor, nota = procurar(~d["jogado"].values & (np.abs(dts - dia) <= 30 * 86400))
            if nota < 1.9:
                melhor = None
        if melhor is None or nota < 1.5:
            continue
        if ev.get("id"):
            d.at[melhor, "espn"] = str(ev["id"])
        if final and not d.at[melhor, "jogado"]:
            d.at[melhor, "gc"], d.at[melhor, "gf"], d.at[melhor, "jogado"] = float(ev["pts_casa"]), float(ev["pts_fora"]), True
            n += 1
    return n


def janela_espn(d, hoje=None, max_dias=200, adiante=7):
    """Dias a consultar na ESPN: do jogo mais antigo que já devia ter acontecido e ainda não tem placar (menos 2 dias de folga)
    até `adiante` dias à frente (para guardar o id da ESPN dos próximos jogos). Pelo menos os últimos 3 dias."""
    hoje = hoje or datetime.now(TZ_BR).date()
    agora = pd.Timestamp(hoje, tz="UTC") + pd.Timedelta(days=1)
    atual = d["ano"].max()
    pend = d[(d["ano"] == atual) & ~d["jogado"] & ~d["adiado"] & (d["dt"] < agora)]
    ini = hoje - pd.Timedelta(days=3).to_pytimedelta()
    if len(pend):
        ini = min(ini, pend["dt"].min().date() - pd.Timedelta(days=2).to_pytimedelta())
    ini = max(ini, hoje - pd.Timedelta(days=max_dias).to_pytimedelta())
    import espn
    return espn.dias_entre(ini, hoje + pd.Timedelta(days=adiante).to_pytimedelta())


def completar_com_espn(d, lid, hoje=None):
    if "espn" not in d.columns:
        d["espn"] = None
    if os.environ.get("SEM_ESPN"):
        return d
    try:
        import espn
        dias = janela_espn(d, hoje)
        eventos = espn.jogos_dos_dias(f"soccer/{LIGAS[lid]['espn']}", dias)
    except Exception as e:
        print(f"::warning::ESPN indisponível para {lid} ({e}); seguindo só com o openfootball.")
        return d
    n = casar_espn(d, eventos)
    print(f"ESPN: {len(eventos)} evento(s) em {len(dias)} dia(s); {n} placar(es) de {LIGAS[lid]['nome']} completado(s)")
    return d


# ----------------------------------------------------------------------------
# Champions League: a ESPN é a fonte. Cada temporada fica guardada em web/public/dados/champions/AAAA-AAAA.json
# (só jogos da competição principal; a ESPN não traz as fases preliminares).
# ----------------------------------------------------------------------------
PASTA_CHAMPIONS = Path(__file__).resolve().parent / "web" / "public" / "dados" / "champions"
FASES_TABELA = {"league-phase"}                       # fases que contam para a tabela
FASES_MATA = {  # slug da ESPN -> (nome, sigla curta, ordem)
    "knockout-round-playoffs": ("Playoff", "PO", 1), "round-of-16": ("Oitavas", "OI", 2), "quarterfinals": ("Quartas", "QF", 3),
    "semifinals": ("Semifinal", "SF", 4), "final": ("Final", "F", 5),
}


def _arquivo_champions(ano, pasta=None):
    return (pasta or PASTA_CHAMPIONS) / f"{ano}-{ano + 1}.json"


def fase_preliminar(fase):
    """Fases eliminatórias de agosto (antes da fase de grupos/liga): ficam fora da base."""
    return bool(fase) and (fase.startswith("qualifying") or fase == "playoffs")


def jogo_champions(ev):
    """Evento da ESPN (espn.interpretar) -> registro guardado no arquivo da temporada (data e hora de Brasília)."""
    if not ev.get("data") or fase_preliminar(ev.get("fase")):
        return None
    ini = pd.Timestamp(ev["data"]).tz_convert(TZ_BR)
    final = bool(ev.get("final")) and ev.get("pts_casa") is not None and ev.get("pts_fora") is not None
    return {"id": str(ev["id"]), "data": ini.strftime("%Y-%m-%d"), "hora": ini.strftime("%H:%M"),
            "mandante": ev.get("nome_casa") or "?", "visitante": ev.get("nome_fora") or "?", "estado": ev.get("estado") or "pre",
            "finalizado": final, "placar": [int(ev["pts_casa"]), int(ev["pts_fora"])] if final else None,
            "fase": ev.get("fase"), "nota": ev.get("nota"), "temporada": ev.get("temporada")}


def _ler_temporada(arq):
    if not arq.exists():
        return {}
    import json
    return {str(j["id"]): j for j in json.loads(arq.read_text(encoding="utf-8")).get("jogos", [])}


def _gravar_temporada(arq, ano, jogos):
    import json
    lista = sorted(jogos.values(), key=lambda j: (j["data"], j.get("hora") or "", j["id"]))
    arq.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"meta": {"competicao": "UEFA Champions League", "temporada": f"{ano}-{ano + 1}", "quantidade": len(lista),
                         "finalizadas": sum(bool(j.get("finalizado")) for j in lista), "fonte": "ESPN"}, "jogos": lista}
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(arq)


def _juntar(antigo, novo):
    """Nunca troca um resultado final por uma informação incompleta."""
    if antigo and antigo.get("finalizado") and not novo.get("finalizado"):
        return antigo
    return novo


def coletar_champions(ano, ini, fim, pasta=None):
    """Consulta a ESPN dia a dia de `ini` a `fim` e junta ao arquivo da temporada `ano`. Devolve quantos jogos mudaram."""
    import espn
    arq = _arquivo_champions(ano, pasta)
    jogos = _ler_temporada(arq)
    mudou = 0
    for ev in espn.jogos_dos_dias(f"soccer/{LIGAS['champions']['espn']}", espn.dias_entre(ini, fim)):
        if ev.get("temporada") not in (None, ano):
            continue
        j = jogo_champions(ev)
        if j is None:
            continue
        novo = _juntar(jogos.get(j["id"]), j)
        if novo != jogos.get(j["id"]):
            jogos[j["id"]] = novo
            mudou += 1
    if jogos:
        _gravar_temporada(arq, ano, jogos)
    return mudou


def atualizar_champions(hoje=None, pasta=None):
    """Atualiza a temporada atual: do jogo mais antigo ainda sem placar até o fim da fase de liga (ou 3 semanas à frente,
    o que vier depois). Se o arquivo não tiver a fase dos jogos (formato antigo), baixa a temporada inteira de novo."""
    hoje = hoje or datetime.now(TZ_BR).date()
    ano = temporada_atual_europa(hoje)
    jogos = _ler_temporada(_arquivo_champions(ano, pasta))
    comeco = date(ano, 8, 1)
    pend = [date.fromisoformat(j["data"]) for j in jogos.values() if not j.get("finalizado") and j["data"] <= hoje.isoformat()]
    if not jogos or any(not j.get("fase") for j in jogos.values()):
        ini = comeco
    else:
        ini = max(comeco, min([hoje - pd.Timedelta(days=3).to_pytimedelta()]
                              + [p - pd.Timedelta(days=1).to_pytimedelta() for p in pend]))
    fim = min(date(ano + 1, 6, 30), max(hoje + pd.Timedelta(days=21).to_pytimedelta(), date(ano + 1, 1, 31)))
    n = coletar_champions(ano, ini, fim, pasta)
    print(f"ESPN: Champions {ano}-{ano + 1}, {(fim - ini).days + 1} dia(s) consultado(s), {n} jogo(s) novo(s) ou atualizado(s)")


def _rodadas_temporada(jogos):
    """Numera as rodadas de uma temporada pela semana do jogo: primeiro as semanas da fase de liga (1 a 8), depois as do
    mata-mata. Devolve {id: rodada}."""
    sem = {j["id"]: date.fromisoformat(j["data"]).isocalendar()[:2] for j in jogos}
    liga = sorted({sem[j["id"]] for j in jogos if j.get("fase") in FASES_TABELA})
    resto = sorted({sem[j["id"]] for j in jogos if sem[j["id"]] not in liga})
    ordem = {w: i + 1 for i, w in enumerate(liga + resto)}
    return {j["id"]: ordem[sem[j["id"]]] for j in jogos}


def linhas_champions(hoje=None, ate_ano=None, pasta=None, atualizar=True):
    """Linhas (mesmo formato das outras ligas) de todas as temporadas guardadas desde PRIMEIRO_ANO."""
    hoje = hoje or datetime.now(TZ_BR).date()
    if atualizar and not os.environ.get("SEM_ESPN") and ate_ano is None:
        try:
            atualizar_champions(hoje, pasta)
        except Exception as e:
            print(f"::warning::ESPN indisponível para a Champions ({e}); seguindo com os jogos já guardados.")
    linhas = []
    for arq in sorted((pasta or PASTA_CHAMPIONS).glob("20??-20??.json")):
        ano = int(arq.stem[:4])
        if ano < PRIMEIRO_ANO or (ate_ano and ano > ate_ano):
            continue
        jogos = list(_ler_temporada(arq).values())
        rod = _rodadas_temporada(jogos)
        tem_liga = any(j.get("fase") in FASES_TABELA for j in jogos)
        for j in jogos:
            pl = j.get("placar") if j.get("finalizado") else None
            linhas.append(dict(temp=f"{ano}-{str(ano + 1)[2:]}", rodada=rod[j["id"]], dia=j["data"], hora=j.get("hora"), tz="America/Sao_Paulo",
                               casa_raw=j["mandante"], fora_raw=j["visitante"], gc=float(pl[0]) if pl else np.nan,
                               gf=float(pl[1]) if pl else np.nan, adiado=False, espn=str(j["id"]), fase=j.get("fase"),
                               nota=j.get("nota"), na_tabela=(j.get("fase") in FASES_TABELA) if tem_liga else True))
    return linhas


def rotulos_rodada(cur):
    """Nome de cada rodada do mata-mata ({rodada: {nome, curto}}), a partir da fase da ESPN. Vazio se não houver."""
    out = {}
    if "fase" not in cur.columns:
        return out
    vistos = {}
    for r, g in cur.sort_values("dt").groupby("rodada", sort=True):
        fase = g["fase"].dropna().mode()
        if fase.empty or fase.iloc[0] not in FASES_MATA:
            continue
        nome, curto, _ = FASES_MATA[fase.iloc[0]]
        vistos[nome] = vistos.get(nome, 0) + 1
        if fase.iloc[0] == "final":
            out[str(int(r))] = {"nome": nome, "curto": curto}
        else:
            perna = "ida" if vistos[nome] == 1 else "volta"
            out[str(int(r))] = {"nome": f"{nome} ({perna})", "curto": f"{curto}{vistos[nome]}"}
    return out


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


def jogos_tabela(S):
    """Jogos da temporada atual que contam para a tabela (na Champions, só a fase de liga)."""
    d = S["d"]
    return d[(d["ano"] == S["atual"]) & d["na_tabela"]]


def tabela_atual(S, cfg):
    cur = jogos_tabela(S)
    t = cur[cur["jogado"]]
    times = sorted(set(cur["casa"]) | set(cur["fora"]))
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
    cur = jogos_tabela(S)
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
    tit = dist[:, 0]
    if cfg.get("mata_mata"):
        elo = np.array([S["elo"].get(t, ELO_INICIAL) for t in times])
        tit = simular_mata_mata(S, (-chave).argsort(1), elo[None, :] + choque, ix, rng)
    return dict(n=n, times=times, sigma=sigma, pts=pts.mean(0), pts_lo=np.percentile(pts, 10, axis=0), pts_hi=np.percentile(pts, 90, axis=0),
                pos_media=pos.mean(0) + 1, dist=dist, tit=tit, topo=dist[:, :topo].sum(1), rebaixa=dist[:, T - baixo:].sum(1),
                meio=dist[:, topo:T - baixo].sum(1), n_rest=int(len(resto)))


# ----------------------------------------------------------------------------
# Mata-mata da Champions (chance de título)
# ----------------------------------------------------------------------------
def _gols(S, rng, elo_c, elo_f, neutro=False):
    """Gols sorteados de um jogo para cada simulação (elo_c e elo_f: arrays (n,))."""
    a, (b, c) = S["modelo"].m.intercept_, S["modelo"].m.coef_
    x = (elo_c - elo_f) / 100
    casa = c / 2 if neutro else c
    return rng.poisson(np.exp(a + b * x + casa)), rng.poisson(np.exp(a - b * x + (c / 2 if neutro else 0)))


def _confronto(S, rng, A, B, forca, ja=None, pernas=None, vencedor=None):
    """Quem passa em cada simulação. A e B: índices dos times (n,). forca: Elo por simulação (n, T).
    ja: gols já marcados (A, B) em pernas jogadas; pernas: lista dos mandantes ('A' ou 'B') das pernas que faltam
    (padrão: ida na casa de B, volta na casa de A). Empate no agregado: prorrogação/pênaltis, 50% para cada."""
    n = len(A)
    if vencedor is not None:
        return np.where(vencedor == "A", A, B)
    ga, gb = np.full(n, (ja or (0, 0))[0]), np.full(n, (ja or (0, 0))[1])
    rows = np.arange(n)
    ea, eb = forca[rows, A], forca[rows, B]
    for mand in (["B", "A"] if pernas is None else pernas):
        if mand == "N":
            x, y = _gols(S, rng, ea, eb, neutro=True)
            ga, gb = ga + x, gb + y
        elif mand == "A":
            x, y = _gols(S, rng, ea, eb)
            ga, gb = ga + x, gb + y
        else:
            x, y = _gols(S, rng, eb, ea)
            ga, gb = ga + y, gb + x
    sorteio = rng.random(n) < 0.5
    return np.where((ga > gb) | ((ga == gb) & sorteio), A, B)


def _confrontos_reais(S, fase, ix):
    """Confrontos de uma fase do mata-mata já definidos na base: [(A, B, ja, pernas_restantes, vencedor_ou_None)]."""
    d = S["d"]
    g = d[(d["ano"] == S["atual"]) & (d["fase"] == fase)].sort_values("dt")
    pares = {}
    for r in g.itertuples():
        if r.casa not in ix or r.fora not in ix:
            continue
        pares.setdefault(frozenset((r.casa, r.fora)), []).append(r)
    out = []
    for jogos in pares.values():
        if len(jogos) == 1 and fase != "final":
            A, B = jogos[0].fora, jogos[0].casa       # só a ida na base: a volta será na casa de quem jogou fora
        else:
            A, B = jogos[-1].casa, jogos[-1].fora     # A recebe o último jogo (a volta)
        nome_raw = {jogos[0].casa: jogos[0].casa_raw, jogos[0].fora: jogos[0].fora_raw}
        ja, faltam, venc = [0, 0], [], None
        for r in jogos:
            if r.jogado:
                ja[0] += int(r.gc if r.casa == A else r.gf)
                ja[1] += int(r.gf if r.casa == A else r.gc)
                # ex.: "2nd Leg - Arsenal advance 2-1 on aggregate" / "Paris Saint-Germain win 4-3 on penalties"
                m = re.search(r"(.+?) (?:advance|win)\b", str(r.nota or "").split(" - ")[-1])
                if m:
                    venc = "A" if _sim_nome(m.group(1), nome_raw[A]) >= _sim_nome(m.group(1), nome_raw[B]) else "B"
            else:
                faltam.append("N" if fase == "final" else ("A" if r.casa == A else "B"))
        if len(jogos) == 1 and fase != "final":
            faltam.append("A")
        if venc is None and not faltam:            # tudo jogado e sem nota: decide pelo agregado (empate = pênaltis, 50%)
            venc = "A" if ja[0] > ja[1] else "B" if ja[1] > ja[0] else None
            if venc is None:
                faltam = []
        out.append((ix[A], ix[B], tuple(ja), faltam, venc))
    return out


def simular_mata_mata(S, ordem, forca, ix, rng):
    """Chance de título de cada time. ordem: (n, T) índices dos times do 1º ao último da fase de liga em cada simulação.
    Chaveamento simplificado do formato 2024+: playoff 9º x 24º, 10º x 23º...; oitavas 1º x vencedor de 16º/17º, 2º x 15º/18º...;
    quartas 1/8 x 4/5... Confrontos já definidos na base substituem os simulados."""
    n, T = ordem.shape
    if T < 24:
        return np.zeros(T)
    rows = np.arange(n)

    def fase(nome, pares_sim):
        """pares_sim: lista de (A, B) arrays (n,). Usa os confrontos reais se a fase já estiver na base."""
        reais = _confrontos_reais(S, nome, ix)
        if reais and len(reais) == len(pares_sim):
            # ordena os confrontos reais na mesma ordem do chaveamento: pelo melhor colocado de cada um
            pos = np.empty((n, T), dtype=int)
            pos[rows[:, None], ordem] = np.arange(T)
            melhor = [np.minimum(pos[:, a], pos[:, b]).mean() for a, b, *_ in reais]
            reais = [reais[i] for i in np.argsort(melhor)]
            return [_confronto(S, rng, np.full(n, a), np.full(n, b), forca, ja, pernas, None if v is None else np.full(n, v))
                    for a, b, ja, pernas, v in reais]
        return [_confronto(S, rng, A, B, forca, pernas=["N"] if nome == "final" else None) for A, B in pares_sim]

    seed = lambda k: ordem[:, k - 1]                       # time na posição k em cada simulação
    po = fase("knockout-round-playoffs", [(seed(9 + i), seed(24 - i)) for i in range(8)])     # po[i]: 9+i x 24-i
    # oitavas: o k-ésimo colocado (k=1..8) enfrenta o vencedor de (17-k) x (16+k), que é po[8-k]
    oit = fase("round-of-16", [(seed(k), po[8 - k]) for k in range(1, 9)])
    qf = fase("quarterfinals", [(oit[i], oit[7 - i]) for i in range(4)])      # 1/8, 2/7, 3/6, 4/5
    sf = fase("semifinals", [(qf[0], qf[3]), (qf[1], qf[2])])
    campeao = fase("final", [(sf[0], sf[1])])[0]
    return np.bincount(campeao, minlength=T) / n


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
    d = carregar_liga(lid, hoje)
    if LIGAS[lid].get("fonte") != "espn":          # a Champions já vem da ESPN
        d = completar_com_espn(d, lid, hoje)
    S = construir(d)
    S["adj"] = noticias.carregar("futebol", lid, hoje)
    ruins = noticias.desconhecidos(S["adj"], set(d["casa"]) | set(d["fora"]))
    if ruins:
        print(f"::warning::ajustes_noticias.csv: time(s) sem correspondência em {LIGAS[lid]['nome']}: {', '.join(ruins)}")
    return S


def main(argv):
    if argv[:1] == ["coletar-champions"]:
        ini, fim = (int(argv[1]), int(argv[2] if len(argv) > 2 else argv[1])) if len(argv) > 1 else (PRIMEIRO_ANO, temporada_atual_europa(date.today()))
        for ano in range(ini, fim + 1):
            n = coletar_champions(ano, date(ano, 8, 1), min(date(ano + 1, 8, 31), date.today() + pd.Timedelta(days=120).to_pytimedelta()))
            print(f"Champions {ano}-{ano + 1}: {n} jogo(s) novo(s) ou atualizado(s)")
        return
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

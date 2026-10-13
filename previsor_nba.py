#!/usr/bin/env python3
"""
Previsor NBA
============
Mesma ideia do previsor da NFL, adaptada ao basquete:

  1) Palpite de cada jogo (chance de vitória do mandante), com a acurácia medida de verdade.
  2) Projeção de recorde de cada time até o fim da temporada regular (82 jogos).

Dados: calendário e placares abertos do projeto hoopR (sportsdataverse), via GitHub.
O modelo usa só: Elo, forma recente, descanso e fase (temporada regular ou mata-mata).

Uso (terminal):
    python previsor_nba.py                    -> resumo e acurácia do modelo
    python previsor_nba.py dia 2026-10-20     -> palpites de um dia
    python previsor_nba.py time BOS           -> recorde projetado do Boston Celtics

Requisitos: pandas, numpy, scikit-learn.
"""
import os
import sys
import warnings
from collections import deque
from datetime import date

import numpy as np
import pandas as pd

import noticias
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

URL = os.environ.get(
    "NBA_CSV",
    "https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/schedules/nba_schedule_master.csv",
)
COLUNAS = [
    "game_id", "date", "game_date", "season", "season_type", "notes_headline", "time_valid", "neutral_site",
    "status_type_name", "status_type_completed", "home_id", "away_id", "home_abbreviation", "away_abbreviation",
    "home_score", "away_score",
]

# sigla (padrão ESPN) -> (nome, apelido, conferência, divisão)
TIMES = {
    "ATL": ("Atlanta Hawks", "Hawks", "Leste", "Sudeste"), "BOS": ("Boston Celtics", "Celtics", "Leste", "Atlântico"),
    "BKN": ("Brooklyn Nets", "Nets", "Leste", "Atlântico"), "CHA": ("Charlotte Hornets", "Hornets", "Leste", "Sudeste"),
    "CHI": ("Chicago Bulls", "Bulls", "Leste", "Central"), "CLE": ("Cleveland Cavaliers", "Cavaliers", "Leste", "Central"),
    "DAL": ("Dallas Mavericks", "Mavericks", "Oeste", "Sudoeste"), "DEN": ("Denver Nuggets", "Nuggets", "Oeste", "Noroeste"),
    "DET": ("Detroit Pistons", "Pistons", "Leste", "Central"), "GS": ("Golden State Warriors", "Warriors", "Oeste", "Pacífico"),
    "HOU": ("Houston Rockets", "Rockets", "Oeste", "Sudoeste"), "IND": ("Indiana Pacers", "Pacers", "Leste", "Central"),
    "LAC": ("LA Clippers", "Clippers", "Oeste", "Pacífico"), "LAL": ("Los Angeles Lakers", "Lakers", "Oeste", "Pacífico"),
    "MEM": ("Memphis Grizzlies", "Grizzlies", "Oeste", "Sudoeste"), "MIA": ("Miami Heat", "Heat", "Leste", "Sudeste"),
    "MIL": ("Milwaukee Bucks", "Bucks", "Leste", "Central"), "MIN": ("Minnesota Timberwolves", "Timberwolves", "Oeste", "Noroeste"),
    "NO": ("New Orleans Pelicans", "Pelicans", "Oeste", "Sudoeste"), "NY": ("New York Knicks", "Knicks", "Leste", "Atlântico"),
    "OKC": ("Oklahoma City Thunder", "Thunder", "Oeste", "Noroeste"), "ORL": ("Orlando Magic", "Magic", "Leste", "Sudeste"),
    "PHI": ("Philadelphia 76ers", "76ers", "Leste", "Atlântico"), "PHX": ("Phoenix Suns", "Suns", "Oeste", "Pacífico"),
    "POR": ("Portland Trail Blazers", "Trail Blazers", "Oeste", "Noroeste"), "SA": ("San Antonio Spurs", "Spurs", "Oeste", "Sudoeste"),
    "SAC": ("Sacramento Kings", "Kings", "Oeste", "Pacífico"), "TOR": ("Toronto Raptors", "Raptors", "Leste", "Atlântico"),
    "UTAH": ("Utah Jazz", "Jazz", "Oeste", "Noroeste"), "WSH": ("Washington Wizards", "Wizards", "Leste", "Sudeste"),
}

# Parâmetros do Elo (valores clássicos do basquete)
ELO_MEDIA, ELO_K, ELO_CASA, ELO_REVERSAO = 1505, 20, 70, 0.75
JANELA_FORMA = 10
JOGOS_TEMPORADA = 82
# Incerteza sobre a força real dos times na simulação (em pontos de Elo). Medida no histórico:
# antes da temporada, o Elo erra o desempenho real em ~105 pontos (trocas, lesões, evolução); o erro cai
# conforme a temporada avança. Sem isso, o favorito fica favorito demais.
SIGMA_ELO_INICIO, SIGMA_ELO_FIM = 105.0, 35.0
KAPPA_SERIE = 2.2   # uma série melhor de 7 amplifica a vantagem de um jogo ~2,2x (em log-odds)
PRIMEIRA_TEMP_TREINO = 2004   # a de 2003 serve só para aquecer o Elo
PRIMEIRA_TEMP_TESTE = 2012
ANOS_REF = (2017, 2026)       # temporadas (ano final) usadas para a acurácia mostrada no site
FEATS = ["dif_elo", "dif_forma", "dif_desc", "h_b2b", "a_b2b", "playoff"]

AVISOS = [
    "Lesões, descanso de astros (load management), trocas e mudanças de elenco NÃO entram no modelo.",
    "O Elo vem das temporadas passadas: no começo do ano, com elencos novos, o modelo é menos confiável.",
    "Quanto mais distante o jogo, menos confiável: a força dos times é medida até hoje e não muda na projeção.",
    "O modelo usa só calendário e placares; informações de mercado e de lesões deixariam os palpites mais precisos.",
    "A acurácia é uma média de várias temporadas; numa noite isolada o resultado varia muito.",
    "Isto é um estudo estatístico, não uma recomendação de aposta.",
]


def rotulo_temporada(ano):
    """2027 (ano em que a temporada termina) -> '2026-27'."""
    return f"{ano - 1}-{str(ano)[2:]}"


# ----------------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------------
def _rodada(tipo, nota):
    """Nome da fase dos mata-matas a partir da legenda do jogo."""
    n = nota.lower() if isinstance(nota, str) else ""
    if tipo == "PI":
        return "Play-in"
    if "1st round" in n:
        return "Primeira rodada"
    if "semifinals" in n:
        return "Semifinais de conferência"
    if "finals" in n and "nba" not in n:
        return "Finais de conferência"
    if "nba finals" in n:
        return "Finais da NBA"
    return "Playoffs"


def _completar_com_espn(d):
    """O hoopR atualiza uma vez por dia; a ESPN (de onde vêm os ids dos jogos) tem o placar minutos depois."""
    import espn
    finais = espn.finais("nba")
    if not finais:
        return d
    n = 0
    for i in d.index[~d["status_type_completed"].astype(bool)]:
        r = finais.get(str(int(d.at[i, "game_id"])))
        if r:
            d.at[i, "away_score"], d.at[i, "home_score"], d.at[i, "status_type_completed"] = r[0], r[1], True
            n += 1
    if n:
        print(f"ESPN: {n} placar(es) completado(s)")
    return d


def carregar():
    """Baixa o calendário/placares e devolve um DataFrame limpo, só com os 30 times e jogos que valem."""
    d = _completar_com_espn(pd.read_csv(URL, usecols=COLUNAS, low_memory=False))
    d = d[d["season_type"].isin([2, 3, 5]) & (d["season"] >= 2003)]
    d = d[~d["status_type_name"].isin(["STATUS_POSTPONED", "STATUS_CANCELED"])]

    # Times pelo id (assim Seattle -> OKC, New Jersey -> Brooklyn etc. viram a mesma franquia)
    ult = d[d["season"] == d["season"].max()]
    atuais = {}
    for lado in ("home", "away"):
        for i, s in zip(ult[f"{lado}_id"], ult[f"{lado}_abbreviation"]):
            if s in TIMES:
                atuais[int(i)] = s
    d = d[d["home_id"].isin(atuais) & d["away_id"].isin(atuais)].copy()
    d["m"] = d["home_id"].astype(int).map(atuais)
    d["v"] = d["away_id"].astype(int).map(atuais)
    d["id_m"], d["id_v"] = d["home_id"].astype(int), d["away_id"].astype(int)

    dt = pd.to_datetime(d["date"], utc=True).dt.tz_convert("America/New_York")
    d["dt"] = dt
    d["dia"] = dt.dt.strftime("%Y-%m-%d")
    d["hora"] = np.where(d["time_valid"].astype(bool), dt.dt.strftime("%H:%M"), None)
    d["tipo"] = d["season_type"].map({2: "REG", 3: "PO", 5: "PI"})
    d["rodada"] = [_rodada(t, n) if t != "REG" else "" for t, n in zip(d["tipo"], d["notes_headline"])]
    d["jogado"] = d["status_type_completed"].astype(bool) & d["home_score"].notna()
    d["neutro"] = d["neutral_site"].fillna(False).astype(bool)
    d = d.rename(columns={"home_score": "pts_m", "away_score": "pts_v"})
    return d.sort_values(["dt", "game_id"]).drop_duplicates("game_id").reset_index(drop=True)


# ----------------------------------------------------------------------------
# Features (Elo, forma, descanso) — cada uma usa só jogos anteriores
# ----------------------------------------------------------------------------
def _descanso(jg):
    """Dias desde o jogo anterior de cada time (de 1 a 7). 1 = jogo em dia seguido (back-to-back).
    Vale também para jogos futuros: o calendário é conhecido, então isso não é vazamento."""
    longo = pd.concat([
        pd.DataFrame({"game_id": jg["game_id"], "t": jg["id_m"], "dia": jg["dia"], "lado": "h"}),
        pd.DataFrame({"game_id": jg["game_id"], "t": jg["id_v"], "dia": jg["dia"], "lado": "a"}),
    ]).sort_values(["t", "dia", "game_id"])
    dias = pd.to_datetime(longo["dia"])
    longo["desc"] = dias.groupby(longo["t"]).diff().dt.days.fillna(7).clip(1, 7)
    h = longo[longo["lado"] == "h"].set_index("game_id")["desc"]
    a = longo[longo["lado"] == "a"].set_index("game_id")["desc"]
    return jg["game_id"].map(h).values, jg["game_id"].map(a).values


def calcular_features(jg):
    """Percorre os jogos em ordem de data. Devolve o DataFrame com features e o estado atual dos times."""
    elo, temp_do_time, forma = {}, {}, {}
    h_elo, a_elo, h_forma, a_forma, h_nf, a_nf = [], [], [], [], [], []

    for r in jg.itertuples():
        for t in (r.id_m, r.id_v):
            if temp_do_time.get(t) != r.season:  # nova temporada: Elo volta 25% para a média, forma zera
                elo[t] = ELO_MEDIA + ELO_REVERSAO * (elo.get(t, ELO_MEDIA) - ELO_MEDIA)
                forma[t] = deque(maxlen=JANELA_FORMA)
                temp_do_time[t] = r.season
        m, v = r.id_m, r.id_v
        h_elo.append(elo[m]); a_elo.append(elo[v])
        h_nf.append(len(forma[m])); a_nf.append(len(forma[v]))
        h_forma.append(np.mean(forma[m]) if forma[m] else 0.0)
        a_forma.append(np.mean(forma[v]) if forma[v] else 0.0)

        if r.jogado:
            margem = r.pts_m - r.pts_v
            dif = elo[m] + (0 if r.neutro else ELO_CASA) - elo[v]
            esperado = 1 / (1 + 10 ** (-dif / 400))
            venceu = 1.0 if margem > 0 else 0.0
            dif_vencedor = dif if margem > 0 else -dif
            mult = ((abs(margem) + 3) ** 0.8) / (7.5 + 0.006 * dif_vencedor)
            delta = ELO_K * mult * (venceu - esperado)
            elo[m] += delta; elo[v] -= delta
            forma[m].append(margem); forma[v].append(-margem)

    jg = jg.copy()
    jg["h_elo"], jg["a_elo"], jg["h_forma"], jg["a_forma"] = h_elo, a_elo, h_forma, a_forma
    jg["h_nf"], jg["a_nf"] = h_nf, a_nf  # quantos jogos entraram na forma (0 no começo da temporada)
    jg["h_desc"], jg["a_desc"] = _descanso(jg)
    jg["dif_elo"] = jg["h_elo"] - jg["a_elo"]
    jg["dif_forma"] = jg["h_forma"] - jg["a_forma"]
    jg["dif_desc"] = jg["h_desc"].clip(upper=4) - jg["a_desc"].clip(upper=4)
    jg["h_b2b"] = (jg["h_desc"] == 1).astype(int)
    jg["a_b2b"] = (jg["a_desc"] == 1).astype(int)
    jg["playoff"] = (jg["tipo"] != "REG").astype(int)
    jg["venceu_m"] = np.where(jg["jogado"], (jg["pts_m"] > jg["pts_v"]).astype(float), np.nan)
    return jg, elo


def _modelo():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def construir(jogos):
    """Features + backtest walk-forward + modelo final. Devolve um dicionário com tudo que o site/CLI usa."""
    jg, elo = calcular_features(jogos)
    feitos = jg[jg["jogado"] & (jg["season"] >= PRIMEIRA_TEMP_TREINO)]
    atual = int(jg["season"].max())

    # Backtest: cada temporada é prevista por um modelo treinado só com as anteriores
    partes = []
    for s in range(PRIMEIRA_TEMP_TESTE, atual + 1):
        tr, te = feitos[feitos["season"] < s], feitos[feitos["season"] == s]
        if te.empty:
            continue
        mdl = _modelo().fit(tr[FEATS], tr["venceu_m"])
        partes.append(te.assign(p=mdl.predict_proba(te[FEATS])[:, 1]))
    bt = pd.concat(partes)
    bt["ok"] = ((bt["p"] >= 0.5) == (bt["venceu_m"] == 1)).astype(int)

    ref = bt[(bt["season"] >= ANOS_REF[0]) & (bt["season"] <= ANOS_REF[1])]
    atu = bt[bt["season"] == atual]
    final = _modelo().fit(feitos[FEATS], feitos["venceu_m"])
    ids = {**dict(zip(jg["id_m"], jg["m"])), **dict(zip(jg["id_v"], jg["v"]))}
    return {
        "jogos": jg, "bt": bt, "modelo": final, "elo": elo, "atual": atual,
        "elo_sigla": {ids[i]: e for i, e in elo.items() if i in ids},
        "acc": float(ref["ok"].mean()), "acc_reg": float(ref[ref["tipo"] == "REG"]["ok"].mean()),
        "acc_mandante": float(ref["venceu_m"].mean()),
        "acc_atual": float(atu["ok"].mean()) if len(atu) else None, "n_atual": int(len(atu)),
        "n_ref": int(len(ref)),
    }


def prever_futuros(S, fut):
    """Chance de o mandante vencer em jogos que ainda não aconteceram (força dos times congelada no estado atual)."""
    if fut.empty:
        return fut.assign(p=[])
    fut = fut.copy()
    adj = _noticias()
    if adj:  # ajustes por notícia (lesões etc.), só nos dias em que valem
        fut["dif_elo"] = fut["dif_elo"] + [noticias.delta(adj, m, d) - noticias.delta(adj, v, d) for m, v, d in zip(fut["m"], fut["v"], fut["dia"])]
    return fut.assign(p=S["modelo"].predict_proba(fut[FEATS])[:, 1])


_NOT = {}


def _noticias():
    if "adj" not in _NOT:
        _NOT["adj"] = noticias.carregar("nba")
    return _NOT["adj"]


# ----------------------------------------------------------------------------
# Projeção de recorde
# ----------------------------------------------------------------------------
def dist_vitorias(ps):
    """Distribuição do nº de vitórias dado a chance de vitória em cada jogo restante (Poisson-binomial)."""
    d = np.array([1.0])
    for p in ps:
        d = np.append(d, 0.0) * (1 - p) + np.insert(d, 0, 0.0) * p
    return d


def projecao(S, sigla):
    jg, atual = S["jogos"], S["atual"]
    reg = jg[(jg["season"] == atual) & (jg["tipo"] == "REG") & ((jg["m"] == sigla) | (jg["v"] == sigla))]
    jog, resta = reg[reg["jogado"]], reg[~reg["jogado"]].sort_values("dt")
    v = int(((jog["m"] == sigla) & (jog["pts_m"] > jog["pts_v"])).sum() + ((jog["v"] == sigla) & (jog["pts_v"] > jog["pts_m"])).sum())
    d = int(len(jog) - v)
    # O calendário às vezes ainda não define todos os 82 jogos (os 2 ligados à NBA Cup entram depois).
    # Esses jogos sem data entram na conta com a chance média do time nos jogos já marcados.
    sem_data = max(0, JOGOS_TEMPORADA - len(reg))
    if resta.empty and not sem_data:
        return {"v": v, "d": d, "n_rest": 0, "n_sem_data": 0, "dist": [], "jogos": []}
    fut = prever_futuros(S, resta)
    fut = fut.assign(p_time=np.where(fut["m"] == sigla, fut["p"], 1 - fut["p"]))
    ps = list(fut["p_time"].values) + [float(fut["p_time"].mean()) if len(fut) else 0.5] * sem_data
    dist = dist_vitorias(ps)
    cum = np.cumsum(dist)
    return {
        "v": v, "d": d, "n_rest": len(ps), "n_sem_data": sem_data, "dist": dist, "fut": fut,
        "esperado": v + float((np.arange(len(dist)) * dist).sum()), "moda": int(np.argmax(dist)),
        "lo": int(np.searchsorted(cum, 0.10)), "hi": int(np.searchsorted(cum, 0.90)),
    }



# ----------------------------------------------------------------------------
# Simulação da temporada: classificação, play-in, playoffs e título
# ----------------------------------------------------------------------------
def _serie_melhor_de_7(pa_casa, pb_casa):
    """Chance de A vencer uma série melhor de 7 em que A tem o mando (jogos 1, 2, 5 e 7 na casa de A).
    pa_casa = chance de A vencer jogando em casa; pb_casa = chance de B vencer jogando em casa."""
    em_casa = [1, 1, 0, 0, 1, 0, 1]
    pa = [pa_casa if c else 1 - pb_casa for c in em_casa]
    memo = {}

    def f(i, a, b):
        if a == 4:
            return 1.0
        if b == 4:
            return 0.0
        if (i, a, b) not in memo:
            memo[(i, a, b)] = pa[i] * f(i + 1, a + 1, b) + (1 - pa[i]) * f(i + 1, a, b + 1)
        return memo[(i, a, b)]

    return f(0, 0, 0)


def simular(S, n=10000, semente=2026):
    """Joga a temporada n vezes com as chances do modelo (força dos times congelada no estado atual).
    Regras: 6 primeiros de cada conferência vão direto aos playoffs; 7º a 10º disputam o play-in;
    séries melhor de 7. Desempate de vitórias é sorteado. Devolve a chance de cada time em cada etapa."""
    rng = np.random.default_rng(semente)
    siglas = list(TIMES)
    ix = {s: i for i, s in enumerate(siglas)}
    nt = len(siglas)
    jg, atual = S["jogos"], S["atual"]
    reg = jg[(jg["season"] == atual) & (jg["tipo"] == "REG")]

    # vitórias já conquistadas + jogos restantes sorteados com a chance do modelo
    jog = reg[reg["jogado"]]
    vit = np.zeros(nt)
    for g in jog.itertuples():
        vit[ix[g.m if g.pts_m > g.pts_v else g.v]] += 1
    W = np.tile(vit, (n, 1))
    fut = prever_futuros(S, reg[~reg["jogado"]])
    mi, vi, pp = fut["m"].map(ix).values, fut["v"].map(ix).values, fut["p"].values

    # cada simulação sorteia um "desvio de força" por time (o Elo de hoje pode estar errado)
    coef = S["modelo"][1].coef_[0][FEATS.index("dif_elo")] / S["modelo"][0].scale_[FEATS.index("dif_elo")]
    frac = len(fut) / max(len(reg), 1)
    sigma = SIGMA_ELO_FIM + (SIGMA_ELO_INICIO - SIGMA_ELO_FIM) * np.sqrt(frac)
    Z = rng.normal(0, sigma, (n, nt))
    expit = lambda x: 1 / (1 + np.exp(-x))
    logit = lambda q: np.log(q / (1 - q))

    for k in range(len(fut)):
        casa = rng.random(n) < expit(logit(pp[k]) + coef * (Z[:, mi[k]] - Z[:, vi[k]]))
        W[:, mi[k]] += casa
        W[:, vi[k]] += ~casa
    # jogos ainda sem data no calendário: chance média do time
    for s in siglas:
        marcados = int(((reg["m"] == s) | (reg["v"] == s)).sum())
        falta = max(0, JOGOS_TEMPORADA - marcados)
        if falta:
            mine = np.where(fut["m"] == s, fut["p"], 1 - fut["p"]) if len(fut) else np.array([0.5])
            sel = (fut["m"] == s) | (fut["v"] == s) if len(fut) else np.array([False])
            pbar = float(mine[np.asarray(sel)].mean()) if np.asarray(sel).any() else 0.5
            W[:, ix[s]] += rng.binomial(falta, expit(logit(pbar) + coef * Z[:, ix[s]]))

    # chance de cada time vencer o outro em casa, num jogo de mata-mata (Elo atual; sem forma recente nem descanso)
    elo = S["elo_sigla"]
    linhas = [(a, b) for a in siglas for b in siglas if a != b]
    X = pd.DataFrame({"dif_elo": [elo[a] - elo[b] for a, b in linhas], "dif_forma": 0.0, "dif_desc": 0.0,
                      "h_b2b": 0, "a_b2b": 0, "playoff": 1})[FEATS]
    ph = np.zeros((nt, nt))
    for (a, b), p in zip(linhas, S["modelo"].predict_proba(X)[:, 1]):
        ph[ix[a], ix[b]] = p
    serie = np.zeros((nt, nt))
    for a in range(nt):
        for b in range(nt):
            if a != b:
                serie[a, b] = _serie_melhor_de_7(ph[a, b], ph[b, a])

    lph, lserie = logit(np.clip(ph, 1e-6, 1 - 1e-6)), logit(np.clip(serie, 1e-6, 1 - 1e-6))

    confs = [[ix[s] for s in siglas if TIMES[s][2] == c] for c in ("Leste", "Oeste")]
    etapas = ["dir", "playin", "pof", "r2", "r3", "fin", "tit"]
    cont = {e: np.zeros(nt) for e in etapas}
    desempate = rng.random((n, nt)) * 0.5
    sorteio = rng.random((n, 40))

    for s in range(n):
        w = W[s] + desempate[s]
        k = 0

        def serie_entre(a, b):
            nonlocal k
            if w[a] < w[b]:
                a, b = b, a  # mando de quadra: quem fez mais vitórias
            k += 1
            return a if sorteio[s, k - 1] < expit(lserie[a, b] + KAPPA_SERIE * coef * (Z[s, a] - Z[s, b])) else b

        def casa_vence(a, b):  # jogo único (play-in) em casa de a
            nonlocal k
            k += 1
            return sorteio[s, k - 1] < expit(lph[a, b] + coef * (Z[s, a] - Z[s, b]))

        campeoes = []
        for idx in confs:
            ordem = sorted(idx, key=lambda t: -w[t])
            cont["dir"][ordem[:6]] += 1
            cont["playin"][ordem[6:10]] += 1
            a, b, c, d = ordem[6:10]
            v78 = a if casa_vence(a, b) else b
            l78 = b if v78 == a else a
            v910 = c if casa_vence(c, d) else d
            oitavo = l78 if casa_vence(l78, v910) else v910
            seeds = ordem[:6] + [v78, oitavo]
            cont["pof"][seeds] += 1
            r1 = [serie_entre(seeds[0], seeds[7]), serie_entre(seeds[3], seeds[4]),
                  serie_entre(seeds[2], seeds[5]), serie_entre(seeds[1], seeds[6])]
            cont["r2"][r1] += 1
            r2 = [serie_entre(r1[0], r1[1]), serie_entre(r1[3], r1[2])]
            cont["r3"][r2] += 1
            cf = serie_entre(r2[0], r2[1])
            cont["fin"][cf] += 1
            campeoes.append(cf)
        cont["tit"][serie_entre(campeoes[0], campeoes[1])] += 1

    return {"n": n, "v": W.mean(axis=0), "siglas": siglas, **{e: cont[e] / n for e in etapas}}

# ----------------------------------------------------------------------------
# Terminal
# ----------------------------------------------------------------------------
def main(args):
    print("Carregando dados e treinando…")
    S = construir(carregar())
    a0, a1 = ANOS_REF
    print(f"\nAcurácia {rotulo_temporada(a0)} a {rotulo_temporada(a1)} ({S['n_ref']} jogos): {S['acc']:.1%}"
          f"  (se o time da casa sempre vencesse: {S['acc_mandante']:.1%})")
    if not args:
        print("\nExemplos:  python previsor_nba.py dia 2026-10-20   |   python previsor_nba.py time BOS")
    elif args[0] == "dia" and len(args) > 1:
        sub = S["jogos"][S["jogos"]["dia"] == args[1]]
        fut = prever_futuros(S, sub[~sub["jogado"]])
        bt = S["bt"].set_index("game_id")
        for g in sub.itertuples():
            p = float(fut.set_index("game_id").loc[g.game_id, "p"]) if not g.jogado else float(bt.loc[g.game_id, "p"]) if g.game_id in bt.index else None
            res = f"{int(g.pts_v)}-{int(g.pts_m)}" if g.jogado else "  -  "
            print(f"{g.v:>4} @ {g.m:<4} {res:>7}   casa {p:.0%}" if p is not None else f"{g.v:>4} @ {g.m:<4} {res:>7}")
        if sub.empty:
            print("Nenhum jogo nesse dia.")
    elif args[0] == "time" and len(args) > 1 and args[1].upper() in TIMES:
        sg = args[1].upper()
        p = projecao(S, sg)
        print(f"\n{TIMES[sg][0]} — temporada {rotulo_temporada(S['atual'])}: {p['v']}-{p['d']} até agora")
        if p["n_rest"]:
            print(f"Recorde mais provável: {p['v'] + p['moda']}-{p['d'] + p['n_rest'] - p['moda']}"
                  f" · vitórias esperadas {p['esperado']:.1f} · faixa de 80%: {p['v'] + p['lo']} a {p['v'] + p['hi']}")
    else:
        print("Uso: python previsor_nba.py [dia AAAA-MM-DD | time SIGLA]")
    print("\nAvisos:")
    for a in AVISOS:
        print(" -", a)


if __name__ == "__main__":
    main(sys.argv[1:])

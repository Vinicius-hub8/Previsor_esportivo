"""Ajustes por notícias (lesões, suspensões, descanso de astros...) que mudam a previsão de jogos futuros.

O modelo só enxerga resultados passados. Notícia ele não lê. Por isso o jeito honesto é um arquivo simples,
ajustes_noticias.csv, onde você (ou eu, a seu pedido) registra cada notícia como um ajuste de força (pontos de Elo)
para um time, numa janela de datas. O ajuste vale só para jogos dentro da janela e aparece no cartão do jogo com o
motivo e a fonte. Colunas:

    esporte   nfl | nba | futebol
    liga      (só futebol) premier | laliga | seriea | bundesliga | ligue1 | brasileirao
    time      NFL/NBA: sigla (KC, BOS...). Futebol: o nome como aparece no site (Man City, Flamengo...)
    delta_elo número; negativo enfraquece o time, positivo reforça (ex.: -40)
    motivo    texto curto (ex.: "Mahomes fora por lesão")
    fonte     link da notícia
    inicio    (opcional) primeiro dia em que vale, AAAA-MM-DD
    valido_ate último dia em que vale, AAAA-MM-DD (obrigatório: lesão não dura para sempre)

Ordem de grandeza (julgamento, NÃO testado no histórico): veja a tabela de referência no README. Na NFL, jogos que já têm linha de aposta não são ajustados (a linha já embute a notícia).
"""
import csv
import os
from datetime import date
from pathlib import Path

LIMITE = 150.0   # soma máxima de ajuste por time e jogo (pontos de Elo)
ARQUIVO = Path(os.environ.get("AJUSTES_NOTICIAS") or Path(__file__).resolve().parent / "ajustes_noticias.csv")


def _linhas(arquivo):
    if not Path(arquivo).exists():
        return []
    with open(arquivo, encoding="utf-8", newline="") as f:
        txt = [ln for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    return list(csv.DictReader(txt))


def carregar(esporte, liga="", hoje=None, arquivo=None):
    """Lista de ajustes válidos hoje (ou no futuro) para o esporte (e liga). Linhas inválidas são ignoradas com aviso."""
    hoje = (hoje or date.today()).isoformat()
    saida = []
    for i, r in enumerate(_linhas(arquivo or ARQUIVO), 1):
        try:
            if (r.get("esporte") or "").strip().lower() != esporte:
                continue
            if esporte == "futebol" and (r.get("liga") or "").strip().lower() != liga:
                continue
            ate = (r.get("valido_ate") or "").strip()
            date.fromisoformat(ate)
            ini = (r.get("inicio") or "").strip()
            if ini:
                date.fromisoformat(ini)
            item = {"time": r["time"].strip(), "delta": float(r["delta_elo"]), "motivo": (r.get("motivo") or "").strip(),
                    "fonte": (r.get("fonte") or "").strip(), "inicio": ini or "0000-00-00", "ate": ate}
        except Exception as e:
            print(f"::warning::ajustes_noticias.csv, linha {i} ignorada ({e!r})")
            continue
        if ate >= hoje:
            saida.append(item)
    return saida


def itens(adj, time, dia):
    """Ajustes que valem para esse time no dia (AAAA-MM-DD) do jogo."""
    return [a for a in adj if a["time"] == time and a["inicio"] <= dia <= a["ate"]]


def delta(adj, time, dia):
    if not adj:
        return 0.0
    s = sum(a["delta"] for a in itens(adj, time, dia))
    return max(-LIMITE, min(LIMITE, s))


def para_json(adj, times_dia):
    """times_dia = [(codigo_no_site, nome_no_modelo, dia), ...] -> lista [{t, d, m, f}] para o cartão do jogo."""
    out = []
    for cod, nome, dia in times_dia:
        for a in itens(adj, nome, dia):
            out.append({"t": cod, "d": a["delta"], "m": a["motivo"], "f": a["fonte"]})
    return out


def desconhecidos(adj, conhecidos):
    """Nomes de time no CSV que não existem no modelo (erro de digitação)."""
    return sorted({a["time"] for a in adj} - set(conhecidos))

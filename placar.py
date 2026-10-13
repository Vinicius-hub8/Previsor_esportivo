"""Placar previsto (NFL e NBA) e conversão de horário para Brasília.

Placar previsto: a chance de vitória vira uma margem esperada (margem = k * z, onde z é o ponto da curva normal que
corresponde à chance; k é ajustado no histórico), e o total de pontos sai do ritmo recente dos dois times.
É uma estimativa do placar mais típico, não do placar exato (quase nunca se acerta o placar exato)."""
from statistics import NormalDist

import numpy as np
import pandas as pd

TZ_BR = "America/Sao_Paulo"
_inv = NormalDist().inv_cdf


def z(p):
    return _inv(min(max(float(p), 0.02), 0.98))


def inclinacao(ps, margens, padrao=12.0):
    """k que melhor liga z(p) à margem real do mandante (mínimos quadrados sem intercepto)."""
    zs = np.array([z(p) for p in ps])
    m = np.array(margens, dtype=float)
    ok = np.isfinite(zs) & np.isfinite(m)
    if ok.sum() < 50:
        return padrao
    return float((zs[ok] * m[ok]).sum() / (zs[ok] ** 2).sum())


def placar_previsto(p, total, k):
    """[pontos do visitante, pontos do mandante]. O palpite (quem tem p >= 50%) nunca termina empatado."""
    margem = k * z(p)
    casa, fora = int(round((total + margem) / 2)), int(round((total - margem) / 2))
    if casa == fora:
        casa, fora = (casa + 1, fora) if p >= 0.5 else (casa, fora + 1)
    return [fora, casa]


def erro_medio(ps, margens, k):
    prev = np.array([k * z(p) for p in ps])
    return float(np.abs(prev - np.array(margens, dtype=float)).mean())


def para_brasilia(dia, hora, tz_origem="America/New_York"):
    """('2026-10-18', '13:00') no fuso de origem -> (data BRT, hora BRT). Sem hora, devolve (dia, None)."""
    if hora is None or (isinstance(hora, float) and np.isnan(hora)) or not hora:
        return dia, None
    t = pd.Timestamp(f"{dia} {hora}").tz_localize(tz_origem, ambiguous="NaT", nonexistent="shift_forward")
    if pd.isna(t):
        return dia, None
    b = t.tz_convert(TZ_BR)
    return b.strftime("%Y-%m-%d"), b.strftime("%H:%M")

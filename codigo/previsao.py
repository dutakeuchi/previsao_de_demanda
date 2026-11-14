"""Camada 4: métodos de previsão (Ballou, cap. 8), backtest e projeção de 6 meses.

Fluxo para cada modal (série semanal de fretes):
1. Testa os métodos candidatos prevendo UMA semana à frente nas últimas N semanas.
2. Escolhe o de menor MAPE (o erro é levemente otimista: a escolha usa as mesmas semanas).
3. Projeta as próximas semanas: nível pelo método escolhido sobre a série
   dessazonalizada, multiplicado pelo índice sazonal do mês (decomposição T x S).
4. Faixa de ~95%: previsão ± z · RMSE · raiz(1 + (h-1)·a²), com a = constante efetiva.
   É uma aproximação do trabalho, não uma fórmula do livro.
O total é a soma das previsões dos modais.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import SEMANAS_PREVISAO, SEMANAS_TESTE, Z_95

CANDIDATOS = [
    {"id": "ingenuo", "tipo": "ingenuo", "nome": "Ingênuo (repete a semana anterior)"},
    {"id": "mm4", "tipo": "mm", "k": 4, "nome": "Média móvel de 4 semanas"},
    {"id": "mm8", "tipo": "mm", "k": 8, "nome": "Média móvel de 8 semanas"},
    {"id": "ses01", "tipo": "ses", "alfa": 0.1, "nome": "Ponderação exponencial simples (α = 0,1)"},
    {"id": "ses02", "tipo": "ses", "alfa": 0.2, "nome": "Ponderação exponencial simples (α = 0,2)"},
    {"id": "ses03", "tipo": "ses", "alfa": 0.3, "nome": "Ponderação exponencial simples (α = 0,3)"},
    {"id": "ses05", "tipo": "ses", "alfa": 0.5, "nome": "Ponderação exponencial simples (α = 0,5)"},
    {"id": "holt1", "tipo": "holt", "alfa": 0.3, "beta": 0.1, "nome": "Ponderação exponencial com tendência (α = 0,3; β = 0,1)"},
    {"id": "holt2", "tipo": "holt", "alfa": 0.5, "beta": 0.1, "nome": "Ponderação exponencial com tendência (α = 0,5; β = 0,1)"},
    {"id": "holt3", "tipo": "holt", "alfa": 0.3, "beta": 0.3, "nome": "Ponderação exponencial com tendência (α = 0,3; β = 0,3)"},
]


# ------------------------------------------------------------------- métodos --
def _holt(y, alfa, beta):
    nivel, tend = y[0], y[1] - y[0]
    f = [y[0]]
    for i in range(1, len(y)):
        f.append(nivel + tend)
        novo = alfa * y[i] + (1 - alfa) * (nivel + tend)
        tend = beta * (novo - nivel) + (1 - beta) * tend
        nivel = novo
    return np.array(f), nivel, tend


def ajustar(y: np.ndarray, c: dict) -> np.ndarray:
    """Previsão de uma semana à frente: f[t] usa só dados até t-1."""
    t = c["tipo"]
    if t == "ingenuo":
        return np.r_[np.nan, y[:-1]]
    if t == "mm":
        k = c["k"]
        return np.array([np.nan] * k + [y[i - k:i].mean() for i in range(k, len(y))])
    if t == "ses":
        a = c["alfa"]
        f = [y[0]]
        for i in range(1, len(y)):
            f.append(a * y[i - 1] + (1 - a) * f[-1])
        return np.array(f)
    if t == "holt":
        return _holt(y, c["alfa"], c["beta"])[0]
    raise ValueError(t)


def nivel_futuro(y: np.ndarray, c: dict, h: int) -> np.ndarray:
    """Previsões de 1 a h semanas à frente, a partir de toda a série."""
    t = c["tipo"]
    if t == "ingenuo":
        return np.full(h, y[-1])
    if t == "mm":
        return np.full(h, y[-c["k"]:].mean())
    if t == "ses":
        f = ajustar(y, c)
        return np.full(h, c["alfa"] * y[-1] + (1 - c["alfa"]) * f[-1])
    if t == "holt":
        _, nivel, tend = _holt(y, c["alfa"], c["beta"])
        return nivel + np.arange(1, h + 1) * tend
    raise ValueError(t)


def alfa_efetivo(c: dict) -> float:
    if c["tipo"] in ("ses", "holt"):
        return c["alfa"]
    if c["tipo"] == "mm":
        return 2 / (c["k"] + 1)
    return 1.0


# ------------------------------------------------------------------ métricas --
def metricas(real: np.ndarray, prev: np.ndarray) -> dict:
    ok = ~np.isnan(prev)
    a, f = real[ok], prev[ok]
    e = a - f
    mad = float(np.abs(e).mean())
    return {
        "MAD": round(mad, 2),
        "MAPE": round(float((np.abs(e) / a).mean() * 100), 2),
        "vies": round(float(e.mean()), 2),
        "sinalRastreamento": round(float(e.sum() / mad), 2) if mad else 0.0,
        "RMSE": round(float(np.sqrt((e ** 2).mean())), 2),
        "erroPadrao": round(float(np.sqrt((e ** 2).sum() / max(len(e) - 1, 1))), 2),
        "pontos": int(len(e)),
    }


def comparar(y: np.ndarray, janela: int) -> list[dict]:
    linhas = []
    for c in CANDIDATOS:
        f = ajustar(y, c)
        m = metricas(y[-janela:], f[-janela:])
        linhas.append({"id": c["id"], "nome": c["nome"], **m})
    return sorted(linhas, key=lambda r: r["MAPE"])


# ------------------------------------------------------- projeção sazonal -----
def _mes_da_semana(inicio: pd.Timestamp) -> int:
    """Mês de uma semana = mês da quinta-feira (evita semanas partidas)."""
    return (inicio + pd.Timedelta(days=3)).month


def projetar_modal(semanas: pd.DatetimeIndex, y: np.ndarray, idx_mes: dict,
                   mensal_real: pd.DataFrame) -> dict:
    """Backtest, escolha do método e projeção de SEMANAS_PREVISAO semanas."""
    n_teste = SEMANAS_TESTE
    comp = comparar(y, n_teste)
    escolhido = next(c for c in CANDIDATOS if c["id"] == comp[0]["id"])

    f_fit = ajustar(y, escolhido)
    validacao = {
        "semanas": [d.strftime("%Y-%m-%d") for d in semanas[-n_teste:]],
        "real": [round(float(v), 2) for v in y[-n_teste:]],
        "previsto": [round(float(v), 2) for v in f_fit[-n_teste:]],
    }
    met = metricas(y[-n_teste:], f_fit[-n_teste:])

    # dessazonaliza, projeta o nível e volta a aplicar a sazonalidade do mês
    s_obs = np.array([idx_mes[_mes_da_semana(d)] for d in semanas])
    nivel = nivel_futuro(y / s_obs, escolhido, SEMANAS_PREVISAO)
    futuras = pd.DatetimeIndex([semanas[-1] + pd.Timedelta(weeks=i) for i in range(1, SEMANAS_PREVISAO + 1)])
    s_fut = np.array([idx_mes[_mes_da_semana(d)] for d in futuras])
    prev = nivel * s_fut

    a = alfa_efetivo(escolhido)
    h = np.arange(1, SEMANAS_PREVISAO + 1)
    sd = met["RMSE"] * np.sqrt(1 + (h - 1) * a ** 2)

    return {
        "escolhido": escolhido,
        "comparacao": comp,
        "metricas": met,
        "validacao": validacao,
        "futuras": futuras,
        "prev": prev,
        "sd": sd,
        "nivel": nivel,
        "s_fut": s_fut,
        "fit": f_fit,
    }


def _mensal(futuras, nivel, idx_mes, mensal_real: pd.DataFrame) -> list[dict]:
    """Projeção mensal = nível semanal/7 × dias do mês × índice sazonal do mês."""
    df = pd.DataFrame({"semana": futuras, "nivel": nivel})
    df["mes"] = [(d + pd.Timedelta(days=3)).to_period("M") for d in futuras]
    linhas = []
    for per, g in df.groupby("mes"):
        previsto = g["nivel"].mean() / 7 * per.days_in_month * idx_mes[per.month]
        ant = per - 12
        real_ant = float(mensal_real.loc[ant, "fretes"]) if ant in mensal_real.index else None
        linhas.append({
            "mes": str(per),
            "previsto": round(float(previsto), 0),
            "anoAnterior": real_ant,
            "variacao": round((previsto / real_ant - 1) * 100, 2) if real_ant else None,
        })
    return linhas


def gerar_previsoes(df, series_mod) -> dict:
    """Roda tudo para cada modal e soma para o total.

    `series_mod`: dict modal -> (DataFrame semanal, DataFrame mensal, índice sazonal por mês).
    """
    modais = list(series_mod)
    res = {}
    brutos = {}
    for m in modais:
        sem, mes, idx_mes = series_mod[m]
        y = sem["fretes"].to_numpy(dtype=float)
        r = projetar_modal(sem.index, y, idx_mes, mes)
        brutos[m] = (r, mes, idx_mes)

    def pacote_modal(m):
        r, mes, idx_mes = brutos[m]
        z = Z_95
        return {
            "metodo": {"id": r["escolhido"]["id"], "nome": r["escolhido"]["nome"],
                       "tipo": r["escolhido"]["tipo"], "alfa": r["escolhido"].get("alfa"),
                       "beta": r["escolhido"].get("beta"), "k": r["escolhido"].get("k")},
            "comparacao": r["comparacao"],
            "metricas": r["metricas"],
            "validacao": r["validacao"],
            "semanal": {
                "semanas": [d.strftime("%Y-%m-%d") for d in r["futuras"]],
                "previsto": [round(float(v), 1) for v in r["prev"]],
                "inferior": [round(float(max(v - z * s, 0)), 1) for v, s in zip(r["prev"], r["sd"])],
                "superior": [round(float(v + z * s), 1) for v, s in zip(r["prev"], r["sd"])],
            },
            "mensal": _mensal(r["futuras"], r["nivel"], idx_mes, mes),
        }

    for m in modais:
        res[m] = pacote_modal(m)

    # Total = soma dos modais (previsão, faixa em quadratura, validação e mensal)
    z = Z_95
    prev_t = sum(brutos[m][0]["prev"] for m in modais)
    sd_t = np.sqrt(sum(brutos[m][0]["sd"] ** 2 for m in modais))
    val_real = sum(np.array(res[m]["validacao"]["real"]) for m in modais)
    val_prev = sum(np.array(res[m]["validacao"]["previsto"]) for m in modais)
    futuras = brutos[modais[0]][0]["futuras"]
    mensal_t = []
    for i, linha in enumerate(res[modais[0]]["mensal"]):
        prev_m = sum(res[m]["mensal"][i]["previsto"] for m in modais)
        ant = [res[m]["mensal"][i]["anoAnterior"] for m in modais]
        ant_t = sum(ant) if all(a is not None for a in ant) else None
        mensal_t.append({"mes": linha["mes"], "previsto": prev_m, "anoAnterior": ant_t,
                         "variacao": round((prev_m / ant_t - 1) * 100, 2) if ant_t else None})
    res["Total"] = {
        "metodo": {"id": "soma", "nome": "Soma das previsões dos modais", "tipo": "soma"},
        "comparacao": None,
        "metricas": metricas(val_real, val_prev),
        "validacao": {"semanas": res[modais[0]]["validacao"]["semanas"],
                      "real": [round(float(v), 2) for v in val_real],
                      "previsto": [round(float(v), 2) for v in val_prev]},
        "semanal": {
            "semanas": [d.strftime("%Y-%m-%d") for d in futuras],
            "previsto": [round(float(v), 1) for v in prev_t],
            "inferior": [round(float(max(v - z * s, 0)), 1) for v, s in zip(prev_t, sd_t)],
            "superior": [round(float(v + z * s), 1) for v, s in zip(prev_t, sd_t)],
        },
        "mensal": mensal_t,
    }
    return res


# -------------------------------------------------- exemplos para a aba de fórmulas
def exemplo_ses(y: np.ndarray, semanas, alfa: float = 0.2, passos: int = 4) -> dict:
    c = {"tipo": "ses", "alfa": alfa}
    f = ajustar(y, c)
    prox = float(alfa * y[-1] + (1 - alfa) * f[-1])
    linhas = []
    n = len(y)
    for t in range(n - passos, n):
        f_next = f[t + 1] if t + 1 < n else prox
        linhas.append({"semana": semanas[t].strftime("%Y-%m-%d"), "real": float(y[t]),
                       "previsaoAnterior": round(float(f[t]), 1),
                       "novaPrevisao": round(float(f_next), 1)})
    return {"alfa": alfa, "linhas": linhas}


def exemplo_erros(validacao: dict, n: int = 4) -> dict:
    real = np.array(validacao["real"][-n:])
    prev = np.array(validacao["previsto"][-n:])
    e = real - prev
    mad = float(np.abs(e).mean())
    return {
        "semanas": validacao["semanas"][-n:],
        "real": [round(float(v), 1) for v in real],
        "previsto": [round(float(v), 1) for v in prev],
        "erro": [round(float(v), 1) for v in e],
        "MAD": round(mad, 1),
        "MAPE": round(float((np.abs(e) / real).mean() * 100), 2),
        "sinal": round(float(e.sum() / mad), 2) if mad else 0.0,
    }

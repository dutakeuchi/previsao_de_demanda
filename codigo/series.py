"""Camadas 2 e 3: séries agregadas e análises descritivas.

A série DIÁRIA é a fonte única. Semanas e meses são somas dela, o que garante
que todos os números fechem entre si (e com o total da planilha).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import TOP_N

MEDIDAS_SOMA = ["fretes", "volumes", "pesoTaxado", "pesoReal"]


def _arredonda(valores, casas=2):
    return [None if pd.isna(v) else round(float(v), casas) for v in valores]


def recortes(df: pd.DataFrame) -> list[str]:
    """Total primeiro; depois os modais, do mais para o menos frequente."""
    modais = df["Modal do frete"].value_counts().index.tolist()
    return ["Total"] + modais


def _filtra(df: pd.DataFrame, recorte: str) -> pd.DataFrame:
    return df if recorte == "Total" else df[df["Modal do frete"] == recorte]


def diaria_df(df: pd.DataFrame, recorte: str) -> pd.DataFrame:
    sub = _filtra(df, recorte)
    dias = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    g = sub.groupby("data").agg(
        fretes=("Volumes", "size"),
        volumes=("Volumes", "sum"),
        pesoTaxado=("Peso Taxado", "sum"),
        pesoReal=("Peso Real", "sum"),
    )
    return g.reindex(dias, fill_value=0)


def serie_diaria(df: pd.DataFrame) -> dict:
    out = {"datas": [], "dados": {}}
    for rec in recortes(df):
        g = diaria_df(df, rec)
        if not out["datas"]:
            out["datas"] = [d.strftime("%Y-%m-%d") for d in g.index]
        out["dados"][rec] = {
            "fretes": [int(v) for v in g["fretes"]],
            "volumes": [int(v) for v in g["volumes"]],
            "pesoTaxado": _arredonda(g["pesoTaxado"]),
            "pesoReal": _arredonda(g["pesoReal"]),
        }
    return out


def agregar(g: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Soma a série diária por semana (segunda a domingo) ou mês, só períodos completos."""
    ini, fim = g.index.min(), g.index.max()
    if freq == "semana":
        chave = g.index - pd.to_timedelta(g.index.dayofweek, unit="D")
        a = g.groupby(chave).sum()
        a.index.name = "inicio"
        completo = (a.index >= ini) & (a.index + pd.Timedelta(days=6) <= fim)
        a = a[completo]
    elif freq == "mes":
        a = g.groupby(g.index.to_period("M")).sum()
        a.index.name = "inicio"
        completo = [(p.start_time >= ini) and (p.end_time.normalize() <= fim) for p in a.index]
        a = a[np.array(completo)]
        a["dias"] = [p.days_in_month for p in a.index]
        a["fretesPorDia"] = a["fretes"] / a["dias"]
    else:
        raise ValueError(freq)
    a = a.copy()
    a["pesoMedioTaxado"] = np.where(a["fretes"] > 0, a["pesoTaxado"] / a["fretes"].where(a["fretes"] > 0), np.nan)
    a["pesoMedioReal"] = np.where(a["fretes"] > 0, a["pesoReal"] / a["fretes"].where(a["fretes"] > 0), np.nan)
    return a


def _para_json(a: pd.DataFrame, freq: str) -> dict:
    if freq == "semana":
        rot = [d.strftime("%Y-%m-%d") for d in a.index]
    else:
        rot = [str(p) for p in a.index]
    out = {"periodos": rot}
    for col in a.columns:
        casas = 0 if col in ("fretes", "volumes", "dias") else 2
        out[col] = _arredonda(a[col], casas)
    return out


def series_agregadas(df: pd.DataFrame) -> dict:
    sem, mes = {}, {}
    for rec in recortes(df):
        g = diaria_df(df, rec)
        sem[rec] = _para_json(agregar(g, "semana"), "semana")
        mes[rec] = _para_json(agregar(g, "mes"), "mes")
    return {"semanal": sem, "mensal": mes}


# --------------------------------------------------------------- sazonalidade --
def indice_sazonal(df: pd.DataFrame, rec: str) -> dict:
    """Índice sazonal mensal sobre fretes por dia (multiplicativo, Eq. 8-15 simplificada).

    Usa os 12 últimos meses completos. Índice = fretes/dia do mês ÷ média dos 12 meses.
    Com um único ciclo, ele mistura sazonalidade e ruído: é estimativa preliminar.
    """
    m = agregar(diaria_df(df, rec), "mes")
    ciclo = m.tail(12)
    media = ciclo["fretesPorDia"].mean()
    idx = ciclo["fretesPorDia"] / media
    return {
        "meses": [str(p) for p in ciclo.index],
        "fretesPorDia": _arredonda(ciclo["fretesPorDia"], 2),
        "indice": _arredonda(idx, 4),
        "mediaFretesPorDia": round(float(media), 2),
        "porNumeroDoMes": {int(p.month): float(v) for p, v in zip(ciclo.index, idx)},
    }


def perfil_dia_da_semana(df: pd.DataFrame, rec: str) -> dict:
    sub = _filtra(df, rec)
    cont = sub.groupby("dow").size().reindex(range(7), fill_value=0)
    return {
        "dias": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"],
        "fretes": [int(v) for v in cont],
        "percentual": _arredonda(cont / cont.sum() * 100, 2),
    }


def variacao_anual(df: pd.DataFrame, rec: str) -> dict | None:
    """Último mês completo contra o mesmo mês do ano anterior (se existir)."""
    m = agregar(diaria_df(df, rec), "mes")
    ultimo = m.index[-1]
    anterior = ultimo - 12
    if anterior not in m.index:
        return None

    def par(col):
        ant, atual = float(m.loc[anterior, col]), float(m.loc[ultimo, col])
        return {"anterior": round(ant, 2), "atual": round(atual, 2),
                "variacao": round((atual / ant - 1) * 100, 2) if ant else None}

    return {
        "mesAtual": str(ultimo),
        "mesAnterior": str(anterior),
        "fretes": par("fretes"),
        "fretesPorDia": par("fretesPorDia"),
        "pesoTaxado": par("pesoTaxado"),
        "pesoMedioTaxado": par("pesoMedioTaxado"),
        "pesoMedioReal": par("pesoMedioReal"),
    }


def variabilidade_semanal(df: pd.DataFrame, rec: str) -> dict:
    """Coeficiente de variação das semanas completas (para enquadrar a demanda)."""
    s = agregar(diaria_df(df, rec), "semana")["fretes"].astype(float)
    cv = float(s.std(ddof=1) / s.mean())
    return {"semanas": int(len(s)), "media": round(float(s.mean()), 1),
            "desvioPadrao": round(float(s.std(ddof=1)), 1), "cv": round(cv * 100, 2)}


# --------------------------------------------------------------- distribuição --
def distribuicao(df: pd.DataFrame, rec: str) -> dict:
    sub = _filtra(df, rec)
    total = len(sub)

    def top(chaves, nome):
        g = sub.groupby(chaves).size().sort_values(ascending=False).head(TOP_N)
        return [{"nome": nome(i), "fretes": int(v), "percentual": round(v / total * 100, 2)}
                for i, v in g.items()]

    return {
        "total": int(total),
        "destinos": top(["Cidade destino", "UF Destino"], lambda i: f"{i[0]}/{i[1]}"),
        "origens": top(["Cidade origem", "UF Origem"], lambda i: f"{i[0]}/{i[1]}"),
        "rotas": top(["UF Origem", "UF Destino"], lambda i: f"{i[0]} para {i[1]}"),
        "cidadesDestinoDistintas": int(sub["Cidade destino"].nunique()),
        "cidadesOrigemDistintas": int(sub["Cidade origem"].nunique()),
        "concentracaoPeso1pct": round(float(
            sub["Peso Taxado"].sort_values(ascending=False).head(max(1, int(total * 0.01))).sum()
            / sub["Peso Taxado"].sum() * 100), 2),
    }

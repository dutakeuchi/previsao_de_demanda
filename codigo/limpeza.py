"""Camada 1: leitura da planilha, conferência e colunas derivadas."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import COLUNAS


def carregar(caminho: Path) -> tuple[pd.DataFrame, dict]:
    """Lê a planilha e devolve (tabela limpa, relatório do que foi tratado).

    Regras:
    - linhas sem data de frete ou com medidas ausentes são descartadas (e contadas);
    - linhas totalmente idênticas são MANTIDAS (o grupo as considera fretes distintos);
    - nada é removido por "valor extremo".
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Não encontrei a planilha: {caminho}")

    bruto = pd.read_excel(caminho, sheet_name=0)
    faltam = [c for c in COLUNAS if c not in bruto.columns]
    if faltam:
        raise ValueError("Colunas ausentes na planilha: " + ", ".join(faltam))

    df = bruto[COLUNAS].copy()
    df["Data Frete"] = pd.to_datetime(df["Data Frete"], errors="coerce")
    df["Data Entrega"] = pd.to_datetime(df["Data Entrega"], errors="coerce")
    for c in ("Volumes", "Peso Real", "Peso Taxado"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Modal do frete"] = df["Modal do frete"].astype(str).str.strip()

    rel: dict = {"linhasLidas": int(len(bruto))}

    sem_data = df["Data Frete"].isna()
    rel["semDataFrete"] = int(sem_data.sum())
    df = df[~sem_data]

    sem_medida = df[["Volumes", "Peso Real", "Peso Taxado"]].isna().any(axis=1)
    rel["medidasAusentes"] = int(sem_medida.sum())
    df = df[~sem_medida].copy()

    rel["linhasUsadas"] = int(len(df))

    # Fretes idênticos em todas as colunas: mantidos, apenas informados.
    repetidas = df.duplicated(keep="first")
    rel["linhasIdenticasMantidas"] = int(repetidas.sum())
    rel["paresIdenticosMantidos"] = int(
        df[df.duplicated(keep=False)].groupby(COLUNAS, dropna=False).ngroups
    )

    fim = df["Data Frete"].max()
    rel["entregasAposFimDoPeriodo"] = int((df["Data Entrega"] > fim).sum())
    rel["entregaAntesDoFrete"] = int((df["Data Entrega"] < df["Data Frete"]).sum())
    rel["pesoTaxadoMenorQueReal"] = int((df["Peso Taxado"] < df["Peso Real"] - 1e-9).sum())

    prazo = (df["Data Entrega"] - df["Data Frete"]).dt.days
    rel["prazoMedianoDias"] = {
        m: float(prazo[df["Modal do frete"] == m].median())
        for m in df["Modal do frete"].unique()
    }

    # Colunas derivadas
    df["data"] = df["Data Frete"].dt.normalize()
    df["semana"] = df["data"] - pd.to_timedelta(df["data"].dt.dayofweek, unit="D")
    df["mes"] = df["data"].dt.strftime("%Y-%m")
    df["dow"] = df["data"].dt.dayofweek
    return df, rel

"""Mapa de rotas: coordenadas das cidades, contorno dos estados e rotas mais usadas.

Dados de apoio (na mesma pasta):
- estados_br.json   contorno dos estados do Brasil (Natural Earth, domínio público)
- municipios_br.csv coordenadas dos municípios (base do IBGE)
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent
ARQ_ESTADOS = PASTA / "dados_mapa" / "estados_br.json"
ARQ_MUNICIPIOS = PASTA / "dados_mapa" / "municipios_br.csv"

# projeção simples (equiretangular com correção de latitude média) para o desenho
ESCALA = 15.0
COS_LAT = 0.9703          # cos(14 graus)
LON0, LAT0 = -76.0, 6.0
LARGURA, ALTURA = 680, 640
N_ROTAS = 30              # rotas guardadas por recorte (a página mostra 10, 20 ou 30)


def projetar(lon: float, lat: float) -> tuple[float, float]:
    return round((lon - LON0) * COS_LAT * ESCALA, 1), round((LAT0 - lat) * ESCALA, 1)


def _norm(s) -> str:
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _carregar():
    estados = json.loads(ARQ_ESTADOS.read_text(encoding="utf-8"))
    mun = pd.read_csv(ARQ_MUNICIPIOS)
    mun["k"] = mun["nome"].map(_norm) + "|" + mun["uf"]
    coords = {k: (lat, lon) for k, lat, lon in zip(mun["k"], mun["latitude"], mun["longitude"])}
    capitais = {r.uf: (r.latitude, r.longitude) for r in mun[mun["capital"] == 1].itertuples()}
    return estados, coords, capitais


def desenho_estados() -> dict:
    """Caminhos SVG de cada estado, já projetados."""
    estados, _, _ = _carregar()
    saida = {}
    for uf, e in estados.items():
        partes = []
        for anel in e["aneis"]:
            pts = [projetar(lon, lat) for lon, lat in anel]
            partes.append("M" + "L".join(f"{x} {y}" for x, y in pts) + "Z")
        saida[uf] = {"nome": e["nome"], "d": "".join(partes)}
    return {"largura": LARGURA, "altura": ALTURA, "estados": saida}


def rotas_mais_usadas(df: pd.DataFrame, recorte_modal: str | None, n: int = N_ROTAS) -> dict:
    """Rotas mais frequentes por cidade e por estado (capital como ponto do estado)."""
    estados, coords, capitais = _carregar()
    sub = df if recorte_modal in (None, "Total") else df[df["Modal do frete"] == recorte_modal]
    total = int(len(sub))
    nome_uf = {uf: e["nome"] for uf, e in estados.items()}

    def no(nome, x_y, extra=None):
        d = {"nome": nome, "x": x_y[0], "y": x_y[1]}
        if extra:
            d.update(extra)
        return d

    # ---- por cidade
    ch = ["Cidade origem", "UF Origem", "Cidade destino", "UF Destino"]
    g = sub.groupby(ch).size().reset_index(name="fretes")
    g = g[~((g["Cidade origem"] == g["Cidade destino"]) & (g["UF Origem"] == g["UF Destino"]))]
    distintas_cidade = int(len(g))
    g = g.sort_values("fretes", ascending=False)
    cidades, sem_coord = [], 0
    for r in g.itertuples(index=False):
        ko = _norm(r[0]) + "|" + r[1]
        kd = _norm(r[2]) + "|" + r[3]
        if ko not in coords or kd not in coords:
            sem_coord += int(r.fretes) if len(cidades) < n else 0
            continue
        cidades.append({
            "o": no(f"{r[0]}/{r[1]}", projetar(coords[ko][1], coords[ko][0])),
            "d": no(f"{r[2]}/{r[3]}", projetar(coords[kd][1], coords[kd][0])),
            "fretes": int(r.fretes),
        })
        if len(cidades) == n:
            break

    # ---- por estado
    h = sub.groupby(["UF Origem", "UF Destino"]).size().reset_index(name="fretes")
    h = h[h["UF Origem"] != h["UF Destino"]]
    mesmo_estado = int(total - h["fretes"].sum())
    distintas_uf = int(len(h))
    h = h.sort_values("fretes", ascending=False).head(n)
    ufs = []
    for r in h.itertuples(index=False):
        if r[0] not in capitais or r[1] not in capitais:
            continue
        po, pd_ = capitais[r[0]], capitais[r[1]]
        ufs.append({
            "o": no(f"{nome_uf.get(r[0], r[0])} ({r[0]})", projetar(po[1], po[0])),
            "d": no(f"{nome_uf.get(r[1], r[1])} ({r[1]})", projetar(pd_[1], pd_[0])),
            "fretes": int(r.fretes),
        })

    return {
        "total": total,
        "cidades": cidades, "rotasDistintasCidades": distintas_cidade,
        "estados": ufs, "rotasDistintasEstados": distintas_uf,
        "fretesMesmoEstado": mesmo_estado,
    }


def montar(df: pd.DataFrame, recortes: list[str]) -> dict:
    return {"desenho": desenho_estados(),
            "rotas": {r: rotas_mais_usadas(df, r) for r in recortes},
            "creditos": "Contorno dos estados: Natural Earth (domínio público). Coordenadas das cidades: IBGE."}

"""Gera o site (index.html) e o arquivo de auditoria (dados.json) a partir da planilha.

Uso:
    python gerar_site.py                      # usa "Base Movimento.xlsx" da pasta
    python gerar_site.py outra_planilha.xlsx

Dependências: pandas, numpy e openpyxl.
"""
from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import config as cfg
import limpeza
import mapa
import previsao
import series


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, pd.Period):
        return str(o)
    raise TypeError(f"Tipo não serializável: {type(o)}")


def _logo_data_uri():
    if cfg.LOGO and Path(cfg.LOGO).exists():
        p = Path(cfg.LOGO)
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml", ".webp": "image/webp"}.get(p.suffix.lower(), "image/png")
        return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return None


def montar(df: pd.DataFrame, rel: dict, arquivo: str) -> dict:
    recs = series.recortes(df)
    modais = [r for r in recs if r != "Total"]

    diaria = series.serie_diaria(df)
    agreg = series.series_agregadas(df)

    sazonal = {r: series.indice_sazonal(df, r) for r in recs}
    dia_sem = {r: series.perfil_dia_da_semana(df, r) for r in recs}
    var_anual = {r: series.variacao_anual(df, r) for r in recs}
    variab = {r: series.variabilidade_semanal(df, r) for r in recs}
    distrib = {r: series.distribuicao(df, r) for r in recs}

    # insumos da previsão (um conjunto por modal)
    series_mod = {}
    for m in modais:
        g = series.diaria_df(df, m)
        series_mod[m] = (series.agregar(g, "semana"), series.agregar(g, "mes"),
                         sazonal[m]["porNumeroDoMes"])
    prev = previsao.gerar_previsoes(df, series_mod)

    # exemplos reais para a aba de fórmulas (modal principal)
    principal = modais[0]
    sem_p = series_mod[principal][0]
    y_p = sem_p["fretes"].to_numpy(dtype=float)
    mes_p = series_mod[principal][1]
    ultimo_mes = mes_p.index[-1]
    mes_ex = [p for p in mes_p.index if p.month == 12]
    mes_ex = mes_ex[-1] if mes_ex else mes_p.index[len(mes_p) // 2]
    exemplos = {
        "modal": principal,
        "ses": previsao.exemplo_ses(y_p, sem_p.index, alfa=0.2),
        "erros": previsao.exemplo_erros(prev[principal]["validacao"]),
        "indice": {
            "mes": str(mes_ex),
            "fretesPorDia": round(float(mes_p.loc[mes_ex, "fretesPorDia"]), 2),
            "media": sazonal[principal]["mediaFretesPorDia"],
            "indice": round(float(mes_p.loc[mes_ex, "fretesPorDia"] / sazonal[principal]["mediaFretesPorDia"]), 4),
        },
        "pesoMedio": {
            "mes": str(ultimo_mes),
            "pesoTaxado": round(float(mes_p.loc[ultimo_mes, "pesoTaxado"]), 2),
            "fretes": int(mes_p.loc[ultimo_mes, "fretes"]),
            "media": round(float(mes_p.loc[ultimo_mes, "pesoMedioTaxado"]), 2),
        },
        "faixa": {
            "semana": prev[principal]["semanal"]["semanas"][0],
            "previsto": prev[principal]["semanal"]["previsto"][0],
            "inferior": prev[principal]["semanal"]["inferior"][0],
            "superior": prev[principal]["semanal"]["superior"][0],
            "rmse": prev[principal]["metricas"]["RMSE"],
        },
    }

    n_mod = df["Modal do frete"].value_counts()
    resumo = {
        "fretes": int(len(df)),
        "porModal": {m: int(n_mod[m]) for m in modais},
        "inicio": df["data"].min().strftime("%Y-%m-%d"),
        "fim": df["data"].max().strftime("%Y-%m-%d"),
        "mesesCompletos": len(agreg["mensal"]["Total"]["periodos"]),
        "semanasCompletas": len(agreg["semanal"]["Total"]["periodos"]),
        "pesoMedioTaxado": round(float(df["Peso Taxado"].mean()), 2),
        "pesoMedioReal": round(float(df["Peso Real"].mean()), 2),
        "razaoTaxadoReal": round(float(df["Peso Taxado"].sum() / df["Peso Real"].sum()), 4),
    }

    return {
        "meta": {
            "titulo": cfg.TITULO, "subtitulo": cfg.SUBTITULO, "empresa": cfg.EMPRESA,
            "faculdade": cfg.FACULDADE,
            "equipe": list(getattr(cfg, "EQUIPE", [])), "disciplinas": [list(x) for x in getattr(cfg, "DISCIPLINAS", [])], "curso": cfg.CURSO, "dataEntrega": cfg.DATA_ENTREGA,
            "referencia": cfg.REFERENCIA, "arquivo": arquivo, "logo": _logo_data_uri(),
            "geradoEm": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "parametros": {"semanasTeste": cfg.SEMANAS_TESTE, "semanasPrevisao": cfg.SEMANAS_PREVISAO,
                           "z": cfg.Z_95},
        },
        "tratamento": rel,
        "resumo": resumo,
        "recortes": recs,
        "diaria": diaria,
        "semanal": agreg["semanal"],
        "mensal": agreg["mensal"],
        "sazonalidade": sazonal,
        "diaSemana": dia_sem,
        "variacaoAnual": var_anual,
        "variabilidade": variab,
        "distribuicao": distrib,
        "previsao": prev,
        "exemplos": exemplos,
        "mapa": mapa.montar(df, recs),
    }


def conferir(df: pd.DataFrame, p: dict) -> list[str]:
    """Conferências que precisam fechar. Levanta erro se algo não bater."""
    ok = []

    def exigir(cond, msg):
        if not cond:
            raise AssertionError("Conferência falhou: " + msg)
        ok.append(msg)

    recs = p["recortes"]
    modais = [r for r in recs if r != "Total"]
    d = p["diaria"]["dados"]

    exigir(sum(d["Total"]["fretes"]) == len(df), "soma diária de fretes = linhas da planilha")
    exigir(sum(d["Total"]["volumes"]) == int(df["Volumes"].sum()), "soma diária de volumes = planilha")
    exigir(abs(sum(d["Total"]["pesoTaxado"]) - df["Peso Taxado"].sum()) < 1, "soma diária do peso taxado = planilha")
    exigir(abs(sum(d["Total"]["pesoReal"]) - df["Peso Real"].sum()) < 1, "soma diária do peso real = planilha")
    for medida in ("fretes", "volumes"):
        soma = np.sum([d[m][medida] for m in modais], axis=0)
        exigir(bool((soma == np.array(d["Total"][medida])).all()), f"total diário de {medida} = soma dos modais")

    ini = pd.Timestamp(p["resumo"]["inicio"])
    mensal_total = sum(p["mensal"]["Total"]["fretes"])
    meses = pd.PeriodIndex(p["mensal"]["Total"]["periodos"], freq="M")
    dentro = df[df["data"].dt.to_period("M").isin(meses)]
    exigir(mensal_total == len(dentro), "soma mensal = linhas dos meses completos")

    semanas = pd.to_datetime(p["semanal"]["Total"]["periodos"])
    dentro_s = df[df["semana"].isin(semanas)]
    exigir(sum(p["semanal"]["Total"]["fretes"]) == len(dentro_s), "soma semanal = linhas das semanas completas")

    for m in modais:
        exigir(p["resumo"]["porModal"][m] == int((df["Modal do frete"] == m).sum()), f"fretes do modal {m}")

    pt, pm = p["previsao"]["Total"], [p["previsao"][m] for m in modais]
    soma_prev = np.sum([x["semanal"]["previsto"] for x in pm], axis=0)
    exigir(bool(np.allclose(soma_prev, pt["semanal"]["previsto"], atol=0.2)), "previsão do total = soma dos modais")
    for rec, x in p["previsao"].items():
        v = np.array(x["semanal"]["previsto"])
        exigir(bool((v >= 0).all() and np.isfinite(v).all()), f"previsão semanal válida ({rec})")
        exigir(len(v) == cfg.SEMANAS_PREVISAO, f"{cfg.SEMANAS_PREVISAO} semanas de previsão ({rec})")
        exigir(bool(np.all(np.array(x["semanal"]["inferior"]) <= v) and np.all(v <= np.array(x["semanal"]["superior"]))),
               f"faixa envolve a previsão ({rec})")
    exigir(len(pt["mensal"]) == 6, "projeção mensal de 6 meses")

    for rec, m in p["mapa"]["rotas"].items():
        for nivel in ("cidades", "estados"):
            lista = m[nivel]
            soma = sum(r["fretes"] for r in lista)
            exigir(0 < len(lista) <= mapa.N_ROTAS and soma <= m["total"], f"mapa: rotas por {nivel} ({rec}) somam no máximo o total")
            exigir(all(0 <= r[k]["x"] <= mapa.LARGURA and 0 <= r[k]["y"] <= mapa.ALTURA for r in lista for k in ("o", "d")),
                   f"mapa: pontos de {nivel} ({rec}) dentro da área do desenho")
        exigir(m["total"] == p["resumo"]["fretes"] if rec == "Total" else m["total"] == p["resumo"]["porModal"][rec],
               f"mapa: total de fretes ({rec}) = planilha")
    return ok


def escrever(p: dict):
    dados = json.dumps(p, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    cfg.SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    cfg.SAIDA_JSON.write_text(json.dumps(p, ensure_ascii=False, indent=1, default=_json_default), encoding="utf-8")

    template = cfg.TEMPLATE.read_text(encoding="utf-8")
    chartjs = cfg.CHARTJS.read_text(encoding="utf-8").replace("</script", "<\\/script")
    descricao = (f"{cfg.SUBTITULO}. Trabalho de {cfg.CURSO}, {cfg.FACULDADE}, {cfg.DATA_ENTREGA}."
                 .replace('"', "&quot;"))
    html = (template
            .replace("__TITULO_PAGINA__", f"{cfg.TITULO} | {cfg.SUBTITULO}")
            .replace("__DESCRICAO__", descricao)
            .replace("__CHARTJS__", chartjs)
            .replace("__DADOS__", dados.replace("</", "<\\/")))
    cfg.SAIDA_HTML.write_text(html, encoding="utf-8")


def main():
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else cfg.PLANILHA
    print(f"Lendo {origem.name} ...")
    df, rel = limpeza.carregar(origem)
    print(f"  {rel['linhasUsadas']:,} fretes usados; {rel['linhasIdenticasMantidas']} linhas idênticas mantidas")
    p = montar(df, rel, origem.name)
    for linha in conferir(df, p):
        print("  ok:", linha)
    escrever(p)
    print(f"Site gerado: {cfg.SAIDA_HTML}")
    print(f"Auditoria:   {cfg.SAIDA_JSON}")
    for rec, x in p["previsao"].items():
        m = x["metricas"]
        print(f"  {rec:11s} método: {x['metodo']['nome']:62s} MAPE {m['MAPE']:5.1f}%  sinal {m['sinalRastreamento']:+.1f}")


if __name__ == "__main__":
    main()

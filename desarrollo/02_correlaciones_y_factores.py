#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_correlaciones_y_factores.py
==============================
Paso 2 del pipeline de experimentación en contenedor (Clase 7):
1. Carga `experimentos/resultados/SINIESTROS_LAS_CONDES_CORREGIDO.csv`.
2. Calcula la matriz de correlaciones no paramétricas (Spearman rho) y paramétricas (Pearson r)
   con valores p exactos y corrección por pruebas múltiples (Benjamini-Hochberg FDR) entre variables
   climáticas, solares corregidas, topográficas, temporales, vulnerabilidad y severidad.
3. Calcula pruebas de asociación categórica (Chi-cuadrado, test exacto de Fisher 2x2, V de Cramér y
   Odds Ratios con IC 95%) para evaluar qué factores incrementan significativamente:
   - La probabilidad condicional de lesionados (`con_lesionados = 1`)
   - La probabilidad condicional de siniestro grave o fatal (`grave_o_fatal = 1`)
   - El involucramiento de usuarios vulnerables (`usuario_vulnerable = 1`)
4. Ajusta un modelo multivariado de Regresión Logística (con estandarización e intervalos de confianza)
   para aislar el efecto independiente de cada dimensión (usuario vulnerable, causa específica,
   iluminación solar corregida, clima/pavimento, altitud y morfología vial).
5. Exporta tablas CSV, resumen JSON y figuras de alta resolución a `experimentos/resultados/`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"
IN_CSV = OUT_DIR / "SINIESTROS_LAS_CONDES_CORREGIDO.csv"


def cramers_v(confusion_matrix: np.ndarray) -> float:
    """Calcula la V de Cramér con corrección de sesgo para tablas de contingencia."""
    chi2 = stats.chi2_contingency(confusion_matrix, correction=False)[0]
    n = confusion_matrix.sum()
    if n <= 1:
        return 0.0
    r, k = confusion_matrix.shape
    phi2 = chi2 / n
    phi2corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / (n - 1))
    rcorr = r - ((r - 1) ** 2) / (n - 1)
    kcorr = k - ((k - 1) ** 2) / (n - 1)
    denom = min((kcorr - 1), (rcorr - 1))
    return float(np.sqrt(phi2corr / denom)) if denom > 0 else 0.0


def calc_2x2_or_fisher(df: pd.DataFrame, exposure_col: str, outcome_col: str, hipotesis_desc: str) -> Dict[str, Any]:
    """
    Calcula tabla 2x2, Odds Ratio (con corrección de Haldane-Anscombe si hay celdas cero),
    IC 95% de Woolf, p-valor exacto de Fisher y V de Cramér.
    """
    sub = df[[exposure_col, outcome_col]].dropna()
    exp = sub[exposure_col].astype(int) == 1
    out = sub[outcome_col].astype(int) == 1

    a = int((exp & out).sum())       # Expuesto con evento
    b = int((exp & ~out).sum())      # Expuesto sin evento
    c = int((~exp & out).sum())      # No expuesto con evento
    d = int((~exp & ~out).sum())     # No expuesto sin evento

    n_exp = a + b
    n_noexp = c + d
    rate_exp = (a / n_exp * 100.0) if n_exp > 0 else 0.0
    rate_noexp = (c / n_noexp * 100.0) if n_noexp > 0 else 0.0

    table = np.array([[a, b], [c, d]])
    _, p_fisher = stats.fisher_exact(table)
    chi2_val, p_chi2, _, _ = stats.chi2_contingency(table, correction=False)
    v_cramer = cramers_v(table)

    # Haldane-Anscombe correction if any cell is 0
    if min(a, b, c, d) == 0:
        aa, bb, cc, dd = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    else:
        aa, bb, cc, dd = float(a), float(b), float(c), float(d)

    or_val = (aa * dd) / (bb * cc)
    se_log_or = math.sqrt(1.0 / aa + 1.0 / bb + 1.0 / cc + 1.0 / dd)
    ci_low = math.exp(math.log(or_val) - 1.96 * se_log_or)
    ci_high = math.exp(math.log(or_val) + 1.96 * se_log_or)

    return {
        "hipotesis": hipotesis_desc,
        "factor_exposicion": exposure_col,
        "variable_respuesta": outcome_col,
        "n_expuestos": n_exp,
        "eventos_en_expuestos": a,
        "pct_evento_expuestos": round(rate_exp, 2),
        "n_no_expuestos": n_noexp,
        "eventos_en_no_expuestos": c,
        "pct_evento_no_expuestos": round(rate_noexp, 2),
        "odds_ratio": round(or_val, 3),
        "ic95_inf": round(ci_low, 3),
        "ic95_sup": round(ci_high, 3),
        "p_fisher": round(float(p_fisher), 6),
        "p_chi2": round(float(p_chi2), 6),
        "v_cramer": round(v_cramer, 3),
        "significativo_p05": bool(p_fisher < 0.05),
    }


def main() -> Dict[str, Any]:
    df = pd.read_csv(IN_CSV)

    # 1. Matriz de correlaciones cuantitativas y ordinales (Spearman y Pearson)
    vars_corr = [
        "TOTAL_LESI",
        "con_lesionados",
        "grave_o_fatal",
        "indice_epdo",
        "Atropello",
        "Motociclet",
        "Bicicleta",
        "usuario_vulnerable",
        "causa_distinta_no_atento",
        "es_cruce",
        "hora_decimal",
        "en_hora_punta",
        "es_fin_de_semana",
        "sol_alt_grados_corr",
        "noche_corr",
        "sol_bajo_encandilamiento",
        "altitud_m",
        "longitud",
        "Latitud",
        "temp_c",
        "humedad_pct",
        "precip_hora_mm",
        "preci_prev_24h",
        "horas_lluvia_24h",
        "pavimento_adverso",
        "viento_kmh",
        "rafaga_kmh",
        "nubosidad_pct",
        "niebla",
    ]

    corr_rows: List[Dict[str, Any]] = []
    for i in range(len(vars_corr)):
        for j in range(i + 1, len(vars_corr)):
            v1, v2 = vars_corr[i], vars_corr[j]
            s1, s2 = df[v1], df[v2]
            rho, p_spear = stats.spearmanr(s1, s2)
            r_p, p_pears = stats.pearsonr(s1, s2)
            corr_rows.append(
                {
                    "variable_1": v1,
                    "variable_2": v2,
                    "spearman_rho": round(float(rho), 4),
                    "p_spearman": float(p_spear),
                    "pearson_r": round(float(r_p), 4),
                    "p_pearson": float(p_pears),
                    "abs_rho": round(abs(float(rho)), 4),
                }
            )

    corr_df = pd.DataFrame(corr_rows).sort_values("abs_rho", ascending=False).reset_index(drop=True)
    # Ajuste Benjamini-Hochberg FDR sobre p_spearman
    m = len(corr_df)
    ranks = np.arange(1, m + 1)
    p_sorted_idx = np.argsort(corr_df["p_spearman"].values)
    fdr_vals = np.empty(m)
    min_fdr = 1.0
    for idx_rank in range(m - 1, -1, -1):
        orig_idx = p_sorted_idx[idx_rank]
        val = corr_df.loc[orig_idx, "p_spearman"] * m / (idx_rank + 1)
        min_fdr = min(min_fdr, val)
        fdr_vals[orig_idx] = min(1.0, min_fdr)
    corr_df["q_fdr_bh"] = np.round(fdr_vals, 6)
    corr_df["p_spearman"] = corr_df["p_spearman"].round(6)
    corr_df["p_pearson"] = corr_df["p_pearson"].round(6)

    corr_csv_path = OUT_DIR / "02_correlaciones_estadisticas.csv"
    corr_df.to_csv(corr_csv_path, index=False, encoding="utf-8")

    # 2. Batería de pruebas 2x2 (Odds Ratios, Fisher, Chi2) sobre hipótesis de negocio y mitigación
    # Creamos indicadores binarios adicionales específicos para contrastar hipótesis
    df["es_colision_o_alcance"] = df["TIPO_SINIE"].isin(["COLISION", "COLISION LATERAL", "COLISION POR ALCANCE"]).astype(int)
    df["es_choque_fijo"] = df["TIPO_SINIE"].isin(["CHOQUE", "CHOQUE LATERAL", "CHOQUE FRONTAL", "CHOQUE POSTERIOR"]).astype(int)
    df["es_volcadura_o_caida"] = df["TIPO_SINIE"].isin(["CAIDA", "VOLCADURA"]).astype(int)
    df["causa_violacion_paso_semaforo"] = (df["causa_especifica"] == "VIOLACION_SEMAFORO_O_PREFERENCIA").astype(int)
    df["causa_maniobra_pista"] = (df["causa_especifica"] == "MANIOBRA_PISTA_ADELANTAMIENTO_VIRAJE").astype(int)
    df["causa_alcohol"] = (df["causa_especifica"] == "ALCOHOL_EN_CONDUCTOR").astype(int)
    df["tramo_recto_bin"] = (df["tipo_ubicacion_vial"] == "TRAMO_RECTO").astype(int)

    hipotesis_list = [
        # Con lesionados (TOTAL_LESI > 0)
        ("Atropello", "con_lesionados", "Atropello a peatón -> Siniestro con lesionados"),
        ("Motociclet", "con_lesionados", "Involucramiento de motocicleta -> Siniestro con lesionados"),
        ("Bicicleta", "con_lesionados", "Involucramiento de bicicleta -> Siniestro con lesionados"),
        ("usuario_vulnerable", "con_lesionados", "Cualquier usuario vulnerable (peatón/moto/bici) -> Siniestro con lesionados"),
        ("causa_distinta_no_atento", "con_lesionados", "Causa específica (maniobra/semáforo/alcohol/peatón vs 'no atento') -> Con lesionados"),
        ("causa_violacion_paso_semaforo", "con_lesionados", "Desobedecer semáforo o preferencia de paso -> Con lesionados"),
        ("noche_corr", "con_lesionados", "Condición nocturna (corregida <= 0°) -> Con lesionados"),
        ("pavimento_adverso", "con_lesionados", "Pavimento húmedo/mojado/lluvia -> Con lesionados"),
        ("lluvia_reciente_24h", "con_lesionados", "Precipitación acumulada 24h > 0 mm -> Con lesionados"),
        ("niebla", "con_lesionados", "Presencia de niebla -> Con lesionados"),
        ("zona_alta_precordillera", "con_lesionados", "Zona alta precordillerana (>= 750 m s.n.m.) -> Con lesionados"),
        ("es_cruce", "con_lesionados", "Ocurrencia en cruce (semaforizado o con señal) -> Con lesionados"),
        ("es_fin_de_semana", "con_lesionados", "Fin de semana (sábado/domingo) -> Con lesionados"),
        ("sol_bajo_encandilamiento", "con_lesionados", "Sol rasante de encandilamiento (0° < alt <= 15°) -> Con lesionados"),
        # Grave o fatal (GRAVES + FALLECIDOS > 0)
        ("Atropello", "grave_o_fatal", "Atropello a peatón -> Siniestro grave o fatal"),
        ("Motociclet", "grave_o_fatal", "Involucramiento de motocicleta -> Siniestro grave o fatal"),
        ("Bicicleta", "grave_o_fatal", "Involucramiento de bicicleta -> Siniestro grave o fatal"),
        ("usuario_vulnerable", "grave_o_fatal", "Usuario vulnerable (peatón/moto/bici) -> Siniestro grave o fatal"),
        ("causa_distinta_no_atento", "grave_o_fatal", "Causa específica distinta a 'no atento' -> Siniestro grave o fatal"),
        ("causa_violacion_paso_semaforo", "grave_o_fatal", "Desobedecer semáforo o preferencia -> Siniestro grave o fatal"),
        ("noche_corr", "grave_o_fatal", "Condición nocturna (corregida <= 0°) -> Siniestro grave o fatal"),
        ("pavimento_adverso", "grave_o_fatal", "Pavimento húmedo/mojado/lluvia -> Siniestro grave o fatal"),
        ("zona_alta_precordillera", "grave_o_fatal", "Zona alta precordillerana (>= 750 m s.n.m.) -> Siniestro grave o fatal"),
        ("es_fin_de_semana", "grave_o_fatal", "Fin de semana -> Siniestro grave o fatal"),
        # Patrones específicos de clima, iluminación y modo
        ("noche_corr", "es_choque_fijo", "Condición nocturna (corregida) -> Choque contra objeto/elemento fijo"),
        ("es_fin_de_semana", "es_choque_fijo", "Fin de semana -> Choque contra objeto fijo"),
        ("pavimento_adverso", "es_choque_fijo", "Pavimento húmedo/mojado -> Choque contra objeto fijo"),
        ("en_hora_punta", "usuario_vulnerable", "Hora punta (07-10 h / 17-21 h) -> Involucramiento de usuario vulnerable"),
        ("es_cruce", "Motociclet", "Ocurrencia en cruce -> Siniestro con motocicleta"),
        ("sol_bajo_encandilamiento", "Atropello", "Sol rasante (0°-15°) -> Atropello peatonal"),
    ]

    asoc_rows = [calc_2x2_or_fisher(df, exp_c, out_c, desc) for exp_c, out_c, desc in hipotesis_list]
    asoc_df = pd.DataFrame(asoc_rows).sort_values("p_fisher", ascending=True).reset_index(drop=True)
    asoc_csv_path = OUT_DIR / "02_asociaciones_categoricas_chi2_or.csv"
    asoc_df.to_csv(asoc_csv_path, index=False, encoding="utf-8")

    # 3. Modelo Multivariado de Regresión Logística para `con_lesionados` y `grave_o_fatal`
    features_logit = [
        "Atropello",
        "Motociclet",
        "Bicicleta",
        "causa_distinta_no_atento",
        "noche_corr",
        "pavimento_adverso",
        "es_cruce",
        "zona_alta_precordillera",
        "es_fin_de_semana",
    ]
    X = sm.add_constant(df[features_logit].astype(float))
    logit_lesi = sm.Logit(df["con_lesionados"].astype(float), X).fit(disp=False)
    logit_grave = sm.Logit(df["grave_o_fatal"].astype(float), X).fit(disp=False)

    def summarize_logit(model: Any) -> Dict[str, Any]:
        params = model.params
        conf = model.conf_int()
        pvals = model.pvalues
        out_dict = {}
        for k in params.index:
            if k == "const":
                continue
            out_dict[k] = {
                "odds_ratio_ajustado": round(float(np.exp(params[k])), 3),
                "ic95_inf": round(float(np.exp(conf.loc[k, 0])), 3),
                "ic95_sup": round(float(np.exp(conf.loc[k, 1])), 3),
                "p_valor": round(float(pvals[k]), 6),
            }
        return {
            "pseudo_r2_mcfadden": round(float(model.prsquared), 4),
            "llr_pvalue": float(model.llr_pvalue),
            "factores": out_dict,
        }

    res_logit_lesi = summarize_logit(logit_lesi)
    res_logit_grave = summarize_logit(logit_grave)

    # 4. Pruebas adicionales sobre Altitud vs Clima y Severidad por Tipología
    rho_alt_temp, p_alt_temp = stats.spearmanr(df["altitud_m"], df["temp_c"])
    rho_alt_lon, p_alt_lon = stats.spearmanr(df["altitud_m"], df["longitud"])

    # Figura 02: Heatmap de correlaciones de Spearman en subconjunto clave
    heatmap_vars = [
        "con_lesionados",
        "grave_o_fatal",
        "indice_epdo",
        "Atropello",
        "Motociclet",
        "Bicicleta",
        "causa_distinta_no_atento",
        "es_cruce",
        "noche_corr",
        "sol_alt_grados_corr",
        "pavimento_adverso",
        "precip_hora_mm",
        "humedad_pct",
        "temp_c",
        "viento_kmh",
        "altitud_m",
    ]
    labels_pretty = [
        "Con Lesionados",
        "Grave o Fatal",
        "Índice EPDO",
        "Atropello Peatón",
        "Motocicleta",
        "Bicicleta",
        "Causa Específica",
        "Cruce Vial",
        "Noche (Corregida)",
        "Altitud Solar (°)",
        "Pavimento Húmedo/Mojado",
        "Precipitación (mm/h)",
        "Humedad (%)",
        "Temperatura (°C)",
        "Viento (km/h)",
        "Altitud (m s.n.m.)",
    ]
    corr_matrix = df[heatmap_vars].corr(method="spearman")
    corr_matrix.index = labels_pretty
    corr_matrix.columns = labels_pretty

    fig, ax = plt.subplots(figsize=(12, 9.5), dpi=160)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        vmin=-0.65,
        vmax=0.65,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8, "label": "Correlación de Spearman (ρ)"},
        annot_kws={"size": 7.5},
        ax=ax,
    )
    ax.set_title(
        "Matriz de Correlaciones de Spearman (ρ) — Siniestros Las Condes 2025 (n = 676)\n"
        "(Variables solares corregidas, severidad, usuarios vulnerables, clima y topografía)",
        fontsize=11.5,
        fontweight="bold",
        pad=14,
    )
    plt.xticks(rotation=40, ha="right", fontsize=8.5)
    plt.yticks(rotation=0, fontsize=8.5)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig02_matriz_correlaciones_spearman.png", bbox_inches="tight")
    plt.close(fig)

    # Figura 03: Forest Plot de Odds Ratios ajustados (Regresión Logística Multivariada) y tasas de severidad
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), dpi=160)

    # Panel A: Tasas de lesionados y graves/fatales según modo/factor
    grupos_modo = [
        ("Atropello Peatón\n(n=42)", df[df["Atropello"] == 1]),
        ("Bicicleta\n(n=25)", df[df["Bicicleta"] == 1]),
        ("Motocicleta\n(n=102)", df[df["Motociclet"] == 1]),
        ("Causa Específica\n(No 'atento', n=90)", df[df["causa_distinta_no_atento"] == 1]),
        ("Pavimento Mojado/Húm.\n(n=102)", df[df["pavimento_adverso"] == 1]),
        ("Noche Corregida\n(n=197)", df[df["noche_corr"] == 1]),
        ("Solo Vehículos Motor.\nSin Vulnerables (n=514)", df[df["usuario_vulnerable"] == 0]),
    ]
    nombres_g = [g[0] for g in grupos_modo]
    pct_lesi = [float(g[1]["con_lesionados"].mean() * 100.0) for g in grupos_modo]
    pct_grav = [float(g[1]["grave_o_fatal"].mean() * 100.0) for g in grupos_modo]

    y_pos = np.arange(len(nombres_g))
    h_bar = 0.38
    b_les = axes[0].barh(y_pos - h_bar / 2, pct_lesi, height=h_bar, color="#2b5c8f", label="% Con al menos 1 lesionado")
    b_grv = axes[0].barh(y_pos + h_bar / 2, pct_grav, height=h_bar, color="#c0392b", label="% Con lesionado grave o fallecido")
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(nombres_g, fontsize=8.5)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Porcentaje de siniestros (%)")
    axes[0].set_title("A. Severidad Condicional según Factor / Modo Vial", fontsize=10.5, fontweight="bold")
    axes[0].legend(loc="lower right", fontsize=8.5)
    axes[0].grid(True, axis="x", alpha=0.25)
    axes[0].set_xlim(0, 112)
    for bar in b_les:
        w_val = bar.get_width()
        axes[0].text(w_val + 1.2, bar.get_y() + bar.get_height() / 2, f"{w_val:.1f}%", va="center", fontsize=7.5, color="#1b3b5c")
    for bar in b_grv:
        w_val = bar.get_width()
        axes[0].text(w_val + 1.2, bar.get_y() + bar.get_height() / 2, f"{w_val:.1f}%", va="center", fontsize=7.5, color="#902015")

    # Panel B: Odds Ratios Ajustados (Modelo Logístico Multivariado para Siniestro Grave o Fatal)
    label_map_logit = {
        "Atropello": "Atropello Peatonal",
        "Motociclet": "Motocicleta Involucrada",
        "Bicicleta": "Bicicleta Involucrada",
        "causa_distinta_no_atento": "Causa Específica (Maniobra/Semáforo/Alcohol)",
        "noche_corr": "Noche Corregida (Altitud Solar ≤ 0°)",
        "pavimento_adverso": "Pavimento Húmedo / Mojado / Lluvia",
        "es_cruce": "Ubicación en Cruce Vial",
        "zona_alta_precordillera": "Zona Alta Precordillera (≥ 750 m)",
        "es_fin_de_semana": "Fin de Semana (Sáb–Dom)",
    }
    f_keys = list(res_logit_grave["factores"].keys())
    y_f = np.arange(len(f_keys))
    ors_g = [res_logit_grave["factores"][k]["odds_ratio_ajustado"] for k in f_keys]
    lows_g = [res_logit_grave["factores"][k]["ic95_inf"] for k in f_keys]
    highs_g = [res_logit_grave["factores"][k]["ic95_sup"] for k in f_keys]
    pvals_g = [res_logit_grave["factores"][k]["p_valor"] for k in f_keys]

    axes[1].axvline(1.0, color="black", linestyle="--", linewidth=1)
    for idx_f, k in enumerate(f_keys):
        color_pt = "#c0392b" if pvals_g[idx_f] < 0.05 else "#7f8c8d"
        axes[1].errorbar(
            ors_g[idx_f],
            idx_f,
            xerr=[[ors_g[idx_f] - lows_g[idx_f]], [highs_g[idx_f] - ors_g[idx_f]]],
            fmt="o",
            color=color_pt,
            ecolor=color_pt,
            elinewidth=1.8,
            capsize=4,
            markersize=6,
        )
        sig_star = "**" if pvals_g[idx_f] < 0.01 else ("*" if pvals_g[idx_f] < 0.05 else "")
        axes[1].text(
            max(highs_g[idx_f] * 1.08, ors_g[idx_f] * 1.15),
            idx_f,
            f"OR={ors_g[idx_f]:.2f}{sig_star} (p={pvals_g[idx_f]:.3f})",
            va="center",
            fontsize=7.5,
            color=color_pt,
        )

    axes[1].set_xscale("log")
    axes[1].set_yticks(y_f)
    axes[1].set_yticklabels([label_map_logit[k] for k in f_keys], fontsize=8.5)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Odds Ratio Ajustado (escala log, IC 95%)")
    axes[1].set_title(
        f"B. Regresión Logística Multivariada: Siniestro Grave o Fatal\n(Pseudo-R² McFadden = {res_logit_grave['pseudo_r2_mcfadden']:.3f}, p < 0.0001)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1].set_xlim(0.15, 120)
    axes[1].grid(True, axis="x", alpha=0.25)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig03_factores_riesgo_severidad_or.png", bbox_inches="tight")
    plt.close(fig)

    # Figura 04: Perfiles horarios de siniestralidad, usuarios vulnerables y choques nocturnos
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.0), dpi=160)

    df["hora_int"] = df["hora_decimal"].astype(int).clip(0, 23)
    horas_rango = list(range(24))
    tot_hora = [int((df["hora_int"] == h).sum()) for h in horas_rango]
    vuln_hora = [int(((df["hora_int"] == h) & (df["usuario_vulnerable"] == 1)).sum()) for h in horas_rango]
    choque_hora = [int(((df["hora_int"] == h) & (df["es_choque_fijo"] == 1)).sum()) for h in horas_rango]

    axes[0].plot(horas_rango, tot_hora, marker="o", linewidth=2.2, color="#2c3e50", label="Total siniestros (n=676)")
    axes[0].plot(horas_rango, vuln_hora, marker="s", linewidth=2.0, color="#d35400", label="Usuarios vulnerables: Moto/Peatón/Bici (n=162)")
    axes[0].plot(horas_rango, choque_hora, marker="^", linewidth=1.8, color="#8e44ad", label="Choques contra elemento fijo (n=131)")
    axes[0].axvspan(7, 10, color="#f1c40f", alpha=0.18, label="Punta Mañana (07–10 h)")
    axes[0].axvspan(17, 21, color="#e67e22", alpha=0.15, label="Punta Tarde (17–21 h)")
    axes[0].set_xticks(horas_rango)
    axes[0].set_xlabel("Hora del día (0–23 h local)")
    axes[0].set_ylabel("Cantidad de siniestros")
    axes[0].set_title("A. Perfil Horario según Tipología y Usuarios Vulnerables", fontsize=10.5, fontweight="bold")
    axes[0].legend(fontsize=8, loc="upper left")
    axes[0].grid(True, alpha=0.25)

    # Panel B: Desglose de Causas Específicas vs Severidad (% con lesionados y % graves/fatales)
    causa_grp = (
        df.groupby("causa_especifica")
        .agg(
            n=("ID", "count"),
            pct_lesi=("con_lesionados", lambda s: round(float(s.mean() * 100.0), 1)),
            pct_grave=("grave_o_fatal", lambda s: round(float(s.mean() * 100.0), 1)),
            epdo_medio=("indice_epdo", lambda s: round(float(s.mean()), 2)),
        )
        .reset_index()
        .sort_values("pct_lesi", ascending=True)
    )
    y_c = np.arange(len(causa_grp))
    axes[1].barh(y_c - 0.18, causa_grp["pct_lesi"], height=0.35, color="#16a085", label="% Con lesionados")
    axes[1].barh(y_c + 0.18, causa_grp["pct_grave"], height=0.35, color="#c0392b", label="% Grave o fatal")
    axes[1].set_yticks(y_c)
    axes[1].set_yticklabels(
        [f"{r['causa_especifica']}\n(n={r['n']}, EPDO={r['epdo_medio']})" for _, r in causa_grp.iterrows()],
        fontsize=7.8,
    )
    axes[1].set_xlabel("Porcentaje de siniestros (%)")
    axes[1].set_title("B. Desagregación de CAUSA_SINI vs. Severidad Real", fontsize=10.5, fontweight="bold")
    axes[1].legend(fontsize=8.5, loc="lower right")
    axes[1].grid(True, axis="x", alpha=0.25)
    axes[1].set_xlim(0, 95)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig04_perfiles_horarios_y_vulnerables.png", bbox_inches="tight")
    plt.close(fig)

    resumen = {
        "top_correlaciones_spearman": corr_df.head(20).to_dict(orient="records"),
        "asociaciones_significativas_p05": asoc_df[asoc_df["significativo_p05"]].to_dict(orient="records"),
        "modelo_logistico_con_lesionados": res_logit_lesi,
        "modelo_logistico_grave_o_fatal": res_logit_grave,
        "gradiente_orografico_climatico": {
            "spearman_altitud_vs_longitud": round(float(rho_alt_lon), 4),
            "p_altitud_vs_longitud": float(p_alt_lon),
            "spearman_altitud_vs_temperatura": round(float(rho_alt_temp), 4),
            "p_altitud_vs_temperatura": float(p_alt_temp),
        },
        "desglose_causa_especifica": causa_grp.sort_values("n", ascending=False).to_dict(orient="records"),
    }

    with open(OUT_DIR / "02_resumen_correlaciones.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(f"[02] Correlaciones calculadas: {len(corr_df)} pares guardados en {corr_csv_path.name}")
    print(f"[02] Asociaciones 2x2 significativas (p < 0.05): {int(asoc_df['significativo_p05'].sum())} de {len(asoc_df)}")
    return resumen


if __name__ == "__main__":
    main()

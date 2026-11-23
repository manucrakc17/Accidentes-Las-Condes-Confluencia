#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_correlaciones_y_factores.py
==============================
Paso 2 del pipeline de experimentación en contenedor (Clase 7):
1. Carga `experimentos/privado/SINIESTROS_LAS_CONDES_CORREGIDO.csv`.
2. Calcula la matriz de correlaciones no paramétricas (Spearman rho) y paramétricas (Pearson r)
   con valores p y ajuste Benjamini-Hochberg para Spearman.
3. Calcula pruebas de asociación categórica (Chi-cuadrado, test exacto de Fisher 2x2, V de Cramér y
   Odds Ratios con IC 95%, con ajustes Benjamini-Hochberg y Holm para Fisher) para explorar:
   - La probabilidad condicional de lesionados (`con_lesionados = 1`)
   - La probabilidad condicional de siniestro grave o fatal (`grave_o_fatal = 1`)
   - El involucramiento de usuarios vulnerables (`usuario_vulnerable = 1`)
4. Ajusta dos regresiones logísticas asociativas y evalúa la sensibilidad a la hora y la altitud.
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
from statsmodels.stats.multitest import multipletests
import matplotlib.pyplot as plt
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"
IN_CSV = ROOT_DIR / "experimentos" / "privado" / "SINIESTROS_LAS_CONDES_CORREGIDO.csv"


def ajustar_p_valores(p_values: pd.Series, method: str) -> pd.Series:
    """Conserva la familia planificada y deja sin resultado los contrastes no estimables."""
    adjusted = multipletests(p_values.astype(float).fillna(1.0), method=method)[1]
    return pd.Series(adjusted, index=p_values.index).where(p_values.notna())


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
    if not sub.isin([0, 1]).to_numpy().all():
        raise ValueError(f"Se requieren indicadores binarios para {exposure_col} y {outcome_col}")
    exp = sub[exposure_col] == 1
    out = sub[outcome_col] == 1

    a = int((exp & out).sum())       # Expuesto con evento
    b = int((exp & ~out).sum())      # Expuesto sin evento
    c = int((~exp & out).sum())      # No expuesto con evento
    d = int((~exp & ~out).sum())     # No expuesto sin evento

    n_exp = a + b
    n_noexp = c + d
    table = np.array([[a, b], [c, d]])
    estimable = bool(table.sum(axis=0).all() and table.sum(axis=1).all())
    result = {
        "hipotesis": hipotesis_desc,
        "factor_exposicion": exposure_col,
        "variable_respuesta": outcome_col,
        "n_expuestos": n_exp,
        "eventos_en_expuestos": a,
        "pct_evento_expuestos": round(a / n_exp * 100.0, 2) if n_exp else None,
        "n_no_expuestos": n_noexp,
        "eventos_en_no_expuestos": c,
        "pct_evento_no_expuestos": round(c / n_noexp * 100.0, 2) if n_noexp else None,
        "odds_ratio": None,
        "ic95_inf": None,
        "ic95_sup": None,
        "p_fisher": None,
        "p_chi2": None,
        "v_cramer": None,
        "significativo_p05": False,
        "estimable": estimable,
    }
    if not estimable:
        return result

    _, p_fisher = stats.fisher_exact(table)
    _, p_chi2, _, _ = stats.chi2_contingency(table, correction=False)

    # Haldane-Anscombe para estimar OR e intervalo con algún conteo nulo.
    adjustment = 0.5 if table.min() == 0 else 0.0
    aa, bb, cc, dd = table.ravel() + adjustment
    or_val = (aa * dd) / (bb * cc)
    se_log_or = math.sqrt(1.0 / aa + 1.0 / bb + 1.0 / cc + 1.0 / dd)
    ci_low = math.exp(math.log(or_val) - 1.96 * se_log_or)
    ci_high = math.exp(math.log(or_val) + 1.96 * se_log_or)
    return {
        **result,
        "odds_ratio": round(or_val, 3),
        "ic95_inf": round(ci_low, 3),
        "ic95_sup": round(ci_high, 3),
        "p_fisher": float(p_fisher),
        "p_chi2": float(p_chi2),
        "v_cramer": round(cramers_v(table), 3),
        "significativo_p05": bool(p_fisher < 0.05),
    }


def ajustar_logit(y: pd.Series, predictors: pd.DataFrame) -> Dict[str, Any]:
    model = sm.Logit(y.astype(float), sm.add_constant(predictors, has_constant="add")).fit(disp=False)
    if not model.mle_retvals["converged"]:
        raise RuntimeError(f"La regresión logística de {y.name} no convergió")

    p_values = model.pvalues.drop("const")
    q_bh = ajustar_p_valores(p_values, "fdr_bh")
    p_holm = ajustar_p_valores(p_values, "holm")
    intervals = np.exp(model.conf_int())
    return {
        "n_siniestros": int(model.nobs),
        "n_eventos": int(y.sum()),
        "n_predictores": len(p_values),
        "convergio": bool(model.mle_retvals["converged"]),
        "pseudo_r2_mcfadden": round(float(model.prsquared), 4),
        "llr_pvalue": float(model.llr_pvalue),
        "factores": {
            name: {
                "odds_ratio_ajustado": round(float(np.exp(model.params[name])), 3),
                "ic95_inf": round(float(intervals.loc[name, 0]), 3),
                "ic95_sup": round(float(intervals.loc[name, 1]), 3),
                "p_valor": float(p),
                "q_fdr_bh": float(q_bh[name]),
                "p_holm": float(p_holm[name]),
            }
            for name, p in p_values.items()
        },
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
            pair = df[[v1, v2]].dropna()
            rho = p_spear = r_p = p_pears = np.nan
            if len(pair) >= 3 and pair.nunique().gt(1).all():
                rho, p_spear = stats.spearmanr(pair[v1], pair[v2])
                r_p, p_pears = stats.pearsonr(pair[v1], pair[v2])
            corr_rows.append(
                {
                    "variable_1": v1,
                    "variable_2": v2,
                    "n_pares": len(pair),
                    "spearman_rho": round(float(rho), 4),
                    "p_spearman": float(p_spear),
                    "pearson_r": round(float(r_p), 4),
                    "p_pearson": float(p_pears),
                    "abs_rho": round(abs(float(rho)), 4),
                }
            )

    corr_df = pd.DataFrame(corr_rows).sort_values(
        ["abs_rho", "variable_1", "variable_2"], ascending=[False, True, True]
    ).reset_index(drop=True)
    corr_df["q_fdr_bh"] = ajustar_p_valores(corr_df["p_spearman"], "fdr_bh")
    for column in ["p_spearman", "p_pearson", "q_fdr_bh"]:
        # SciPy puede devolver 0 por subdesborde incluso sin redondeo.
        corr_df[f"{column}_subdesborde"] = corr_df[column].eq(0.0)
        corr_df[column] = corr_df[column].mask(corr_df[f"{column}_subdesborde"])

    corr_csv_path = OUT_DIR / "02_correlaciones_estadisticas.csv"
    corr_df.to_csv(corr_csv_path, index=False, encoding="utf-8")

    # 2. Batería de pruebas 2x2 (Odds Ratios, Fisher, Chi2) sobre hipótesis de negocio y mitigación
    # Creamos indicadores binarios adicionales específicos para contrastar hipótesis
    df["es_choque_fijo"] = df["TIPO_SINIE"].isin(["CHOQUE", "CHOQUE LATERAL", "CHOQUE FRONTAL", "CHOQUE POSTERIOR"]).astype(int)
    df["causa_violacion_paso_semaforo"] = (df["causa_especifica"] == "VIOLACION_SEMAFORO_O_PREFERENCIA").astype(int)

    hipotesis_list = [
        # Con lesionados (TOTAL_LESI > 0)
        ("Atropello", "con_lesionados", "Atropello a peatón -> Siniestro con lesionados"),
        ("Motociclet", "con_lesionados", "Involucramiento de motocicleta -> Siniestro con lesionados"),
        ("Bicicleta", "con_lesionados", "Involucramiento de bicicleta -> Siniestro con lesionados"),
        ("usuario_vulnerable", "con_lesionados", "Cualquier usuario vulnerable (peatón/moto/bici) -> Siniestro con lesionados"),
        ("causa_distinta_no_atento", "con_lesionados", "Causa específica (maniobra/semáforo/alcohol/peatón vs 'no atento') -> Con lesionados"),
        ("causa_violacion_paso_semaforo", "con_lesionados", "Desobedecer semáforo o preferencia de paso -> Con lesionados"),
        ("noche_corr", "con_lesionados", "Condición nocturna (corregida <= 0°) -> Con lesionados"),
        ("pavimento_adverso", "con_lesionados", "Pavimento estimado distinto de seco -> Con lesionados"),
        ("lluvia_reciente_24h", "con_lesionados", "Precipitación acumulada 24h > 0 mm -> Con lesionados"),
        ("niebla", "con_lesionados", "Indicador de niebla estimada -> Con lesionados"),
        ("zona_alta_precordillera", "con_lesionados", "Zona alta precordillerana (>= 750 m s.n.m.) -> Con lesionados"),
        ("es_cruce", "con_lesionados", "Ocurrencia en cruce registrado -> Con lesionados"),
        ("es_fin_de_semana", "con_lesionados", "Fin de semana (sábado/domingo) -> Con lesionados"),
        ("sol_bajo_encandilamiento", "con_lesionados", "Elevación solar entre 0° (excluido) y 15° -> Con lesionados"),
        # Grave o fatal (GRAVES + FALLECIDOS > 0)
        ("Atropello", "grave_o_fatal", "Atropello a peatón -> Siniestro grave o fatal"),
        ("Motociclet", "grave_o_fatal", "Involucramiento de motocicleta -> Siniestro grave o fatal"),
        ("Bicicleta", "grave_o_fatal", "Involucramiento de bicicleta -> Siniestro grave o fatal"),
        ("usuario_vulnerable", "grave_o_fatal", "Usuario vulnerable (peatón/moto/bici) -> Siniestro grave o fatal"),
        ("causa_distinta_no_atento", "grave_o_fatal", "Causa específica distinta a 'no atento' -> Siniestro grave o fatal"),
        ("causa_violacion_paso_semaforo", "grave_o_fatal", "Desobedecer semáforo o preferencia -> Siniestro grave o fatal"),
        ("noche_corr", "grave_o_fatal", "Condición nocturna (corregida <= 0°) -> Siniestro grave o fatal"),
        ("pavimento_adverso", "grave_o_fatal", "Pavimento estimado distinto de seco -> Siniestro grave o fatal"),
        ("zona_alta_precordillera", "grave_o_fatal", "Zona alta precordillerana (>= 750 m s.n.m.) -> Siniestro grave o fatal"),
        ("es_fin_de_semana", "grave_o_fatal", "Fin de semana -> Siniestro grave o fatal"),
        # Patrones específicos de clima, iluminación y modo
        ("noche_corr", "es_choque_fijo", "Condición nocturna (corregida) -> Choque contra objeto/elemento fijo"),
        ("es_fin_de_semana", "es_choque_fijo", "Fin de semana -> Choque contra objeto fijo"),
        ("pavimento_adverso", "es_choque_fijo", "Pavimento estimado distinto de seco -> Choque contra objeto fijo"),
        ("en_hora_punta", "usuario_vulnerable", "Hora punta (07-10 h / 17-21 h) -> Involucramiento de usuario vulnerable"),
        ("es_cruce", "Motociclet", "Ocurrencia en cruce -> Siniestro con motocicleta"),
        ("sol_bajo_encandilamiento", "Atropello", "Elevación solar entre 0° (excluido) y 15° -> Atropello peatonal"),
    ]

    asoc_rows = [calc_2x2_or_fisher(df, exp_c, out_c, desc) for exp_c, out_c, desc in hipotesis_list]
    asoc_df = pd.DataFrame(asoc_rows).sort_values(
        ["p_fisher", "factor_exposicion", "variable_respuesta"]
    ).reset_index(drop=True)
    asoc_df["q_fdr_bh"] = ajustar_p_valores(asoc_df["p_fisher"], "fdr_bh")
    asoc_df["p_holm"] = ajustar_p_valores(asoc_df["p_fisher"], "holm")
    asoc_df["significativo_fdr_bh_05"] = asoc_df["q_fdr_bh"].lt(0.05)
    asoc_df["significativo_holm_05"] = asoc_df["p_holm"].lt(0.05)
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
    X = df[features_logit].astype(float)
    y_grave = df["grave_o_fatal"]
    res_logit_lesi = ajustar_logit(df["con_lesionados"], X)
    res_logit_grave = ajustar_logit(y_grave, X)
    hora_radianes = df["hora_decimal"] * np.pi / 12.0
    sensibilidad = {
        "con_hora_ciclica": ajustar_logit(
            y_grave, X.assign(hora_seno=np.sin(hora_radianes), hora_coseno=np.cos(hora_radianes))
        ),
        "con_altitud_continua": ajustar_logit(
            y_grave,
            X.drop(columns="zona_alta_precordillera").assign(altitud_por_50m=(df["altitud_m"] - 750.0) / 50.0),
        ),
    }

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
        f"Matriz de Correlaciones de Spearman (ρ) — Siniestros Las Condes 2025 (n = {len(df)})\n"
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
        ("Atropello peatonal", df[df["Atropello"] == 1]),
        ("Bicicleta involucrada", df[df["Bicicleta"] == 1]),
        ("Motocicleta involucrada", df[df["Motociclet"] == 1]),
        ("Causa registrada distinta de 'no atento'", df[df["causa_distinta_no_atento"] == 1]),
        ("Pavimento adverso estimado", df[df["pavimento_adverso"] == 1]),
        ("Sol al nivel o bajo el horizonte", df[df["noche_corr"] == 1]),
        ("Sin usuarios vulnerables registrados", df[df["usuario_vulnerable"] == 0]),
    ]
    nombres_g = [f"{label}\n(n={len(group)})" for label, group in grupos_modo]
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
        "causa_distinta_no_atento": "Causa registrada distinta de 'no atento'",
        "noche_corr": "Sol al nivel o bajo el horizonte (≤ 0°)",
        "pavimento_adverso": "Pavimento adverso estimado",
        "es_cruce": "Ubicación en Cruce Vial",
        "zona_alta_precordillera": "Zona Alta Precordillera (≥ 750 m)",
        "es_fin_de_semana": "Fin de Semana (Sáb–Dom)",
    }
    f_keys = list(res_logit_grave["factores"].keys())
    y_f = np.arange(len(f_keys))
    ors_g = [res_logit_grave["factores"][k]["odds_ratio_ajustado"] for k in f_keys]
    lows_g = [res_logit_grave["factores"][k]["ic95_inf"] for k in f_keys]
    highs_g = [res_logit_grave["factores"][k]["ic95_sup"] for k in f_keys]
    qvals_g = [res_logit_grave["factores"][k]["q_fdr_bh"] for k in f_keys]

    axes[1].axvline(1.0, color="black", linestyle="--", linewidth=1)
    for idx_f, k in enumerate(f_keys):
        color_pt = "#c0392b" if qvals_g[idx_f] < 0.05 else "#7f8c8d"
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
        axes[1].text(
            max(highs_g[idx_f] * 1.08, ors_g[idx_f] * 1.15),
            idx_f,
            f"OR={ors_g[idx_f]:.2f} (q={qvals_g[idx_f]:.2g})",
            va="center",
            fontsize=7.5,
            color=color_pt,
        )

    axes[1].set_xscale("log")
    axes[1].set_yticks(y_f)
    axes[1].set_yticklabels([label_map_logit[k] for k in f_keys], fontsize=8.5)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("OR ajustadas (IC 95% nominales, q de Benjamini–Hochberg)")
    axes[1].set_title(
        f"B. Regresión logística de siniestro grave o fatal\n"
        f"({res_logit_grave['n_eventos']} eventos en {res_logit_grave['n_siniestros']} siniestros)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1].set_xlim(min(lows_g) * 0.65, max(highs_g) * 10.0)
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

    axes[0].plot(horas_rango, tot_hora, marker="o", linewidth=2.2, color="#2c3e50", label=f"Total siniestros (n={sum(tot_hora)})")
    axes[0].plot(horas_rango, vuln_hora, marker="s", linewidth=2.0, color="#d35400", label=f"Con peatón, moto o bici (n={sum(vuln_hora)})")
    axes[0].plot(horas_rango, choque_hora, marker="^", linewidth=1.8, color="#8e44ad", label=f"Tipología de choque (n={sum(choque_hora)})")
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
    axes[1].set_title("B. Causa registrada y severidad observada", fontsize=10.5, fontweight="bold")
    axes[1].legend(fontsize=8.5, loc="lower right")
    axes[1].grid(True, axis="x", alpha=0.25)
    axes[1].set_xlim(0, 95)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig04_perfiles_horarios_y_vulnerables.png", bbox_inches="tight")
    plt.close(fig)

    corr_json = corr_df.astype(object).where(corr_df.notna(), None)
    by_pair = corr_json.set_index(["variable_1", "variable_2"])
    alt_lon = by_pair.loc[("altitud_m", "longitud")]
    alt_temp = by_pair.loc[("altitud_m", "temp_c")]
    resumen = {
        "top_correlaciones_spearman": corr_json.head(20).to_dict(orient="records"),
        "asociaciones_significativas_p05": asoc_df[asoc_df["significativo_p05"]].to_dict(orient="records"),
        "resumen_asociaciones": {
            "pruebas": len(asoc_df),
            "estimables": int(asoc_df["estimable"].sum()),
            "significativas_p05": int(asoc_df["significativo_p05"].sum()),
            "significativas_fdr_bh_05": int(asoc_df["significativo_fdr_bh_05"].sum()),
            "significativas_holm_05": int(asoc_df["significativo_holm_05"].sum()),
        },
        "modelo_logistico_con_lesionados": res_logit_lesi,
        "modelo_logistico_grave_o_fatal": res_logit_grave,
        "sensibilidad_modelo_grave_o_fatal": sensibilidad,
        "gradiente_orografico_climatico": {
            "spearman_altitud_vs_longitud": alt_lon["spearman_rho"],
            "p_altitud_vs_longitud": alt_lon["p_spearman"],
            "spearman_altitud_vs_temperatura": alt_temp["spearman_rho"],
            "p_altitud_vs_temperatura": alt_temp["p_spearman"],
        },
        "desglose_causa_especifica": causa_grp.sort_values("n", ascending=False).to_dict(orient="records"),
    }

    with open(OUT_DIR / "02_resumen_correlaciones.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2, allow_nan=False)

    print(f"[02] Correlaciones calculadas: {len(corr_df)} pares guardados en {corr_csv_path.name}")
    print(f"[02] Asociaciones 2x2 significativas (p < 0.05): {int(asoc_df['significativo_p05'].sum())} de {len(asoc_df)}")
    return resumen


if __name__ == "__main__":
    main()

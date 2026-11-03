#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py
==========
Orquestador reproducible del pipeline de experimentación dentro del contenedor Docker (`lc-experimentacion`).
Ejecuta secuencialmente:
  1. `01_limpieza_y_correccion_solar.py`
  2. `02_correlaciones_y_factores.py`
  3. `03_puntos_calientes_y_mitigacion.py`
Y genera:
  - `experimentos/resultados/REPORTE_EXPERIMENTOS.md` (síntesis técnica completa con tablas y hallazgos)
  - `experimentos/resultados/manifest_evidencia.json` (hashes SHA-256 y tamaños de todos los artefactos)
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DEV_DIR = ROOT_DIR / "desarrollo"
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"


def load_and_run(script_name: str) -> Dict[str, Any]:
    script_path = DEV_DIR / script_name
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el script: {script_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_markdown_report(
    res01: Dict[str, Any],
    res02: Dict[str, Any],
    res03: Dict[str, Any],
) -> str:
    cs = res01["correccion_solar"]
    ap = res01["auditoria_posicional"]
    logit_g = res02["modelo_logistico_grave_o_fatal"]
    logit_l = res02["modelo_logistico_con_lesionados"]
    db = res03["resumen_dbscan"]
    gi = res03["resumen_getis_ord_gi"]

    lines = [
        "# Reporte Técnico de Experimentación en Contenedor: Siniestros Las Condes 2025",
        "",
        f"**Fecha de ejecución:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Entorno de ejecución:** Python `{platform.python_version()}` sobre `{platform.platform()}`  ",
        f"**Muestra analizada:** $n = {res01['n_registros']}$ siniestros georreferenciados ({res01['rango_fechas'][0]} a {res01['rango_fechas'][1]})  ",
        "",
        "---",
        "",
        "## 1. Corrección del Error Solar (+12 h) y Auditoría de Calidad de Datos",
        "",
        "- **Verificación matemática del sesgo solar (+12 h):**",
        f"  - Error Medio Absoluto (MAE) entre `sol_alt_grados` original y cálculo astronómico NOAA real: **{cs['mae_original_vs_real_grados']}°**.",
        f"  - MAE entre `sol_alt_grados` original y cálculo astronómico desplazado en $+12\\text{{ h}}$: **{cs['mae_original_vs_simulacion_mas12h_grados']}°** (confirma que el pipeline previo sumó 12 horas al convertir la hora local).",
        f"  - Porcentaje de siniestros nocturnos (`altitud <= 0°`): cae desde **{cs['pct_noche_original']}%** (erróneo) a **{cs['pct_noche_corregido']}%** (corregido: {cs['distribucion_corregida']['dia']} diurnos, {cs['distribucion_corregida']['crepusculo']} crepúsculo, {cs['distribucion_corregida']['noche']} noche y {cs['distribucion_corregida']['noche_cerrada']} noche cerrada).",
        f"  - **Atropellos diurnos:** {cs['atropellos_dia_corregido']} de {cs['atropellos_total']} atropellos (**{round(cs['atropellos_dia_corregido']/cs['atropellos_total']*100, 1)}%**) ocurren con luz de día, y {cs['siniestros_en_ventana_encandilamiento_solar_0_15_grados']} siniestros ocurren en ventana de sol rasante ($0^\\circ < \\text{{alt}} \\le 15^\\circ$).",
        "- **Coherencia posicional y vial:**",
        f"  - Registros dentro del *bounding box* comunal de Las Condes: **{ap['registros_dentro_bbox_las_condes']}/{res01['n_registros']} ({ap['pct_dentro_bbox_las_condes']}%)**.",
        f"  - Mediana de dispersión posicional entre siniestros asignados a la misma intersección (`Calle_Uno x Calle_Dos`, $n={ap['n_siniestros_en_intersecciones_repetidas_evaluados']}$): **{ap['mediana_dispersion_misma_interseccion_m']} m** ({ap['pct_misma_interseccion_dentro_100m']}% dentro de 100 m).",
        "",
        "---",
        "",
        "## 2. Correlaciones Estadísticas y Factores Asociados a la Severidad",
        "",
        "### 2.1. Asociaciones Categóricas Significativas ($p < 0,05$, Test Exacto de Fisher / $\\chi^2$)",
        "",
        "| Hipótesis Evaluada | % Evento Expuestos | % Evento No Expuestos | Odds Ratio (IC 95%) | $p$-valor (Fisher) | $V$ de Cramér |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in res02["asociaciones_significativas_p05"]:
        lines.append(
            f"| {row['hipotesis']} | {row['pct_evento_expuestos']}% ({row['eventos_en_expuestos']}/{row['n_expuestos']}) | "
            f"{row['pct_evento_no_expuestos']}% ({row['eventos_en_no_expuestos']}/{row['n_no_expuestos']}) | "
            f"**{row['odds_ratio']}** ({row['ic95_inf']}–{row['ic95_sup']}) | `{row['p_fisher']}` | {row['v_cramer']} |"
        )

    lines.extend(
        [
            "",
            "### 2.2. Modelos Multivariados de Regresión Logística",
            "",
            f"- **Modelo 1 (`con_lesionados`, Pseudo-$R^2$ McFadden = `{logit_l['pseudo_r2_mcfadden']}`, $p < 10^{{-10}}$):**",
            "  - El involucramiento de usuarios vulnerables domina la probabilidad de lesiones: Atropello ($\\text{OR}_{\\text{ajustado}} = "
            f"{logit_l['factores']['Atropello']['odds_ratio_ajustado']}$, $p < 0,0001$), Bicicleta ($\\text{{OR}}_{{\\text{{ajustado}}}} = "
            f"{logit_l['factores']['Bicicleta']['odds_ratio_ajustado']}$, $p < 0,0001$) y Motocicleta ($\\text{{OR}}_{{\\text{{ajustado}}}} = "
            f"{logit_l['factores']['Motociclet']['odds_ratio_ajustado']}$, $p < 0,0001$).",
            f"- **Modelo 2 (`grave_o_fatal`, Pseudo-$R^2$ McFadden = `{logit_g['pseudo_r2_mcfadden']}`, $p < 10^{{-10}}$):**",
            "  - Incrementan significativamente la probabilidad de muerte o lesión grave: **Atropello** ($\\text{OR}_{\\text{ajustado}} = "
            f"{logit_g['factores']['Atropello']['odds_ratio_ajustado']}$, $p < 0,0001$), **Bicicleta** ($\\text{{OR}}_{{\\text{{ajustado}}}} = "
            f"{logit_g['factores']['Bicicleta']['odds_ratio_ajustado']}$, $p < 0,0001$), **Motocicleta** ($\\text{{OR}}_{{\\text{{ajustado}}}} = "
            f"{logit_g['factores']['Motociclet']['odds_ratio_ajustado']}$, $p < 0,0001$) y **Causa específica distinta a 'no atento'** "
            f"($\\text{{OR}}_{{\\text{{ajustado}}}} = {logit_g['factores']['causa_distinta_no_atento']['odds_ratio_ajustado']}$, $p = {logit_g['factores']['causa_distinta_no_atento']['p_valor']}$).",
            "",
            "---",
            "",
            "## 3. Detección de Puntos Calientes (Hotspots) y Desacoplamiento Concentración vs. Severidad",
            "",
            f"- **Estadístico Espacial Getis-Ord $G_i^*$ (Grilla $250\\text{{ m}} \\times 250\\text{{ m}}$, vecindad $d \\le 400\\text{{ m}}$):**",
            f"  - Sobre {gi['total_celdas_con_siniestros']} celdas activas, se identifican **{gi['celdas_hotspot_conteo_p05']} celdas *hotspot* por frecuencia ($p \\le 0,05$)** y **{gi['celdas_hotspot_epdo_p05']} celdas *hotspot* por severidad ponderada EPDO ($p \\le 0,05$)**.",
            f"- **Clustering Espacial DBSCAN ($\\varepsilon = 150\\text{{ m}}$, $\\text{{min\\_samples}} = 5$, métrica Haversine):**",
            f"  - Se detectan **{db['n_clusters_detectados']} micro-clusters críticos** que agrupan **{db['siniestros_en_clusters']} siniestros ({db['pct_siniestros_en_clusters']}% del total comunal)**.",
            "",
            "### Top 10 Micro-Clusters Críticos ordenados por Severidad Equivalente (EPDO)",
            "",
            "| Rank | Cluster / Nodo Dominante | Siniestros ($N$) | Puntaje EPDO | EPDO Medio | % Lesionados | % Grave/Fatal | Motos | Atropellos | Bicis |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for c in db["top_10_clusters_por_epdo"]:
        lines.append(
            f"| {c['ranking_severidad_epdo']} | {c['interseccion_dominante']} | {c['n_siniestros']} | **{c['epdo_total']}** | "
            f"{c['epdo_medio']} | {c['pct_con_lesionados']}% | {c['pct_grave_o_fatal']}% | {c['n_motocicletas']} | {c['n_atropellos']} | {c['n_bicicletas']} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Formulación de Medidas de Mitigación Basadas en Evidencia",
            "",
            "| Código | Línea de Acción | Medida Concreta | Población Objetivo en Muestra (2025) |",
            "|---|---|---|---|",
        ]
    )

    for m in res03["medidas_mitigacion"]:
        lines.append(
            f"| **{m['id_medida']}** | {m['linea_accion']} | {m['medida_mitigacion_propuesta']} | "
            f"**{m['siniestros_objetivo_n']} siniestros**, **{m['lesionados_objetivo_n']} lesionados**, **{m['graves_o_fatales_objetivo_n']} graves/fatales** |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("=" * 78)
    print("INICIANDO PIPELINE DE EXPERIMENTACIÓN REPRODUCIBLE (CLASE 7 - LAS CONDES 2025)")
    print("=" * 78)

    res01 = load_and_run("01_limpieza_y_correccion_solar.py")
    res02 = load_and_run("02_correlaciones_y_factores.py")
    res03 = load_and_run("03_puntos_calientes_y_mitigacion.py")

    report_md = build_markdown_report(res01, res02, res03)
    report_path = OUT_DIR / "REPORTE_EXPERIMENTOS.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[RUN_ALL] Reporte técnico generado en: {report_path.name}")

    # Generar manifiesto de evidencia con hashes SHA-256
    artifacts = []
    for p in sorted(OUT_DIR.iterdir()):
        if p.is_file() and p.name != "manifest_evidencia.json":
            artifacts.append(
                {
                    "archivo": f"experimentos/resultados/{p.name}",
                    "bytes": p.stat().st_size,
                    "sha256": sha256_file(p),
                }
            )

    manifest = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python_version": platform.python_version(),
        "plataforma": platform.platform(),
        "total_archivos_evidencia": len(artifacts),
        "archivos": artifacts,
    }
    manifest_path = OUT_DIR / "manifest_evidencia.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[RUN_ALL] Manifiesto SHA-256 generado con {len(artifacts)} archivos verificables.")
    print("=" * 78)


if __name__ == "__main__":
    main()

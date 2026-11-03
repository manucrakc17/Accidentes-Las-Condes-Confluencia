#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_limpieza_y_correccion_solar.py
=================================
Paso 1 del pipeline de experimentación en contenedor (Clase 7):
1. Carga `datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx`.
2. Corrige el error sistemático de +12 horas en `sol_alt_grados`, `periodo_solar` y `noche`
   utilizando las ecuaciones astronómicas NOAA para la latitud/longitud exacta de cada siniestro
   y el huso horario oficial de Chile Continental en 2025 (UTC-3 verano / UTC-4 invierno).
3. Recalibra variables climáticas saturadas (`viento_cat_corr`, `visib_proxy_alerta`) y construye
   variables analíticas de morfología vial (`tipo_ubicacion_vial`), severidad ponderada (`indice_epdo`,
   `con_lesionados`, `grave_o_fatal`), usuario vulnerable (`usuario_vulnerable`) y desagregación de
   `CAUSA_SINI` frente al monolitismo de `CAUSA_NUEV`.
4. Audita la coherencia posicional (límites comunales, dispersión transversal de ejes e intersecciones).
5. Exporta el dataset corregido y el reporte JSON de auditoría a `experimentos/resultados/`.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, date, time as dt_time
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "datos" / "SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx"
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"


def chile_utc_offset_hours_2025(dt_local: datetime) -> int:
    """
    Retorna el offset UTC oficial de Chile Continental (America/Santiago) en 2025:
    - Horario de verano (CLST, UTC-3): hasta el primer sábado de abril (2025-04-05 23:59:59)
      y desde el primer sábado de septiembre (2025-09-06 00:00:00).
    - Horario de invierno (CLT, UTC-4): entre el 2025-04-06 y el 2025-09-06.
    """
    d = dt_local.date()
    if date(2025, 4, 6) <= d <= date(2025, 9, 6):
        return -4
    return -3


def parse_hora_to_minutes(hora_val: Any) -> float:
    """Convierte el valor de la columna Hora (string 'H:MM:SS' o datetime.time) a minutos desde medianoche."""
    if isinstance(hora_val, dt_time):
        return hora_val.hour * 60.0 + hora_val.minute + hora_val.second / 60.0
    s = str(hora_val).strip()
    parts = s.split(":")
    if len(parts) >= 2:
        hh = int(parts[0])
        mm = int(parts[1])
        ss = int(float(parts[2])) if len(parts) > 2 else 0
        return hh * 60.0 + mm + ss / 60.0
    return 0.0


def calc_solar_altitude_deg(
    dt_date: datetime,
    minutes_from_midnight: float,
    lat_deg: float,
    lon_deg: float,
    utc_offset_hours: int,
) -> float:
    """
    Calcula la altitud solar aparente (en grados sobre el horizonte) mediante
    las ecuaciones astronómicas NOAA (Spencer 1971 / Iqbal 1983).
    """
    doy = dt_date.timetuple().tm_yday
    hour_float = minutes_from_midnight / 60.0
    # Año fraccional en radianes
    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour_float - 12.0) / 24.0)

    # Ecuación del tiempo (en minutos)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2.0 * gamma)
        - 0.040849 * math.sin(2.0 * gamma)
    )

    # Declinación solar (en radianes)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2.0 * gamma)
        + 0.000907 * math.sin(2.0 * gamma)
        - 0.002697 * math.cos(3.0 * gamma)
        + 0.00148 * math.sin(3.0 * gamma)
    )

    # Tiempo solar verdadero (minutos) y ángulo horario (grados)
    time_offset = eqtime + 4.0 * lon_deg - 60.0 * utc_offset_hours
    tst = (minutes_from_midnight + time_offset) % 1440.0
    ha_deg = (tst / 4.0) - 180.0
    ha_rad = math.radians(ha_deg)
    lat_rad = math.radians(lat_deg)

    # Coseno del ángulo cenital solar
    sin_alt = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_deg = math.degrees(math.asin(sin_alt))
    return round(alt_deg, 2)


def classify_solar_period(alt_deg: float) -> Tuple[str, int, int]:
    """
    Clasifica el período solar según la altitud solar corregida:
    - 'dia': alt > 0°
    - 'crepusculo': -6° <= alt <= 0° (crepúsculo civil)
    - 'noche': -18° <= alt < -6° (crepúsculo náutico/astronómico)
    - 'noche_cerrada': alt < -18°
    Además retorna `noche_corr` (1 si alt <= 0°, 0 si día) y `sol_bajo_encandilamiento`
    (1 si 0° < alt <= 15°, ventana crítica de deslumbramiento solar rasante en ejes E-O).
    """
    if alt_deg > 0.0:
        periodo = "dia"
        noche_bin = 0
    elif alt_deg >= -6.0:
        periodo = "crepusculo"
        noche_bin = 1
    elif alt_deg >= -18.0:
        periodo = "noche"
        noche_bin = 1
    else:
        periodo = "noche_cerrada"
        noche_bin = 1

    encandilamiento = 1 if (0.0 < alt_deg <= 15.0) else 0
    return periodo, noche_bin, encandilamiento


def categorize_ubicacion(ubic: Any) -> str:
    """Agrupa `UBICACION` en categorías operativas de ingeniería de tránsito."""
    u = str(ubic).upper().strip()
    if "SEMAFORO APAGADO" in u:
        return "CRUCE_SEMAFORO_APAGADO"
    if "CRUCE CON SEMAFORO FUNCIONANDO" in u:
        return "CRUCE_SEMAFORIZADO"
    if "CRUCE CON SENAL" in u or "CRUCE SIN SENALIZACION" in u:
        return "CRUCE_PRIORIDAD_SENAL"
    if "ROTONDA" in u or "ENLACE" in u:
        return "ROTONDA_O_ENLACE"
    if "PASO PARA PEATONES" in u or "ACERA" in u or "CICLOVIA" in u:
        return "INFRAESTRUCTURA_PEATON_CICLO"
    if "TRAMO DE VIA RECTA" in u:
        return "TRAMO_RECTO"
    return "OTROS"


def categorize_causa_especifica(causa_sini: Any) -> str:
    """
    Desagrega `CAUSA_SINI` para superar el sesgo monolítico de `CAUSA_NUEV` (86.7% distracción).
    Separa la 'Conducción no atento' de las causas de maniobra, velocidad/distancia, derecho de paso,
    alcohol y peatón.
    """
    c = str(causa_sini).upper().strip()
    if "NO ATENTO" in c:
        return "NO_ATENTO_CONDICIONES_TRANSITO"
    if "CAMBIAR SORPRESIVAMENTE PISTA" in c or "ADELANTAMIENTO" in c or "VIRAJES" in c:
        return "MANIOBRA_PISTA_ADELANTAMIENTO_VIRAJE"
    if "DISTANCIA" in c or "FRENA DE MANERA BRUSCA" in c or "VELOCIDAD" in c:
        return "VELOCIDAD_O_DISTANCIA_SEGUIMIENTO"
    if "DERECHO PREFERENTE" in c or "LUZ ROJA" in c or "CEDA EL PASO" in c or "PARE" in c or "SENALIZACION" in c:
        return "VIOLACION_SEMAFORO_O_PREFERENCIA"
    if "EBRIEDAD" in c or "ALCOHOL" in c or "DROGAS" in c:
        return "ALCOHOL_EN_CONDUCTOR"
    if "PEATON" in c or "PASAJERO" in c:
        return "FACTOR_PEATON_O_PASAJERO"
    return "FALLA_MECANICA_U_OTRA"


def recalibrate_wind(viento_kmh: float, rafaga_kmh: float) -> str:
    """Recalibra la categoría de viento (reemplazando el 100% 'calma' defectuoso del archivo original)."""
    if viento_kmh < 2.0 and rafaga_kmh < 10.0:
        return "calma_real"
    if viento_kmh < 6.0 and rafaga_kmh < 18.0:
        return "brisa_leve"
    if viento_kmh < 12.0 and rafaga_kmh < 28.0:
        return "brisa_moderada"
    return "viento_fuerte_o_rafaga"


def main() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(DATA_PATH, sheet_name="Siniestros")

    # 1. Corrección astronómica solar (+12 h bug)
    alt_corr_list = []
    alt_plus12_list = []
    periodo_corr_list = []
    noche_corr_list = []
    encandilamiento_list = []
    minutos_dia_list = []
    hora_decimal_list = []

    for _, row in df.iterrows():
        dt_val = pd.to_datetime(row["FECHA"]).to_pydatetime()
        mins = parse_hora_to_minutes(row["Hora"])
        lat = float(row["Latitud"])
        lon = float(row["longitud"])
        tz_off = chile_utc_offset_hours_2025(dt_val)

        alt_real = calc_solar_altitude_deg(dt_val, mins, lat, lon, tz_off)
        # Calculamos también con +12 horas (720 minutos) para demostrar el origen exacto del bug
        alt_shifted_12h = calc_solar_altitude_deg(dt_val, (mins + 720.0) % 1440.0, lat, lon, tz_off)

        per_corr, noche_bin, encand = classify_solar_period(alt_real)

        alt_corr_list.append(alt_real)
        alt_plus12_list.append(alt_shifted_12h)
        periodo_corr_list.append(per_corr)
        noche_corr_list.append(noche_bin)
        encandilamiento_list.append(encand)
        minutos_dia_list.append(round(mins, 1))
        hora_decimal_list.append(round(mins / 60.0, 3))

    df["hora_decimal"] = hora_decimal_list
    df["sol_alt_grados_orig"] = df["sol_alt_grados"]
    df["periodo_solar_orig"] = df["periodo_solar"]
    df["noche_orig"] = df["noche"]

    df["sol_alt_grados_corr"] = alt_corr_list
    df["sol_alt_simulacion_mas12h"] = alt_plus12_list
    df["periodo_solar_corr"] = periodo_corr_list
    df["noche_corr"] = noche_corr_list
    df["sol_bajo_encandilamiento"] = encandilamiento_list

    # Verificación cuantitativa del bug de +12 h
    mae_vs_real = float(np.mean(np.abs(df["sol_alt_grados_orig"] - df["sol_alt_grados_corr"])))
    mae_vs_plus12h = float(np.mean(np.abs(df["sol_alt_grados_orig"] - df["sol_alt_simulacion_mas12h"])))

    # 2. Variables derivadas de severidad, vulnerabilidad, clima y vialidad
    df["con_lesionados"] = (df["TOTAL_LESI"] > 0).astype(int)
    df["grave_o_fatal"] = ((df["GRAVES"] + df["FALLECIDOS"]) > 0).astype(int)
    df["usuario_vulnerable"] = ((df["Atropello"] == 1) | (df["Bicicleta"] == 1) | (df["Motociclet"] == 1)).astype(int)

    # Índice de Severidad Equivalente (EPDO - Equivalent Property Damage Only, estándar PIARC/CONASET adaptado)
    # Fallecido = 12, Grave = 6, Menos Grave = 3, Leve = 2, Solo daños materiales = 1
    df["indice_epdo"] = (
        1
        + 11 * df["FALLECIDOS"]
        + 5 * df["GRAVES"]
        + 2 * df["MENOS_GRAV"]
        + 1 * df["LEVES"]
    )

    df["pavimento_adverso"] = (df["pavimento"].astype(str).str.lower() != "seco").astype(int)
    df["lluvia_reciente_24h"] = (df["preci_prev_24h"] > 0).astype(int)
    df["depresion_rocio_c"] = (df["temp_c"] - df["rocio_c"]).round(2)
    df["alta_humedad_80"] = (df["humedad_pct"] >= 80).astype(int)
    df["viento_cat_corr"] = [
        recalibrate_wind(float(v), float(r)) for v, r in zip(df["viento_kmh"], df["rafaga_kmh"])
    ]

    df["tipo_ubicacion_vial"] = df["UBICACION"].apply(categorize_ubicacion)
    df["es_cruce"] = df["tipo_ubicacion_vial"].str.startswith("CRUCE").astype(int)
    df["causa_especifica"] = df["CAUSA_SINI"].apply(categorize_causa_especifica)
    df["causa_distinta_no_atento"] = (df["causa_especifica"] != "NO_ATENTO_CONDICIONES_TRANSITO").astype(int)

    # Bloques horarios y día hábil
    dias_finde = {"Sábado", "Sabado", "Domingo", "Sbado"}
    df["es_fin_de_semana"] = df["Dia_semana"].astype(str).apply(
        lambda x: 1 if ("bado" in x.lower() or "domingo" in x.lower()) else 0
    )

    def clasificar_bloque_horario(h: float) -> str:
        if 7.0 <= h < 10.0:
            return "1_Punta_Manana_07_10"
        if 10.0 <= h < 14.0:
            return "2_Media_Manana_10_14"
        if 14.0 <= h < 17.0:
            return "3_Tarde_14_17"
        if 17.0 <= h < 21.0:
            return "4_Punta_Tarde_17_21"
        if 21.0 <= h < 24.0:
            return "5_Noche_21_24"
        return "0_Madrugada_00_07"

    df["bloque_horario"] = df["hora_decimal"].apply(clasificar_bloque_horario)
    df["en_hora_punta"] = df["bloque_horario"].isin(["1_Punta_Manana_07_10", "4_Punta_Tarde_17_21"]).astype(int)
    df["zona_alta_precordillera"] = (df["altitud_m"] >= 750).astype(int)

    # Normalización de calles e intersecciones
    def normalize_street(s: Any) -> str:
        val = str(s).strip().upper()
        if val in ("", "NAN", "NONE"):
            return ""
        val = val.replace("PDTE.", "PRESIDENTE").replace("PDTE ", "PRESIDENTE ")
        val = val.replace("GRAL.", "GENERAL").replace("GRAL ", "GENERAL ")
        if val == "PRESIDENTE KENNEDY LATERAL":
            return "PRESIDENTE KENNEDY (CALETERA)"
        return val

    df["Calle_Uno_norm"] = df["Calle_Uno"].apply(normalize_street)
    df["Calle_Dos_norm"] = df["Calle_Dos"].apply(normalize_street)
    intersecciones = []
    for c1, c2 in zip(df["Calle_Uno_norm"], df["Calle_Dos_norm"]):
        if c2 and c2 not in ("", "NAN", "NONE"):
            pair = sorted([c1, c2])
            intersecciones.append(f"{pair[0]} x {pair[1]}")
        else:
            intersecciones.append(f"{c1} (TRAMO)")
    df["nodo_vial"] = intersecciones

    # 3. Auditoría de exactitud/coherencia posicional (Crítica #1 del Critic)
    # Verificamos:
    # a) Todos los puntos dentro del bounding box comunal de Las Condes
    in_bbox = (
        (df["Latitud"] >= -33.48)
        & (df["Latitud"] <= -33.36)
        & (df["longitud"] >= -70.62)
        & (df["longitud"] <= -70.49)
    )
    # b) Consistencia de intersecciones repetidas: distancia al centroide de la misma intersección (Calle_Uno x Calle_Dos)
    nodos_con_par = df[df["Calle_Dos_norm"].apply(lambda x: len(x) > 1 and x != "NAN")].copy()
    dist_interseccion_m = []
    for nodo, grp in nodos_con_par.groupby("nodo_vial"):
        if len(grp) >= 2:
            lat_mean = grp["Latitud"].mean()
            lon_mean = grp["longitud"].mean()
            for _, r in grp.iterrows():
                dy = (r["Latitud"] - lat_mean) * 111320.0
                dx = (r["longitud"] - lon_mean) * 111320.0 * math.cos(math.radians(lat_mean))
                dist_interseccion_m.append(math.hypot(dx, dy))

    dist_series = pd.Series(dist_interseccion_m)
    pct_interseccion_menor_100m = float((dist_series <= 100.0).mean() * 100.0) if len(dist_series) else 0.0
    mediana_dispersion_interseccion_m = float(dist_series.median()) if len(dist_series) else 0.0

    # Guardar CSV corregido
    out_csv = OUT_DIR / "SINIESTROS_LAS_CONDES_CORREGIDO.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")

    # Figura 01: Impacto de la corrección solar (+12 h)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), dpi=160)

    # Panel A: Serie horaria de altitud solar original vs corregida
    axes[0].scatter(df["hora_decimal"], df["sol_alt_grados_orig"], alpha=0.35, s=16, color="#d95f02", label="Original (+12 h erróneo)")
    axes[0].scatter(df["hora_decimal"], df["sol_alt_grados_corr"], alpha=0.35, s=16, color="#1b9e77", label="Corregido (Astronómico NOAA)")
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("A. Altitud Solar vs. Hora Local (Las Condes 2025)", fontsize=10, fontweight="bold")
    axes[0].set_xlabel("Hora local del siniestro (0–24 h)")
    axes[0].set_ylabel("Altitud solar (°)")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(True, alpha=0.25)

    # Panel B: Distribución por período solar antes y después
    cats = ["dia", "crepusculo", "noche", "noche_cerrada"]
    labels_cat = ["Día\n(>0°)", "Crepúsculo\n(-6° a 0°)", "Noche\n(-18° a -6°)", "Noche cerrada\n(<-18°)"]
    orig_counts = [int((df["periodo_solar_orig"] == c).sum()) for c in cats]
    corr_counts = [int((df["periodo_solar_corr"] == c).sum()) for c in cats]
    x = np.arange(len(cats))
    w = 0.36
    b1 = axes[1].bar(x - w / 2, orig_counts, width=w, color="#e74c3c", alpha=0.85, label="Archivo original (69.4% noche)")
    b2 = axes[1].bar(x + w / 2, corr_counts, width=w, color="#2980b9", alpha=0.90, label=f"Corregido ({round((1 - corr_counts[0]/len(df))*100, 1)}% noche)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels_cat, fontsize=8.5)
    axes[1].set_title("B. Inversión de la distribución Día/Noche (n=676)", fontsize=10, fontweight="bold")
    axes[1].set_ylabel("Número de siniestros")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, axis="y", alpha=0.25)
    for bars in (b1, b2):
        for bar in bars:
            h_val = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2, h_val + 6, f"{int(h_val)}", ha="center", va="bottom", fontsize=7.5)
    axes[1].set_ylim(0, max(corr_counts) * 1.15)

    # Panel C: Atropellos (n=42) por período solar corregido
    atrop = df[df["Atropello"] == 1]
    atrop_orig = [int((atrop["periodo_solar_orig"] == c).sum()) for c in cats]
    atrop_corr = [int((atrop["periodo_solar_corr"] == c).sum()) for c in cats]
    b3 = axes[2].bar(x - w / 2, atrop_orig, width=w, color="#e67e22", alpha=0.85, label="Original")
    b4 = axes[2].bar(x + w / 2, atrop_corr, width=w, color="#27ae60", alpha=0.90, label="Corregido")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels_cat, fontsize=8.5)
    axes[2].set_title("C. Atropellos (n=42) según iluminación solar", fontsize=10, fontweight="bold")
    axes[2].set_ylabel("Número de atropellos")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, axis="y", alpha=0.25)
    for bars in (b3, b4):
        for bar in bars:
            h_val = bar.get_height()
            axes[2].text(bar.get_x() + bar.get_width() / 2, h_val + 0.5, f"{int(h_val)}", ha="center", va="bottom", fontsize=7.5)
    axes[2].set_ylim(0, max(atrop_corr) * 1.2)

    plt.tight_layout()
    fig_path = OUT_DIR / "fig01_correccion_solar_impacto.png"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)

    auditoria = {
        "n_registros": int(len(df)),
        "rango_fechas": [str(df["FECHA"].min())[:10], str(df["FECHA"].max())[:10]],
        "correccion_solar": {
            "mae_original_vs_real_grados": round(mae_vs_real, 2),
            "mae_original_vs_simulacion_mas12h_grados": round(mae_vs_plus12h, 2),
            "distribucion_original": {c: int((df["periodo_solar_orig"] == c).sum()) for c in cats},
            "distribucion_corregida": {c: int((df["periodo_solar_corr"] == c).sum()) for c in cats},
            "pct_noche_original": round(float(df["noche_orig"].mean() * 100.0), 2),
            "pct_noche_corregido": round(float(df["noche_corr"].mean() * 100.0), 2),
            "siniestros_en_ventana_encandilamiento_solar_0_15_grados": int(df["sol_bajo_encandilamiento"].sum()),
            "atropellos_dia_corregido": int((atrop["periodo_solar_corr"] == "dia").sum()),
            "atropellos_total": int(len(atrop)),
        },
        "auditoria_posicional": {
            "registros_dentro_bbox_las_condes": int(in_bbox.sum()),
            "pct_dentro_bbox_las_condes": round(float(in_bbox.mean() * 100.0), 2),
            "n_siniestros_en_intersecciones_repetidas_evaluados": int(len(dist_series)),
            "mediana_dispersion_misma_interseccion_m": round(mediana_dispersion_interseccion_m, 2),
            "pct_misma_interseccion_dentro_100m": round(pct_interseccion_menor_100m, 2),
            "distribucion_tipo_ubicacion_vial": df["tipo_ubicacion_vial"].value_counts().to_dict(),
        },
        "recalibracion_variables": {
            "viento_cat_original": df["viento_cat"].value_counts().to_dict(),
            "viento_cat_corregida": df["viento_cat_corr"].value_counts().to_dict(),
            "causa_nuev_original": df["CAUSA_NUEV"].value_counts().to_dict(),
            "causa_especifica_desagregada": df["causa_especifica"].value_counts().to_dict(),
        },
    }

    json_path = OUT_DIR / "01_auditoria_calidad_y_solar.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(auditoria, f, ensure_ascii=False, indent=2)

    print(f"[01] Dataset corregido guardado en: {out_csv}")
    print(f"[01] MAE solar original vs real: {mae_vs_real:.2f}° | vs +12h: {mae_vs_plus12h:.2f}°")
    print(f"[01] Noche original: {auditoria['correccion_solar']['pct_noche_original']}% -> Corregido: {auditoria['correccion_solar']['pct_noche_corregido']}%")
    return auditoria


if __name__ == "__main__":
    main()

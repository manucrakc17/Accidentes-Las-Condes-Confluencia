#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida el Excel, recalcula la posición solar y exporta una auditoría agregada."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, time as dt_time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Any, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pyproj import Transformer
from shapely import covers, distance, points, transform
from shapely.geometry import shape

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "datos" / "SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx"
LIMITE_PATH = ROOT_DIR / "datos" / "las_condes_ciren.geojson"
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"
PRIVATE_DIR = ROOT_DIR / "experimentos" / "privado"
PRIVATE_CSV_NAME = "SINIESTROS_LAS_CONDES_CORREGIDO.csv"


def parse_hora_to_minutes(hora_val: Any) -> float:
    if not isinstance(hora_val, dt_time):
        match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?", str(hora_val).strip())
        if match is None:
            raise ValueError("Hora inválida en el Excel. Se requiere una hora local de 24 horas.")
        hour, minute, second, fraction = match.groups()
        hora_val = dt_time(int(hour), int(minute), int(second or "0"), int((fraction or "").ljust(6, "0")))
    if hora_val.tzinfo is not None:
        raise ValueError("Hora debe estar expresada en hora local sin zona horaria.")
    return hora_val.hour * 60 + hora_val.minute + (hora_val.second + hora_val.microsecond / 1e6) / 60


def medir_pertenencia_comunal(lon: pd.Series, lat: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    geojson = json.loads(LIMITE_PATH.read_text(encoding="utf-8"))
    features = geojson["features"]
    if len(features) != 1 or features[0]["properties"]["codcom"] != "13114":
        raise ValueError("El GeoJSON debe contener el límite comunal de Las Condes (13114).")
    polygon = shape(features[0]["geometry"])
    if polygon.geom_type not in ("Polygon", "MultiPolygon") or polygon.is_empty or not polygon.is_valid:
        raise ValueError("El límite comunal debe ser un polígono válido y no vacío.")
    projection = Transformer.from_crs("EPSG:4326", "EPSG:32719", always_xy=True).transform
    boundary = transform(polygon, projection, interleaved=False)
    x, y = projection(lon.to_numpy(), lat.to_numpy())
    sites = points(x, y)
    return covers(boundary, sites), distance(boundary, sites)


def calc_solar_altitude_deg(
    dt_date: datetime,
    minutes_from_midnight: float,
    lat_deg: float,
    lon_deg: float,
    utc_offset_hours: float,
) -> float:
    """
    Aproxima la elevación solar geométrica mediante las ecuaciones NOAA.
    """
    doy = dt_date.timetuple().tm_yday
    hour_float = minutes_from_midnight / 60.0
    # Año fraccional en radianes
    gamma = 2.0 * math.pi / (366 if pd.Timestamp(dt_date).is_leap_year else 365) * (doy - 1 + (hour_float - 12.0) / 24.0)

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
    (1 si 0° < alt <= 15°, indicador geométrico de sol bajo).
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
    if "CRUCE CON SENAL" in u:
        return "CRUCE_PRIORIDAD_SENAL"
    if "CRUCE SIN SENALIZACION" in u:
        return "CRUCE_SIN_SENALIZACION"
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
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Coloca una copia autorizada del Excel en {DATA_PATH.relative_to(ROOT_DIR)}.")
    df = pd.read_excel(DATA_PATH, sheet_name="Siniestros")
    originales = [c for c in df.columns if c not in ("ID", "FID")]
    redundantes = int(df.duplicated(subset=originales).sum())
    numeric = [
        "Latitud", "longitud", "sol_alt_grados", "noche", "TOTAL_LESI", "GRAVES", "FALLECIDOS",
        "MENOS_GRAV", "LEVES", "Atropello", "Bicicleta", "Motociclet", "preci_prev_24h",
        "temp_c", "rocio_c", "humedad_pct", "viento_kmh", "rafaga_kmh", "altitud_m",
        "precip_hora_mm", "horas_lluvia_24h", "nubosidad_pct", "niebla",
    ]
    text = ["ID", "FECHA", "Hora", "COMUNA", "periodo_solar", "pavimento", "UBICACION", "CAUSA_SINI",
            "Calle_Uno", "Calle_Dos", "CAUSA_NUEV", "viento_cat", "TIPO_SINIE", "TIPO__CONA", "Zonas_urb_"]
    missing = set(numeric + text) - set(df.columns)
    if missing:
        raise ValueError(f"Columnas requeridas ausentes: {', '.join(sorted(missing))}")
    if df.empty or df[text].drop(columns=["Calle_Dos"]).isna().any().any() or not df["ID"].is_unique:
        raise ValueError("Se requieren registros con identificador único y campos de análisis completos.")
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(df[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Hay valores numéricos faltantes o no finitos.")
    if not (df["Latitud"].between(-90, 90) & df["longitud"].between(-180, 180)).all():
        raise ValueError("Coordenadas fuera del rango geográfico WGS84.")
    injuries = df[["FALLECIDOS", "GRAVES", "MENOS_GRAV", "LEVES", "TOTAL_LESI"]]
    if not (injuries.ge(0) & injuries.mod(1).eq(0)).all().all() or not (
        df[["GRAVES", "MENOS_GRAV", "LEVES"]].sum(axis=1).eq(df["TOTAL_LESI"]).all()
    ):
        raise ValueError("Los recuentos de personas deben ser enteros no negativos y las lesiones deben cuadrar.")
    if not df[["Atropello", "Bicicleta", "Motociclet", "noche", "niebla"]].isin([0, 1]).all().all():
        raise ValueError("Los indicadores de modalidad, noche y niebla deben ser 0 o 1.")
    fechas = pd.to_datetime(df["FECHA"], errors="raise").dt.normalize()
    comuna = df["COMUNA"].astype(str).str.strip().str.casefold()
    if (
        fechas.isna().any() or not fechas.dt.year.eq(2025).all()
        or not df["Zonas_urb_"].eq("Urbano").all() or not comuna.eq("las condes").all()
    ):
        raise ValueError("Se requieren registros de Las Condes en 2025 con Zonas_urb_ igual a Urbano.")
    for name in ("Calle_Uno", "Calle_Dos"):
        if df[name].dropna().astype(str).str.strip().str.match(r"^[=+@＝＋＠－-]").any():
            raise ValueError("Hay etiquetas de vía con prefijos incompatibles con la exportación a CSV.")
    minutos = df["Hora"].map(parse_hora_to_minutes)
    local = (fechas + pd.to_timedelta(minutos, unit="m").dt.round("us")).dt.tz_localize(
        ZoneInfo("America/Santiago"), ambiguous="raise", nonexistent="raise"
    )
    df["FECHA"] = fechas.dt.strftime("%Y-%m-%d")
    df["Hora"] = df["Hora"].astype(str).str.strip()

    # 1. Corrección astronómica solar (+12 h bug)
    alt_corr_list = []
    alt_plus12_list = []
    periodo_corr_list = []
    noche_corr_list = []
    encandilamiento_list = []
    for dt_val, mins, lat, lon in zip(local, minutos, df["Latitud"], df["longitud"], strict=True):
        tz_off = dt_val.utcoffset().total_seconds() / 3600

        alt_real = calc_solar_altitude_deg(dt_val, mins, lat, lon, tz_off)
        # La comparación modular reproduce la fase opuesta dentro del mismo día civil.
        alt_shifted_12h = calc_solar_altitude_deg(dt_val, (mins + 720.0) % 1440.0, lat, lon, tz_off)

        per_corr, noche_bin, encand = classify_solar_period(alt_real)

        alt_corr_list.append(alt_real)
        alt_plus12_list.append(alt_shifted_12h)
        periodo_corr_list.append(per_corr)
        noche_corr_list.append(noche_bin)
        encandilamiento_list.append(encand)

    df["hora_decimal"] = minutos / 60
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
    df["lesion_o_muerte"] = ((df["TOTAL_LESI"] + df["FALLECIDOS"]) > 0).astype(int)
    df["grave_o_fatal"] = ((df["GRAVES"] + df["FALLECIDOS"]) > 0).astype(int)
    df["usuario_vulnerable"] = ((df["Atropello"] == 1) | (df["Bicicleta"] == 1) | (df["Motociclet"] == 1)).astype(int)

    # Puntaje histórico del estudio. La ponderación por peor consecuencia se compara en el paso 03.
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
    df["es_fin_de_semana"] = fechas.dt.day_of_week.ge(5).astype(int)

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

    dentro, metros = medir_pertenencia_comunal(df["longitud"], df["Latitud"])
    df["dentro_limite_comunal"] = dentro
    df["distancia_limite_comunal_m"] = np.round(metros, 2)
    nodos_con_par = df[df["Calle_Uno_norm"].ne("") & df["Calle_Dos_norm"].ne("")]
    rows_per_node = nodos_con_par.groupby("nodo_vial").size()
    nodos_repetidos = rows_per_node[rows_per_node.gt(1)]
    coords_per_node = nodos_con_par.drop_duplicates(["nodo_vial", "Latitud", "longitud"]).groupby("nodo_vial").size()
    out_csv = PRIVATE_DIR / PRIVATE_CSV_NAME
    with NamedTemporaryFile(dir=PRIVATE_DIR, mode="w", encoding="utf-8", newline="", delete=False) as csv_temporal:
        csv_path = Path(csv_temporal.name)
        try:
            df.to_csv(csv_temporal, index=False)
            csv_temporal.close()
            csv_path.replace(out_csv)
        finally:
            csv_path.unlink(missing_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), dpi=160)

    por_hora = df.groupby(np.floor(df["hora_decimal"]).astype(int))[["sol_alt_grados_orig", "sol_alt_grados_corr"]]
    medias = por_hora.mean().loc[por_hora.size().ge(5)].reindex(range(24))
    axes[0].plot(medias.index, medias["sol_alt_grados_orig"], color="#d95f02", label="Original")
    axes[0].plot(medias.index, medias["sol_alt_grados_corr"], color="#1b9e77", label="Corregida (NOAA)")
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("A. Elevación solar media por hora (n ≥ 5 por hora)", fontsize=10, fontweight="bold")
    axes[0].set_xlabel("Hora local (0–23 h)")
    axes[0].set_ylabel("Elevación solar (°)")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(True, alpha=0.25)

    # Panel B: Distribución por período solar antes y después
    cats = ["dia", "crepusculo", "noche", "noche_cerrada"]
    labels_cat = ["Día\n(>0°)", "Crepúsculo\n(-6° a 0°)", "Noche\n(-18° a -6°)", "Noche cerrada\n(<-18°)"]
    periodo_original_comparable = df["sol_alt_grados_orig"].map(lambda alt: classify_solar_period(alt)[0])
    n_noche_original = int(df["sol_alt_grados_orig"].le(0).sum())
    n_noche_corr = int(df["noche_corr"].sum())
    pct_original = round(100 * n_noche_original / len(df), 2)
    pct_corr = round(100 * n_noche_corr / len(df), 2)
    orig_counts = [int(periodo_original_comparable.eq(c).sum()) for c in cats]
    corr_counts = [int((df["periodo_solar_corr"] == c).sum()) for c in cats]
    x = np.arange(len(cats))
    w = 0.36
    b1 = axes[1].bar(x - w / 2, orig_counts, width=w, color="#e74c3c", alpha=0.85, label=f"Original: {pct_original:.1f}% ≤ 0°")
    b2 = axes[1].bar(x + w / 2, corr_counts, width=w, color="#2980b9", alpha=0.90, label=f"Corregida: {pct_corr:.1f}% ≤ 0°")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels_cat, fontsize=8.5)
    axes[1].set_title(f"B. Período solar con umbrales comunes (n={len(df)})", fontsize=10, fontweight="bold")
    axes[1].set_ylabel("Número de siniestros")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, axis="y", alpha=0.25)
    for bars in (b1, b2):
        for bar in bars:
            h_val = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2, h_val + 6, f"{int(h_val)}", ha="center", va="bottom", fontsize=7.5)
    axes[1].set_ylim(0, max(orig_counts + corr_counts) * 1.15)

    atrop = df[df["Atropello"] == 1]
    atrop_orig = [int(periodo_original_comparable.loc[atrop.index].eq(c).sum()) for c in cats]
    atrop_corr = [int((atrop["periodo_solar_corr"] == c).sum()) for c in cats]
    b3 = axes[2].bar(x - w / 2, atrop_orig, width=w, color="#e67e22", alpha=0.85, label="Original")
    b4 = axes[2].bar(x + w / 2, atrop_corr, width=w, color="#27ae60", alpha=0.90, label="Corregido")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels_cat, fontsize=8.5)
    axes[2].set_title(f"C. Atropellos por período solar (n={len(atrop)})", fontsize=10, fontweight="bold")
    axes[2].set_ylabel("Número de atropellos")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, axis="y", alpha=0.25)
    for bars in (b3, b4):
        for bar in bars:
            h_val = bar.get_height()
            axes[2].text(bar.get_x() + bar.get_width() / 2, h_val + 0.5, f"{int(h_val)}", ha="center", va="bottom", fontsize=7.5)
    axes[2].set_ylim(0, max(atrop_orig + atrop_corr + [1]) * 1.2)

    plt.tight_layout()
    fig_path = OUT_DIR / "fig01_correccion_solar_impacto.png"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)

    auditoria = {
        "n_registros": int(len(df)),
        "rango_fechas": [str(df["FECHA"].min())[:10], str(df["FECHA"].max())[:10]],
        "desenlaces": {
            "personas_lesionadas": int(df["TOTAL_LESI"].sum()),
            "personas_fallecidas": int(df["FALLECIDOS"].sum()),
            "siniestros_con_lesionados": int(df["con_lesionados"].sum()),
            "siniestros_con_lesion_o_muerte": int(df["lesion_o_muerte"].sum()),
            "siniestros_graves_o_fatales": int(df["grave_o_fatal"].sum()),
            "siniestros_con_usuarios_vulnerables": int(df["usuario_vulnerable"].sum()),
            "graves_o_fatales_con_usuarios_vulnerables": int(df.loc[df["usuario_vulnerable"].eq(1), "grave_o_fatal"].sum()),
        },
        "coincidencia_proxy_pavimento_lluvia_24h_n": int(df["pavimento_adverso"].eq(df["lluvia_reciente_24h"]).sum()),
        "correccion_solar": {
            "mae_original_vs_real_grados": round(mae_vs_real, 2),
            "mae_original_vs_simulacion_mas12h_grados": round(mae_vs_plus12h, 2),
            "distribucion_original": dict(zip(cats, orig_counts, strict=True)),
            "distribucion_corregida": {c: int((df["periodo_solar_corr"] == c).sum()) for c in cats},
            "umbral_noche_incluye_crepusculo_grados": 0,
            "n_noche_original": n_noche_original,
            "n_noche_corregida": n_noche_corr,
            "pct_noche_original": pct_original,
            "pct_noche_original_indicador_fuente": round(float(df["noche_orig"].mean() * 100.0), 2),
            "pct_noche_corregido": pct_corr,
            "siniestros_con_sol_bajo_0_15_grados": int(df["sol_bajo_encandilamiento"].sum()),
            "siniestros_en_ventana_encandilamiento_solar_0_15_grados": int(df["sol_bajo_encandilamiento"].sum()),
            "atropellos_dia_corregido": int((atrop["periodo_solar_corr"] == "dia").sum()),
            "atropellos_total": int(len(atrop)),
        },
        "auditoria_posicional": {
            "fuente_limite": "CIREN, codcom 13114. Versión histórica de 2025 no documentada.",
            "registros_dentro_limite_ciren": int(dentro.sum()),
            "registros_fuera_limite_ciren": int((~dentro).sum()),
            "externos_hasta_50_m": int(((~dentro) & (metros <= 50)).sum()),
            "distancia_maxima_fuera_limite_m": round(float(metros.max()), 2),
            "n_siniestros_en_intersecciones_repetidas_evaluados": int(nodos_repetidos.sum()),
            "n_intersecciones_repetidas": int(len(nodos_repetidos)),
            "n_intersecciones_repetidas_coordenada_unica": int(coords_per_node.loc[nodos_repetidos.index].eq(1).sum()),
            "filas_redundantes_candidatas_sin_id_fid": redundantes,
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

    print(f"[01] Dataset corregido guardado en el directorio privado ({out_csv.name}).")
    print(f"[01] MAE solar original vs real: {mae_vs_real:.2f}° | vs +12h: {mae_vs_plus12h:.2f}°")
    print(f"[01] Noche original: {auditoria['correccion_solar']['pct_noche_original']}% -> Corregido: {auditoria['correccion_solar']['pct_noche_corregido']}%")
    return auditoria


if __name__ == "__main__":
    main()

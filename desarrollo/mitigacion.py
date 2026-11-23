"""Selecciona poblaciones para evaluar medidas candidatas, con unidades explícitas."""

from __future__ import annotations

import pandas as pd

CORREDORES_MOTO = {"APOQUINDO", "LAS CONDES", "CRISTOBAL COLON", "MANQUEHUE SUR"}
CORREDORES_CRUCE = CORREDORES_MOTO | {"PRESIDENTE RIESCO"}
CORREDORES_CALZADA = {"PRESIDENTE KENNEDY", "LAS CONDES", "PADRE HURTADO", "CAMINO EL ALBA", "SAN CARLOS DE APOQUINDO"}
CORREDORES_PEATON = {"APOQUINDO", "LAS CONDES"}
GLOSA_GENERICA = "NO_ATENTO_CONDICIONES_TRANSITO"

CANDIDATAS = {
    "MIT-01": {
        "linea_accion": "Protección de cruces semaforizados",
        "focalizacion_espacial_temporal": "Siniestros con usuarios vulnerables en cruces con dos calles identificadas y semáforo activo. Apoquindo, Las Condes, Cristóbal Colón, Manquehue Sur o Presidente Riesco como una de las calles. Lunes a viernes, 07:00–10:00 o 17:00–21:00.",
        "medida_mitigacion_propuesta": "Auditar fases y conflictos de viraje para evaluar una fase peatonal anticipada o ajustes de canalización donde proceda.",
        "indicador_verificacion_impacto": "Conflictos de viraje por cruce peatonal y siniestros con peatones en cruces intervenidos y comparables.",
    },
    "MIT-02": {
        "linea_accion": "Conflictos viales con motocicletas",
        "focalizacion_espacial_temporal": "Siniestros con motocicleta en Apoquindo, Las Condes, Cristóbal Colón o Manquehue Sur, como una de las calles registradas. Todos los días, 12:00–21:00.",
        "medida_mitigacion_propuesta": "Observar virajes y cambios de pista para evaluar demarcación y canalización de conflictos laterales.",
        "indicador_verificacion_impacto": "Conflictos laterales y siniestros por volumen observado de motocicletas en los tramos evaluados.",
    },
    "MIT-03": {
        "linea_accion": "Choques de noche durante el fin de semana",
        "focalizacion_espacial_temporal": "Registros de categoría CHOQUE de CONASET en toda la base. Viernes o sábado desde las 22:00 y sábado o domingo antes de las 06:00.",
        "medida_mitigacion_propuesta": "Revisar partes, iluminación e infraestructura antes de evaluar delineación o protección de obstáculos donde se documenten.",
        "indicador_verificacion_impacto": "Choques de la tipología verificada por exposición nocturna en lugares intervenidos y comparables.",
    },
    "MIT-04": {
        "linea_accion": "Pavimento adverso estimado en sectores altos",
        "focalizacion_espacial_temporal": "Siniestros con pavimento adverso estimado y cota de al menos 750 m, de mayo a agosto, en Presidente Kennedy, Las Condes, Padre Hurtado, Camino El Alba o San Carlos de Apoquindo como una de las calles.",
        "medida_mitigacion_propuesta": "Medir fricción, pendiente y drenaje en terreno para evaluar tratamiento de alta fricción u otras soluciones donde proceda.",
        "indicador_verificacion_impacto": "Siniestros comparables por exposición en condiciones húmedas medidas y fricción de la calzada antes y después.",
    },
    "MIT-05": {
        "linea_accion": "Cruces peatonales en ejes con atropellos diurnos",
        "focalizacion_espacial_temporal": "Atropellos con el sol sobre el horizonte en Apoquindo o Las Condes como una de las calles. Lunes a viernes, 08:00–19:00.",
        "medida_mitigacion_propuesta": "Auditar maniobras, visibilidad y recorridos peatonales para evaluar cruces elevados, refugios u otras mejoras de cruce.",
        "indicador_verificacion_impacto": "Conflictos y atropellos diurnos por volumen peatonal en sitios comparables.",
    },
    "MIT-06": {
        "linea_accion": "Calidad del registro de causas y ubicación",
        "focalizacion_espacial_temporal": "Registros con la glosa genérica «no atento a las condiciones del tránsito» en la base analizada.",
        "medida_mitigacion_propuesta": "Revisar el protocolo de codificación y evaluar una pauta que registre maniobras, condiciones y precisión geográfica con categorías de desconocido.",
        "indicador_verificacion_impacto": "Proporción de glosas genéricas, concordancia entre revisores y exactitud de ubicación contrastada con el lugar del siniestro.",
    },
}


def construir_matriz(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Devuelve la matriz agregada y la cobertura conjunta sobre siniestros registrados."""
    fecha = pd.to_datetime(df["FECHA"], format="%Y-%m-%d")
    ventana_hora = df["Hora"].astype(str).str.extract(
        r"^([01]?[0-9]|2[0-3]):[0-5]?[0-9](?::[0-5]?[0-9](?:\.[0-9]+)?)?$", expand=False
    )
    if fecha.isna().any() or ventana_hora.isna().any():
        raise ValueError("La matriz de mitigación requiere una fecha y una hora local válidas por siniestro")

    hora = ventana_hora.astype(int)
    dia = fecha.dt.day_of_week
    lunes_a_viernes = dia.lt(5)
    punta = hora.between(7, 10, inclusive="left") | hora.between(17, 21, inclusive="left")
    turno_fin_de_semana = (dia.isin((4, 5)) & hora.ge(22)) | (dia.isin((5, 6)) & hora.lt(6))
    primera_calle = df["Calle_Uno_norm"].fillna("")
    segunda_calle = df["Calle_Dos_norm"].fillna("")
    interseccion_identificada = primera_calle.ne("") & segunda_calle.ne("") & primera_calle.ne(segunda_calle)

    def en_corredor(calles: set[str]) -> pd.Series:
        return primera_calle.isin(calles) | segunda_calle.isin(calles)

    filtros = {
        "MIT-01": (
            df["usuario_vulnerable"].eq(1) & df["tipo_ubicacion_vial"].eq("CRUCE_SEMAFORIZADO")
            & interseccion_identificada & en_corredor(CORREDORES_CRUCE) & lunes_a_viernes & punta
        ),
        "MIT-02": df["Motociclet"].eq(1) & en_corredor(CORREDORES_MOTO) & hora.between(12, 21, inclusive="left"),
        "MIT-03": df["TIPO__CONA"].eq("CHOQUE") & turno_fin_de_semana,
        "MIT-04": (
            df["pavimento_adverso"].eq(1) & df["altitud_m"].ge(750)
            & fecha.dt.month.between(5, 8) & en_corredor(CORREDORES_CALZADA)
        ),
        "MIT-05": (
            df["Atropello"].eq(1) & df["sol_alt_grados_corr"].gt(0)
            & en_corredor(CORREDORES_PEATON) & lunes_a_viernes & hora.between(8, 19, inclusive="left")
        ),
        "MIT-06": df["causa_especifica"].eq(GLOSA_GENERICA),
    }
    selecciones = pd.DataFrame(filtros).sum(axis=1)
    filas = []
    for medida, filtro in filtros.items():
        casos = df.loc[filtro]
        eventos = len(casos)
        eventos_con_lesionados = int(casos["con_lesionados"].sum())
        eventos_graves = int(casos["grave_o_fatal"].sum())
        filas.append({
            "id_medida": medida,
            **CANDIDATAS[medida],
            "hallazgo_empirico_respaldo": (
                f"{eventos} siniestros registrados cumplen el filtro, con {eventos_con_lesionados} eventos "
                f"con personas lesionadas y {eventos_graves} eventos graves o fatales. La medida queda pendiente de evaluación."
            ),
            "siniestros_objetivo_n": eventos,
            "siniestros_con_lesionados_objetivo_n": eventos_con_lesionados,
            "lesionados_objetivo_n": int(casos["TOTAL_LESI"].sum()),
            "graves_o_fatales_objetivo_n": eventos_graves,
            "personas_graves_objetivo_n": int(casos["GRAVES"].sum()),
            "personas_fallecidas_objetivo_n": int(casos["FALLECIDOS"].sum()),
            "siniestros_en_otras_medidas_n": int((filtro & selecciones.gt(1)).sum()),
        })

    cobertura = {
        "siniestros_base_n": len(df),
        "siniestros_unicos_con_medida_n": int(selecciones.gt(0).sum()),
        "siniestros_en_varias_medidas_n": int(selecciones.gt(1).sum()),
        "selecciones_totales_n": int(selecciones.sum()),
    }
    return pd.DataFrame(filas), cobertura

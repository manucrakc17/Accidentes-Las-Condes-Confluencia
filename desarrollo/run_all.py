"""Ejecuta el estudio y verifica la integridad de los resultados agregados."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import platform
from importlib.metadata import version
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DEV_DIR = ROOT_DIR / "desarrollo"
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"
PRIVATE_DIR = ROOT_DIR / "experimentos" / "privado"
PRIVATE_CSV_NAME = "SINIESTROS_LAS_CONDES_CORREGIDO.csv"
MANIFEST_NAME = "manifest_evidencia.json"
STAGING_PREFIX = ".ejecucion-"
STEPS = (
    "01_limpieza_y_correccion_solar.py",
    "02_correlaciones_y_factores.py",
    "03_puntos_calientes_y_mitigacion.py",
)
PUBLIC_FILES = (
    "01_auditoria_calidad_y_solar.json",
    "02_asociaciones_categoricas_chi2_or.csv",
    "02_correlaciones_estadisticas.csv",
    "02_resumen_correlaciones.json",
    "03_grilla_getis_ord_gi.csv",
    "03_hotspots_dbscan.csv",
    "03_intersecciones_y_ejes_criticos.csv",
    "03_matriz_mitigacion_evidencia.csv",
    "03_sintesis_mitigacion.json",
    "REPORTE_EXPERIMENTOS.md",
    "fig01_correccion_solar_impacto.png",
    "fig02_matriz_correlaciones_spearman.png",
    "fig03_factores_riesgo_severidad_or.png",
    "fig04_perfiles_horarios_y_vulnerables.png",
    "fig05_mapa_hotspots_y_severidad.png",
    "fig06_perfiles_clusters_criticos.png",
)


def load_and_run(script_name: str, out_dir: Path, private_dir: Path) -> dict[str, Any]:
    script_path = DEV_DIR / script_name
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {script_name}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = out_dir
    if script_name == STEPS[0]:
        module.PRIVATE_DIR = private_dir
    else:
        module.IN_CSV = private_dir / PRIVATE_CSV_NAME
    return module.main()


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def artifact_records(directory: Path) -> list[dict[str, str | int]]:
    files = []
    for name in PUBLIC_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Falta el archivo regular esperado {name}.")
        files.append({
            "archivo": f"experimentos/resultados/{name}",
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return files


def verify_manifest(directory: Path = OUT_DIR) -> int:
    entries = {path.name for path in directory.iterdir()}
    expected = {*PUBLIC_FILES, MANIFEST_NAME}
    if entries != expected:
        raise ValueError(
            f"Inventario inválido. Faltan {sorted(expected - entries)}. "
            f"Hay entradas inesperadas {sorted(entries - expected)}."
        )
    path = directory / MANIFEST_NAME
    if path.is_symlink():
        raise ValueError("El manifiesto debe ser un archivo regular.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["total_archivos_evidencia"] != len(PUBLIC_FILES) or manifest["archivos"] != artifact_records(directory):
        raise ValueError("Los nombres, los tamaños o los hashes de los resultados difieren del manifiesto.")
    return len(PUBLIC_FILES)


def fmt_p(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3g}" if value else "Por debajo de la precisión numérica"


def build_markdown_report(
    res01: dict[str, Any], res02: dict[str, Any], res03: dict[str, Any],
) -> str:
    solar = res01["correccion_solar"]
    pos = res01["auditoria_posicional"]
    outcomes = res01["desenlaces"]
    tests = res02["resumen_asociaciones"]
    severe = res02["modelo_logistico_grave_o_fatal"]
    sensitivity = res02["sensibilidad_modelo_grave_o_fatal"]
    grid = res03["resumen_getis_ord_gi"]
    clusters = res03["resumen_dbscan"]
    weights = res03["sensibilidad_ponderacion"]
    coverage = res03["cobertura_mitigacion"]
    n = res01["n_registros"]
    v = outcomes["siniestros_con_usuarios_vulnerables"]
    s = outcomes["graves_o_fatales_con_usuarios_vulnerables"]
    s_other = outcomes["siniestros_graves_o_fatales"] - s
    n_other = n - v
    lines = [
        "# Siniestros registrados en Las Condes en 2025",
        "",
        f"Análisis exploratorio de **{n} siniestros** etiquetados `Zonas_urb_ = Urbano` en la planilla local. "
        "[Cotejo de la planilla de referencia con CONASET, cobertura y definiciones](../../docs/fuente_y_alcance.md)",
        "",
        f"El conjunto registra **{outcomes['personas_lesionadas']} personas lesionadas** y "
        f"**{outcomes['personas_fallecidas']} personas fallecidas**. "
        f"Hay **{outcomes['siniestros_con_lesionados']} siniestros con personas lesionadas**, "
        f"**{outcomes['siniestros_con_lesion_o_muerte']} con lesión o muerte** y "
        f"**{outcomes['siniestros_graves_o_fatales']} con al menos una lesión grave o muerte**.",
        "",
        "## Posición solar y clima",
        "",
        f"- Con el mismo umbral de elevación solar ≤0°, que incluye el crepúsculo, la proporción pasa de "
        f"**{solar['pct_noche_original']}% ({solar['n_noche_original']}/{n})** a "
        f"**{solar['pct_noche_corregido']}% ({solar['n_noche_corregida']}/{n})**. "
        f"El indicador original por sí solo marcaba {solar['pct_noche_original_indicador_fuente']}%.",
        f"- El error medio absoluto de la elevación original es **{solar['mae_original_vs_real_grados']}°** "
        f"respecto de la elevación corregida y **{solar['mae_original_vs_simulacion_mas12h_grados']}°** "
        "respecto de la simulación desplazada 12 h en el reloj del mismo día. "
        "La simulación identifica la fase horaria opuesta. El mecanismo original requiere el proceso de enriquecimiento.",
        f"- **{solar['atropellos_dia_corregido']} de {solar['atropellos_total']} atropellos** "
        "tuvieron el sol sobre el horizonte. El indicador geométrico de sol bajo describe elevación solar. "
        "Para medir encandilamiento hacen falta orientación y condiciones observadas.",
        f"- El pavimento adverso estimado y el indicador de lluvia previa coinciden en "
        f"**{res01['coincidencia_proxy_pavimento_lluvia_24h_n']}/{n} filas**. "
        "Faltan mediciones en calzada y exposición para evaluar la ocurrencia de siniestros según clima.",
        "",
        "## Severidad dentro de los siniestros registrados",
        "",
        f"- **{s}/{v} siniestros con usuarios vulnerables** tuvieron desenlace grave o fatal "
        f"frente a **{s_other}/{n_other}** del resto.",
        f"- De {tests['pruebas']} pruebas de Fisher, {tests['estimables']} fueron estimables. "
        f"Hay {tests['significativas_p05']} con p <0,05, "
        f"{tests['significativas_fdr_bh_05']} con ajuste Benjamini–Hochberg (BH) "
        f"y {tests['significativas_holm_05']} con ajuste Holm. Cada familia de pruebas se ajustó por separado.",
        f"- El modelo grave/fatal usa **{severe['n_eventos']} eventos**, {severe['n_siniestros']} registros "
        f"y {severe['n_predictores']} predictores. Los OR describen odds ajustadas dentro de la muestra. "
        "El análisis carece de aforos y los coeficientes son exploratorios.",
        "",
        "| Factor | OR ajustado (IC 95% nominal) | p | q BH | p Holm |",
        "|---|---:|---:|---:|---:|",
    ]
    labels = {
        "Atropello": "Atropello", "Motociclet": "Motocicleta", "Bicicleta": "Bicicleta",
        "causa_distinta_no_atento": "Causa específica registrada", "noche_corr": "Elevación solar ≤0°",
        "pavimento_adverso": "Pavimento adverso estimado", "es_cruce": "Ubicación clasificada como cruce",
        "zona_alta_precordillera": "Cota ≥750 m", "es_fin_de_semana": "Sábado o domingo",
    }
    for factor, stats in severe["factores"].items():
        lines.append(
            f"| {labels[factor]} | {stats['odds_ratio_ajustado']:.3g} "
            f"({stats['ic95_inf']:.3g}–{stats['ic95_sup']:.3g}) | "
            f"{fmt_p(stats['p_valor'])} | {fmt_p(stats['q_fdr_bh'])} | {fmt_p(stats['p_holm'])} |"
        )
    night = sensitivity["con_hora_ciclica"]["factores"]["noche_corr"]
    altitude = sensitivity["con_altitud_continua"]["factores"]["altitud_por_50m"]
    lines.extend([
        "",
        f"Al añadir hora cíclica, el OR de elevación solar ≤0° pasa a **{night['odds_ratio_ajustado']:.3g}** "
        f"(IC {night['ic95_inf']:.3g}–{night['ic95_sup']:.3g}, p = {fmt_p(night['p_valor'])}). "
        f"Con altitud continua, el OR por 50 m es **{altitude['odds_ratio_ajustado']:.3g}** "
        f"(IC {altitude['ic95_inf']:.3g}–{altitude['ic95_sup']:.3g}). "
        "La pendiente, el tipo de vía y la velocidad requieren datos adicionales.",
        "",
        "## Concentración espacial",
        "",
        f"- **{pos['registros_fuera_limite_ciren']} puntos** quedan fuera del límite comunal de referencia de CIREN. "
        f"{pos['externos_hasta_50_m']} están a 50 m o menos. El máximo es {pos['distancia_maxima_fuera_limite_m']:.0f} m. "
        f"En {pos['n_intersecciones_repetidas_coordenada_unica']}/{pos['n_intersecciones_repetidas']} "
        "intersecciones repetidas todas las filas comparten exactamente la coordenada. La exactitud vial requiere el catastro y los partes.",
        f"- DBSCAN a {clusters['parametros']['eps_metros']:.0f} m agrupa **{clusters['siniestros_en_clusters']}/{n} "
        f"siniestros en {clusters['n_clusters_detectados']} grupos**. "
        f"{clusters['n_clusters_mas_de_300_m']} grupos se extienden más de 300 m. "
        "El parámetro es distancia de vecindad y el rótulo es el nodo más frecuente dentro del grupo. "
        f"Se publican {clusters['n_clusters_publicados']} grupos con al menos {clusters['clusters_publicados_min_n']} siniestros.",
        f"- Gi* usa {grid['total_celdas_con_siniestros']} celdas ocupadas, centros geométricos y "
        f"{grid['n_permutaciones']} permutaciones. "
        "El criterio principal exige Z positivo y q BH ≤0,05 tanto con la aproximación analítica como con permutaciones. "
        f"Se publican {grid['n_celdas_publicadas']} celdas con al menos {grid['celdas_publicadas_min_n']} siniestros.",
        f"- Los dos puntajes acumulados suman {weights['indice_original_total']} (ponderación histórica por persona) y "
        f"{weights['puntaje_conaset_total']} (peor consecuencia por siniestro, más frecuencia). "
        f"Comparten {weights['n_clusters_top_10_comunes']} grupos en sus diez primeros lugares.",
        "",
        "| Atributo para Gi* | Nominal | BH analítico | BH con permutación | Ambos BH |",
        "|---|---:|---:|---:|---:|",
    ])
    for key, name in (("conteo", "Frecuencia"), ("epdo", "Puntaje histórico"), ("conaset", "Puntaje CONASET")):
        counts = [grid[f"celdas_hotspot_{key}_{suffix}"] for suffix in ("p05", "bh_analitico", "bh_permutacion", "ambos")]
        lines.append(f"| {name} | {counts[0]} | {counts[1]} | {counts[2]} | {counts[3]} |")
    lines.extend([
        "",
        "La comparación espacial es exploratoria y está condicionada a celdas con registros. "
        "La priorización requiere una red vial de referencia, validación temporal y comprobación en terreno.",
        "",
        "## Medidas candidatas a evaluación",
        "",
        f"Los filtros generan {coverage['selecciones_totales_n']} selecciones en "
        f"{coverage['siniestros_unicos_con_medida_n']} siniestros distintos. "
        f"{coverage['siniestros_en_varias_medidas_n']} entran en más de una medida. "
        "Los conteos describen el filtro aplicado. La efectividad local de cada medida requiere una evaluación.",
        "",
        "| Código | Línea de acción | Siniestros | Personas lesionadas | Siniestros graves o fatales |",
        "|---|---|---:|---:|---:|",
    ])
    for row in res03["medidas_mitigacion"]:
        lines.append(
            f"| {row['id_medida']} | {row['linea_accion']} | {row['siniestros_objetivo_n']} | "
            f"{row['lesionados_objetivo_n']} | {row['graves_o_fatales_objetivo_n']} |"
        )
    lines.extend(["", "[Filtros, evidencia y verificación propuesta](03_matriz_mitigacion_evidencia.csv)", ""])
    return "\n".join(lines)


def discard_interrupted_staging(*directories: Path) -> None:
    for directory in directories:
        for staging in directory.glob(f"{STAGING_PREFIX}*"):
            if staging.is_dir() and not staging.is_symlink():
                rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Comprueba los resultados publicados y sus hashes.")
    if parser.parse_args().verificar:
        print(f"{verify_manifest()} archivos agregados verificados.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (PRIVATE_DIR / ".ejecucion.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        discard_interrupted_staging(OUT_DIR, PRIVATE_DIR)
        unexpected = {p.name for p in OUT_DIR.iterdir()} - {*PUBLIC_FILES, MANIFEST_NAME}
        if unexpected:
            raise ValueError(f"Retira del directorio de resultados las entradas inesperadas: {sorted(unexpected)}.")
        inputs = {
            "planilla_local": ROOT_DIR / "datos" / "SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx",
            "limite_ciren": ROOT_DIR / "datos" / "las_condes_ciren.geojson",
        }
        if not inputs["planilla_local"].is_file():
            raise FileNotFoundError("Coloca una copia autorizada de la planilla enriquecida en datos/.")
        input_hashes = {name: sha256_file(path) for name, path in inputs.items()}
        with (
            TemporaryDirectory(dir=OUT_DIR, prefix=STAGING_PREFIX) as out_tmp,
            TemporaryDirectory(dir=PRIVATE_DIR, prefix=STAGING_PREFIX) as private_tmp,
        ):
            out = Path(out_tmp)
            private = Path(private_tmp)
            results = [load_and_run(step, out, private) for step in STEPS]
            (out / "REPORTE_EXPERIMENTOS.md").write_text(build_markdown_report(*results), encoding="utf-8")
            if any(sha256_file(path) != input_hashes[name] for name, path in inputs.items()):
                raise ValueError("Cambió un insumo durante la ejecución. Repite el análisis con una copia estable.")
            manifest = {
                "version_manifiesto": 1,
                "python_version": platform.python_version(),
                "plataforma": f"{platform.system()}-{platform.machine()}",
                "dependencias": {
                    name: version(name) for name in (
                        "matplotlib", "numpy", "openpyxl", "pandas", "pyproj", "scikit-learn", "scipy",
                        "seaborn", "shapely", "statsmodels", "tzdata",
                    )
                },
                "sha256_insumos": input_hashes,
                "total_archivos_evidencia": len(PUBLIC_FILES),
                "archivos": artifact_records(out),
            }
            (out / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            verify_manifest(out)
            (private / PRIVATE_CSV_NAME).replace(PRIVATE_DIR / PRIVATE_CSV_NAME)
            # El manifiesto se reemplaza al final para que una publicación interrumpida falle al verificar.
            for name in (*PUBLIC_FILES, MANIFEST_NAME):
                (out / name).replace(OUT_DIR / name)
        print(f"{verify_manifest()} archivos agregados verificados.")


if __name__ == "__main__":
    main()

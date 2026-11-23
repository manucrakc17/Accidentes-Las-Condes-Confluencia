#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exploración de concentraciones espaciales de los siniestros registrados."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.spatial.distance import cdist
from scipy.stats import norm
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import haversine_distances
from statsmodels.stats.multitest import multipletests

from mitigacion import construir_matriz

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "experimentos" / "resultados"
IN_CSV = ROOT_DIR / "experimentos" / "privado" / "SINIESTROS_LAS_CONDES_CORREGIDO.csv"

EARTH_RADIUS_M = 6371000.0
CRS_UTM = "EPSG:32719"
CELL_SIZE_M = 250
DISTANCE_M = 400
N_PERMUTATIONS = 19_999
PERMUTATION_SEED = 681_221
ALPHA = 0.05
DBSCAN_METERS = 150
MIN_SAMPLES = 5
MIN_PUBLIC_COUNT = 5


def compute_getis_ord_gi_star(
    values: np.ndarray, adjacency: csr_matrix, *, n_permutations: int = N_PERMUTATIONS
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gi* bilateral para vecindad binaria, con auto-vecindad y permutación global."""
    n = len(values)
    if n <= 2 or np.std(values) == 0 or np.all(adjacency.getnnz(axis=1) == n):
        return np.zeros(n), np.ones(n), np.ones(n)

    neighbors = adjacency.getnnz(axis=1)
    centered = values - values.mean()
    observed = adjacency @ centered
    denom = np.std(values) * np.sqrt(neighbors * (n - neighbors) / (n - 1))
    z = np.divide(observed, denom, out=np.zeros(n), where=denom > 0)
    p_analytic = 2 * norm.sf(np.abs(z))

    rng = np.random.default_rng(PERMUTATION_SEED)
    extreme = np.zeros(n, dtype=int)
    # Agrupar permutaciones limita la memoria sin construir una matriz densa de pesos.
    for offset in range(0, n_permutations, 500):
        permutations = np.stack(
            [rng.permutation(centered) for _ in range(min(500, n_permutations - offset))], axis=1,
        )
        extreme += (np.abs(adjacency @ permutations) >= np.abs(observed[:, None]) - 1e-10).sum(axis=1)
    p_permutation = (extreme + 1) / (n_permutations + 1)
    p_permutation[denom == 0] = 1
    return z, p_analytic, p_permutation


def grid_indices(easting: np.ndarray, northing: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.floor(easting / CELL_SIZE_M).astype(int), np.floor(northing / CELL_SIZE_M).astype(int)


def statistics_for_grid(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    grid = (
        df.groupby(["grid_ix", "grid_iy"])
        .agg(
            n_siniestros=("ID", "size"),
            epdo_total=("indice_epdo", "sum"),
            epdo_medio=("indice_epdo", "mean"),
            puntaje_conaset_total=("puntaje_conaset", "sum"),
            lesionados_total=("TOTAL_LESI", "sum"),
            graves_o_fatales=("grave_o_fatal", "sum"),
            vulnerables=("usuario_vulnerable", "sum"),
        )
        .reset_index()
    )
    grid["x_centro_m"] = (grid["grid_ix"] + .5) * CELL_SIZE_M
    grid["y_centro_m"] = (grid["grid_iy"] + .5) * CELL_SIZE_M
    centers = grid[["x_centro_m", "y_centro_m"]].to_numpy()
    adjacency = csr_matrix(cdist(centers, centers) <= DISTANCE_M, dtype=float)

    summary = {
        "crs": CRS_UTM,
        "origen_m": [0, 0],
        "tamano_celda_m": CELL_SIZE_M,
        "distancia_vecindad_m": DISTANCE_M,
        "total_celdas_con_siniestros": len(grid),
        "universo": "celdas ocupadas por los siniestros de la muestra",
        "alcance": "concentración observada de siniestros y puntajes acumulados, sin denominador de exposición",
        "n_permutaciones": N_PERMUTATIONS,
        "semilla_permutacion": PERMUTATION_SEED,
        "nulo_permutacion": "intercambiabilidad entre celdas ocupadas, con vecindad fija",
        "alfa": ALPHA,
        "criterio_positivo": "z > 0 y q BH <= 0.05 en ambos métodos",
    }
    metrics = (("conteo", "n_siniestros"), ("epdo", "epdo_total"), ("conaset", "puntaje_conaset_total"))
    for suffix, col in metrics:
        z, p, p_perm = compute_getis_ord_gi_star(grid[col].to_numpy(), adjacency)
        q = multipletests(p, method="fdr_bh")[1]
        q_perm = multipletests(p_perm, method="fdr_bh")[1]
        positive = z > 0
        combined = positive & (q <= ALPHA) & (q_perm <= ALPHA)
        grid[f"gi_z_{suffix}"] = z
        grid[f"gi_p_{suffix}"] = p
        grid[f"gi_p_perm_{suffix}"] = p_perm
        grid[f"gi_q_bh_{suffix}"] = q
        grid[f"gi_q_bh_perm_{suffix}"] = q_perm
        grid[f"hotspot_{suffix}"] = combined
        summary.update({
            f"celdas_hotspot_{suffix}_p05": int(np.sum(positive & (p <= ALPHA))),
            f"celdas_hotspot_{suffix}_bh_analitico": int(np.sum(positive & (q <= ALPHA))),
            f"celdas_hotspot_{suffix}_bh_permutacion": int(np.sum(positive & (q_perm <= ALPHA))),
            f"celdas_hotspot_{suffix}_ambos": int(np.sum(combined)),
        })
    return grid, summary


def conaset_score(df: pd.DataFrame) -> np.ndarray:
    """Un punto por ocurrencia y un incremento por la peor consecuencia del siniestro."""
    return np.select(
        [df["FALLECIDOS"] > 0, df["GRAVES"] > 0, df["MENOS_GRAV"] > 0, df["LEVES"] > 0],
        [11, 7, 5, 3],
        default=1,
    )


def dbscan_labels(coordinates: np.ndarray, radius_m: int) -> np.ndarray:
    if len(coordinates) == 0:
        return np.array([], dtype=int)
    return DBSCAN(
        eps=radius_m / EARTH_RADIUS_M, min_samples=MIN_SAMPLES, metric="haversine",
    ).fit_predict(coordinates)


def cluster_counts(labels: np.ndarray) -> dict[str, int]:
    assigned = labels[labels >= 0]
    return {"n_clusters_detectados": int(np.unique(assigned).size), "siniestros_en_clusters": len(assigned)}


def summarize_crashes(groups) -> pd.DataFrame:
    summary = groups.agg(
        n_siniestros=("ID", "size"),
        epdo_total=("indice_epdo", "sum"),
        epdo_medio=("indice_epdo", "mean"),
        puntaje_conaset_total=("puntaje_conaset", "sum"),
        fallecidos=("FALLECIDOS", "sum"),
        graves=("GRAVES", "sum"),
        total_lesionados=("TOTAL_LESI", "sum"),
        siniestros_graves_o_fatales=("grave_o_fatal", "sum"),
        n_motocicletas=("Motociclet", "sum"),
        n_atropellos=("Atropello", "sum"),
        n_bicicletas=("Bicicleta", "sum"),
        pct_con_lesionados=("con_lesionados", "mean"),
        pct_grave_o_fatal=("grave_o_fatal", "mean"),
        pct_usuarios_vulnerables=("usuario_vulnerable", "mean"),
    )
    for column in ("pct_con_lesionados", "pct_grave_o_fatal", "pct_usuarios_vulnerables"):
        summary[column] = (100 * summary[column]).round(1)
    return summary.round({"epdo_medio": 2})


def rank_road_units(df: pd.DataFrame) -> pd.DataFrame:
    streets = (
        df[["ID", "Calle_Uno_norm", "Calle_Dos_norm"]]
        .melt(id_vars="ID", value_name="unidad_vial")
        .dropna(subset="unidad_vial")
    )
    streets = streets.loc[streets["unidad_vial"] != "", ["ID", "unidad_vial"]].drop_duplicates()
    pairs = df.loc[
        df["Calle_Uno_norm"].fillna("").ne("")
        & df["Calle_Dos_norm"].fillna("").ne("")
        & (df["Calle_Uno_norm"] != df["Calle_Dos_norm"]),
        ["ID", "nodo_vial"],
    ].rename(columns={"nodo_vial": "unidad_vial"})
    units = pd.concat(
        [streets.assign(tipo_unidad="eje"), pairs.assign(tipo_unidad="interseccion")],
        ignore_index=True,
    )
    return summarize_crashes(
        units.merge(df, on="ID", validate="many_to_one").groupby(["tipo_unidad", "unidad_vial"]),
    ).reset_index().sort_values(
        ["tipo_unidad", "epdo_total", "n_siniestros", "unidad_vial"],
        ascending=[True, False, False, True],
    )


def cluster_profile(df: pd.DataFrame, coordinates: np.ndarray) -> pd.DataFrame:
    assigned = df.loc[df["cluster_dbscan"] >= 0]
    clusters = summarize_crashes(assigned.groupby("cluster_dbscan")).rename_axis("cluster_id")
    support_rows = []
    for cluster_id, group in assigned.groupby("cluster_dbscan"):
        node_support = group["nodo_vial"].fillna("").value_counts().sort_index().idxmax()
        node_count = int(group["nodo_vial"].fillna("").eq(node_support).sum())
        points = coordinates[group.index.to_numpy()]
        support_rows.append({
            "cluster_id": cluster_id,
            "interseccion_dominante": node_support,
            "n_nodo_dominante": node_count,
            "pct_nodo_dominante": round(100 * node_count / len(group), 1),
            "n_coordenadas_distintas": int(np.unique(points, axis=0).shape[0]),
            "diametro_m": round(float(haversine_distances(points).max() * EARTH_RADIUS_M), 1),
        })
    support = pd.DataFrame(support_rows, columns=[
        "cluster_id", "interseccion_dominante", "n_nodo_dominante", "pct_nodo_dominante",
        "n_coordenadas_distintas", "diametro_m",
    ]).set_index("cluster_id")
    clusters = clusters.join(support).reset_index().sort_values(
        ["epdo_total", "n_siniestros", "cluster_id"], ascending=[False, False, True],
    )
    clusters["ranking_severidad_epdo"] = np.arange(1, len(clusters) + 1)
    conaset_order = clusters.sort_values(
        ["puntaje_conaset_total", "n_siniestros", "cluster_id"], ascending=[False, False, True],
    )
    clusters["ranking_puntaje_conaset"] = pd.Series(np.arange(1, len(clusters) + 1), index=conaset_order.index)
    return clusters


def save_figures(grid: pd.DataFrame, clusters: pd.DataFrame, *, n_tested: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout="constrained")
    z_limit = max(1.0, float(grid[["gi_z_conteo", "gi_z_epdo"]].abs().max().max()))
    for ax, suffix, title in (
        (axes[0], "conteo", "Frecuencia de siniestros registrados"),
        (axes[1], "epdo", "Puntaje ponderado acumulado"),
    ):
        cells = ax.scatter(
            grid["x_centro_m"], grid["y_centro_m"], c=grid[f"gi_z_{suffix}"],
            marker="s", s=42, cmap="coolwarm", vmin=-z_limit, vmax=z_limit,
        )
        hotspots = grid.loc[grid[f"hotspot_{suffix}"]]
        ax.scatter(
            hotspots["x_centro_m"], hotspots["y_centro_m"], marker="s",
            s=65, facecolors="none", edgecolors="black",
        )
        ax.set(title=title, xlabel="Este (m)", ylabel="Norte (m)", aspect="equal")
        ax.ticklabel_format(style="plain", useOffset=False)
    fig.colorbar(cells, ax=axes, label="Z de Getis-Ord Gi*")
    fig.suptitle(
        f"Grilla UTM de 250 m · {len(grid)} de {n_tested} celdas analizadas visibles "
        f"({MIN_PUBLIC_COUNT} o más siniestros)\n"
        "Borde negro: asociación positiva con ajuste BH en ambos métodos"
    )
    fig.savefig(OUT_DIR / "fig05_mapa_hotspots_y_severidad.png", dpi=160)
    plt.close(fig)

    top = clusters.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    y = np.arange(len(top))
    ax.barh(y, top["siniestros_graves_o_fatales"], label="Graves o fatales")
    ax.barh(
        y, top["n_siniestros"] - top["siniestros_graves_o_fatales"],
        left=top["siniestros_graves_o_fatales"], label="Otros siniestros",
    )
    ax.set_yticks(y, [f"Grupo {cid}" for cid in top["cluster_id"]])
    ax.set(xlabel="Siniestros", title="Grupos DBSCAN con mayor puntaje acumulado")
    ax.legend()
    fig.savefig(OUT_DIR / "fig06_perfiles_clusters_criticos.png", dpi=160)
    plt.close(fig)


def main() -> dict:
    df = pd.read_csv(IN_CSV, dtype={"dentro_limite_comunal": "boolean"})
    if df.empty:
        raise ValueError("El análisis espacial requiere al menos un siniestro.")
    transformer = Transformer.from_crs("EPSG:4326", CRS_UTM, always_xy=True)
    easting, northing = transformer.transform(df["longitud"].to_numpy(), df["Latitud"].to_numpy())
    df["grid_ix"], df["grid_iy"] = grid_indices(easting, northing)
    df["puntaje_conaset"] = conaset_score(df)

    coordinates = np.deg2rad(df[["Latitud", "longitud"]].to_numpy())
    df["cluster_dbscan"] = dbscan_labels(coordinates, DBSCAN_METERS)
    clusters = cluster_profile(df, coordinates)
    public_clusters = clusters.loc[clusters["n_siniestros"] >= MIN_PUBLIC_COUNT].drop(columns="fallecidos").copy()
    public_clusters.loc[
        public_clusters["n_nodo_dominante"] < MIN_PUBLIC_COUNT, "interseccion_dominante"
    ] = "Nodo con menos de cinco registros"
    cluster_summary = cluster_counts(df["cluster_dbscan"].to_numpy())
    cluster_summary.update({
        "parametros": {"eps_metros": DBSCAN_METERS, "min_samples": MIN_SAMPLES, "metrica": "haversine"},
        "pct_siniestros_en_clusters": round(100 * cluster_summary["siniestros_en_clusters"] / len(df), 2),
        "n_clusters_publicados": len(public_clusters),
        "clusters_publicados_min_n": MIN_PUBLIC_COUNT,
        "top_10_clusters_por_epdo": public_clusters.head(10).to_dict(orient="records"),
        "sensibilidad_eps": [
            {"eps_metros": eps, **cluster_counts(dbscan_labels(coordinates, eps))}
            for eps in (100, 150, 200)
        ],
        "n_clusters_mas_de_300_m": int(clusters["diametro_m"].gt(300).sum()),
        "n_clusters_una_coordenada": int(clusters["n_coordenadas_distintas"].eq(1).sum()),
        "n_clusters_nodo_dominante_menos_50_pct": int(
            (2 * clusters["n_nodo_dominante"] < clusters["n_siniestros"]).sum()
        ),
        "n_graves_o_fatales_en_clusters": int(clusters["siniestros_graves_o_fatales"].sum()),
    })
    if "dentro_limite_comunal" in df:
        inside = df["dentro_limite_comunal"].fillna(False).to_numpy(dtype=bool)
        cluster_summary["sensibilidad_solo_dentro_limite"] = {
            "n_siniestros": int(inside.sum()),
            **cluster_counts(dbscan_labels(coordinates[inside], DBSCAN_METERS)),
        }

    grid, grid_summary = statistics_for_grid(df)
    public_grid = grid.loc[grid["n_siniestros"] >= MIN_PUBLIC_COUNT]
    grid_summary["celdas_publicadas_min_n"] = MIN_PUBLIC_COUNT
    grid_summary["n_celdas_publicadas"] = len(public_grid)
    roads = rank_road_units(df)
    roads = roads.loc[roads["n_siniestros"] >= MIN_PUBLIC_COUNT].drop(columns="fallecidos")
    mitigacion, cobertura_mitigacion = construir_matriz(df)
    for frame, filename in (
        (public_clusters, "03_hotspots_dbscan.csv"),
        (public_grid, "03_grilla_getis_ord_gi.csv"),
        (roads, "03_intersecciones_y_ejes_criticos.csv"),
        (mitigacion, "03_matriz_mitigacion_evidencia.csv"),
    ):
        frame.to_csv(OUT_DIR / filename, index=False, encoding="utf-8")
    save_figures(public_grid, public_clusters, n_tested=len(grid))

    top_epdo = set(clusters.head(10)["cluster_id"])
    top_conaset = set(clusters.nsmallest(10, "ranking_puntaje_conaset")["cluster_id"])
    summary = {
        "resumen_dbscan": cluster_summary,
        "resumen_getis_ord_gi": grid_summary,
        "sensibilidad_ponderacion": {
            "indice_original_total": int(df["indice_epdo"].sum()),
            "puntaje_conaset_total": int(df["puntaje_conaset"].sum()),
            "n_puntajes_distintos": int(df["indice_epdo"].ne(df["puntaje_conaset"]).sum()),
            "n_clusters_top_10_comunes": len(top_epdo & top_conaset),
        },
        "top_10_ejes_criticos": roads.loc[roads["tipo_unidad"] == "eje"].head(10).to_dict(orient="records"),
        "top_10_intersecciones_criticas": roads.loc[
            roads["tipo_unidad"] == "interseccion"
        ].head(10).to_dict(orient="records"),
        "medidas_mitigacion": mitigacion.to_dict(orient="records"),
        "cobertura_mitigacion": cobertura_mitigacion,
    }
    with (OUT_DIR / "03_sintesis_mitigacion.json").open("w", encoding="utf-8") as out:
        json.dump(summary, out, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"[03] Grupos DBSCAN: {len(clusters)} ({cluster_summary['siniestros_en_clusters']}/{len(df)} siniestros)")
    print(
        "[03] Celdas Gi* positivas con BH en ambos métodos: "
        f"frecuencia={grid_summary['celdas_hotspot_conteo_ambos']}, "
        f"puntaje ponderado={grid_summary['celdas_hotspot_epdo_ambos']}"
    )
    return summary


if __name__ == "__main__":
    main()

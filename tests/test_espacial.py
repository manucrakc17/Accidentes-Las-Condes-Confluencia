import importlib.util
from itertools import permutations
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


DESARROLLO = Path(__file__).resolve().parents[1] / "desarrollo"
sys.path.insert(0, str(DESARROLLO))
spec = importlib.util.spec_from_file_location("analisis_espacial", DESARROLLO / "03_puntos_calientes_y_mitigacion.py")
espacial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(espacial)


def sample_crashes() -> pd.DataFrame:
    return pd.DataFrame({
        "ID": [1, 2, 3, 4],
        "indice_epdo": [3, 1, 1, 12],
        "FALLECIDOS": [0, 0, 0, 1],
        "GRAVES": [0, 0, 0, 2],
        "MENOS_GRAV": [1, 0, 0, 0],
        "LEVES": [1, 0, 0, 1],
        "TOTAL_LESI": [2, 0, 0, 3],
        "grave_o_fatal": [0, 0, 0, 1],
        "con_lesionados": [1, 0, 0, 1],
        "Atropello": [0, 0, 0, 1],
        "Bicicleta": [0, 0, 0, 0],
        "Motociclet": [0, 0, 0, 0],
        "usuario_vulnerable": [0, 0, 0, 1],
        "Calle_Uno_norm": ["A", "B", "B", "C"],
        "Calle_Dos_norm": ["B", "A", "B", None],
        "nodo_vial": ["A x B", "A x B", "B x B", "C (TRAMO)"],
    })


class TestEspacial(unittest.TestCase):
    def test_gi_star_permutation_matches_enumeration_and_is_reproducible(self):
        values = np.array([3, 1, 2, 8])
        weights = csr_matrix([
            [1, 1, 0, 0],
            [1, 1, 0, 0],
            [0, 0, 1, 1],
            [1, 1, 1, 1],
        ])
        z, p_analytic, p_permutation = espacial.compute_getis_ord_gi_star(values, weights, n_permutations=4_999)
        centered = values - values.mean()
        expected = (np.abs(weights @ np.array(list(permutations(centered))).T)
                    >= np.abs(weights @ centered)[:, None]).mean(axis=1)
        np.testing.assert_allclose(p_permutation, expected, atol=.025)
        _, _, repeated = espacial.compute_getis_ord_gi_star(values, weights, n_permutations=4_999)
        np.testing.assert_array_equal(p_permutation, repeated)
        self.assertLess(z[0], 0)
        self.assertGreater(z[2], 0)
        self.assertEqual(z[-1], 0)
        self.assertEqual(p_analytic[-1], 1)
        self.assertEqual(p_permutation[-1], 1)

    def test_grid_has_fixed_origin_and_uses_geometric_center(self):
        data = sample_crashes()
        x = np.array([500_000, 500_249.9, 500_250, 500_251])
        y = np.full(4, 6_300_001)
        data["grid_ix"], data["grid_iy"] = espacial.grid_indices(x, y)
        data["puntaje_conaset"] = espacial.conaset_score(data)
        grid, summary = espacial.statistics_for_grid(data)
        self.assertEqual(summary["origen_m"], [0, 0])
        self.assertEqual(summary["crs"], "EPSG:32719")
        self.assertEqual(grid.n_siniestros.to_list(), [2, 2])
        self.assertEqual(grid.x_centro_m.to_list(), [500_125, 500_375])
        self.assertEqual(grid.y_centro_m.to_list(), [6_300_125, 6_300_125])
        self.assertFalse(grid.hotspot_conteo.any())

    def test_ranking_counts_same_crash_once_per_street_and_unordered_pair(self):
        data = sample_crashes()
        data["puntaje_conaset"] = espacial.conaset_score(data)
        self.assertEqual(data.puntaje_conaset.to_list(), [5, 1, 1, 11])
        ranked = espacial.rank_road_units(data).set_index(["tipo_unidad", "unidad_vial"])
        self.assertEqual(ranked.loc[("eje", "A"), "n_siniestros"], 2)
        self.assertEqual(ranked.loc[("eje", "B"), "n_siniestros"], 3)
        self.assertEqual(ranked.loc[("interseccion", "A x B"), "n_siniestros"], 2)
        self.assertNotIn(("interseccion", "B x B"), ranked.index)

    def test_dbscan_group_extent_exceeds_local_radius(self):
        data = pd.concat([sample_crashes()] * 2, ignore_index=True)
        data["puntaje_conaset"] = espacial.conaset_score(data)
        latitude = np.tile([-33.41, -33.411, -33.412, -33.413], 2)
        coordinates = np.deg2rad(np.column_stack([latitude, np.full(8, -70.58)]))
        data["cluster_dbscan"] = espacial.dbscan_labels(coordinates, radius_m=150)
        cluster = espacial.cluster_profile(data, coordinates).iloc[0]
        self.assertEqual(cluster.n_siniestros, 8)
        self.assertEqual(cluster.n_coordenadas_distintas, 4)
        self.assertEqual(cluster.n_nodo_dominante, 4)
        self.assertGreater(cluster.diametro_m, 300)


if __name__ == "__main__":
    unittest.main()

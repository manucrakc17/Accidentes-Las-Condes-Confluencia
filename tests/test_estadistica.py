import importlib.util
from pathlib import Path
import unittest

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "desarrollo/02_correlaciones_y_factores.py"
SPEC = importlib.util.spec_from_file_location("correlaciones", SCRIPT)
correlaciones = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(correlaciones)


class AsociacionesTests(unittest.TestCase):
    def calcular(self, exposicion, resultado):
        data = pd.DataFrame({"x": exposicion, "y": resultado})
        return correlaciones.calc_2x2_or_fisher(data, "x", "y", "Asociación de prueba")

    def test_p_pequeno_y_celdas_cero_estimables(self):
        indicador = [0] * 35 + [1] * 35
        row = self.calcular(indicador, indicador)
        self.assertTrue(row["estimable"])
        self.assertGreater(row["p_fisher"], 0.0)
        self.assertLess(row["p_fisher"], 1e-12)
        self.assertGreater(row["odds_ratio"], 1.0)

    def test_margen_cero_queda_sin_estimacion(self):
        for x, y in [([0, 0], [0, 1]), ([0, 1], [0, 0]), ([], [])]:
            with self.subTest(x=x, y=y):
                row = self.calcular(x, y)
                self.assertFalse(row["estimable"])
                self.assertFalse(row["significativo_p05"])
                self.assertIsNone(row["p_fisher"])
                self.assertIsNone(row["odds_ratio"])

    def test_valor_no_binario_se_rechaza(self):
        with self.assertRaisesRegex(ValueError, "indicadores binarios"):
            self.calcular([0, 0.5, 1], [0, 1, 1])

    def test_multiplicidad_conserva_familia_planificada(self):
        p_values = pd.Series({"a": 1e-12, "b": 0.02, "c": 0.04, "no_estimable": None})
        for method, expected in [
            ("fdr_bh", [4e-12, 0.04, 0.04 * 4 / 3]),
            ("holm", [4e-12, 0.06, 0.08]),
        ]:
            with self.subTest(method=method):
                adjusted = correlaciones.ajustar_p_valores(p_values, method)
                for index, value in zip(["a", "b", "c"], expected):
                    self.assertAlmostEqual(adjusted[index], value, delta=value * 1e-10)
                self.assertTrue(pd.isna(adjusted["no_estimable"]))


class RegresionTests(unittest.TestCase):
    def test_resume_la_muestra_y_ajusta_coeficientes(self):
        x = pd.DataFrame({"bici": [0] * 40 + [1] * 40, "cruce": ([0] * 20 + [1] * 20) * 2})
        y = pd.Series(
            [0] * 18 + [1] * 2 + [0] * 16 + [1] * 4 + [0] * 14 + [1] * 6 + [0] * 10 + [1] * 10,
            name="grave_o_fatal",
        )
        model = correlaciones.ajustar_logit(y, x)
        self.assertEqual(model["n_siniestros"], 80)
        self.assertEqual(model["n_eventos"], 22)
        self.assertEqual(model["n_predictores"], 2)
        self.assertTrue(model["convergio"])
        self.assertEqual(set(model["factores"]), {"bici", "cruce"})
        for factor in model["factores"].values():
            self.assertGreaterEqual(factor["q_fdr_bh"], factor["p_valor"])
            self.assertGreaterEqual(factor["p_holm"], factor["p_valor"])


if __name__ == "__main__":
    unittest.main()

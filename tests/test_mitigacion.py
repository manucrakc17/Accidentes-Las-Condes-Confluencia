import unittest

import pandas as pd

from desarrollo.mitigacion import construir_matriz


def siniestro(**campos):
    return {
        "FECHA": "2025-05-09",
        "Hora": "14:00:00",
        "Calle_Uno_norm": "VIA SECUNDARIA",
        "Calle_Dos_norm": None,
        "usuario_vulnerable": 0,
        "tipo_ubicacion_vial": "TRAMO_RECTO",
        "Motociclet": 0,
        "TIPO__CONA": "COLISION",
        "pavimento_adverso": 0,
        "altitud_m": 620,
        "Atropello": 0,
        "sol_alt_grados_corr": 25,
        "causa_especifica": "OTRA",
        "con_lesionados": 0,
        "grave_o_fatal": 0,
        "TOTAL_LESI": 0,
        "GRAVES": 0,
        "FALLECIDOS": 0,
        **campos,
    }


class MitigacionTest(unittest.TestCase):
    def test_turno_nocturno_incluye_madrugada_del_dia_siguiente(self):
        expectativas = (
            ("2025-05-09", "21:59:59", "CHOQUE", 0),
            ("2025-05-09", "22:00:00", "CHOQUE", 1),
            ("2025-05-10", "05:59:59", "CHOQUE", 1),
            ("2025-05-10", "06:00:00", "CHOQUE", 0),
            ("2025-05-10", "22:00", "CHOQUE", 1),
            ("2025-05-11", "05:59:59", "CHOQUE", 1),
            ("2025-05-09", "05:59:59", "CHOQUE", 0),
            ("2025-05-11", "22:00:00", "CHOQUE", 0),
            ("2025-05-09", "22:00:00", "VOLCADURA", 0),
        )
        for fecha, hora, tipo, esperado in expectativas:
            with self.subTest(fecha=fecha, hora=hora, tipo=tipo):
                matriz, _ = construir_matriz(
                    pd.DataFrame([siniestro(FECHA=fecha, Hora=hora, TIPO__CONA=tipo)])
                )
                self.assertEqual(matriz.set_index("id_medida").at["MIT-03", "siniestros_objetivo_n"], esperado)

    def test_filtros_y_recuentos_distinguen_personas_de_siniestros(self):
        caso = siniestro(
            Hora="17:00:00", Calle_Dos_norm="LAS CONDES", usuario_vulnerable=1,
            tipo_ubicacion_vial="CRUCE_SEMAFORIZADO", Motociclet=1, Atropello=1,
            altitud_m=750, pavimento_adverso=1, causa_especifica="NO_ATENTO_CONDICIONES_TRANSITO",
            con_lesionados=1, grave_o_fatal=1, TOTAL_LESI=3, GRAVES=2, FALLECIDOS=1,
        )
        matriz, cobertura = construir_matriz(pd.DataFrame([caso, siniestro()]))
        filas = matriz.set_index("id_medida")
        self.assertEqual(filas["siniestros_objetivo_n"].tolist(), [1, 1, 0, 1, 1, 1])
        self.assertEqual(filas.at["MIT-01", "siniestros_con_lesionados_objetivo_n"], 1)
        self.assertEqual(filas.at["MIT-01", "lesionados_objetivo_n"], 3)
        self.assertEqual(filas.at["MIT-01", "graves_o_fatales_objetivo_n"], 1)
        self.assertEqual(filas.at["MIT-01", "personas_graves_objetivo_n"], 2)
        self.assertEqual(filas.at["MIT-01", "personas_fallecidas_objetivo_n"], 1)
        self.assertEqual(filas.at["MIT-01", "siniestros_en_otras_medidas_n"], 1)
        self.assertEqual(cobertura, {
            "siniestros_base_n": 2,
            "siniestros_unicos_con_medida_n": 1,
            "siniestros_en_varias_medidas_n": 1,
            "selecciones_totales_n": 5,
        })

        caso.update(
            Hora="21:00:00", tipo_ubicacion_vial="CRUCE_SEMAFORO_APAGADO",
            pavimento_adverso=0, causa_especifica="OTRA",
        )
        matriz, _ = construir_matriz(pd.DataFrame([caso]))
        self.assertEqual(matriz["siniestros_objetivo_n"].tolist(), [0, 0, 0, 0, 0, 0])

    def test_hora_invalida_no_se_asigna_a_madrugada(self):
        with self.assertRaises(ValueError):
            construir_matriz(pd.DataFrame([siniestro(Hora="24:00:00", TIPO__CONA="CHOQUE")]))

    def test_cruce_requiere_dos_calles_distintas_y_semaforo_activo(self):
        caso = siniestro(
            Hora="08:00:00", Calle_Uno_norm="LAS CONDES", Calle_Dos_norm="VIA SECUNDARIA",
            usuario_vulnerable=1, tipo_ubicacion_vial="CRUCE_SEMAFORIZADO",
        )
        variantes_excluidas = (
            {**caso, "Calle_Dos_norm": None},
            {**caso, "Calle_Dos_norm": "LAS CONDES"},
            {**caso, "tipo_ubicacion_vial": "CRUCE_SEMAFORO_APAGADO"},
        )
        matriz, _ = construir_matriz(pd.DataFrame([caso, *variantes_excluidas]))
        self.assertEqual(matriz.set_index("id_medida").at["MIT-01", "siniestros_objetivo_n"], 1)

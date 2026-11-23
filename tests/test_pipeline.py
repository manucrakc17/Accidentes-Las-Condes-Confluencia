import importlib.util
import json
from datetime import time
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


def load_script(filename):
    path = Path(__file__).resolve().parents[1] / "desarrollo" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleaning = load_script("01_limpieza_y_correccion_solar.py")
pipeline = load_script("run_all.py")


class SolarTest(unittest.TestCase):
    def test_hora_local_rejects_unusable_input(self):
        self.assertEqual(cleaning.parse_hora_to_minutes(time(6, 30)), 390)
        self.assertAlmostEqual(cleaning.parse_hora_to_minutes("6:30:30.500"), 390 + 30.5 / 60)
        for value in ("", "24:00", "6:99:00", "6:30:99", "6:30:00 PM", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cleaning.parse_hora_to_minutes(value)

    def test_periodo_solar_uses_common_boundaries(self):
        self.assertEqual(cleaning.classify_solar_period(-18), ("noche", 1, 0))
        self.assertEqual(cleaning.classify_solar_period(-6), ("crepusculo", 1, 0))
        self.assertEqual(cleaning.classify_solar_period(0), ("crepusculo", 1, 0))
        self.assertEqual(cleaning.classify_solar_period(0.01), ("dia", 0, 1))

    def test_cruce_sin_senal_is_not_classified_as_signposted(self):
        self.assertEqual(cleaning.categorize_ubicacion("CRUCE SIN SENALIZACION"), "CRUCE_SIN_SENALIZACION")
        self.assertEqual(cleaning.categorize_ubicacion("CRUCE CON SENAL PARE"), "CRUCE_PRIORIDAD_SENAL")


class ManifestTest(unittest.TestCase):
    def test_discards_only_reserved_staging_directories(self):
        with TemporaryDirectory() as folder:
            output = Path(folder)
            staging = output / f"{pipeline.STAGING_PREFIX}interrumpida"
            staging.mkdir()
            preserved = output / "aporte_manual"
            preserved.mkdir()
            outside = output / f"{pipeline.STAGING_PREFIX}enlace"
            outside.symlink_to(preserved, target_is_directory=True)
            pipeline.discard_interrupted_staging(output)
            self.assertFalse(staging.exists())
            self.assertTrue(preserved.exists())
            self.assertTrue(outside.is_symlink())

    def test_fails_on_same_size_tampering_and_extra_files(self):
        with TemporaryDirectory() as folder:
            output = Path(folder)
            for name in pipeline.PUBLIC_FILES:
                (output / name).write_bytes(b"ok")
            manifest = {
                "total_archivos_evidencia": len(pipeline.PUBLIC_FILES),
                "archivos": pipeline.artifact_records(output),
            }
            (output / pipeline.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(pipeline.verify_manifest(output), len(pipeline.PUBLIC_FILES))
            extra = output / pipeline.PRIVATE_CSV_NAME
            extra.write_bytes(b"test")
            with self.assertRaisesRegex(ValueError, "inesperadas"):
                pipeline.verify_manifest(output)
            extra.unlink()
            (output / pipeline.PUBLIC_FILES[0]).write_bytes(b"no")
            with self.assertRaisesRegex(ValueError, "hashes"):
                pipeline.verify_manifest(output)


if __name__ == "__main__":
    unittest.main()

import unittest
from app.sadci import calcular_porcentaje, cargar_catalogo, cumple_meta, evaluar_catalogo, validar_catalogo

class SadciTests(unittest.TestCase):
    def test_percentages(self):
        self.assertAlmostEqual(calcular_porcentaje(1, 4), 25.0)
        self.assertAlmostEqual(calcular_porcentaje(420000000, 500000000), 84.0)
    def test_missing_or_invalid_denominator(self):
        self.assertIsNone(calcular_porcentaje(1, 0))
        self.assertIsNone(calcular_porcentaje(None, 4))
        self.assertIsNone(calcular_porcentaje("x", 4))
    def test_strict_thresholds(self):
        self.assertTrue(cumple_meta(19.9, "<", 20))
        self.assertFalse(cumple_meta(20, "<", 20))
        self.assertTrue(cumple_meta(85.1, ">", 85))
        self.assertFalse(cumple_meta(85, ">", 85))
    def test_catalog_structure_and_codes(self):
        data = cargar_catalogo()
        self.assertEqual(len(data), 10)
        self.assertEqual(len({x["codigo"] for x in data}), 10)
        self.assertEqual(validar_catalogo(data), [])
    def test_tdn_semaphore_conflict(self):
        tdn = next(x for x in evaluar_catalogo(cargar_catalogo()) if x["codigo"] == "TDN")
        self.assertEqual(tdn["resultado_calculado_pct"], 25.0)
        self.assertFalse(tdn["meta_cumplida"])
        self.assertTrue(tdn["semaforo_fuente_requiere_revision"])
    def test_source_percentages_match(self):
        for item in evaluar_catalogo(cargar_catalogo()):
            self.assertAlmostEqual(item["resultado_calculado_pct"], item["resultado_fuente_pct"], delta=0.02, msg=item["codigo"])

if __name__ == "__main__":
    unittest.main()

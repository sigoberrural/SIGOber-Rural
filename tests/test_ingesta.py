import unittest
import pandas as pd

from app.ingesta import (
    aplicar_actualizacion_sadci,
    crear_excel_plantilla,
    validar_importacion_sadci,
    validar_problematicas,
)


class IngestionTests(unittest.TestCase):
    def test_templates_are_valid_xlsx(self):
        for tipo in ("problematicas", "sadci"):
            data = crear_excel_plantilla(tipo, [{"codigo": "TDN"}])
            self.assertTrue(data.startswith(b"PK"))

    def test_problematicas_detects_missing_fields_and_duplicate_ids(self):
        df = pd.DataFrame([
            {"id_registro": "A", "vereda": "X", "categoria": "agua", "descripcion": "Falta agua", "fuente": "Taller"},
            {"id_registro": "A", "vereda": "X", "categoria": "agua", "descripcion": "Falta agua", "fuente": "Taller"},
        ])
        result = validar_problematicas(df)
        self.assertFalse(result["valido_revision_tecnica"].any())
        self.assertTrue(result["errores_validacion"].str.contains("ID duplicado").all())

    def test_sadci_validation_and_session_overlay(self):
        catalogo = [{"codigo": "TDN", "valor_numerador": 1, "valor_denominador": 4, "fuentes": "Original"}]
        df = pd.DataFrame([{
            "codigo": "TDN", "periodo": "2026", "valor_numerador": "2",
            "valor_denominador": "5", "fuentes": "Informe", "responsable": "Equipo",
        }])
        validated = validar_importacion_sadci(df, catalogo)
        self.assertTrue(validated["valido_revision_tecnica"].all())
        actualizados = aplicar_actualizacion_sadci(catalogo, validated[validated["valido_revision_tecnica"]], "2026")
        self.assertEqual(actualizados[0]["valor_numerador"], 2.0)
        self.assertEqual(catalogo[0]["valor_numerador"], 1)

    def test_unknown_sadci_code_rejected(self):
        df = pd.DataFrame([{"codigo": "XX", "periodo": "2026", "valor_numerador": "1", "valor_denominador": "2"}])
        result = validar_importacion_sadci(df, [{"codigo": "TDN"}])
        self.assertFalse(result["valido_revision_tecnica"].iloc[0])


if __name__ == "__main__":
    unittest.main()

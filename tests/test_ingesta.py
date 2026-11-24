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

    def test_original_sadci_template_keeps_working_columns(self):
        from io import BytesIO
        import openpyxl

        data = crear_excel_plantilla("sadci")
        workbook = openpyxl.load_workbook(BytesIO(data), data_only=True)
        self.assertEqual(workbook.sheetnames, ["Glosario y Guía", "Variables de Cálculo"])
        ws = workbook["Variables de Cálculo"]
        self.assertEqual(
            [cell.value for cell in ws[1]],
            [
                "codigo_variable", "nombre_variable_o_indicador", "periodo",
                "valor_ingresado", "unidad_medida", "fuente_informacion",
                "responsable_reporte", "fecha_corte", "observaciones",
            ],
        )
        self.assertEqual(ws.max_row, 7)
        self.assertEqual(ws["A2"].value, "presupuesto_anual_rural")
        self.assertEqual(ws["A7"].value, "calificacion_mepi")

    def test_original_sadci_rows_validate_without_numerator_denominator(self):
        df = pd.DataFrame([{
            "codigo_variable": "presupuesto_anual_rural",
            "nombre_variable_o_indicador": "Presupuesto Anual Rural",
            "periodo": "2026",
            "valor_ingresado": "5304139831",
            "unidad_medida": "COP ($)",
            "fuente_informacion": "Informe de ejecución",
            "responsable_reporte": "Equipo",
            "fecha_corte": "2026-06-30",
            "observaciones": "",
        }])
        result = validar_importacion_sadci(df, [])
        self.assertTrue(result["valido_revision_tecnica"].iloc[0])

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

import unittest

import pandas as pd

from app.cartografia_social import validar_registros


class ValidarRegistrosTests(unittest.TestCase):
    def registro_valido(self):
        return {
            "id_registro": "CS-001",
            "taller_id": "T-001",
            "fecha": "2026-10-01",
            "vereda": "Vereda de prueba",
            "categoria": "INFRAESTRUCTURA_CRITICA",
            "descripcion": "Puente reportado por participantes",
            "geometria_tipo": "punto",
            "latitud": "1.9",
            "longitud": "-75.2",
            "fuente": "Taller participativo",
            "estado_validacion": "PENDIENTE",
            "geometria_geojson": '{"type":"Point","coordinates":[-75.2,1.9]}',
        }

    def test_registro_valido_pasa_revision_tecnica(self):
        resultado = validar_registros(pd.DataFrame([self.registro_valido()]))
        self.assertTrue(bool(resultado.iloc[0]["valido_revision_tecnica"]))

    def test_latitud_fuera_de_rango_es_reportada(self):
        fila = self.registro_valido()
        fila["latitud"] = "95"
        resultado = validar_registros(pd.DataFrame([fila]))
        self.assertFalse(bool(resultado.iloc[0]["valido_revision_tecnica"]))
        self.assertIn("latitud fuera del rango WGS84", resultado.iloc[0]["errores_validacion"])

    def test_geojson_malformado_es_reportado(self):
        fila = self.registro_valido()
        fila["geometria_geojson"] = "{invalido"
        resultado = validar_registros(pd.DataFrame([fila]))
        self.assertIn("no contiene JSON válido", resultado.iloc[0]["errores_validacion"])

    def test_categoria_no_reconocida_no_se_inventa(self):
        fila = self.registro_valido()
        fila["categoria"] = "INDICADOR_DEFINITIVO_INVENTADO"
        resultado = validar_registros(pd.DataFrame([fila]))
        self.assertIn("Categoría general no reconocida", resultado.iloc[0]["errores_validacion"])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.territorio import leer_eventos_territoriales, resumir_eventos_por_vereda


ENCABEZADO = (
    "id,fecha,anio,vereda_referencia,codigo_ver_resuelto,nombre_capa_resuelto,"
    "tipo_conflicto,subtipo,confianza,precision_espacial,fuente,tipo_fuente,url,"
    "estado_territorial"
)


class EventosTerritorialesTests(unittest.TestCase):
    def test_lectura_separa_filas_con_numero_incorrecto_de_columnas(self):
        contenido = (
            ENCABEZADO + "\n"
            "EV-1,2024-01-01,2024,Vereda A,001,VEREDA A,Conflicto,Acción,ALTA,"
            "VEREDA,Fuente,Oficial,https://fuente.gov,VALIDADA_EN_CAPA\n"
            "EV-2,2024-01-01,2024,Vereda B,,VEREDA B,,,,ALTA,VEREDA,Fuente,Oficial,"
            "PENDIENTE\n"
        )
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "eventos.csv"
            ruta.write_text(contenido, encoding="utf-8")
            datos, auditoria = leer_eventos_territoriales(ruta)

        self.assertEqual(len(datos), 1)
        self.assertEqual(datos.iloc[0]["id"], "EV-1")
        self.assertEqual(len(auditoria["filas_incompletas"]), 1)
        self.assertEqual(auditoria["filas_incompletas"][0]["id"], "EV-2")

    def test_solo_agrega_registros_validados_a_escala_vereda(self):
        datos = pd.DataFrame([
            {"id": "EV-1", "codigo_ver_resuelto": "001", "estado_territorial": "VALIDADA_EN_CAPA",
             "precision_espacial": "VEREDA", "anio": "2024", "tipo_conflicto": "Conflicto", "confianza": "ALTA"},
            {"id": "EV-2", "codigo_ver_resuelto": "002", "estado_territorial": "PENDIENTE",
             "precision_espacial": "VEREDA", "anio": "2024", "tipo_conflicto": "Conflicto", "confianza": "ALTA"},
            {"id": "EV-3", "codigo_ver_resuelto": "003", "estado_territorial": "VALIDADA_EN_CAPA",
             "precision_espacial": "CORREGIMIENTO + VEREDAS", "anio": "2024", "tipo_conflicto": "Conflicto", "confianza": "ALTA"},
            {"id": "EV-4", "codigo_ver_resuelto": "999", "estado_territorial": "VALIDADA_EN_CAPA",
             "precision_espacial": "VEREDA", "anio": "2024", "tipo_conflicto": "Conflicto", "confianza": "ALTA"},
        ])

        resumen = resumir_eventos_por_vereda(datos, {"001", "002", "003"})

        self.assertEqual(resumen["codigo_ver_resuelto"].tolist(), ["001"])
        self.assertEqual(int(resumen.iloc[0]["SIGOber_situaciones"]), 1)

    def test_no_agrega_si_faltan_columnas_de_validacion(self):
        resumen = resumir_eventos_por_vereda(
            pd.DataFrame([{"codigo_ver_resuelto": "001"}]), {"001"}
        )
        self.assertTrue(resumen.empty)


if __name__ == "__main__":
    unittest.main()

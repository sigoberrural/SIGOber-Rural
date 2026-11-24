"""Funciones puras para validar registros de cartografía social.

Las comprobaciones son técnicas y no equivalen a validación metodológica o factual.
"""
import json

import pandas as pd

CATEGORIAS = {
    "TENENCIA_USO_TIERRA",
    "PRESENCIA_AUSENCIA_INSTITUCIONAL",
    "INFRAESTRUCTURA_CRITICA",
    "CONFLICTO_ARMADO",
}
CAMPOS = [
    "id_registro", "taller_id", "fecha", "vereda", "codigo_ver", "categoria",
    "subcategoria", "descripcion", "geometria_tipo", "latitud", "longitud",
    "geometria_geojson", "fuente", "tipo_fuente", "participante_tipo",
    "confianza", "estado_validacion", "observaciones",
]
OBLIGATORIOS = [
    "id_registro", "taller_id", "fecha", "vereda", "categoria",
    "descripcion", "geometria_tipo", "fuente", "estado_validacion",
]
ESTADOS = {"PENDIENTE", "VALIDADA", "REQUIERE_REVISION"}
TIPOS_GEOMETRIA = {"punto", "línea", "linea", "polígono", "poligono", "sin_geometria"}
TIPOS_GEOJSON = {
    "Point", "LineString", "Polygon", "MultiPoint",
    "MultiLineString", "MultiPolygon",
}


def validar_registros(df):
    """Devuelve copia con errores por fila; no corrige ni imputa valores."""
    resultado = df.copy()
    for campo in CAMPOS:
        if campo not in resultado.columns:
            resultado[campo] = ""
    resultado["errores_validacion"] = ""

    def agregar_error(idx, mensaje):
        previo = str(resultado.at[idx, "errores_validacion"] or "")
        resultado.at[idx, "errores_validacion"] = f"{previo}; {mensaje}".strip("; ")

    for idx, fila in resultado.iterrows():
        for campo in OBLIGATORIOS:
            if pd.isna(fila[campo]) or not str(fila[campo]).strip():
                agregar_error(idx, f"Falta {campo}")

        categoria = str(fila["categoria"]).strip().upper()
        if categoria and categoria not in CATEGORIAS:
            agregar_error(idx, "Categoría general no reconocida; requiere revisión")
        tipo = str(fila["geometria_tipo"]).strip().lower()
        if tipo and tipo not in TIPOS_GEOMETRIA:
            agregar_error(idx, "geometria_tipo no reconocido")

        for campo, minimo, maximo in [("latitud", -90, 90), ("longitud", -180, 180)]:
            valor = fila[campo]
            if pd.notna(valor) and str(valor).strip():
                try:
                    numero = float(str(valor).replace(",", "."))
                    if not minimo <= numero <= maximo:
                        agregar_error(idx, f"{campo} fuera del rango WGS84")
                except (ValueError, TypeError):
                    agregar_error(idx, f"{campo} no es numérico")

        estado = str(fila["estado_validacion"]).strip().upper()
        if estado and estado not in ESTADOS:
            agregar_error(idx, "estado_validacion no reconocido")

        geojson = fila["geometria_geojson"]
        if pd.notna(geojson) and str(geojson).strip():
            try:
                geometria = json.loads(str(geojson))
                if not isinstance(geometria, dict):
                    raise ValueError("GeoJSON debe ser un objeto")
                if geometria.get("type") not in TIPOS_GEOJSON:
                    agregar_error(idx, "Tipo de geometría GeoJSON no soportado")
                elif geometria.get("type") == "Point":
                    coords = geometria.get("coordinates")
                    if (not isinstance(coords, list) or len(coords) < 2
                            or not all(isinstance(v, (int, float)) for v in coords[:2])
                            or not -180 <= coords[0] <= 180
                            or not -90 <= coords[1] <= 90):
                        agregar_error(idx, "Coordenadas Point inválidas; GeoJSON usa [longitud, latitud]")
            except (ValueError, TypeError, json.JSONDecodeError):
                agregar_error(idx, "geometria_geojson no contiene JSON válido")
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
    return resultado

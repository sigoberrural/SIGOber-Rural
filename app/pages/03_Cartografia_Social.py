"""Revisión y preparación de registros de cartografía social.

Esta página no calcula indicadores ni publica índices de aislamiento/superposición.
"""
import json
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cartografía social | SIGOber-Rural", layout="wide")
st.title("Cartografía social")
st.caption("Importación y control de calidad preliminar de registros participativos")
st.warning(
    "Herramienta de preparación de datos. Las categorías y validaciones no sustituyen "
    "la aprobación de la matriz metodológica. No se calculan índices territoriales."
)

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


def validar_registros(df):
    """Devuelve una copia con errores por fila; no corrige ni imputa valores."""
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
                tipo_geo = geometria.get("type")
                if tipo_geo not in {"Point", "LineString", "Polygon", "MultiPoint",
                                    "MultiLineString", "MultiPolygon"}:
                    agregar_error(idx, "Tipo de geometría GeoJSON no soportado")
            except (ValueError, TypeError, json.JSONDecodeError):
                agregar_error(idx, "geometria_geojson no contiene JSON válido")
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
    return resultado


st.markdown("#### Plantilla de registro")
st.write("Campos obligatorios:", ", ".join(OBLIGATORIOS))
plantilla = pd.DataFrame(columns=CAMPOS)
st.download_button(
    "Descargar plantilla CSV",
    plantilla.to_csv(index=False).encode("utf-8-sig"),
    file_name="plantilla_cartografia_social.csv",
    mime="text/csv",
)

archivo = st.file_uploader("Cargar CSV de registros digitalizados", type=["csv"])
if archivo is not None:
    try:
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False)
        revisado = validar_registros(df)
        correctos = int(revisado["valido_revision_tecnica"].sum())
        total = len(revisado)
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros", total)
        c2.metric("Sin errores técnicos detectados", correctos)
        c3.metric("Requieren revisión", total - correctos)
        st.caption(
            "La ausencia de errores técnicos no significa validación metodológica ni "
            "confirmación factual de la observación."
        )
        st.dataframe(revisado, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar CSV revisado",
            revisado.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"cartografia_social_revision_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    except Exception as exc:
        st.error(f"No se pudo leer el CSV: {exc}")

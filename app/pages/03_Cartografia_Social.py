"""Interfaz de revisión técnica para registros de cartografía social."""
from datetime import date

import pandas as pd
import streamlit as st

from app.cartografia_social import CAMPOS, OBLIGATORIOS, validar_registros

st.set_page_config(page_title="Cartografía social · SIGOber-Rural", page_icon="📍", layout="wide")


with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    st.markdown("**Espacios de trabajo**")
    st.page_link("main.py", label="Ingesta y gestión de datos", icon="📥")
    st.page_link("pages/01_Exploracion.py", label="Exploración de resultados", icon="🗺️")
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")
st.markdown("""
<style>
.cs-hero{padding:1.05rem 1.25rem 1.1rem;border:1px solid rgba(128,128,128,.22);border-radius:1rem;background:linear-gradient(115deg,rgba(31,91,75,.12),rgba(91,128,108,.025));margin:.2rem 0 1rem}
.cs-eyebrow{font-size:.73rem;letter-spacing:.13em;text-transform:uppercase;font-weight:750;opacity:.65}
.cs-hero h1{font-size:2rem;line-height:1.1;margin:.2rem 0 .4rem}
.cs-hero p{margin:0;opacity:.78;max-width:850px}
.cs-card{padding:.8rem .9rem;border:1px solid rgba(128,128,128,.2);border-radius:.8rem;background:rgba(128,128,128,.025)}
div[data-testid="stMetric"]{padding:.55rem .7rem;border:1px solid rgba(128,128,128,.17);border-radius:.72rem;background:rgba(128,128,128,.03)}
</style>
<div class="cs-hero">
  <div class="cs-eyebrow">SIGOber-Rural · conocimiento comunitario</div>
  <h1>Cartografía social</h1>
  <p>Preparación, revisión técnica y trazabilidad de observaciones participativas del territorio rural.</p>
</div>
""", unsafe_allow_html=True)

st.info(
    "**Uso recomendado:** 1) descarga la plantilla, 2) completa una fila por observación, "
    "3) carga el CSV para revisar errores, 4) corrige y vuelve a cargar, y 5) conserva la fuente "
    "y el acta o taller que respalda cada registro."
)

st.warning(
    "La revisión automática detecta problemas de estructura, categorías, coordenadas y GeoJSON. "
    "No valida la veracidad de una observación ni sustituye la revisión metodológica comunitaria."
)

tab_revision, tab_plantilla, tab_protocolo = st.tabs(
    ["Revisar registros", "Plantilla de captura", "Criterios y trazabilidad"]
)

with tab_revision:
    st.subheader("Importar una tabla de registros")
    st.write("Carga un archivo CSV digitalizado. El original no se modifica y el resultado revisado se puede descargar.")
    archivo = st.file_uploader("Archivo CSV", type=["csv"], key="cs_upload")
    if archivo is None:
        st.info("Todavía no hay un archivo cargado. Puedes descargar la plantilla en la pestaña siguiente.")
    else:
        try:
            df = pd.read_csv(archivo, dtype=str, keep_default_na=False)
            revisado = validar_registros(df)
            total = len(revisado)
            correctos = int(revisado["valido_revision_tecnica"].sum())
            con_errores = total - correctos
            c1, c2, c3 = st.columns(3)
            c1.metric("Registros leídos", total)
            c2.metric("Sin errores técnicos detectados", correctos)
            c3.metric("Requieren revisión técnica", con_errores)
            if total == 0:
                st.warning("El CSV no contiene registros. Revisa que tenga una fila por observación.")
            elif con_errores == 0:
                st.success("No se detectaron errores técnicos en los registros cargados. Aún requieren validación factual y metodológica.")
            else:
                st.error(f"Hay {con_errores} registros con uno o más problemas técnicos.")

            if "categoria" in revisado.columns and total:
                conteo = (
                    revisado.assign(categoria=revisado["categoria"].replace("", "Sin categoría"))
                    .groupby("categoria", dropna=False)
                    .size()
                    .rename("Registros")
                    .reset_index()
                )
                with st.expander("Resumen por categoría", expanded=False):
                    st.dataframe(conteo, use_container_width=True, hide_index=True)

            solo_errores = st.checkbox("Mostrar solo registros que requieren revisión", value=con_errores > 0)
            vista = revisado.loc[~revisado["valido_revision_tecnica"]] if solo_errores else revisado
            columnas = ["id_registro", "fecha", "vereda", "codigo_ver", "categoria", "descripcion",
                        "geometria_tipo", "latitud", "longitud", "estado_validacion",
                        "valido_revision_tecnica", "errores_validacion"]
            columnas = [c for c in columnas if c in vista.columns]
            st.dataframe(vista[columnas], use_container_width=True, hide_index=True)
            st.caption(
                f"Mostrando {len(vista)} de {total} registros. "
                "La columna de errores explica qué debe corregirse; la aplicación no imputa ni corrige valores."
            )

            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button(
                    "Descargar revisión completa",
                    data=revisado.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"cartografia_social_revision_{date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    disabled=total == 0,
                )
            with ex2:
                st.download_button(
                    "Descargar solo registros con errores",
                    data=revisado.loc[~revisado["valido_revision_tecnica"]].to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"cartografia_social_pendientes_{date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    disabled=con_errores == 0,
                )
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
            st.error(f"No se pudo interpretar el CSV. Revisa su codificación y estructura: {exc}")
        except Exception as exc:
            st.error(f"Ocurrió un error al revisar el archivo: {type(exc).__name__}: {exc}")

with tab_plantilla:
    st.subheader("Plantilla de captura")
    st.write("La plantilla incluye todos los campos esperados por el validador. Completa una fila por observación participativa.")
    plantilla = pd.DataFrame(columns=CAMPOS)
    st.download_button(
        "Descargar plantilla CSV",
        data=plantilla.to_csv(index=False).encode("utf-8-sig"),
        file_name="plantilla_cartografia_social.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown("**Campos obligatorios:** " + ", ".join(OBLIGATORIOS))
    st.markdown("**Categorías generales admitidas:**")
    st.code(
        "TENENCIA_USO_TIERRA\nPRESENCIA_AUSENCIA_INSTITUCIONAL\nINFRAESTRUCTURA_CRITICA\nCONFLICTO_ARMADO",
        language="text",
    )
    st.caption("Las categorías son un vocabulario controlado de trabajo. Los casos que no encajen deben documentarse para revisión metodológica, no forzarse a una categoría.")

with tab_protocolo:
    st.subheader("Qué comprueba la revisión")
    controles = [
        ("Completitud", "Comprueba la presencia de campos obligatorios."),
        ("Vocabulario", "Comprueba categorías, tipos de geometría y estados reconocidos."),
        ("Coordenadas", "Comprueba formato numérico y rangos de latitud/longitud."),
        ("GeoJSON", "Comprueba estructura JSON y tipos de geometría admitidos; para puntos revisa orden longitud/latitud y rangos."),
        ("Trazabilidad", "Conserva identificadores, fecha, vereda, fuente, tipo de fuente, participante, confianza y observaciones cuando estén disponibles."),
    ]
    for titulo, detalle in controles:
        st.markdown(f"- **{titulo}:** {detalle}")
    st.subheader("Límites y flujo de trabajo")
    st.markdown(
        "1. Importar el CSV y revisar las filas señaladas.\n"
        "2. Corregir los datos en la fuente de trabajo y volver a cargar el archivo.\n"
        "3. Contrastar la observación con el acta, taller o fuente indicada.\n"
        "4. Cambiar el estado de validación solo mediante el procedimiento acordado por el equipo.\n"
        "5. Conservar la fuente y la fecha de revisión para que el registro sea auditable."
    )
    st.info(
        "Esta página no guarda los registros de forma permanente ni sincroniza automáticamente la información con Google Sheets. "
        "Los cambios deben descargarse y guardarse en el repositorio o sistema de datos autorizado."
    )

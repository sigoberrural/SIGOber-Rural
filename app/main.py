"""
=============================================================================
PROYECTO: SIGOber-Rural
ARCHIVO: main.py (Rama Develope - Módulo de Ingesta y Gestión de Datos)
DESCRIPCIÓN: Aplicación principal de Streamlit para la incorporación, validación 
             y gestión temporal de datos territoriales, organizada con un diseño 
             de controles a la izquierda y resultados a la derecha.
=============================================================================
"""

from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import streamlit as st

# =============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO Y RUTAS DEL SISTEMA
# =============================================================================

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingesta import (
    crear_excel_plantilla, leer_archivo_tabular,
    validar_importacion_sadci, validar_problematicas,
)
from app.sadci import cargar_catalogo

st.set_page_config(page_title="Ingesta de datos · SIGOber-Rural", page_icon="📥", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Inicialización de variables de estado en la sesión
st.session_state.setdefault("sigo_uploads", {})
st.session_state.setdefault("sigo_upload_widget_version", 0)
st.session_state.setdefault("sigo_problematicas_validadas", None)
st.session_state.setdefault("sigo_sadci_importado", None)


# =============================================================================
# 2. BARRA LATERAL (SIDEBAR) - ESPACIOS FIJOS Y PANEL INFERIOR DESPLEGABLE
# =============================================================================

with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    
    st.markdown("**Espacios de trabajo**")
    st.markdown("📥 **Ingesta y gestión de datos** *(Activo)*")
    st.page_link("pages/01_Exploracion.py", label="Visualización de resultados", icon="🗺️")
    
    st.divider()
    
    with st.expander("⚙️ Opciones y configuración", expanded=True):
        st.markdown("**Módulo de Ingesta**")
        st.caption("Herramientas activas en esta vista:")
        st.markdown("• Plantilla de problemáticas")
        st.markdown("• Actualización institucional SADCI")
        st.markdown("• Gestión de archivos temporales")
        
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")


# =============================================================================
# 3. INTERFAZ DE USUARIO - CABECERA Y ESTILOS CSS
# =============================================================================

st.markdown("""
<style>
.ingesta-hero{padding:1.35rem 1.5rem;border:1px solid rgba(128,128,128,.2);border-radius:1.1rem;background:linear-gradient(118deg,rgba(38,105,78,.14),rgba(122,143,102,.035));margin:.25rem 0 1rem}
.ingesta-kicker{font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;font-weight:750;opacity:.65}
.ingesta-hero h1{font-size:2.15rem;line-height:1.15;margin:.25rem 0 .4rem}
.ingesta-hero p{max-width:850px;margin:0;opacity:.8}
.ingesta-step{padding:.75rem .85rem;border:1px solid rgba(128,128,128,.2);border-radius:.8rem;background:rgba(128,128,128,.025);min-height:94px}
.ingesta-step strong{display:block;margin-bottom:.2rem}
.ingesta-step span{font-size:.84rem;opacity:.75}
</style>
<div class="ingesta-hero">
  <div class="ingesta-kicker">SIGOber-Rural · Puerto Rico, Caquetá</div>
  <h1>Ingesta y gestión de datos</h1>
  <p>Incorpora información territorial mediante plantillas guiadas. Revisa los datos antes de confirmarlos y consulta después los resultados en el espacio de visualización.</p>
</div>
""", unsafe_allow_html=True)

st.info("**Importante:** los archivos confirmados permanecen disponibles durante la sesión activa. Esta versión todavía no los guarda en una base de datos compartida ni garantiza su conservación al cerrar la sesión.")


# =============================================================================
# 4. PESTAÑAS PRINCIPALES DE GESTIÓN (TABS) - DISEÑO IZQ (CONTROLES) / DER (RESULTADOS)
# =============================================================================

tab_social, tab_sadci, tab_archivos = st.tabs(["Problemáticas por vereda", "Capacidad institucional · SADCI", "Archivos de apoyo"])


# -----------------------------------------------------------------------------
# 4.1. MÓDULO: Problemáticas por vereda
# -----------------------------------------------------------------------------
with tab_social:
    col_izq, col_der = st.columns([1, 1.4], gap="large")
    
    with col_izq:
        st.subheader("1. Controles y Carga")
        st.write("Descarga la plantilla, complétala con una fila por observación y cárgala aquí.")
        
        st.download_button(
            "Descargar plantilla Excel de problemáticas",
            data=crear_excel_plantilla("problematicas"),
            file_name="plantilla_problematicas_sigo_rural.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("Campos clave: ID, código y nombre de vereda, categoría, descripción, fecha, coordenadas opcionales, fuente y estado de validación.")
        
        st.divider()
        social_file = st.file_uploader("Carga tu plantilla completada (CSV o Excel)", type=["csv", "xlsx", "xls"], key="sigo_social_template")
        
        # Lógica de procesamiento de archivo subido
        social_df = None
        reviewed = None
        valid_count = 0
        if social_file is not None:
            try:
                social_df = leer_archivo_tabular(social_file)
                reviewed = validar_problematicas(social_df)
                valid_count = int(reviewed["valido_revision_tecnica"].sum())
            except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
                st.error(f"No se pudo leer la plantilla: {exc}")

        if reviewed is not None:
            st.divider()
            if valid_count != len(reviewed):
                st.error("Hay filas con errores técnicos. Corrígelas antes de confirmar.")
            elif reviewed.empty:
                st.warning("El archivo no contiene filas.")
            else:
                st.info("Validación técnica exitosa. Puedes confirmar la incorporación.")
                if st.button("Confirmar e incorporar a esta sesión", key="confirm_social_import", type="primary", use_container_width=True):
                    st.session_state.sigo_problematicas_validadas = reviewed.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                    st.success(f"Se incorporaron {len(reviewed)} registros a la sesión actual.")
                    st.rerun()

        if st.session_state.sigo_problematicas_validadas is not None:
            if st.button("Retirar problemáticas de esta sesión", key="clear_social_import", use_container_width=True):
                st.session_state.sigo_problematicas_validadas = None
                st.rerun()

    with col_der:
        st.subheader("2. Resultados y Validación")
        if social_file is not None and reviewed is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("Filas leídas", len(reviewed))
            c2.metric("Sin errores", valid_count)
            c3.metric("Con errores", len(reviewed) - valid_count)
            
            st.markdown("**Vista previa del informe de validación:**")
            st.dataframe(reviewed, use_container_width=True, hide_index=True)
            st.download_button("Descargar informe de validación", reviewed.to_csv(index=False).encode("utf-8-sig"), "revision_problematicas.csv", "text/csv", use_container_width=True)
        else:
            st.info("Sube un archivo en el panel izquierdo para ver los resultados de validación y métricas aquí.")

        if st.session_state.sigo_problematicas_validadas is not None:
            current = st.session_state.sigo_problematicas_validadas
            st.success(f"Registros activos en sesión: {len(current)}")
            with st.expander("Ver registros incorporados en sesión"):
                st.dataframe(current, use_container_width=True, hide_index=True)
            st.download_button("Descargar registros incorporados", current.to_csv(index=False).encode("utf-8-sig"), "problematicas_sesion.csv", "text/csv", use_container_width=True)


# -----------------------------------------------------------------------------
# 4.2. MÓDULO: Capacidad institucional · SADCI
# -----------------------------------------------------------------------------
with tab_sadci:
    col_izq_s, col_der_s = st.columns([1, 1.4], gap="large")
    
    try:
        catalogo_sadci = cargar_catalogo()
        
        with col_izq_s:
            st.subheader("1. Controles y Carga SADCI")
            st.write("Descarga la plantilla institucional, completa los valores y súbela para su revisión.")
            
            st.download_button(
                "Descargar plantilla Excel SADCI",
                data=crear_excel_plantilla("sadci", catalogo_sadci),
                file_name="plantilla_actualizacion_sadci.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption("Completa numerador, denominador, periodo, fecha de corte, fuente y responsable.")
            
            st.divider()
            sadci_file = st.file_uploader("Carga la plantilla SADCI completada (CSV o Excel)", type=["csv", "xlsx", "xls"], key="sigo_sadci_template")
            
            sadci_review = None
            valid_count_sadci = 0
            if sadci_file is not None:
                try:
                    sadci_df = leer_archivo_tabular(sadci_file)
                    sadci_review = validar_importacion_sadci(sadci_df, catalogo_sadci)
                    valid_count_sadci = int(sadci_review["valido_revision_tecnica"].sum())
                except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
                    st.error(f"No se pudo leer la plantilla SADCI: {exc}")

            if sadci_review is not None:
                st.divider()
                if valid_count_sadci != len(sadci_review) or sadci_review.empty:
                    st.error("Corrige los códigos, periodos y valores numéricos antes de confirmar.")
                else:
                    st.info("Los valores importados están listos para confirmación.")
                    if st.button("Confirmar actualización SADCI en esta sesión", key="confirm_sadci_import", type="primary", use_container_width=True):
                        st.session_state.sigo_sadci_importado = sadci_review.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                        st.success(f"Se incorporaron {len(sadci_review)} filas SADCI.")
                        st.rerun()

            if st.session_state.sigo_sadci_importado is not None:
                if st.button("Retirar actualización SADCI de esta sesión", key="clear_sadci_import", use_container_width=True):
                    st.session_state.sigo_sadci_importado = None
                    st.rerun()

        with col_der_s:
            st.subheader("2. Resultados y Validación SADCI")
            if sadci_file is not None and sadci_review is not None:
                c1, c2, c3 = st.columns(3)
                c1.metric("Filas leídas", len(sadci_review))
                c2.metric("Sin errores", valid_count_sadci)
                c3.metric("Con errores", len(sadci_review) - valid_count_sadci)
                
                st.markdown("**Vista previa del informe SADCI:**")
                st.dataframe(sadci_review, use_container_width=True, hide_index=True)
                st.download_button("Descargar informe de validación SADCI", sadci_review.to_csv(index=False).encode("utf-8-sig"), "revision_sadci.csv", "text/csv", use_container_width=True)
            else:
                st.info("Carga una plantilla SADCI en el panel izquierdo para visualizar las métricas y el informe aquí.")

            if st.session_state.sigo_sadci_importado is not None:
                current_sadci = st.session_state.sigo_sadci_importado
                st.success(f"Actualización SADCI activa en sesión: {len(current_sadci)} fila(s).")
                st.dataframe(current_sadci, use_container_width=True, hide_index=True)
                st.caption("Para consultar los resultados calculados, abre el módulo SADCI.")

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"No fue posible preparar la plantilla SADCI: {exc}")


# -----------------------------------------------------------------------------
# 4.3. MÓDULO: Archivos de apoyo (Carga temporal)
# -----------------------------------------------------------------------------
with tab_archivos:
    col_izq_a, col_der_a = st.columns([1, 1.4], gap="large")
    
    with col_izq_a:
        st.subheader("1. Controles de Carga")
        st.write("Selecciona archivos auxiliares para inspección rápida en memoria.")
        
        uploads = st.file_uploader(
            "Selecciona uno o varios archivos",
            type=["csv", "xlsx", "xls", "json", "geojson"],
            accept_multiple_files=True,
            key=f"sigo_file_uploader_{st.session_state.sigo_upload_widget_version}",
            help="Los archivos se mantienen en memoria de esta sesión.",
        )
        
        for uploaded in uploads or []:
            raw = uploaded.getvalue()
            file_id = f"{uploaded.name}::{len(raw)}::{uploaded.type}"
            st.session_state.sigo_uploads[file_id] = {
                "name": uploaded.name, "bytes": raw, "size": len(raw),
                "type": uploaded.type, "loaded_at": datetime.now().isoformat(timespec="seconds"),
            }
            
        files = list(st.session_state.sigo_uploads.items())
        
        if files:
            st.divider()
            confirm = st.checkbox("Confirmo que quiero retirar todos los archivos de esta sesión", key="confirm_clear_session_uploads")
            if st.button("Retirar todos los archivos", type="secondary", disabled=not confirm, use_container_width=True):
                st.session_state.sigo_uploads.clear()
                st.session_state.sigo_upload_widget_version += 1
                st.session_state.confirm_clear_session_uploads = False
                st.rerun()

    with col_der_a:
        st.subheader("2. Resultados y Vistas Previas")
        files = list(st.session_state.sigo_uploads.items())
        if not files:
            st.info("No hay archivos de apoyo cargados en esta sesión.")
        else:
            st.success(f"{len(files)} archivo(s) disponibles en memoria.")
            for idx, (file_id, item) in enumerate(files):
                with st.container(border=True):
                    sub_l, sub_r = st.columns([3, 1])
                    with sub_l:
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"{item['type'] or 'Tipo no identificado'} · {item['size'] / 1024:.1f} KB")
                    with sub_r:
                        if st.button("Retirar", key=f"remove_upload_{idx}", use_container_width=True):
                            del st.session_state.sigo_uploads[file_id]
                            st.session_state.sigo_upload_widget_version += 1
                            st.rerun()
                    try:
                        from io import BytesIO
                        suffix = Path(item["name"]).suffix.lower()
                        if suffix == ".csv":
                            preview = pd.read_csv(BytesIO(item["bytes"]), dtype=str, keep_default_na=False, nrows=100)
                            st.caption("Vista previa (hasta 100 filas):")
                            st.dataframe(preview, use_container_width=True, hide_index=True)
                        elif suffix in {".xlsx", ".xls"}:
                            preview = pd.read_excel(BytesIO(item["bytes"]), nrows=100)
                            st.caption("Vista previa (hasta 100 filas):")
                            st.dataframe(preview, use_container_width=True, hide_index=True)
                        elif suffix in {".json", ".geojson"}:
                            parsed = json.loads(item["bytes"].decode("utf-8-sig"))
                            if isinstance(parsed, dict) and parsed.get("type") == "FeatureCollection":
                                st.caption(f"GeoJSON · {len(parsed.get('features', []))} entidades.")
                            else:
                                st.caption("JSON válido.")
                            st.json(parsed, expanded=False)
                    except Exception as exc:
                        st.warning(f"No se pudo generar vista previa: {type(exc).__name__}")


# =============================================================================
# 5. PIE DE PÁGINA Y ENLACES A OTRAS HERRAMIENTAS
# =============================================================================

st.divider()
st.subheader("Otras herramientas de ingesta")
st.write("Para revisar la estructura y la calidad de los registros de cartografía social, abre la herramienta específica.")
st.page_link("pages/03_Cartografia_Social.py", label="Abrir revisión de cartografía social", icon="📍")
st.caption("La retirada de archivos solo afecta a la sesión actual. Los datos persistentes requieren una operación autorizada sobre su fuente.")

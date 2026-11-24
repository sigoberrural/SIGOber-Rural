"""
=============================================================================
PROYECTO: SIGOber-Rural
ARCHIVO: main.py (Rama Develope - Módulo de Ingesta y Gestión de Datos)
DESCRIPCIÓN: Aplicación principal de Streamlit para la incorporación, validación 
             y gestión temporal de datos territoriales (problemáticas por vereda, 
             actualización institucional SADCI y archivos de apoyo).
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

# Asegura que la raíz del repositorio esté disponible en el path antes de importar paquetes locales
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingesta import (
    crear_excel_plantilla, leer_archivo_tabular,
    validar_importacion_sadci, validar_problematicas,
)
from app.sadci import cargar_catalogo

# Configuración inicial de la página de Streamlit
st.set_page_config(page_title="Ingesta de datos · SIGOber-Rural", page_icon="📥", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Inicialización de variables de estado en la sesión (Session State)
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
    
    # 1. Espacios de trabajo siempre visibles en la parte superior
    st.markdown("**Espacios de trabajo**")
    st.markdown("📥 **Ingesta y gestión de datos** *(Activo)*")
    st.page_link("pages/01_Exploracion.py", label="Visualización de resultados", icon="🗺️")
    
    st.divider()
    
    # 2. Parte inferior desplegable con la configuración del espacio actual
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

# Guía visual de los 3 pasos de ingesta
paso1, paso2, paso3 = st.columns(3, gap="small")
with paso1:
    st.markdown('<div class="ingesta-step"><strong>1 · Descarga</strong><span>Elige la plantilla del tipo de información que vas a registrar.</span></div>', unsafe_allow_html=True)
with paso2:
    st.markdown('<div class="ingesta-step"><strong>2 · Completa y carga</strong><span>Rellena los campos y sube el archivo Excel o CSV.</span></div>', unsafe_allow_html=True)
with paso3:
    st.markdown('<div class="ingesta-step"><strong>3 · Revisa y confirma</strong><span>Corrige errores técnicos y confirma la incorporación a la sesión.</span></div>', unsafe_allow_html=True)

st.info("**Importante:** los archivos confirmados permanecen disponibles durante la sesión activa. Esta versión todavía no los guarda en una base de datos compartida ni garantiza su conservación al cerrar la sesión.")


# =============================================================================
# 4. PESTAÑAS PRINCIPALES DE GESTIÓN (TABS)
# =============================================================================

tab_social, tab_sadci, tab_archivos = st.tabs(["Problemáticas por vereda", "Capacidad institucional · SADCI", "Archivos de apoyo"])


# -----------------------------------------------------------------------------
# 4.1. MÓDULO: Problemáticas por vereda
# -----------------------------------------------------------------------------
with tab_social:
    st.subheader("1. Descargar plantilla de problemáticas")
    st.write("Completa una fila por observación. Conserva la fuente, la fecha y la evidencia disponible; no incluyas datos personales sensibles innecesarios.")
    
    st.download_button(
        "Descargar plantilla Excel de problemáticas",
        data=crear_excel_plantilla("problematicas"),
        file_name="plantilla_problematicas_sigo_rural.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.caption("Campos clave: ID, código y nombre de vereda, categoría, descripción, fecha, coordenadas opcionales, fuente y estado de validación.")
    st.divider()
    
    st.subheader("2. Cargar y revisar")
    social_file = st.file_uploader("Carga tu plantilla completada (CSV o Excel)", type=["csv", "xlsx", "xls"], key="sigo_social_template")
    
    if social_file is not None:
        try:
            social_df = leer_archivo_tabular(social_file)
            reviewed = validar_problematicas(social_df)
            valid_count = int(reviewed["valido_revision_tecnica"].sum())
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Filas leídas", len(reviewed))
            c2.metric("Sin errores técnicos", valid_count)
            c3.metric("Con errores", len(reviewed) - valid_count)
            
            st.dataframe(reviewed, use_container_width=True, hide_index=True)
            st.download_button("Descargar informe de validación", reviewed.to_csv(index=False).encode("utf-8-sig"), "revision_problematicas.csv", "text/csv")
            
            if valid_count != len(reviewed):
                st.error("Corrige las filas con errores y vuelve a cargar el archivo. No se puede confirmar una importación con errores técnicos.")
            elif reviewed.empty:
                st.warning("El archivo no contiene filas.")
            else:
                st.info("La validación técnica no certifica la veracidad de las observaciones. Confirma que la fuente y la evidencia fueron revisadas.")
                if st.button("Confirmar e incorporar a esta sesión", key="confirm_social_import", type="primary"):
                    st.session_state.sigo_problematicas_validadas = reviewed.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                    st.success(f"Se incorporaron {len(reviewed)} registros a la sesión actual.")
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            st.error(f"No se pudo leer la plantilla: {exc}")
            
    if st.session_state.sigo_problematicas_validadas is not None:
        current = st.session_state.sigo_problematicas_validadas
        st.success(f"Registros de problemáticas disponibles en esta sesión: {len(current)}.")
        with st.expander("Ver registros incorporados"):
            st.dataframe(current, use_container_width=True, hide_index=True)
        st.download_button("Descargar registros incorporados", current.to_csv(index=False).encode("utf-8-sig"), "problematicas_sesion.csv", "text/csv")
        if st.button("Retirar problemáticas de esta sesión", key="clear_social_import"):
            st.session_state.sigo_problematicas_validadas = None
            st.rerun()


# -----------------------------------------------------------------------------
# 4.2. MÓDULO: Capacidad institucional · SADCI
# -----------------------------------------------------------------------------
with tab_sadci:
    st.subheader("1. Descargar plantilla de actualización SADCI")
    try:
        catalogo_sadci = cargar_catalogo()
        st.download_button(
            "Descargar plantilla Excel SADCI",
            data=crear_excel_plantilla("sadci", catalogo_sadci),
            file_name="plantilla_actualizacion_sadci.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("La plantilla incluye los códigos existentes. Completa numerador, denominador, periodo, fecha de corte, fuente y responsable. El porcentaje se calcula desde esos valores.")
        st.divider()
        
        st.subheader("2. Cargar, validar y confirmar")
        sadci_file = st.file_uploader("Carga la plantilla SADCI completada (CSV o Excel)", type=["csv", "xlsx", "xls"], key="sigo_sadci_template")
        
        if sadci_file is not None:
            try:
                sadci_df = leer_archivo_tabular(sadci_file)
                sadci_review = validar_importacion_sadci(sadci_df, catalogo_sadci)
                valid_count = int(sadci_review["valido_revision_tecnica"].sum())
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Filas leídas", len(sadci_review))
                c2.metric("Sin errores técnicos", valid_count)
                c3.metric("Con errores", len(sadci_review) - valid_count)
                
                st.dataframe(sadci_review, use_container_width=True, hide_index=True)
                st.download_button("Descargar informe de validación SADCI", sadci_review.to_csv(index=False).encode("utf-8-sig"), "revision_sadci.csv", "text/csv")
                
                if valid_count != len(sadci_review) or sadci_review.empty:
                    st.error("Corrige los códigos, periodos y valores numéricos antes de confirmar.")
                else:
                    st.info("Los valores importados quedan marcados como pendientes de verificación documental. No se modifican las metas ni las fórmulas del catálogo.")
                    if st.button("Confirmar actualización SADCI en esta sesión", key="confirm_sadci_import", type="primary"):
                        st.session_state.sigo_sadci_importado = sadci_review.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                        st.success(f"Se incorporaron {len(sadci_review)} filas SADCI a la sesión actual.")
            except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
                st.error(f"No se pudo leer la plantilla SADCI: {exc}")
                
        if st.session_state.sigo_sadci_importado is not None:
            current = st.session_state.sigo_sadci_importado
            st.success(f"Actualización SADCI cargada en esta sesión: {len(current)} fila(s).")
            st.dataframe(current, use_container_width=True, hide_index=True)
            st.caption("Para consultar los resultados calculados con estos valores, abre el módulo SADCI y carga allí la actualización. La importación todavía no se conserva entre sesiones.")
            if st.button("Retirar actualización SADCI de esta sesión", key="clear_sadci_import"):
                st.session_state.sigo_sadci_importado = None
                st.rerun()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"No fue posible preparar la plantilla SADCI: {exc}")


# -----------------------------------------------------------------------------
# 4.3. MÓDULO: Archivos de apoyo (Carga temporal)
# -----------------------------------------------------------------------------
with tab_archivos:
    st.subheader("Carga temporal de otros archivos")
    st.write("Admite CSV, Excel, JSON y GeoJSON para inspección rápida. Estos archivos no se integran automáticamente a las capas ni a los indicadores del sistema.")
    
    uploads = st.file_uploader(
        "Selecciona uno o varios archivos",
        type=["csv", "xlsx", "xls", "json", "geojson"],
        accept_multiple_files=True,
        key=f"sigo_file_uploader_{st.session_state.sigo_upload_widget_version}",
        help="Los archivos se mantienen en memoria de esta sesión; no se publican ni sincronizan automáticamente.",
    )
    
    for uploaded in uploads or []:
        raw = uploaded.getvalue()
        file_id = f"{uploaded.name}::{len(raw)}::{uploaded.type}"
        st.session_state.sigo_uploads[file_id] = {
            "name": uploaded.name, "bytes": raw, "size": len(raw),
            "type": uploaded.type, "loaded_at": datetime.now().isoformat(timespec="seconds"),
        }
        
    files = list(st.session_state.sigo_uploads.items())
    if not files:
        st.caption("Todavía no hay archivos cargados en esta sesión.")
    else:
        st.caption(f"{len(files)} archivo(s) disponibles en memoria de esta sesión.")
        for idx, (file_id, item) in enumerate(files):
            with st.container(border=True):
                left, middle, right = st.columns([3, 2, 1])
                with left:
                    st.markdown(f"**{item['name']}**")
                    st.caption(item["type"] or "Tipo no identificado")
                with middle:
                    st.metric("Tamaño", f"{item['size'] / 1024:.1f} KB")
                with right:
                    if st.button("Retirar", key=f"remove_upload_{idx}", use_container_width=True):
                        del st.session_state.sigo_uploads[file_id]
                        st.session_state.sigo_upload_widget_version += 1
                        st.rerun()
                try:
                    from io import BytesIO
                    suffix = Path(item["name"]).suffix.lower()
                    if suffix == ".csv":
                        preview = pd.read_csv(BytesIO(item["bytes"]), dtype=str, keep_default_na=False, nrows=100)
                        st.caption("Vista previa: hasta 100 filas.")
                        st.dataframe(preview, use_container_width=True, hide_index=True)
                    elif suffix in {".xlsx", ".xls"}:
                        preview = pd.read_excel(BytesIO(item["bytes"]), nrows=100)
                        st.caption("Vista previa: hasta 100 filas de la primera hoja.")
                        st.dataframe(preview, use_container_width=True, hide_index=True)
                    elif suffix in {".json", ".geojson"}:
                        parsed = json.loads(item["bytes"].decode("utf-8-sig"))
                        if isinstance(parsed, dict) and parsed.get("type") == "FeatureCollection":
                            st.caption(f"GeoJSON · {len(parsed.get('features', []))} entidades.")
                        else:
                            st.caption("JSON válido. Se muestra una vista abreviada.")
                        st.json(parsed, expanded=False)
                except Exception as exc:
                    st.warning(f"No se pudo generar una vista previa: {type(exc).__name__}. El archivo permanece en esta sesión.")
                    
        confirm = st.checkbox("Confirmo que quiero retirar todos los archivos de esta sesión", key="confirm_clear_session_uploads")
        if st.button("Retirar todos los archivos", type="secondary", disabled=not confirm, use_container_width=True):
            st.session_state.sigo_uploads.clear()
            st.session_state.sigo_upload_widget_version += 1
            st.session_state.confirm_clear_session_uploads = False
            st.rerun()


# =============================================================================
# 5. PIE DE PÁGINA Y ENLACES A OTRAS HERRAMIENTAS
# =============================================================================

st.divider()
st.subheader("Otras herramientas de ingesta")
st.write("Para revisar la estructura y la calidad de los registros de cartografía social, abre la herramienta específica.")
st.page_link("pages/03_Cartografia_Social.py", label="Abrir revisión de cartografía social", icon="📍")
st.caption("La retirada de archivos solo afecta a la sesión actual. Los datos persistentes requieren una operación autorizada sobre su fuente.")

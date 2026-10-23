"""Espacio de ingesta y gestión de datos de SIGOber-Rural."""
from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ingesta de datos · SIGOber-Rural", page_icon="📥", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
st.session_state.setdefault("sigo_uploads", {})
st.session_state.setdefault("sigo_upload_widget_version", 0)

with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    st.markdown("**Espacios de trabajo**")
    st.markdown("📥 **Ingesta y gestión de datos**")
    st.page_link("pages/01_Exploracion.py", label="Exploración de resultados", icon="🗺️")
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")

st.markdown("""
<div style="padding:1.2rem 1.35rem;border:1px solid rgba(128,128,128,.22);border-radius:1rem;
background:linear-gradient(115deg,rgba(31,91,75,.12),rgba(91,128,108,.025));margin:.2rem 0 1rem">
  <div style="font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;font-weight:750;opacity:.65">SIGOber-Rural · espacio de trabajo</div>
  <h1 style="margin:.25rem 0 .4rem">Ingesta y gestión de datos</h1>
  <p style="margin:0;opacity:.8;max-width:900px">Carga archivos, revisa una muestra y retira de esta sesión los archivos que ya no necesitas.</p>
</div>
""", unsafe_allow_html=True)

st.info("Los archivos que cargues aquí se conservan únicamente en la sesión activa de esta aplicación. Esta pantalla no modifica los archivos del repositorio, Google Sheets ni otras fuentes persistentes.")

st.subheader("1. Cargar información")
st.write("Admite CSV, Excel, JSON y GeoJSON. Después de cargar, revisa el nombre, el tamaño y una muestra antes de usar la información.")
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
        "name": uploaded.name,
        "bytes": raw,
        "size": len(raw),
        "type": uploaded.type,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    }

st.subheader("2. Archivos de esta sesión")
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
                st.warning(f"No se pudo generar una vista previa de este archivo: {type(exc).__name__}. El archivo permanece disponible en esta sesión.")

    st.divider()
    st.subheader("3. Retirar datos cargados")
    st.write("Puedes retirar un archivo individual con su botón «Retirar» o vaciar todos los archivos de esta sesión.")
    confirm = st.checkbox("Confirmo que quiero retirar todos los archivos cargados en esta sesión", key="confirm_clear_session_uploads")
    if st.button("Retirar todos los archivos de esta sesión", type="secondary", disabled=not confirm, use_container_width=True):
        st.session_state.sigo_uploads.clear()
        st.session_state.sigo_upload_widget_version += 1
        st.session_state.confirm_clear_session_uploads = False
        st.rerun()

st.divider()
st.subheader("Herramientas de ingesta")
st.write("Para revisar la estructura y la calidad de los registros de cartografía social, abre la herramienta específica. Esta revisión no guarda ni sincroniza los datos por sí sola.")
st.page_link("pages/03_Cartografia_Social.py", label="Abrir revisión de cartografía social", icon="📍")

st.caption("Importante: retirar un archivo aquí solo lo elimina de la sesión de trabajo. La eliminación de datos persistentes requiere una operación autorizada sobre su fuente y una confirmación específica.");

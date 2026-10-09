"""Revisión y preparación de registros de cartografía social."""
from datetime import date

import pandas as pd
import streamlit as st

from cartografia_social import CAMPOS, OBLIGATORIOS, validar_registros

st.set_page_config(page_title="Cartografía social | SIGOber-Rural", layout="wide")
st.title("Cartografía social")
st.caption("Importación y control de calidad preliminar de registros participativos")
st.warning(
    "Herramienta de preparación de datos. Las categorías y validaciones no sustituyen "
    "la aprobación de la matriz metodológica. No se calculan índices territoriales."
)

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

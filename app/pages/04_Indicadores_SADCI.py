"""Tablero SADCI v1.0: resultados, trazabilidad y disponibilidad territorial."""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Streamlit Cloud puede ejecutar una página multipágina con un directorio
# de trabajo distinto de la raíz del repositorio. Aseguramos la raíz en
# sys.path antes de importar el paquete local.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.sadci import cargar_catalogo, evaluar_catalogo
from app.ingesta import (
    aplicar_actualizacion_sadci, crear_excel_plantilla,
    leer_archivo_tabular, validar_importacion_sadci,
)

st.set_page_config(page_title="SADCI · SIGOber-Rural", page_icon="📊", layout="wide")


with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    st.markdown("**Espacios de trabajo**")
    st.page_link("main.py", label="Ingesta y gestión de datos", icon="📥")
    st.page_link("pages/01_Exploracion.py", label="Visualización de resultados", icon="🗺️")
    st.markdown("📊 **Indicadores SADCI**")
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")

try:
    catalogo = cargar_catalogo()
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"No fue posible cargar el catálogo SADCI: {exc}")
    st.stop()

# La importación confirmada en Ingesta se aplica como una superposición temporal
# sobre una copia del catálogo; no modifica el archivo fuente ni persiste entre sesiones.
catalogo_visualizacion = [dict(item) for item in catalogo]
importacion = st.session_state.get("sigo_sadci_importado")
if importacion is not None and not importacion.empty:
    periodos = sorted(importacion["periodo"].astype(str).str.strip().unique().tolist())
    with st.sidebar:\n        st.markdown("**Periodo de resultados**")\n        periodo_activo = st.selectbox("Actualización cargada", periodos, key="sadci_periodo_importado")
    filas_periodo = importacion[importacion["periodo"].astype(str).str.strip() == periodo_activo]
    catalogo_visualizacion = aplicar_actualizacion_sadci(catalogo_visualizacion, filas_periodo, periodo_activo)
    st.info(f"Vista temporal con {len(filas_periodo)} actualización(es) del periodo {periodo_activo}. El catálogo original permanece intacto y los datos siguen pendientes de verificación.")
evaluados = evaluar_catalogo(catalogo_visualizacion)
df = pd.DataFrame(evaluados)


df["resultado_mostrar"] = df["resultado_calculado_pct"].map(lambda x: round(float(x), 2) if pd.notna(x) else None)
df["estado_meta"] = df["estado_meta"].fillna("SIN DATOS")


with st.sidebar:
    st.divider()
    st.markdown("### Ingesta y carga SADCI")
    st.caption("Actualiza los indicadores desde una plantilla Excel. La carga queda disponible durante esta sesión.")
    try:
        st.download_button(
            "Descargar plantilla SADCI",
            data=crear_excel_plantilla("sadci", catalogo),
            file_name="plantilla_actualizacion_sadci.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        archivo_sadci = st.file_uploader("Cargar plantilla completada", type=["csv", "xlsx", "xls"], key="sadci_sidebar_upload")
        if archivo_sadci is not None:
            datos_sadci = leer_archivo_tabular(archivo_sadci)
            revision_sadci = validar_importacion_sadci(datos_sadci, catalogo)
            validos = int(revision_sadci["valido_revision_tecnica"].sum())
            st.caption(f"{len(revision_sadci)} filas · {validos} válidas · {len(revision_sadci)-validos} con errores")
            if validos == len(revision_sadci) and not revision_sadci.empty:
                if st.button("Confirmar carga SADCI", type="primary", use_container_width=True, key="sadci_sidebar_confirm"):
                    st.session_state.sigo_sadci_importado = revision_sadci.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                    st.rerun()
            else:
                st.error("Revisa los errores de la plantilla antes de confirmar.")
                st.dataframe(revision_sadci, use_container_width=True, hide_index=True)
        if st.session_state.get("sigo_sadci_importado") is not None:
            st.success(f"Actualización activa: {len(st.session_state.sigo_sadci_importado)} filas")
            if st.button("Retirar actualización", key="sadci_sidebar_clear", use_container_width=True):
                st.session_state.sigo_sadci_importado = None
                st.rerun()
    except (ValueError, UnicodeDecodeError, pd.errors.ParserError, OSError) as exc:
        st.error(f"No se pudo procesar la plantilla: {exc}")

    st.divider()
    st.markdown("### Filtrar resultados")
    dimensiones = ["Todas"] + sorted(df["dimension"].dropna().unique().tolist())
    dimension_sel = st.selectbox("Dimensión", dimensiones, key="sadci_filtro_dimension")
    busqueda = st.text_input("Buscar indicador", placeholder="Código o nombre…", key="sadci_busqueda")
    estado_sel = st.selectbox("Evaluación de meta", ["Todas", "Cumple meta", "No cumple meta", "Sin datos"], key="sadci_filtro_estado")

# La zona principal presenta exclusivamente resultados SADCI.
filtrado = df.copy()
if dimension_sel != "Todas":
    filtrado = filtrado[filtrado["dimension"] == dimension_sel]
if busqueda.strip():
    q = busqueda.strip().casefold()
    filtrado = filtrado[filtrado.apply(lambda r: q in str(r["codigo"]).casefold() or q in str(r["nombre"]).casefold(), axis=1)]
mapa_estado = {"Cumple meta": "CUMPLE META", "No cumple meta": "NO CUMPLE META", "Sin datos": "SIN DATOS"}
if estado_sel != "Todas":
    filtrado = filtrado[filtrado["estado_meta"] == mapa_estado[estado_sel]]

tabla = pd.DataFrame({
    "Código": filtrado["codigo"], "Dimensión": filtrado["dimension"],
    "Indicador": filtrado["nombre"], "Resultado (%)": filtrado["resultado_mostrar"],
    "Meta": filtrado["meta_texto"], "Evaluación": filtrado["estado_meta"],
    "Semáforo de origen": filtrado["semaforo_fuente"], "Estado del dato": filtrado["estado_dato"],
})
st.dataframe(tabla, use_container_width=True, hide_index=True, column_config={"Resultado (%)": st.column_config.NumberColumn(format="%.2f%%")})
st.caption(f"Mostrando {len(filtrado)} de {len(evaluados)} indicadores. La evaluación automática y el semáforo de origen se muestran por separado.")

export_cols = ["codigo", "dimension", "nombre", "resultado_calculado_pct", "meta_texto", "estado_meta", "semaforo_fuente", "estado_dato", "fuentes", "responsable", "periodicidad", "observaciones"]
exp1, exp2, _ = st.columns([1, 1, 3])
exp1.download_button("Descargar CSV", data=filtrado[export_cols].to_csv(index=False).encode("utf-8-sig"), file_name="indicadores_sadci_filtrados.csv", mime="text/csv", use_container_width=True)
exp2.download_button("Descargar JSON", data=json.dumps(filtrado[export_cols].to_dict(orient="records"), ensure_ascii=False, indent=2, default=str).encode("utf-8"), file_name="indicadores_sadci_filtrados.json", mime="application/json", use_container_width=True)

if not filtrado.empty:
    st.subheader("Resultados por indicador")
    graf = filtrado[["codigo", "nombre", "resultado_mostrar", "valor_meta", "dimension"]].dropna(subset=["resultado_mostrar"])
    if not graf.empty:
        graf = graf.rename(columns={"codigo": "Código", "nombre": "Indicador", "resultado_mostrar": "Resultado (%)", "valor_meta": "Umbral (%)"})
        fig = px.bar(graf, x="Resultado (%)", y="Código", orientation="h", hover_name="Indicador", hover_data={"Umbral (%)": True, "Resultado (%)": ":.2f"}, color="dimension", labels={"dimension": "Dimensión"})
        fig.update_layout(height=max(320, 42 * len(graf)), margin=dict(l=8, r=12, t=15, b=10), legend_title_text="Dimensión", xaxis_title="Resultado calculado (%)", yaxis_title="")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        st.caption("Los umbrales se muestran como referencia. Las metas tienen direcciones y escalas distintas; las barras no constituyen un ranking de desempeño.")

st.subheader("Fichas técnicas")
for x in filtrado.to_dict(orient="records"):
    with st.expander(f'{x["codigo"]} · {x["nombre"]}'):
        left, right = st.columns(2)
        with left:
            st.markdown(f'**Dimensión:** {x["dimension"]}')
            st.markdown(f'**Fórmula:** {x["formula"]}')
            st.markdown(f'**Numerador:** {x["numerador"]}')
            st.markdown(f'**Denominador:** {x["denominador"]}')
            st.markdown(f'**Meta:** {x["meta_texto"]}')
            st.markdown(f'**Dirección deseable:** {"Menor es mejor" if x["direccion"] == "menor_es_mejor" else "Mayor es mejor"}')
        with right:
            st.markdown(f'**Valores de la matriz:** {x["valor_numerador"]} / {x["valor_denominador"]}')
            valor = x["resultado_calculado_pct"]
            st.metric("Resultado reproducido", f"{valor:.2f}%" if valor is not None else "Sin datos calculables")
            st.markdown(f'**Evaluación de meta:** {x["estado_meta"]}')
            st.markdown(f'**Semáforo de origen:** {x.get("semaforo_fuente", "No informado")}')
            st.markdown(f'**Fuentes declaradas:** {x["fuentes"]}')
            st.markdown(f'**Responsable:** {x["responsable"]}')
            st.markdown(f'**Periodicidad:** {x["periodicidad"]}')
        if x.get("semaforo_fuente_requiere_revision"):
            st.error("Inconsistencia: la hoja marca VERDE, pero el resultado no cumple la meta explícita.")
        st.info(x.get("observaciones", "Pendiente de precisar criterios de medición."))
        st.caption("Estado de evidencia: pendiente de verificación documental.")


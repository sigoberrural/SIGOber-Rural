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

st.set_page_config(page_title="SADCI · SIGOber-Rural", page_icon="📊", layout="wide")


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
.sadci-hero{padding:1.2rem 1.3rem;border:1px solid rgba(128,128,128,.22);border-radius:1rem;background:linear-gradient(115deg,rgba(31,91,75,.12),rgba(91,128,108,.025));margin:.2rem 0 1rem}
.sadci-hero h1{margin:.1rem 0 .35rem;font-size:2rem}
.sadci-hero p{margin:0;opacity:.78;max-width:850px}
.sadci-eyebrow{font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;font-weight:750;opacity:.65}
.sadci-note{padding:.8rem 1rem;border-left:3px solid #B88746;background:rgba(184,135,70,.09);border-radius:.3rem .7rem .7rem .3rem}
div[data-testid="stMetric"]{padding:.65rem .75rem;border:1px solid rgba(128,128,128,.2);border-radius:.8rem;background:rgba(128,128,128,.035)}
</style>
<div class="sadci-hero">
<div class="sadci-eyebrow">SIGOber-Rural · módulo institucional</div>
<h1>Indicadores SADCI</h1>
<p>Capacidades institucionales para la gobernanza rural de Puerto Rico, Caquetá. Consulta de resultados, metas, fuentes y condiciones para el análisis territorial.</p>
</div>
""", unsafe_allow_html=True)

try:
    catalogo = cargar_catalogo()
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"No fue posible cargar el catálogo SADCI: {exc}")
    st.stop()

evaluados = evaluar_catalogo(catalogo)
df = pd.DataFrame(evaluados)

with st.expander("Cómo usar este tablero", expanded=False):
    st.markdown(
        "1. **Empieza por el resumen municipal** para ver los diez indicadores y sus resultados calculados.\n"
        "2. **Filtra** por dimensión, código, nombre o cumplimiento de meta para encontrar un indicador.\n"
        "3. **Abre su ficha** para consultar fórmula, valores, fuente, responsable y periodicidad.\n"
        "4. **Descarga los resultados** si necesitas analizarlos o incorporarlos a un informe."
    )
    st.caption("La pestaña veredal informa qué datos faltan para una desagregación válida; no reparte automáticamente los valores municipales entre veredas.")
df["resultado_mostrar"] = df["resultado_calculado_pct"].map(lambda x: round(float(x), 2) if pd.notna(x) else None)
df["estado_meta"] = df["estado_meta"].fillna("SIN DATOS")

st.markdown('<div class="sadci-note"><strong>Estado de la evidencia.</strong> Los valores proceden de la matriz de trabajo y están pendientes de verificación documental. El tablero reproduce los cálculos y compara las metas consignadas; no certifica por sí solo el desempeño institucional.</div>', unsafe_allow_html=True)

tab_municipal, tab_veredal, tab_metodo = st.tabs(["Resumen municipal", "Disponibilidad veredal", "Metodología y calidad"])

with tab_municipal:
    calculables = [x for x in evaluados if x["resultado_calculado_pct"] is not None]
    cumplen = sum(x["meta_cumplida"] is True for x in calculables)
    pendientes = sum(x.get("estado_dato") == "PENDIENTE_VERIFICACION" for x in evaluados)
    a, b, c, d = st.columns(4)
    a.metric("Indicadores", len(evaluados))
    b.metric("Cálculos reproducidos", len(calculables))
    c.metric("Metas alcanzadas", cumplen, help="Según valores de la matriz y operadores explícitos.")
    d.metric("Datos por verificar", pendientes)

    st.subheader("Explorar indicadores")
    f1, f2, f3 = st.columns([1.1, 1.4, 1.3])
    dimensiones = ["Todas"] + sorted(df["dimension"].dropna().unique().tolist())
    dimension_sel = f1.selectbox("Dimensión SADCI", dimensiones)
    busqueda = f2.text_input("Buscar indicador", placeholder="Código o nombre…")
    estado_sel = f3.selectbox("Evaluación de meta", ["Todas", "Cumple meta", "No cumple meta", "Sin datos"])
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

with tab_veredal:
    st.subheader("Disponibilidad para análisis veredal")
    st.write("La matriz actual contiene valores agregados de capacidad institucional municipal. La desagregación requiere datos territoriales observados y una definición válida de la unidad de análisis.")
    readiness = [{
        "Código": x["codigo"], "Indicador": x["nombre"],
        "Escala actual": "Municipal", "Estado veredal": "Sin datos veredales validados",
        "Condición para habilitar": x["desagregacion_veredal"],
    } for x in evaluados]
    st.dataframe(pd.DataFrame(readiness), use_container_width=True, hide_index=True)
    st.markdown("#### Esquema mínimo de registro veredal")
    st.code("codigo_indicador | codigo_vereda | periodo | numerador | denominador | fuente | fecha_corte | responsable | estado_validacion", language="text")
    st.warning("No se prorratean valores municipales entre veredas. Los indicadores normativos, organizacionales o de vinculación pueden no admitir desagregación veredal directa.")

with tab_metodo:
    st.subheader("Reglas de cálculo")
    st.markdown(
        "- Resultado (%) = numerador / denominador × 100.\n"
        "- Si falta el denominador, no es numérico o es menor o igual a cero, el resultado no se calcula.\n"
        "- La meta se evalúa con el operador literal consignado en la matriz.\n"
        "- La evaluación de meta no reemplaza el semáforo de origen.\n"
        "- No se inventan bandas amarillas o rojas mientras no se aprueben sus umbrales."
    )
    st.subheader("Controles pendientes de cierre")
    controles = [
        ("Fuentes documentales", "Contrastar cada valor con el documento institucional y registrar fecha de corte."),
        ("Universo de conteo", "Aprobar qué procesos, convenios, activos, personas o metas se incluyen."),
        ("Semáforos", "Definir bandas y sentido de mejora por indicador."),
        ("Periodicidad NSF", "Confirmar si “Bi-anual” significa semestral o bienal."),
        ("Series temporales", "Comparar periodos solo si son metodológicamente equivalentes."),
        ("Escala veredal", "Habilitar únicamente con numeradores y denominadores territorializados y trazables."),
    ]
    for titulo, detalle in controles:
        st.markdown(f"- **{titulo}:** {detalle}")
    st.subheader("Control de consistencia")
    conflictos = [x for x in evaluados if x.get("semaforo_fuente_requiere_revision")]
    if conflictos:
        for x in conflictos:
            st.error(f'{x["codigo"]}: semáforo fuente VERDE incompatible con la meta ({x["estado_meta"]}).')
    else:
        st.success("No se detectaron contradicciones directas entre VERDE y la meta explícita.")
    st.caption("La matriz y las fichas siguen siendo instrumentos de trabajo hasta completar la verificación institucional.")

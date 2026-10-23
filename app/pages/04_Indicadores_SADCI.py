"""Tablero municipal SADCI y evaluación de disponibilidad veredal."""
import pandas as pd
import streamlit as st

from app.sadci import cargar_catalogo, evaluar_catalogo

st.set_page_config(page_title="Indicadores SADCI · SIGOber-Rural", page_icon="📊", layout="wide")
st.title("Indicadores SADCI")
st.caption("SIGOber-Rural · Puerto Rico, Caquetá · matriz de diez indicadores")
st.warning(
    "Los valores proceden de la matriz entregada al proyecto y están pendientes de verificación "
    "documental. Los cálculos se reproducen; no constituyen por sí solos un diagnóstico "
    "institucional confirmado."
)

try:
    catalogo = cargar_catalogo()
except (OSError, ValueError) as exc:
    st.error(f"No fue posible cargar el catálogo SADCI: {exc}")
    st.stop()

evaluados = evaluar_catalogo(catalogo)
nivel = st.radio("Nivel territorial", ["Municipal", "Veredal"], horizontal=True)

if nivel == "Municipal":
    calculables = [x for x in evaluados if x["resultado_calculado_pct"] is not None]
    cumplen = sum(x["meta_cumplida"] is True for x in calculables)
    no_cumplen = sum(x["meta_cumplida"] is False for x in calculables)
    a, b, c, d = st.columns(4)
    a.metric("Indicadores", len(evaluados))
    b.metric("Con cálculo", len(calculables))
    c.metric("Cumplen meta explícita", cumplen)
    d.metric("No cumplen meta explícita", no_cumplen)

    filas = [{
        "Código": x["codigo"],
        "Dimensión": x["dimension"],
        "Indicador": x["nombre"],
        "Resultado calculado (%)": round(x["resultado_calculado_pct"], 2) if x["resultado_calculado_pct"] is not None else None,
        "Meta": x["meta_texto"],
        "Evaluación": x["estado_meta"],
        "Semáforo fuente": x.get("semaforo_fuente", "No informado"),
        "Validación del dato": x.get("estado_dato", "PENDIENTE_VERIFICACION"),
    } for x in evaluados]
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    st.subheader("Ficha técnica y trazabilidad")
    for x in evaluados:
        with st.expander(f'{x["codigo"]} · {x["nombre"]}'):
            izquierda, derecha = st.columns(2)
            with izquierda:
                st.markdown(f'**Dimensión:** {x["dimension"]}')
                st.markdown(f'**Fórmula:** {x["formula"]}')
                st.markdown(f'**Numerador:** {x["numerador"]}')
                st.markdown(f'**Denominador:** {x["denominador"]}')
                st.markdown(f'**Meta explícita:** {x["meta_texto"]}')
                st.markdown(f'**Dirección de mejora:** {"menor es mejor" if x["direccion"] == "menor_es_mejor" else "mayor es mejor"}')
            with derecha:
                st.markdown(f'**Valores de la matriz:** {x["valor_numerador"]} / {x["valor_denominador"]}')
                valor = x["resultado_calculado_pct"]
                st.metric("Resultado reproducido", f"{valor:.2f}%" if valor is not None else "Sin datos")
                st.markdown(f'**Semáforo de origen:** {x.get("semaforo_fuente", "No informado")} (pendiente de validación)')
                st.markdown(f'**Fuentes declaradas:** {x["fuentes"]}')
                st.markdown(f'**Responsable:** {x["responsable"]}')
                st.markdown(f'**Periodicidad:** {x["periodicidad"]}')
            if x.get("semaforo_fuente_requiere_revision"):
                st.error("Inconsistencia: la hoja marca VERDE, pero el resultado no cumple la meta explícita.")
            st.info(x.get("observaciones", "Pendiente de precisar criterios de medición."))

    st.subheader("Reglas de interpretación")
    st.markdown(
        "- **Resultado calculado:** numerador / denominador × 100; el dato de origen se conserva para comparación.\n"
        "- **Evaluación de meta:** comparación literal con el operador y el umbral consignados. No se inventan bandas amarillas o rojas.\n"
        "- **Semáforo de origen:** se conserva como dato de procedencia; las bandas definitivas requieren aprobación metodológica.\n"
        "- **Publicabilidad:** exige verificar fuentes, fecha de corte, universo de conteo y responsable."
    )
else:
    st.subheader("Disponibilidad para análisis veredal")
    st.info(
        "La matriz actual contiene valores agregados institucionales municipales. No incluye una tabla "
        "de observaciones con código de vereda, periodo, numerador y denominador. Por eso, esta vista "
        "no calcula resultados por vereda ni distribuye los valores municipales entre ellas."
    )
    filas = [{
        "Código": x["codigo"],
        "Indicador": x["nombre"],
        "Disponibilidad actual": "No hay datos veredales acreditados en la matriz",
        "Condición para habilitar": x["desagregacion_veredal"],
        "Estado": "NO CALCULABLE A NIVEL VEREDAL",
    } for x in evaluados]
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    st.markdown(
        "**Contrato mínimo de datos veredales:** código y nombre de vereda; periodo; numerador y "
        "denominador observados; fuente documental; fecha de corte; responsable; regla para evitar "
        "duplicados; y validación de que el indicador admite esa escala."
    )

st.caption("La aplicación diferencia la reproducción aritmética, la evaluación de metas y la verificación documental.")

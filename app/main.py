import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def cargar_eventos():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv", "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"):
        ruta = DATA_DIR / nombre
        if ruta.exists():
            return pd.read_csv(ruta, dtype=str).fillna("")
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def preparar_veredas(eventos_records):
    """Convierte la capa TopoJSON una sola vez por versión de datos."""
    topo = cargar_json("veredas_puerto_rico.json")
    if not topo:
        return None
    if topo.get("type") == "FeatureCollection":
        geojson = topo
    elif topo.get("type") == "Topology":
        try:
            import topojson
            resultado = topojson.Topology(topo).to_geojson()
            geojson = json.loads(resultado) if isinstance(resultado, str) else resultado
        except Exception as e:
            raise RuntimeError(f"No fue posible convertir la cartografía de veredas: {type(e).__name__}: {e}") from e
    else:
        raise RuntimeError(f"Formato cartográfico no reconocido: {topo.get('type')}")

    conteo = {}
    for registro in eventos_records:
        codigo = str(registro.get("codigo_ver_resuelto", "")).strip()
        if codigo:
            conteo[codigo] = conteo.get(codigo, 0) + 1

    for feature in geojson.get("features", []):
        props = feature.setdefault("properties", {})
        codigo = str(props.get("CODIGO_VER", "")).strip()
        props["eventos_documentados"] = int(conteo.get(codigo, 0))

    return geojson


def construir_mapa(geojson=None):
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="CartoDB positron")
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(m)

    if geojson:
        folium.GeoJson(
            geojson,
            name="Veredas + situaciones territoriales",
            style_function=lambda feature: {
                "fillColor": "#d73027" if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else "#eeeeee",
                "color": "#555555",
                "weight": 0.7,
                "fillOpacity": 0.55 if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else 0.18,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["NOMBRE_VER", "CODIGO_VER", "eventos_documentados", "FUENTE"],
                aliases=["Vereda", "Código", "Situaciones documentadas", "Fuente cartográfica"],
                localize=True,
            ),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")

eventos = cargar_eventos()
eventos_records = tuple(eventos.to_dict("records"))

c1, c2, c3 = st.columns(3)
c1.metric("Situaciones documentadas", len(eventos))
c2.metric("Veredas con eventos", eventos["codigo_ver_resuelto"].nunique() if "codigo_ver_resuelto" in eventos.columns and not eventos.empty else 0)
c3.metric("Estado", "Operativo")

st.success("La aplicación inició correctamente con datos locales. Las fuentes externas se cargan solo bajo demanda.")

# La capa se conserva en session_state y no vuelve a convertirse en cada rerun.
if "veredas_geojson" not in st.session_state:
    st.session_state["veredas_geojson"] = None

if st.button("Cargar capa de veredas", type="primary", disabled=st.session_state["veredas_geojson"] is not None):
    with st.spinner("Preparando la cartografía de veredas por primera vez…"):
        try:
            st.session_state["veredas_geojson"] = preparar_veredas(eventos_records)
            st.success("Capa de veredas cargada correctamente.")
        except Exception as e:
            st.error(str(e))

m = construir_mapa(st.session_state["veredas_geojson"])
st_folium(m, width="100%", height=620)

st.divider()
st.subheader("Fuentes externas")
st.write("Google Sheets permanece separado del arranque de la aplicación. Primero se estabiliza la cartografía local y luego se valida la conexión externa.")

if st.button("Probar conexión con Google Sheets"):
    try:
        from streamlit_gsheets import GSheetsConnection
        with st.spinner("Consultando Google Sheets…"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Conflictos", ttl=300)

        if isinstance(df, pd.DataFrame):
            st.success(f"Google Sheets respondió correctamente: {len(df)} registros.")
        else:
            st.warning(f"Google Sheets respondió, pero el resultado no es una tabla pandas sino {type(df).__name__}: {df!r}")
    except Exception as e:
        st.error(
            "Google Sheets respondió al servidor, pero la lectura de la hoja no pudo completarse. "
            f"Tipo de error: {type(e).__name__}. Detalle: {e}"
        )
        st.info("Esto apunta a la configuración/lectura de la conexión (secrets, URL/ID o nombre de la hoja), no a una caída de Google Sheets.")

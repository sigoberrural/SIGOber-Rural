import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape, mapping

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_eventos():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv", "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"):
        ruta = DATA_DIR / nombre
        if ruta.exists():
            return pd.read_csv(ruta, dtype=str).fillna("")
    return pd.DataFrame()


def topo_a_geojson(topo):
    if not topo:
        return None
    if topo.get("type") == "FeatureCollection":
        return topo
    if topo.get("type") != "Topology":
        return None
    try:
        import topojson
        resultado = topojson.Topology(topo).to_geojson()
        return json.loads(resultado) if isinstance(resultado, str) else resultado
    except Exception as e:
        st.error(f"No fue posible preparar la cartografía de veredas: {e}")
        return None


def enriquecer(geojson, eventos):
    if not geojson:
        return None
    conteo = {}
    if not eventos.empty and "codigo_ver_resuelto" in eventos.columns:
        conteo = eventos["codigo_ver_resuelto"].astype(str).str.strip().value_counts().to_dict()
    for f in geojson.get("features", []):
        p = f.setdefault("properties", {})
        codigo = str(p.get("CODIGO_VER", "")).strip()
        p["eventos_documentados"] = int(conteo.get(codigo, 0))
    return geojson


st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")

# El arranque usa únicamente archivos locales. No se conecta a servicios externos automáticamente.
eventos = cargar_eventos()

c1, c2, c3 = st.columns(3)
c1.metric("Situaciones documentadas", len(eventos))
c2.metric("Veredas con eventos", eventos["codigo_ver_resuelto"].nunique() if "codigo_ver_resuelto" in eventos.columns and not eventos.empty else 0)
c3.metric("Estado", "Operativo")

st.success("La aplicación inició correctamente con datos locales. Las fuentes externas se cargan solo bajo demanda.")

# Mapa base inmediato: no convierte 177 polígonos ni hace operaciones geométricas costosas durante el arranque.
m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="CartoDB positron")
folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(m)

if st.button("Cargar capa de veredas", type="primary"):
    with st.spinner("Preparando la cartografía de veredas…"):
        topo = cargar_json("veredas_puerto_rico.json")
        geojson = enriquecer(topo_a_geojson(topo), eventos)
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
        st.session_state["veredas_cargadas"] = True
    else:
        st.error("La capa de veredas no pudo prepararse.")

if st.session_state.get("veredas_cargadas"):
    # Recalcular el mapa solamente después de que el usuario solicite la capa.
    topo = cargar_json("veredas_puerto_rico.json")
    geojson = enriquecer(topo_a_geojson(topo), eventos)
    if geojson:
        folium.GeoJson(
            geojson,
            name="Veredas + situaciones territoriales",
            style_function=lambda feature: {
                "fillColor": "#d73027" if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else "#eeeeee",
                "color": "#555555", "weight": 0.7,
                "fillOpacity": 0.55 if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else 0.18,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["NOMBRE_VER", "CODIGO_VER", "eventos_documentados", "FUENTE"],
                aliases=["Vereda", "Código", "Situaciones documentadas", "Fuente cartográfica"],
            ),
        ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, width="100%", height=620)

st.divider()
st.subheader("Fuentes externas")
st.write("La conexión con Google Sheets y la captura GPS quedan desactivadas durante el arranque para evitar bloqueos. Se reincorporarán después de confirmar que el núcleo de la aplicación carga correctamente.")

if st.button("Probar conexión con Google Sheets"):
    try:
        from streamlit_gsheets import GSheetsConnection
        with st.spinner("Consultando Google Sheets…"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Conflictos", ttl=300)
        st.success(f"Google Sheets respondió correctamente: {len(df)} registros.")
    except Exception as e:
        st.error(f"La conexión con Google Sheets falló: {e}")

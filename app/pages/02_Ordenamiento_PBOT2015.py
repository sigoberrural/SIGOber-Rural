import base64
import gzip
import json
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="PBOT 2015 — SIGOber-Rural", page_icon="🗺️", layout="wide")
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "PBOT2015"

st.title("Ordenamiento Territorial — PBOT 2015")
st.caption("Cartografía de formulación PBOT 2015. No implica actualización al PBOT 2023.")

@st.cache_data(show_spinner=False)
def cargar_geojson_b64(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        return None
    texto = ruta.read_text(encoding="utf-8").strip()
    return json.loads(gzip.decompress(base64.b64decode(texto)).decode("utf-8"))

geo = cargar_geojson_b64("ZONIFICACION_RURAL.geojson.gz.b64")

if geo is None:
    st.error("No está disponible la capa PBOT 2015 de zonificación rural en el repositorio.")
else:
    m = folium.Map(location=[1.91, -75.18], zoom_start=10, tiles="CartoDB positron")
    fg = folium.FeatureGroup(name="Zonificación de uso del suelo rural — PBOT 2015", show=True)
    tooltip = folium.GeoJsonTooltip(
        fields=[c for c in ["UGOT", "Aptitud", "area_ha"] if c in (geo.get("features", [{}])[0].get("properties", {}) or {})],
        aliases=["UGOT", "Aptitud", "Área (ha)"],
        localize=True,
        labels=True,
        sticky=True,
    )
    folium.GeoJson(geo, name="Zonificación rural", tooltip=tooltip).add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width="100%", height=700)
    st.info("Esta primera visualización usa la capa PBOT 2015 ya almacenada en el repositorio. Las demás capas de formulación se incorporarán progresivamente sin sustituir ni inventar geometrías.")

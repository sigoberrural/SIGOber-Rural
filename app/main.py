import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", page_icon="🛰️", layout="wide")

# 2. TÍTULO Y CRÉDITOS
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("**Grupo:** Colectivo Guadalupe Salcedo | **ESAP**")
st.divider()

# 3. CARGA DE DATOS SEGUROS
@st.cache_data(ttl=3600)
def obtener_veredas_oficiales():
    url = "https://ags.esri.co/arcgis/rest/services/DatosAbiertos/VEREDAS_2016/MapServer/0/query?where=MPIO_CNMBRE='PUERTO RICO' AND DPTO_CNMBRE='CAQUETÁ'&outFields=*&f=geojson"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "features" in data and len(data["features"]) > 0:
                return data
        return None
    except:
        return None

def cargar_conflictos_locales(ruta):
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

veredas = obtener_veredas_oficiales()
conflictos = cargar_conflictos_locales('data/ejemplo_conflictos.geojson')

# 4. INTERFAZ
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Panel")
    if veredas:
        st.metric("Veredas (IGAC)", len(veredas['features']))
    if conflictos:
        st.metric("Conflictos", len(conflictos['features']))
    st.info("Si el mapa no carga, refresca la página.")

with col2:
    # Centrado en Puerto Rico, Caquetá
    m = folium.Map(location=[1.91, -75.18], zoom_start=11)

    # Añadir Satélite
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Satélite',
        overlay=False
    ).add_to(m)

    # CAPA VEREDAS (Sin Tooltip complejo para evitar el AssertionError)
    if veredas:
        folium.GeoJson(
            veredas,
            name="Veredas Oficiales",
            style_function=lambda x: {'fillColor': 'green', 'color': 'white', 'weight': 1, 'fillOpacity': 0.2},
            # Usamos una forma más simple de Tooltip
            tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'])
        ).add_to(m)

    # CAPA CONFLICTOS
    if conflictos:
        folium.GeoJson(
            conflictos,
            name="Conflictos",
            marker=folium.Marker(icon=folium.Icon(color='red')),
            tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Conflicto:'])
        ).add_to(m)

    folium.LayerControl().add_to(m)

    # RENDERIZADO FINAL (Cambié width="100%" por un número fijo para evitar el error de Streamlit)
    st_folium(m, width=900, height=600)

st.caption("Fase 1 - Proyecto de Investigación")

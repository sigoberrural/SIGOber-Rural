import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

st.set_page_config(page_title="SIGOber-Rural", layout="wide")

st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")

# --- CARGA DE DATOS ---
def cargar_geojson(ruta):
    try:
        with open(ruta) as f:
            return json.load(f)
    except:
        return None

conflictos = cargar_geojson('data/ejemplo_conflictos.geojson')
veredas = cargar_geojson('data/ejemplo_veredas.geojson')

# --- DISEÑO DE LA INTERFAZ ---
col1, col2 = st.columns([1, 3]) # Columna 1 para datos, Columna 2 para el mapa

with col1:
    st.subheader("Estadísticas")
    if conflictos:
        st.metric("Conflictos", len(conflictos['features']))
    if veredas:
        st.metric("Áreas Mapeadas", len(veredas['features']))
    
    st.write("---")
    st.info("Usa el mapa para explorar los hallazgos de la cartografía social.")

with col2:
    st.subheader("Mapa de Gobernanza y Territorio")
    
    # Crear el mapa base centrado en Puerto Rico, Caquetá
    # Coordenadas aprox: [1.91, -75.18]
   # Crear el mapa base centrado en Puerto Rico, Caquetá
    m = folium.Map(location=[1.91, -75.18], zoom_start=12, tiles=None)

    # Añadir Capa de Mapa Callejero (OpenStreetMap)
    folium.TileLayer('OpenStreetMap', name="Mapa de Carreteras").add_to(m)

    # Añadir Capa Satelital (Google)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Satélite',
        overlay=False,
        control=True
    ).add_to(m)

    # Añadir las capas GeoJSON que ya tenías
    if veredas:
        folium.GeoJson(
            veredas,
            name="Capa: Veredas",
            style_function=lambda x: {'fillColor': 'green', 'color': 'darkgreen', 'weight': 2, 'fillOpacity': 0.3}
        ).add_to(m)

    if conflictos:
        folium.GeoJson(
            conflictos,
            name="Capa: Conflictos",
            tooltip=folium.GeoJsonTooltip(fields=['vereda', 'tipo_conflicto'], aliases=['Vereda:', 'Tipo:'])
        ).add_to(m)

    # Añadir el controlador de capas (el selector arriba a la derecha)
    folium.LayerControl().add_to(m)

    # Mostrar el mapa
    st_folium(m, width=800, height=500)
st.caption("Fase 1: Diagnóstico e Indicadores de Gestión Pública.")

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

# 1. Configuración de página
st.set_page_config(page_title="SIGOber-Rural", layout="wide")

# 2. Título y Créditos Institucionales
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("""
    **Grupo de Investigación:** Colectivo Guadalupe Salcedo  
    **Institución:** Escuela Superior de Administración Pública (ESAP)  
    *Proyecto de Iniciación Científica - Fase de Diagnóstico*
""")
st.divider()

# 3. Carga de datos (con manejo de errores)
def cargar_geojson(ruta):
    try:
        with open(ruta) as f:
            return json.load(f)
    except:
        return None

conflictos = cargar_geojson('data/ejemplo_conflictos.geojson')
veredas = cargar_geojson('data/ejemplo_veredas.geojson')

# 4. Interfaz Principal
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Estadísticas")
    if conflictos:
        st.metric("Conflictos", len(conflictos['features']))
    if veredas:
        st.metric("Áreas Mapeadas", len(veredas['features']))
    
    st.info("Utilice el selector en el mapa (arriba a la derecha) para cambiar entre vista de Satélite o Mapa.")

with col2:
    st.subheader("🗺️ Mapa Territorial")
    
    # Crear mapa base sin capas predefinidas
    m = folium.Map(location=[1.91, -75.18], zoom_start=12, tiles=None)

    # CAPA 1: Mapa Callejero
    folium.TileLayer('OpenStreetMap', name="Mapa de Carreteras").add_to(m)

    # CAPA 2: Satélite Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Vista Satelital',
        overlay=False,
        control=True
    ).add_to(m)

    # AÑADIR CAPAS DE DATOS
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

    # ESTA ES LA LÍNEA QUE FALTABA: El control de capas
    folium.LayerControl(collapsed=False).add_to(m)

    # Mostrar mapa
    st_folium(m, width=800, height=500)

st.caption("Fase 1: Recolección de datos y cartografía social participativa.")

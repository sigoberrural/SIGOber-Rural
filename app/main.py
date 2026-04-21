import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="SIGOber-Rural Puerto Rico",
    page_icon="🛰️",
    layout="wide"
)

# 2. TÍTULO Y CRÉDITOS INSTITUCIONALES
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("""
    **Grupo de Investigación:** Colectivo Guadalupe Salcedo  
    **Institución:** Escuela Superior de Administración Pública (ESAP)  
    *Proyecto de Iniciación Científica - Fase de Diagnóstico Territorial*
""")
st.divider()

# 3. FUNCIONES DE CARGA DE DATOS
@st.cache_data
def obtener_veredas_oficiales():
    """Obtiene veredas de Puerto Rico, Caquetá desde el servicio oficial de ArcGIS"""
    url = "https://ags.esri.co/arcgis/rest/services/DatosAbiertos/VEREDAS_2016/MapServer/0/query?where=MPIO_CNMBRE='PUERTO RICO' AND DPTO_CNMBRE='CAQUETÁ'&outFields=*&f=geojson"
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return None

def cargar_conflictos_locales(ruta):
    """Carga los puntos de conflictos desde el archivo GeoJSON local"""
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# Ejecutar carga
veredas_oficiales = obtener_veredas_oficiales()
conflictos_locales = cargar_conflictos_locales('data/ejemplo_conflictos.geojson')

# 4. INTERFAZ DE USUARIO (COLUMNAS)
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Panel de Control")
    
    # Métricas dinámicas
    if veredas_oficiales:
        cant_veredas = len(veredas_oficiales.get('features', []))
        st.metric("Veredas Oficiales (DANE)", cant_veredas)
    
    if conflictos_locales:
        cant_conflictos = len(conflictos_locales.get('features', []))
        st.metric("Conflictos Mapeados", cant_conflictos)
    
    st.write("---")
    st.info("""
        **Instrucciones:**
        1. Usa el icono de capas en el mapa para alternar la vista satelital.
        2. Pasa el cursor sobre los polígonos para ver el nombre de la vereda.
        3. Haz clic en los puntos para ver detalles del conflicto.
    """)

with col2:
    st.subheader("🗺️ Visualizador Geográfico Interactiva")
    
    # Crear mapa base centrado en el casco urbano de Puerto Rico, Caquetá
    m = folium.Map(location=[1.91, -75.18], zoom_start=11, tiles=None)

    # CAPA: Mapa de Calles
    folium.TileLayer('OpenStreetMap', name="Mapa de Carreteras").add_to(m)

    # CAPA: Satélite Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Vista Satelital',
        overlay=False,
        control=True
    ).add_to(m)

    # DIBUJAR VEREDAS (POLÍGONOS OFICIALES)
    if veredas_oficiales:
        folium.GeoJson(
            veredas_oficiales,
            name="Límites Veredales (IGAC)",
            style_function=lambda x: {
                'fillColor': '#2e7d32', 
                'color': 'white', 
                'weight': 1, 
                'fillOpacity': 0.25
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['NOMBRE_VER', 'CODIGO_VER'], 
                aliases=['Vereda:', 'Código:']
            )
        ).add_to(m)

    # DIBUJAR CONFLICTOS (PUNTOS LOCALES)
    if conflictos_locales:
        folium.GeoJson(
            conflictos_locales,
            name="Conflictos Reportados",
            marker=folium.Marker(icon=folium.Icon(color='red', icon='info-sign')),
            tooltip=folium.GeoJsonTooltip(
                fields=['vereda', 'tipo_conflicto', 'descripcion'], 
                aliases=['Ubicación:', 'Tipo:', 'Detalle:']
            )
        ).add_to(m)

    # Control de Capas (Selector)
    folium.LayerControl(collapsed=False).add_to(m)

    # Renderizar mapa en Streamlit
    st_folium(m, width="100%", height=600)

# 5. PIE DE PÁGINA
st.divider()
st.caption("Fase de recolección de datos - SIGOber-Rural 2026. Los límites veredales son referenciales según el IGAC.")

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

# 3. FUNCIONES DE CARGA DE DATOS (FILTRADO SEGURO)
@st.cache_data(ttl=3600)
def obtener_veredas_oficiales():
    """Trae datos del servidor nacional y filtra localmente para evitar errores del servidor"""
    # Usamos una consulta base para obtener los datos
    url = "https://ags.esri.co/arcgis/rest/services/DatosAbiertos/VEREDAS_2016/MapServer/0/query?where=1%3D1&outFields=MPIO_CNMBRE,DPTO_CNMBRE,NOMBRE_VER,CODIGO_VER&f=geojson"
    try:
        r = requests.get(url, timeout=25)
        if r.status_code == 200:
            todo = r.json()
            # Filtro manual robusto (ignora mayúsculas/minúsculas)
            features_puerto_rico = [
                f for f in todo.get('features', [])
                if str(f['properties'].get('MPIO_CNMBRE')).strip().upper() == 'PUERTO RICO'
                and str(f['properties'].get('DPTO_CNMBRE')).strip().upper() == 'CAQUETÁ'
            ]
            return {"type": "FeatureCollection", "features": features_puerto_rico}
        return None
    except Exception as e:
        return None

def cargar_conflictos_locales(ruta):
    """Carga los puntos de conflictos desde el archivo GeoJSON local en el repo"""
    try:
        with open(ruta, encoding='utf-8') as f:
            data = json.load(f)
            if "features" in data:
                return data
        return None
    except:
        return None

# Ejecutar carga de datos
veredas_oficiales = obtener_veredas_oficiales()
conflictos_locales = cargar_conflictos_locales('data/ejemplo_conflictos.geojson')

# 4. INTERFAZ DE USUARIO (DASHBOARD)
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Panel de Control")
    
    # Métricas dinámicas
    if veredas_oficiales and veredas_oficiales['features']:
        st.metric("Veredas Identificadas", len(veredas_oficiales['features']))
    else:
        st.error("No se detectaron polígonos veredales.")
    
    if conflictos_locales:
        st.metric("Conflictos Mapeados", len(conflictos_locales['features']))
    
    st.write("---")
    st.info("""
        **Guía:**
        * Los polígonos verdes son los límites oficiales del IGAC.
        * El selector de la derecha permite activar la **Vista Satelital**.
        * Si no ves los polígonos, intenta recargar la página.
    """)

with col2:
    # Crear mapa centrado en el área rural de Puerto Rico, Caquetá
    # Nota: Se usa un ancho fijo en píxeles para evitar el AssertionError de blanca/folium
    m = folium.Map(location=[1.9143, -75.1819], zoom_start=10)

    # CAPA: Satélite Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Vista Satelital',
        overlay=False
    ).add_to(m)

    # CAPA: Mapa de Calles (OpenStreetMap)
    folium.TileLayer('OpenStreetMap', name="Mapa de Carreteras").add_to(m)

    # DIBUJAR VEREDAS (POLÍGONOS)
    if veredas_oficiales and veredas_oficiales['features']:
        folium.GeoJson(
            veredas_oficiales,
            name="Límites Veredales (Fuente Oficial)",
            style_function=lambda x: {
                'fillColor': '#2e7d32', 
                'color': 'white', 
                'weight': 1, 
                'fillOpacity': 0.3
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['NOMBRE_VER'], 
                aliases=['Vereda:']
            )
        ).add_to(m)

    # DIBUJAR CONFLICTOS (PUNTOS)
    if conflictos_locales:
        folium.GeoJson(
            conflictos_locales,
            name="Conflictos Territoriales",
            marker=folium.Marker(icon=folium.Icon(color='red', icon='exclamation-sign')),
            tooltip=folium.GeoJsonTooltip(
                fields=['tipo_conflicto'], 
                aliases=['Conflicto:']
            )
        ).add_to(m)

    # Control de Capas (Selector)
    folium.LayerControl(collapsed=False).add_to(m)

    # Renderizar mapa (Ancho fijo para máxima compatibilidad)
    st_folium(m, width=800, height=550)

# 5. PIE DE PÁGINA
st.divider()
st.caption("SIGOber-Rural v1.0 | Puerto Rico, Caquetá - 2026")

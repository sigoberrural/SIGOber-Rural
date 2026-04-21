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

# 3. FUNCIONES DE CARGA DE DATOS CON VALIDACIÓN
@st.cache_data(ttl=3600) # El cache expira cada hora para asegurar frescura de datos
def obtener_veredas_oficiales():
    """Obtiene veredas de Puerto Rico, Caquetá desde el servicio oficial de ArcGIS con validación de formato"""
    url = "https://ags.esri.co/arcgis/rest/services/DatosAbiertos/VEREDAS_2016/MapServer/0/query?where=MPIO_CNMBRE='PUERTO RICO' AND DPTO_CNMBRE='CAQUETÁ'&outFields=*&f=geojson"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # Validación crucial: Verificar que sea un GeoJSON válido
            if "features" in data and "type" in data:
                return data
        return None
    except Exception:
        return None

def cargar_conflictos_locales(ruta):
    """Carga los puntos de conflictos desde el archivo GeoJSON local"""
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

# 4. INTERFAZ DE USUARIO (COLUMNAS)
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Panel de Control")
    
    # Métricas dinámicas con validación
    if veredas_oficiales:
        cant_veredas = len(veredas_oficiales.get('features', []))
        st.metric("Veredas Oficiales (DANE)", cant_veredas)
    else:
        st.warning("⚠️ Capa oficial no disponible temporalmente.")
    
    if conflictos_locales:
        cant_conflictos = len(conflictos_locales.get('features', []))
        st.metric("Conflictos Mapeados", cant_conflictos)
    
    st.write("---")
    st.info("""
        **Guía de uso:**
        * Usa el selector arriba a la derecha para ver la **Vista Satelital**.
        * Toca las veredas para ver su nombre oficial.
        * Los puntos rojos indican conflictos identificados.
    """)

with col2:
    st.subheader("🗺️ Visualizador Geográfico Interactiva")
    
    # Crear mapa base centrado en Puerto Rico, Caquetá
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

    # DIBUJAR VEREDAS (Con manejo de errores para evitar que la App se caiga)
    if veredas_oficiales and 'features' in veredas_oficiales:
        try:
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
        except Exception as e:
            st.error(f"Error técnico en capa de veredas: {e}")

    # DIBUJAR CONFLICTOS
    if conflictos_locales and 'features' in conflictos_locales:
        try:
            folium.GeoJson(
                conflictos_locales,
                name="Conflictos Reportados",
                marker=folium.Marker(icon=folium.Icon(color='red', icon='info-sign')),
                tooltip=folium.GeoJsonTooltip(
                    fields=['vereda', 'tipo_conflicto', 'descripcion'], 
                    aliases=['Ubicación:', 'Tipo:', 'Detalle:']
                )
            ).add_to(m)
        except Exception as e:
            st.error(f"Error técnico en capa de conflictos: {e}")

    # Control de Capas (Selector siempre visible)
    folium.LayerControl(collapsed=False).add_to(m)

    # Renderizar mapa
    st_folium(m, width="100%", height=600)

# 5. PIE DE PÁGINA
st.divider()
st.caption("Fase 1: Diagnóstico Territorial. Datos consumidos de la infraestructura de Datos Abiertos de Colombia.")

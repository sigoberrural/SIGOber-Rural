import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", layout="wide")

st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("**Versión de Alta Velocidad** | Colectivo Guadalupe Salcedo - ESAP")
st.divider()

# 2. CARGA DE DATOS LOCALES
def cargar_archivo(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

# Cargamos tus archivos
veredas_topo = cargar_archivo('veredas_puerto_rico.json')
conflictos_geo = cargar_archivo('ejemplo_conflictos.geojson')

# 3. INTERFAZ
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📊 Inventario Territorial")
    if veredas_topo:
        st.success("✅ Capa de veredas optimizada")
    else:
        st.error("Archivo 'veredas_puerto_rico.json' no encontrado en /data")
        
    if conflictos_geo:
        st.info(f"📍 {len(conflictos_geo['features'])} Conflictos reportados")
    
    st.write("---")
    st.caption("Nota: El formato TopoJSON permite que el mapa cargue rápido incluso en zonas con señal 3G.")

with col2:
    # Centramos el mapa en las coordenadas de Puerto Rico, Caquetá
    m = folium.Map(location=[1.91, -75.18], zoom_start=11)

    # Añadimos capa de satélite
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google', name='Satélite', overlay=False
    ).add_to(m)

    # CAPA VEREDAS (Específica para TopoJSON)
    if veredas_topo:
        try:
            # Buscamos el nombre interno de la capa que puso Mapshaper
            nombre_interno = list(veredas_topo['objects'].keys())[0]
            
            folium.TopoJson(
                data=veredas_topo,
                object_path=f"objects.{nombre_interno}",
                name="Límites Veredales",
                style_function=lambda x: {
                    'fillColor': '#2e7d32', 
                    'color': 'white', 
                    'weight': 1.2, 
                    'fillOpacity': 0.3
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['NOMBRE_VER'], 
                    aliases=['Vereda:']
                )
            ).add_to(m)
        except Exception as e:
            st.error(f"Error al leer la estructura del TopoJSON: {e}")

    # CAPA CONFLICTOS (GeoJSON estándar)
    if conflictos_geo:
        folium.GeoJson(
            conflictos_geo,
            name="Puntos de Conflicto",
            marker=folium.Marker(icon=folium.Icon(color='red', icon='info-sign')),
            tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Tipo:'])
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Mostrar el mapa
    st_folium(m, width=900, height=600)

st.divider()
st.caption("Investigación ESAP 2026")

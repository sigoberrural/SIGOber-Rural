import streamlit as st

st.title("SIGOber-Rural: Puerto Rico (Caquetá)")
st.subheader("Sistema de Gobernanza Rural y Seguimiento al CMDR")

st.write("Bienvenido Jhon Fredy. El software está listo para recibir datos de la Fase 1.")

import streamlit as st
import pandas as pd
import json

# Configuración de la página
st.set_page_config(page_title="SIGOber-Rural", layout="wide")

st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.sidebar.header("Panel de Control")

# 1. Cargar Indicadores de Gestión (CSV)
st.sidebar.subheader("1. Capacidad Institucional")
try:
    df_indicadores = pd.read_csv('data/plantilla_indicadores.csv')
    st.sidebar.success("Indicadores cargados")
    
    # Mostrar tabla rápida en el dashboard
    if st.checkbox("Ver matriz de capacidad operativa"):
        st.write("### Matriz de Capacidad Institucional (Fase 1)")
        st.dataframe(df_indicadores)
except:
    st.sidebar.error("Archivo de indicadores no encontrado")

# 2. Cargar Cartografía Social (GeoJSON)
st.sidebar.subheader("2. Visualización Espacial")

def cargar_geojson(ruta):
    with open(ruta) as f:
        return json.load(f)

try:
    conflictos = cargar_geojson('data/ejemplo_conflictos.geojson')
    veredas = cargar_geojson('data/ejemplo_veredas.geojson')
    st.sidebar.success("Mapas cargados correctamente")
    
    st.write("### Mapa de Gobernanza Rural y Conflictos")
    st.info("El mapa mostrará los puntos de conflicto y áreas veredales identificadas en los talleres.")
    
    # Aquí es donde el software "lee" tus esquemas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Conflictos Reportados", len(conflictos['features']))
    with col2:
        st.metric("Áreas Mapeadas", len(veredas['features']))

except Exception as e:
    st.sidebar.warning("Esperando datos geográficos...")
    st.write("Por favor, asegúrate de que los archivos .geojson estén en la carpeta data/")

st.divider()
st.caption("Software desarrollado para el proyecto de investigación ESAP - Colectivo Guadalupe Salcedo.")

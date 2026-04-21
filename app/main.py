import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import uuid

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", layout="wide")
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.divider()

# 2. CONEXIÓN A DATOS
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_json_local(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

veredas_topo = cargar_json_local('veredas_puerto_rico.json')
conflictos_geo = cargar_json_local('ejemplo_conflictos.geojson')

# 3. PESTAÑAS PARA ORGANIZAR EL FLUJO
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa de Conflictos", "🏢 Auditoría SADCI", "👥 Registro de Actores"])

# --- TAB 1: VISUALIZADOR Y CONTADOR DE CONFLICTOS ---
with tab1:
    st.subheader("Análisis Territorial de Conflictos")
    
    # Contador de Conflictos
    if conflictos_geo:
        num_conflictos = len(conflictos_geo['features'])
        st.metric("Total Conflictos Identificados", num_conflictos, delta="Requiere Intervención", delta_color="inverse")
    
    m = folium.Map(location=[1.91, -75.18], zoom_start=11)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Satélite').add_to(m)

    if veredas_topo:
        nombre_obj = list(veredas_topo['objects'].keys())[0]
        folium.TopoJson(veredas_topo, f"objects.{nombre_obj}", name="Veredas",
                        style_function=lambda x: {'fillColor': 'green', 'color': 'white', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)
    
    if conflictos_geo:
        folium.GeoJson(conflictos_geo, name="Zonas de Conflicto",
                       tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Tipo:'])).add_to(m)
    
    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=500)

# --- TAB 2: AUDITORÍA SADCI (INSTITUCIONAL) ---
with tab2:
    st.subheader("Sistema de Análisis de Capacidad Institucional")
    try:
        df_ind = conn.read(ttl=0)
        df_ind.columns = df_ind.columns.str.strip().str.lower().str.replace(' ', '_')

        if not df_ind.empty:
            actual = df_ind.iloc[-1]
            puntos = 0
            if str(actual.get('existencia_cmdr', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 30
            if str(actual.get('tiene_protocolo_articulacion', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 20
            puntos += (int(actual.get('nivel_digitalizacion', 0)) * 10)

            c_sem, c_met = st.columns([1, 2])
            with c_sem:
                color = "🔴" if puntos < 40 else "🟡" if puntos < 75 else "🟢"
                st.markdown(f"### {color} SADCI: {puntos}/100")
            with c_met:
                st.progress(puntos / 100)
                st.write(f"**Entidad:** {actual.get('nombre_entidad', 'Alcaldía')}")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Presupuesto Rural", f"${actual.get('presupuesto_anual_rural', 0):,.0f}")
            m2.metric("Planta/Contratos", f"{actual.get('num_personal_planta', 0)} / {actual.get('num_personal_contratista', 0)}")
            m3.metric("Digitalización", f"{actual.get('nivel_digitalizacion', 0)}/5")
    except:
        st.warning("Conectando con la base de datos de indicadores...")

# --- TAB 3: REGISTRO DE ACTORES (SOCIAL) ---
with tab3:
    st.subheader("Directorio de Actores Rurales")
    
    with st.form("registro_actores_rurales"):
        col_a, col_b = st.columns(2)
        with col_a:
            nombre_act = st.text_input("Nombre del Actor / Organización")
            tipo_act = st.selectbox("Perfil", ["Campesino", "JAC", "Mujer Rural", "Víctima", "Otro"])
        with col_b:
            vereda_act = st.text_input("Vereda de Influencia")
            estado_t = st.selectbox("Tenencia", ["Sin Título", "En Proceso", "Adjudicado"])
        
        obs_act = st.text_area("Notas de la situación agraria")
        
        if st.form_submit_button("Guardar Actor"):
            # Aquí podrías conectar a una SEGUNDA hoja de tu Sheets
            st.success(f"Actor {nombre_act} registrado para análisis.")

st.divider()
st.caption("Investigación ESAP 2026 - Colectivo Guadalupe Salcedo")

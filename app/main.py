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
st.markdown("### Gestión Territorial, Actores y Capacidad Institucional (SADCI)")
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

# 3. PANELES DE CONTROL
tab_mapa, tab_sadci, tab_actores = st.tabs([
    "🗺️ Mapa de Conflictos", 
    "📊 Auditoría SADCI", 
    "👥 Registro de Actores"
])

# --- TAB 1: MAPA ---
with tab_mapa:
    st.subheader("Visualizador de Tenencia y Conflictos")
    col_menu, col_mapa = st.columns([1, 3])
    with col_menu:
        st.markdown("### 🛠️ Panel de Control")
        mostrar_veredas = st.checkbox("Límites Veredales", value=True)
        mostrar_conflictos = st.checkbox("Puntos de Conflicto", value=True)
    with col_mapa:
        m = folium.Map(location=[1.91, -75.18], zoom_start=11)
        if veredas_topo and mostrar_veredas:
            folium.TopoJson(veredas_topo, f"objects.{list(veredas_topo['objects'].keys())[0]}").add_to(m)
        st_folium(m, width=800, height=600, key="mapa_v3")

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("Análisis de Capacidad Institucional")
    try:
        df_ind = conn.read(ttl=0)
        st.dataframe(df_ind.head()) # Vista previa rápida
    except Exception as e:
        st.error(f"Error al conectar con Sheets: {e}")

# --- TAB 3: REGISTRO DE ACTORES (Ajuste aquí) ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    
    # Intento de carga inicial de datos
    try:
        df_social = conn.read(worksheet="Actores", ttl=0)
    except:
        try:
            df_social = conn.read(ttl=0) 
            st.warning("⚠️ Usando pestaña por defecto. No se encontró 'Actores'.")
        except:
            df_social = pd.DataFrame()

    with st.form("registro_social"):
        c1, c2 = st.columns(2)
        with c1:
            nombre_a = st.text_input("Nombre del Actor/Líder")
            perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
        with c2:
            vereda_a = st.text_input("Vereda de ubicación")
            tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
        
        obs_a = st.text_area("Observaciones técnicas de la situación")
        btn_social = st.form_submit_button("📤 Registrar en Base de Datos Social")
    
        if btn_social:
            if nombre_a and vereda_a:
                nuevo_actor = pd.DataFrame([{
                    "ID_Actor": str(uuid.uuid4())[:8],
                    "Nombre": nombre_a,
                    "Perfil": perfil_a,
                    "Vereda": vereda_a,
                    "Tenencia": tenencia_a,
                    "Observaciones": obs_a
                }])
                try:
                    df_final_soc = pd.concat([df_social, nuevo_actor], ignore_index=True)
                    # Intentamos actualizar en 'Actores', si falla, en la principal
                    try:
                        conn.update(worksheet="Actores", data=df_final_soc)
                    except:
                        conn.update(data=df_final_soc)
                    st.success(f"✅ Actor {nombre_a} registrado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    st.divider()
    st.subheader("📊 Análisis de Caracterización Social")
    if not df_social.empty:
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total Actores", len(df_social))
        st.dataframe(df_social, use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

st.divider()
st.caption("Investigación ESAP 2026 - Herramienta Unificada SIGOber-Rural")

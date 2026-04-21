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
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                folium.TopoJson(veredas_topo, f"objects.{obj_name}").add_to(m)
            except:
                st.warning("No se pudo cargar la topología de veredas.")
        st_folium(m, width=800, height=600, key="mapa_v3")

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("Análisis de Capacidad Institucional")
    try:
        df_ind = conn.read(ttl=0)
        st.dataframe(df_ind.head()) 
    except Exception as e:
        st.error(f"Error al conectar con Sheets: {e}")

# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    
    try:
        df_social = conn.read(worksheet="Actores", ttl=0)
    except:
        try:
            df_social = conn.read(ttl=0)
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
                    df_final_soc = pd.concat([df_social, nuevo_actor], ignore_index=True) if not df_social.empty else nuevo_actor
                    
                    # Actualización y limpieza de caché
                    conn.update(worksheet="Actores", data=df_final_soc)
                    st.cache_data.clear() 
                    
                    st.success(f"✅ Actor {nombre_a} registrado correctamente.")
                    st.rerun()
                except Exception as e:
                    if "200" in str(e):
                        st.cache_data.clear()
                        st.success(f"✅ Datos sincronizados con Google Sheets.")
                        st.rerun()
                    else:
                        st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor completa los campos obligatorios (Nombre y Vereda).")

    if not df_social.empty:
        st.divider()
        st.write("### Listado de Actores Registrados")
        st.dataframe(df_social, use_container_width=True)

st.divider()
st.caption("Investigación ESAP 2026 - Herramienta Unificada SIGOber-Rural")

st.sidebar.divider()
if st.sidebar.button("🛠️ Forzar Prueba de Escritura"):
    try:
        # Intentamos escribir un valor de prueba en una celda nueva
        test_df = pd.DataFrame([{"Prueba": "Conexión Exitosa", "Fecha": str(uuid.uuid4())[:5]}])
        conn.update(worksheet="Actores", data=test_df)
        st.sidebar.success("¡Escritura confirmada en Google Sheets!")
        st.cache_data.clear()
    except Exception as e:
        st.sidebar.error(f"Fallo de escritura: {e}")

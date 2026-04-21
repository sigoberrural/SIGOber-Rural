import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import uuid
import gspread
from google.oauth2.service_account import Credentials

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", layout="wide")
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("### Gestión Territorial, Actores y Capacidad Institucional (SADCI)")
st.divider()

# 2. CONEXIÓN A DATOS
conn = st.connection("gsheets", type=GSheetsConnection)

# Función para conexión robusta con gspread (para escritura)
def conectar_gspread():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(creds_dict["spreadsheet"])

def cargar_json_local(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

veredas_topo = cargar_json_local('veredas_puerto_rico.json')

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
    with col_mapa:
        m = folium.Map(location=[1.91, -75.18], zoom_start=11)
        if veredas_topo and mostrar_veredas:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                folium.TopoJson(veredas_topo, f"objects.{obj_name}").add_to(m)
            except: pass
        st_folium(m, width=800, height=600, key="mapa_v3")

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("Análisis de Capacidad Institucional")
    try:
        df_ind = conn.read(ttl=0)
        st.dataframe(df_ind.head()) 
    except Exception as e:
        st.error(f"Error de lectura: {e}")

# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    
    try:
        # Leemos con la conexión normal para visualización
        df_social = conn.read(worksheet="Actores", ttl=0)
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
        
        obs_a = st.text_area("Observaciones técnicas")
        btn_social = st.form_submit_button("📤 Registrar Actor")
    
      if btn_social:
            if nombre_a and vereda_a:
                try:
                    # 1. Intentar conectar
                    sh = conectar_gspread()
                    ws = sh.worksheet("Actores")
                    
                    # 2. Preparar la fila
                    nueva_fila = [
                        str(uuid.uuid4())[:8],
                        nombre_a,
                        perfil_a,
                        vereda_a,
                        tenencia_a,
                        obs_a
                    ]
                    
                    # 3. Escritura directa
                    ws.append_row(nueva_fila)
                    
                    st.cache_data.clear()
                    st.success(f"✅ ¡Éxito! {nombre_a} registrado.")
                    st.rerun()
                    
                except gspread.exceptions.WorksheetNotFound:
                    st.error("❌ Error: No existe una pestaña llamada 'Actores' en tu Excel.")
                except gspread.exceptions.APIError as e:
                    st.error(f"❌ Error de Google API: {e}")
                except Exception as e:
                    # Esto nos dirá el nombre técnico del error si lo anterior falla
                    st.error(f"❌ Error técnico: {type(e).__name__} - {str(e)}")
            else:
                st.warning("Completa Nombre y Vereda.")

    if not df_social.empty:
        st.divider()
        st.dataframe(df_social, use_container_width=True)

st.divider()
st.caption("Investigación ESAP 2026")

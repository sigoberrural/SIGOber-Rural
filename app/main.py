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

def conectar_gspread():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # Cargamos los secrets
    creds_info = dict(st.secrets["connections"]["gsheets"])
    
    # TRUCO CRÍTICO: Asegurar que los \n se lean como saltos de línea reales
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(creds_info["spreadsheet"])

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
    st.subheader("Auditoría SADCI: Capacidad Institucional Integral")
    
    try:
        sh = conectar_gspread()
        ws_sadci = sh.worksheet("SADCI") 
        data_sadci = ws_sadci.get_all_records()
        df_sadci = pd.DataFrame(data_sadci)
        
        if not df_sadci.empty:
            # --- CÁLCULO DE DIMENSIONES SADCI ---
            st.markdown("### 📊 Tablero de Dimensiones SADCI")
            
            # Dimensiones calculadas
            # 1. Dimensión Administrativa (Planta vs Contratos)
            df_sadci['dim_admin'] = (df_sadci['num_personal_planta'] / (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista'])) * 100
            
            # 2. Dimensión Tecnológica
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['dim_tec'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            
            # 3. Dimensión Eficacia (Ejecución + PDT)
            df_sadci['dim_eficacia'] = (df_sadci['ejecucion_presupuestal_pct'] + df_sadci['cumplimiento_pdt_pct']) / 2
            
            # 4. Dimensión Transparencia (Rendición + Protocolos)
            df_sadci['dim_transp'] = df_sadci['frecuencia_rendicion_cuentas'].apply(lambda x: 100 if x != "Nunca" else 0)

            # Visualización de KPIs
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gobernanza (Adm)", f"{df_sadci['dim_admin'].mean():.1f}%")
            m2.metric("Eficacia Fiscal", f"{df_sadci['ejecucion_presupuestal_pct'].mean():.1f}%")
            m3.metric("Desarrollo Tec.", f"{df_sadci['dim_tec'].mean():.1f}%")
            m4.metric("Transparencia", f"{df_sadci['dim_transp'].mean():.1f}%")

            # Gráfico Comparativo por Entidad
            st.write("#### Comparativa Interinstitucional")
            chart_data = df_sadci.set_index('nombre_entidad')[['dim_admin', 'dim_tec', 'dim_eficacia', 'dim_transp']]
            st.bar_chart(chart_data)
            
            st.divider()

        # --- FORMULARIO SADCI AMPLIADO ---
        with st.expander("📝 Formulario de Auditoría Integral (Nuevas Dimensiones)", expanded=df_sadci.empty):
            with st.form("registro_sadci_full", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.info("📦 Gestión y Talento")
                    nombre = st.text_input("Entidad")
                    presupuesto = st.number_input("Presupuesto ($)", min_value=0)
                    planta = st.number_input("Personal Planta", min_value=0)
                    contratos = st.number_input("Personal Contrato", min_value=0)
                
                with c2:
                    st.info("📈 Eficacia y Resultados")
                    ejecucion = st.slider("% Ejecución Presupuestal", 0, 100, 50)
                    pdt = st.slider("% Cumplimiento Plan Desarrollo", 0, 100, 50)
                    mepi = st.number_input("Calificación MEPI (0-100)", 0, 100)
                
                with c3:
                    st.info("🤝 Relacional y Digital")
                    digital = st.select_slider("Digitalización", ["Bajo", "Medio", "Alto", "Excelente"])
                    protocolo = st.selectbox("Protocolo Articulación", ["Sí", "No", "En proceso"])
                    participacion = st.selectbox("Instancias Participación", ["Activas", "Inactivas", "Inexistentes"])
                    rendicion = st.selectbox("Rendición Cuentas", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("🚀 Finalizar Auditoría"):
                    if nombre:
                        # Debe coincidir con el orden de las columnas de tu Excel
                        nueva_fila = [
                            str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                            protocolo, "Sí", rendicion, digital, 
                            ejecucion, pdt, participacion, mepi
                        ]
                        ws_sadci.append_row(nueva_fila)
                        st.success("Auditoría Integral Guardada.")
                        st.cache_data.clear()
                        st.rerun()

        if not df_sadci.empty:
            st.write("### Base de Datos SADCI")
            st.dataframe(df_sadci, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
        
# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    
    try:
        df_social = conn.read(worksheet="Actores", ttl=0)
    except:
        df_social = pd.DataFrame()

    with st.form("registro_social", clear_on_submit=True):
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
                    sh = conectar_gspread()
                    ws = sh.worksheet("Actores")
                    
                    nueva_fila = [
                        str(uuid.uuid4())[:8],
                        nombre_a,
                        perfil_a,
                        vereda_a,
                        tenencia_a,
                        obs_a
                    ]
                    
                    ws.append_row(nueva_fila)
                    
                    st.success(f"✅ ¡Éxito! {nombre_a} registrado correctamente.")
                    st.cache_data.clear()
                    # No usamos rerun inmediato aquí para que el usuario vea el mensaje de éxito
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")
            else:
                st.warning("⚠️ Nombre y Vereda son obligatorios.")

    if not df_social.empty:
        st.divider()
        st.write("### Base de Datos Actual")
        st.dataframe(df_social, use_container_width=True)

st.divider()
st.caption("Investigación ESAP 2026")

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
    # REEMPLAZA ESTO:
    # ws_conf = sh.worksheet("Conflictos")
    # df_conf = pd.DataFrame(ws_conf.get_all_records())
    
    # POR ESTO:
    df_conf = cargar_datos_con_cache("Conflictos")
    
    # Aseguramos tipos numéricos
    if not df_conf.empty:
        df_conf['lat'] = pd.to_numeric(df_conf['lat'], errors='coerce')
        df_conf['lon'] = pd.to_numeric(df_conf['lon'], errors='coerce')
        df_conf = df_conf.dropna(subset=['lat', 'lon'])

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    
    try:
        sh = conectar_gspread()
        ws_sadci = sh.worksheet("SADCI") 
        data_sadci = ws_sadci.get_all_records()
        df_sadci = pd.DataFrame(data_sadci)
        
        if not df_sadci.empty:
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            df_sadci['robustez_adm'] = (df_sadci['num_personal_planta'] / 
                                       (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                promedio_ejecucion = df_sadci['ejecucion_presupuestal_pct'].mean()
                st.metric("Eficacia Presupuestal", f"{promedio_ejecucion:.1f}%")
            with col_kpi2:
                promedio_pdt = df_sadci['cumplimiento_pdt_pct'].mean()
                st.metric("Meta PDT Media", f"{promedio_pdt:.1f}%")
            with col_kpi3:
                mepi_avg = df_sadci['calificacion_mepi'].mean()
                st.metric("Puntaje MEPI Promedio", f"{mepi_avg:.1f}/100")

            st.divider()
            col_graph1, col_graph2 = st.columns(2)
            with col_graph1:
                st.markdown("##### 🚀 Eficacia vs. Cumplimiento Meta")
                st.bar_chart(df_sadci.set_index('nombre_entidad')[['ejecucion_presupuestal_pct', 'cumplimiento_pdt_pct']])
            
            with col_graph2:
                st.markdown("##### 💻 Madurez Digital por Entidad")
                st.line_chart(df_sadci.set_index('nombre_entidad')['puntos_digital'])

            st.markdown("##### 🏛️ Balance de Dimensiones")
            resumen_dim = pd.DataFrame({
                "Dimensión": ["Administrativa", "Digital", "Eficacia", "Desempeño (MEPI)"],
                "Puntaje": [
                    df_sadci['robustez_adm'].mean(),
                    df_sadci['puntos_digital'].mean(),
                    df_sadci['ejecucion_presupuestal_pct'].mean(),
                    df_sadci['calificacion_mepi'].mean()
                ]
            })
            st.area_chart(resumen_dim.set_index("Dimensión"))

        with st.expander("📝 Realizar Nueva Auditoría Integral", expanded=df_sadci.empty):
            with st.form("registro_sadci_full", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nombre = st.text_input("Nombre Entidad")
                    presupuesto = st.number_input("Presupuesto Anual Rural ($)", min_value=0)
                    planta = st.number_input("Personal Planta", min_value=0)
                    contratos = st.number_input("Personal Contratista", min_value=0)
                
                with c2:
                    ejecucion = st.slider("% Ejecución Gasto", 0, 100, 70)
                    pdt = st.slider("% Avance Metas PDT", 0, 100, 50)
                    mepi = st.number_input("Calificación MEPI", 0, 100, 60)
                
                with c3:
                    digital = st.select_slider("Nivel Digital", ["Bajo", "Medio", "Alto", "Excelente"])
                    protocolo = st.selectbox("¿Protocolo Articulación?", ["Sí", "No", "En proceso"])
                    participacion = st.selectbox("Instancias Participación", ["Activas", "Inactivas", "Inexistentes"])
                    rendicion = st.selectbox("Rendición Cuentas", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("🚀 Guardar y Actualizar Dashboard"):
                    if nombre:
                        nueva_fila = [str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                                    protocolo, "Sí", rendicion, digital, 
                                    ejecucion, pdt, participacion, mepi]
                        ws_sadci.append_row(nueva_fila)
                        st.success("✅ Auditoría guardada.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("⚠️ El nombre de la entidad es obligatorio.")

    except Exception as e:
        st.error(f"Error en el sistema SADCI: {e}")
        
# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("👥 Caracterización de Actores Territoriales")
    try:
        sh = conectar_gspread()
        ws = sh.worksheet("Actores")
        df_social = pd.DataFrame(ws.get_all_records())
        
        if not df_social.empty:
            st.markdown("#### 📊 Análisis de Composición Social")
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                st.write("**Distribución por Perfil**")
                st.bar_chart(df_social['Perfil'].value_counts())
            with c_graf2:
                st.write("**Seguridad Jurídica (Tenencia)**")
                st.line_chart(df_social['Tenencia'].value_counts())
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas Cubiertas", df_social['Vereda'].nunique())
            propiedad_total = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            pct_formal = (propiedad_total / len(df_social)) * 100 if len(df_social) > 0 else 0
            m3.metric("Formalidad", f"{pct_formal:.1f}%")

        with st.expander("📝 Registrar Nuevo Actor", expanded=df_social.empty):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre del Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda de ubicación")
                    tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones técnicas")
                if st.form_submit_button("📤 Registrar Actor"):
                    if nombre_a and vereda_a:
                        ws.append_row([str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a])
                        st.success(f"✅ {nombre_a} registrado.")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Error en el módulo de actores: {e}")

st.divider()
st.caption("Investigación ESAP 2026")

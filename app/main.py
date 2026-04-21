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
    creds_info = dict(st.secrets["connections"]["gsheets"])
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
    
    try:
        sh = conectar_gspread()
        ws_conf = sh.worksheet("Conflictos")
        df_conf = pd.DataFrame(ws_conf.get_all_records())
    except:
        df_conf = pd.DataFrame()

    col_menu, col_mapa = st.columns([1, 3])

    with col_menu:
        st.markdown("### 🛠️ Capas y Filtros")
        mostrar_veredas = st.checkbox("Límites Veredales", value=True)
        mostrar_puntos = st.checkbox("Puntos de Conflicto", value=True)
        
        st.divider()
        st.markdown("### ⚠️ Registrar Conflicto")
        with st.form("form_conflictos", clear_on_submit=True):
            tipo_c = st.selectbox("Tipo", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda_c = st.text_input("Vereda afectada")
            c1, c2 = st.columns(2)
            lat_c = c1.number_input("Latitud", value=1.91, format="%.4f")
            lon_c = c2.number_input("Longitud", value=-75.18, format="%.4f")
            desc_c = st.text_area("Descripción breve")
            
            if st.form_submit_button("📍 Marcar en Mapa"):
                if vereda_c:
                    nueva_fila_c = [str(uuid.uuid4())[:5], tipo_c, vereda_c, lat_c, lon_c, desc_c]
                    ws_conf.append_row(nueva_fila_c)
                    st.success("Punto registrado.")
                    st.cache_data.clear()
                    st.rerun()

    with col_mapa:
        m = folium.Map(location=[1.91, -75.18], zoom_start=11, tiles="cartodbpositron")
        
        if veredas_topo and mostrar_veredas:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                geometrias = veredas_topo['objects'][obj_name]['geometries']
                props_ejemplo = geometrias[0].get('properties', {})
                teclas = list(props_ejemplo.keys())
                
                # Buscamos el campo que contiene el nombre (evita el AssertionError)
                prioridades = ['NOMBRE_VEREDA', 'NOM_VER', 'NOMBRE', 'VEREDA']
                campo_nombre = next((p for p in prioridades if p in teclas), (teclas[0] if teclas else None))

                if campo_nombre:
                    folium.TopoJson(
                        veredas_topo, 
                        f"objects.{obj_name}",
                        name="Límites Veredales",
                        tooltip=folium.GeoJsonTooltip(
                            fields=[campo_nombre], 
                            aliases=['📍 Vereda:'],
                            localize=True
                        ),
                        style_function=lambda x: {
                            'fillColor': '#2ecc71', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.2
                        }
                    ).add_to(m)
                else:
                    folium.TopoJson(veredas_topo, f"objects.{obj_name}").add_to(m)
            except Exception as e:
                st.error(f"Error en capa base: {e}")

        if not df_conf.empty and mostrar_puntos:
            for _, row in df_conf.iterrows():
                # Iconos por tipo de conflicto
                color_map = {"Tenencia": "red", "Ambiental": "green", "Linderos": "blue", "Uso de Suelo": "orange"}
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    icon=folium.Icon(color=color_map.get(row['tipo_conflicto'], "gray"), icon="info-sign"),
                    popup=f"<b>{row['tipo_conflicto']}</b><br>{row['descripcion']}",
                    tooltip=f"Conflicto: {row['vereda']}"
                ).add_to(m)

        st_folium(m, width=800, height=600, key="mapa_final")

    if not df_conf.empty:
        with st.expander("📊 Listado de Conflictos Registrados"):
            st.dataframe(df_conf[['tipo_conflicto', 'vereda', 'descripcion']], use_container_width=True)

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    try:
        sh = conectar_gspread()
        ws_sadci = sh.worksheet("SADCI") 
        df_sadci = pd.DataFrame(ws_sadci.get_all_records())
        
        if not df_sadci.empty:
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            df_sadci['robustez_adm'] = (df_sadci['num_personal_planta'] / 
                                       (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.metric("Eficacia Presupuestal", f"{df_sadci['ejecucion_presupuestal_pct'].mean():.1f}%")
            col_kpi2.metric("Meta PDT Media", f"{df_sadci['cumplimiento_pdt_pct'].mean():.1f}%")
            col_kpi3.metric("Puntaje MEPI Promedio", f"{df_sadci['calificacion_mepi'].mean():.1f}/100")

            st.divider()
            c_g1, c_g2 = st.columns(2)
            c_g1.bar_chart(df_sadci.set_index('nombre_entidad')[['ejecucion_presupuestal_pct', 'cumplimiento_pdt_pct']])
            c_g2.line_chart(df_sadci.set_index('nombre_entidad')['puntos_digital'])

        with st.expander("📝 Realizar Nueva Auditoría Integral"):
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
                    rendicion = st.selectbox("Rendición Cuentas", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("🚀 Guardar Auditoría"):
                    if nombre:
                        nueva_fila = [str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos, 
                                     protocolo, "Sí", rendicion, digital, ejecucion, pdt, "Activas", mepi]
                        ws_sadci.append_row(nueva_fila)
                        st.success("✅ Auditoría guardada.")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Error SADCI: {e}")

# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("👥 Caracterización de Actores Territoriales")
    try:
        sh = conectar_gspread()
        ws_act = sh.worksheet("Actores")
        df_social = pd.DataFrame(ws_act.get_all_records())
        
        if not df_social.empty:
            st.markdown("#### 📊 Análisis de Composición Social")
            c_graf1, c_graf2 = st.columns(2)
            c_graf1.bar_chart(df_social['Perfil'].value_counts())
            c_graf2.area_chart(df_social['Tenencia'].value_counts())
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas", df_social['Vereda'].nunique())
            prop = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            m3.metric("Formalidad", f"{(prop/len(df_social)*100):.1f}%" if len(df_social)>0 else "0%")

        with st.expander("📝 Registrar Nuevo Actor"):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre del Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda")
                    tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones")
                if st.form_submit_button("📤 Registrar"):
                    if nombre_a and vereda_a:
                        ws_act.append_row([str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a])
                        st.success("✅ Actor registrado.")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Error Actores: {e}")

st.divider()
st.caption("Investigación ESAP 2026 - SIGOber-Rural Puerto Rico")

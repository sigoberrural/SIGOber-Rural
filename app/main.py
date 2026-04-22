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

# --- FUNCIONES DE CARGA CON CACHÉ ---
@st.cache_data(ttl=600)
def cargar_datos_con_cache(nombre_hoja):
    try:
        sh = conectar_gspread()
        ws = sh.worksheet(nombre_hoja)
        return pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.error(f"Error al cargar la hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

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
    
    # 1. CARGA Y LIMPIEZA
    df_conf = cargar_datos_con_cache("Conflictos")
    if not df_conf.empty:
        # Limpieza profunda de nombres de columnas
        df_conf.columns = df_conf.columns.str.strip().str.lower()
        df_conf['lat'] = pd.to_numeric(df_conf['lat'], errors='coerce')
        df_conf['lon'] = pd.to_numeric(df_conf['lon'], errors='coerce')
        df_conf = df_conf.dropna(subset=['lat', 'lon'])

    col_menu, col_mapa = st.columns([1, 3])

    # Inicializar coordenadas en session_state
    if "lat_click" not in st.session_state:
        st.session_state.lat_click = 1.91
    if "lon_click" not in st.session_state:
        st.session_state.lon_click = -75.18

    with col_menu:
        st.markdown("### ⚠️ Registrar Conflicto")
        st.caption("Toca el mapa para capturar coordenadas automáticamente.")
        
        with st.form("form_conflictos", clear_on_submit=True):
            quien = st.text_input("Encuestador")
            tipo = st.selectbox("Tipo", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda = st.text_input("Vereda")
            
            c1, c2 = st.columns(2)
            # Usamos lat_click y lon_click
            lat_input = c1.number_input("Latitud", value=float(st.session_state.lat_click), format="%.6f")
            lon_input = c2.number_input("Longitud", value=float(st.session_state.lon_click), format="%.6f")
            
            desc = st.text_area("Descripción")
            
            if st.form_submit_button("📍 Guardar Registro"):
                if vereda and quien:
                    sh = conectar_gspread()
                    ws = sh.worksheet("Conflictos")
                    ws.append_row([str(uuid.uuid4())[:5], tipo, vereda, lat_input, lon_input, desc, quien])
                    st.success("✅ Guardado.")
                    st.cache_data.clear()
                    st.rerun()

    with col_mapa:
        m = folium.Map(location=[st.session_state.lat_click, st.session_state.lon_click], 
                       zoom_start=12, tiles="cartodbpositron")
        
        # 2. CAPA VEREDAS (Solución al AssertionError)
        if veredas_topo:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                # Extraemos las propiedades del primer elemento para ver cómo se llama el campo
                sample_props = veredas_topo['objects'][obj_name]['geometries'][0].get('properties', {})
                
                # Buscamos el campo de nombre dinámicamente
                posibles = ['NOMBRE_VEREDA', 'NOM_VER', 'NOMBRE', 'VEREDA', 'NOMB_VER']
                campo_final = next((f for f in posibles if f in sample_props), None)

                tj = folium.TopoJson(
                    data=veredas_topo, 
                    object_path=f"objects.{obj_name}",
                    name="Veredas Puerto Rico",
                    style_function=lambda x: {'fillColor': '#2ecc71', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.1}
                )
                
                # Solo agregamos tooltip si encontramos el campo, para evitar el AssertionError
                if campo_final:
                    folium.GeoJsonTooltip(fields=[campo_final], aliases=['Vereda:']).add_to(tj)
                
                tj.add_to(m)
            except Exception as e:
                st.warning(f"Capa veredas cargada sin etiquetas (Error: {e})")

        # 3. CAPA PUNTOS (Asegurando visibilidad)
        if not df_conf.empty:
            for _, row in df_conf.iterrows():
                # Buscamos el nombre de columna correcto para el tipo
                t_conf = row.get('tipo_conflicto', row.get('tipo', 'Conflicto'))
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=7,
                    color="red" if str(t_conf).lower() == "tenencia" else "orange",
                    fill=True,
                    fill_opacity=0.8,
                    popup=f"Vereda: {row.get('vereda')}<br>Tipo: {t_conf}"
                ).add_to(m)

        # 4. CAPTURA DE CLIC
        output = st_folium(m, width=700, height=500, key="mapa_pr")

        # Si el usuario hace clic, actualizamos la posición
        if output.get("last_clicked"):
            click_lat = output["last_clicked"]["lat"]
            click_lon = output["last_clicked"]["lng"]
            
            # Solo si el clic es nuevo, actualizamos y recargamos
            if abs(st.session_state.lat_click - click_lat) > 0.00001:
                st.session_state.lat_click = click_lat
                st.session_state.lon_click = click_lon
                st.rerun()
                
# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    try:
        df_sadci = cargar_datos_con_cache("SADCI")
        if not df_sadci.empty:
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            df_sadci['robustez_adm'] = (df_sadci['num_personal_planta'] / 
                                       (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                st.metric("Eficacia Presupuestal", f"{df_sadci['ejecucion_presupuestal_pct'].mean():.1f}%")
            with col_kpi2:
                st.metric("Meta PDT Media", f"{df_sadci['cumplimiento_pdt_pct'].mean():.1f}%")
            with col_kpi3:
                st.metric("Puntaje MEPI Promedio", f"{df_sadci['calificacion_mepi'].mean():.1f}/100")

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
                "Puntaje": [df_sadci['robustez_adm'].mean(), df_sadci['puntos_digital'].mean(), 
                           df_sadci['ejecucion_presupuestal_pct'].mean(), df_sadci['calificacion_mepi'].mean()]
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

                if st.form_submit_button("🚀 Guardar y Actualizar"):
                    if nombre:
                        sh_d = conectar_gspread()
                        ws_d = sh_d.worksheet("SADCI")
                        nueva_fila = [str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                                    protocolo, "Sí", rendicion, digital, ejecucion, pdt, participacion, mepi]
                        ws_d.append_row(nueva_fila)
                        st.success("✅ Guardado.")
                        st.cache_data.clear()
                        st.rerun()
    except Exception as e:
        st.error(f"Error SADCI: {e}")

# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("👥 Caracterización de Actores Territoriales")
    try:
        df_social = cargar_datos_con_cache("Actores")
        if not df_social.empty:
            st.markdown("#### 📊 Análisis de Composición Social")
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                st.bar_chart(df_social['Perfil'].value_counts())
            with c_graf2:
                st.line_chart(df_social['Tenencia'].value_counts())
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas Cubiertas", df_social['Vereda'].nunique())
            propiedad_total = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            m3.metric("Formalidad", f"{(propiedad_total/len(df_social))*100:.1f}%")

        with st.expander("📝 Registrar Nuevo Actor", expanded=df_social.empty):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre del Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda de ubicación")
                    tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones")
                if st.form_submit_button("📤 Registrar Actor"):
                    if nombre_a and vereda_a:
                        sh_act = conectar_gspread()
                        ws_act = sh_act.worksheet("Actores")
                        ws_act.append_row([str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a])
                        st.success(f"✅ {nombre_a} registrado.")
                        st.cache_data.clear()
                        st.rerun()
    except Exception as e:
        st.error(f"Error módulo actores: {e}")

st.divider()
st.caption("Investigación ESAP 2026")

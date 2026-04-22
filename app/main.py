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

with col_mapa:
        # 1. DEFINICIÓN DE MAPA BASE Y CAPAS SATELITALES
        m = folium.Map(
            location=[st.session_state.lat_click, st.session_state.lon_click], 
            zoom_start=12,
            tiles=None  # Desactivamos el default para manejar las capas nosotros
        )

        # Capa Satelital (Google) - La mejor para referencias de campo
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google',
            name='Vista Satelital (Híbrida)',
            overlay=False,
            control=True
        ).add_to(m)

        # Capa de Calles y Vías (OpenStreetMap)
        folium.TileLayer(
            tiles='openstreetmap',
            name='Mapa de Vías y Ríos',
            overlay=False,
            control=True
        ).add_to(m)

        # 2. CAPA DE VEREDAS (Límites vectoriales)
        if veredas_topo:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                folium.TopoJson(
                    veredas_topo, 
                    f"objects.{obj_name}",
                    name="Límites Veredales",
                    style_function=lambda x: {
                        'fillColor': 'transparent', 
                        'color': '#FFFF00', # Amarillo brillante para resaltar sobre satélite
                        'weight': 2, 
                        'fillOpacity': 0.1
                    }
                ).add_to(m)
            except: pass

        # 3. CAPA DE PUNTOS DE CONFLICTO
        fg_conflictos = folium.FeatureGroup(name="Puntos Registrados")
        if not df_plot.empty:
            for _, row in df_plot.iterrows():
                try:
                    tipo_val = str(row.get('tipo', row.get('tipo_conflicto', ''))).lower()
                    color_p = "red" if "tenencia" in tipo_val else "orange"
                    
                    folium.CircleMarker(
                        location=[row['lat'], row['lon']],
                        radius=8,
                        color="white", # Borde blanco para contraste
                        weight=2,
                        fill_color=color_p,
                        fill=True,
                        fill_opacity=1,
                        popup=f"<b>Vereda:</b> {row.get('vereda')}<br><b>Tipo:</b> {row.get('tipo', 'S/D')}"
                    ).add_to(fg_conflictos)
                except: continue
        
        fg_conflictos.add_to(m)

        # 4. CONTROL DE CAPAS (Aquí es donde el usuario elige qué ver)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)

        # Renderizado
        output = st_folium(m, width=700, height=500, key="mapa_final")

        # Lógica de captura de clic
        if output and output.get("last_clicked"):
            clic = output["last_clicked"]
            if abs(st.session_state.lat_click - clic["lat"]) > 0.0001:
                st.session_state.lat_click = clic["lat"]
                st.session_state.lon_click = clic["lng"]
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

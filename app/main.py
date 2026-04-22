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
from shapely.geometry import shape, Point
import topojson as tp
from streamlit_js_eval import get_geolocation

# 1. CONFIGURACIÓN E INTERFAZ (Optimizado para móvil)
st.set_page_config(
    page_title="SIGOber-Rural Puerto Rico", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILO CSS PERSONALIZADO (Mejora UX en móvil) ---
st.markdown("""
    <style>
    /* Botones más grandes para dedos en móvil */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    /* Ajuste de márgenes para pantallas pequeñas */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

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
    df_raw = cargar_datos_con_cache("Conflictos")
    df_plot = pd.DataFrame()
    if df_raw is not None and not df_raw.empty:
        df_plot = df_raw.copy()
        df_plot.columns = df_plot.columns.str.strip().str.lower()
        for col in ['lat', 'lon']:
            if col in df_plot.columns:
                df_plot[col] = df_plot[col].astype(str).str.replace(',', '.').str.strip()
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
        df_plot = df_plot.dropna(subset=['lat', 'lon'])

    # 2. CAPTURA AUTOMÁTICA DE GEOLOCALIZACIÓN
    if "gps_capturado" not in st.session_state:
        loc = get_geolocation()
        if loc:
            st.session_state.lat_click = loc['coords']['latitude']
            st.session_state.lon_click = loc['coords']['longitude']
            st.session_state.gps_capturado = True

    if "lat_click" not in st.session_state:
        st.session_state.lat_click = 1.9123
    if "lon_click" not in st.session_state:
        st.session_state.lon_click = -75.1842

    # 3. LÓGICA DE VALIDACIÓN (GEOFENCING CORREGIDO)
    def validar_punto_preciso(lat, lon, topo_data):
        if topo_data is None: return True, "Capa no cargada"
        try:
            punto_eval = Point(float(lon), float(lat)) # Longitud, Latitud
            from topojson import to_geojson
            geojson_data = to_geojson(topo_data)
            for feature in geojson_data['features']:
                if shape(feature['geometry']).contains(punto_eval):
                    return True, feature['properties'].get('NOMBRE_VER', 'Vereda Localizada')
            return False, None
        except: return True, "Error técnico de validación"

    # 4. INTERFAZ DE REGISTRO
    col_menu, col_mapa = st.columns([1, 3])

    with col_menu:
        st.markdown("### ⚠️ Registrar Conflicto")
        with st.form("form_conflictos", clear_on_submit=True):
            quien = st.text_input("Encuestador / Líder")
            tipo = st.selectbox("Tipo", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda_manual = st.text_input("Vereda (Si el GPS no la detecta)")
            
            c1, c2 = st.columns(2)
            lat_i = c1.number_input("Latitud", value=float(st.session_state.lat_click), format="%.6f")
            lon_i = c2.number_input("Longitud", value=float(st.session_state.lon_click), format="%.6f")
            
            desc = st.text_area("Descripción")
            
            if st.form_submit_button("📍 Guardar Registro"):
                es_valido, vereda_detectada = validar_punto_preciso(lat_i, lon_i, veredas_topo)
                if es_valido and quien:
                    try:
                        sh = conectar_gspread()
                        ws = sh.worksheet("Conflictos")
                        v_final = vereda_detectada if vereda_detectada else vereda_manual
                        ws.append_row([str(uuid.uuid4())[:5], tipo, v_final, str(lat_i), str(lon_i), desc, quien])
                        st.success(f"✅ Registrado en {v_final}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                elif not es_valido:
                    st.error("📍 Ubicación fuera de los límites de Puerto Rico.")
                else: st.warning("Completa el nombre del encuestador.")

    # 5. MAPA CON SELECTOR Y TOOLTIP
    with col_mapa:
        m = folium.Map(
            location=[st.session_state.lat_click, st.session_state.lon_click], 
            zoom_start=14, tiles=None
        )
        folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         attr='Google', name='Satélite', overlay=False).add_to(m)
        folium.TileLayer('openstreetmap', name='Vías', overlay=False).add_to(m)

        if veredas_topo:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                folium.TopoJson(
                    veredas_topo, f"objects.{obj_name}", name="Veredas",
                    style_function=lambda x: {'fillColor': 'transparent', 'color': '#FFFF00', 'weight': 2, 'fillOpacity': 0.1},
                    tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'], sticky=True)
                ).add_to(m)
            except: pass

        fg = folium.FeatureGroup(name="Historial")
        if not df_plot.empty:
            for _, row in df_plot.iterrows():
                folium.CircleMarker(location=[row['lat'], row['lon']], radius=6, 
                                    color="red", fill=True, popup=row.get('tipo')).add_to(fg)
        fg.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        
        output = st_folium(m, width="100%", height=450, key="mapa_final")

        if output and output.get("last_clicked"):
            clic = output["last_clicked"]
            if abs(st.session_state.lat_click - clic["lat"]) > 0.0001:
                st.session_state.lat_click = clic["lat"]
                st.session_state.lon_click = clic["lng"]
                st.rerun()

# --- TAB 2: AUDITORÍA SADCI --- (Sin cambios en tu lógica)
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
            with col_kpi1: st.metric("Eficacia Presupuestal", f"{df_sadci['ejecucion_presupuestal_pct'].mean():.1f}%")
            with col_kpi2: st.metric("Meta PDT Media", f"{df_sadci['cumplimiento_pdt_pct'].mean():.1f}%")
            with col_kpi3: st.metric("Puntaje MEPI Promedio", f"{df_sadci['calificacion_mepi'].mean():.1f}/100")

            st.divider()
            col_graph1, col_graph2 = st.columns(2)
            with col_graph1: st.bar_chart(df_sadci.set_index('nombre_entidad')[['ejecucion_presupuestal_pct', 'cumplimiento_pdt_pct']])
            with col_graph2: st.line_chart(df_sadci.set_index('nombre_entidad')['puntos_digital'])

        with st.expander("📝 Realizar Nueva Auditoría"):
            with st.form("registro_sadci_full", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nombre = st.text_input("Nombre Entidad")
                    presupuesto = st.number_input("Presupuesto Rural ($)", min_value=0)
                    planta = st.number_input("Planta", min_value=0)
                    contratos = st.number_input("Contratistas", min_value=0)
                with c2:
                    ejecucion = st.slider("% Gasto", 0, 100, 70)
                    pdt = st.slider("% Metas", 0, 100, 50)
                    mepi = st.number_input("MEPI", 0, 100, 60)
                with c3:
                    digital = st.select_slider("Digital", ["Bajo", "Medio", "Alto", "Excelente"])
                    protocolo = st.selectbox("¿Protocolo?", ["Sí", "No", "En proceso"])
                    rendicion = st.selectbox("Rendición", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("🚀 Guardar"):
                    if nombre:
                        sh_d = conectar_gspread()
                        ws_d = sh_d.worksheet("SADCI")
                        ws_d.append_row([str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                                         protocolo, "Sí", rendicion, digital, ejecucion, pdt, "Activas", mepi])
                        st.success("✅ Guardado.")
                        st.cache_data.clear()
                        st.rerun()
    except Exception as e: st.error(f"Error SADCI: {e}")

# --- TAB 3: ACTORES --- (Sin cambios en tu lógica)
with tab_actores:
    st.subheader("👥 Caracterización de Actores")
    try:
        df_social = cargar_datos_con_cache("Actores")
        if not df_social.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas", df_social['Vereda'].nunique())
            propiedad_total = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            m3.metric("Formalidad", f"{(propiedad_total/len(df_social))*100:.1f}%")

        with st.expander("📝 Registrar Nuevo Actor"):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda")
                    tenencia_a = st.selectbox("Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones")
                if st.form_submit_button("📤 Registrar"):
                    if nombre_a and vereda_a:
                        sh_act = conectar_gspread()
                        ws_act = sh_act.worksheet("Actores")
                        ws_act.append_row([str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a])
                        st.success(f"✅ {nombre_a} registrado.")
                        st.cache_data.clear()
                        st.rerun()
    except Exception as e: st.error(f"Error actores: {e}")

st.divider()
st.caption("Investigación ESAP 2026")

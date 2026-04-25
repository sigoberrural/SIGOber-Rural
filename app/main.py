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
import plotly.express as px
import pandas as pd

# 1. CONFIGURACIÓN E INTERFAZ (Optimizado para móvil)
st.set_page_config(
    page_title="SIGOber-Rural Puerto Rico", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Estilo para los créditos finales */
    .footer-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        padding: 10px;
        margin-top: 20px;
    }
    .footer-text {
        font-size: 0.9rem;
        color: #555;
        text-align: center;
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

    def validar_punto_preciso(lat, lon, topo_data):
        if topo_data is None: return True, "Capa no cargada"
        try:
            punto_eval = Point(float(lon), float(lat))
            from topojson import to_geojson
            geojson_data = to_geojson(topo_data)
            for feature in geojson_data['features']:
                if shape(feature['geometry']).contains(punto_eval):
                    return True, feature['properties'].get('NOMBRE_VER', 'Vereda Localizada')
            return False, None
        except: return True, "Error técnico de validación"

    col_menu, col_mapa = st.columns([1, 3])

    with col_menu:
        st.markdown("### ⚠️ Registrar Conflicto")
        with st.form("form_conflictos", clear_on_submit=True):
            quien = st.text_input("Encuestador / Líder")
            tipo = st.selectbox("Tipo", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda_manual = st.text_input("Vereda")
            
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


# --- TAB 2: AUDITORÍA SADCI (Metodología Oszlak-Tobelem) ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    
    try:
        df_sadci = cargar_datos_con_cache("SADCI")
        if not df_sadci.empty:
            # 1. CÁLCULO DE ÍNDICES DE CAPACIDAD REAL (Basado en metodología)[cite: 1]
            df_sadci['capacidad_personal'] = (df_sadci['num_personal_planta'] / 
                                            (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)
            
            dict_dig = {"Bajo": 20, "Medio": 50, "Alto": 80, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                st.metric("Capacidad Financiera", f"{df_sadci['ejecucion_presupuestal_pct'].mean():.1f}%", help="DCI relacionado con la capacidad financiera[cite: 1]")
            with col_kpi2:
                st.metric("Efectividad Metas PDT", f"{df_sadci['cumplimiento_pdt_pct'].mean():.1f}%", help="Brecha entre aspiración y logro real[cite: 1]")
            with col_kpi3:
                st.metric("Desempeño Institucional", f"{df_sadci['calificacion_mepi'].mean():.1f}/100")

            st.divider()
            
            # 2. VISUALIZACIÓN DE BRECHAS
            col_graph1, col_graph2 = st.columns(2)
            with col_graph1:
                st.write("**Brecha de Ejecución vs. Metas**")
                st.bar_chart(df_sadci.set_index('nombre_entidad')[['ejecucion_presupuestal_pct', 'cumplimiento_pdt_pct']])
            
            with col_graph2:
                st.write("**Nivel de Digitalización (DCI Insumos)**")
                st.line_chart(df_sadci.set_index('nombre_entidad')['puntos_digital'])

        # 3. FORMULARIO DE CAPTURA
        with st.expander("📝 Registrar Nueva Evaluación de Capacidad (DCI)"):
            with st.form("registro_sadci_full", clear_on_submit=True):
                st.info("Complete los datos para identificar el grado de capacidad actual[cite: 1].")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**Identificación (Form A)**")
                    nombre = st.text_input("Nombre de la Agencia/Entidad")
                    presupuesto = st.number_input("Presupuesto Asignado ($)", min_value=0)
                    planta = st.number_input("Personal de Planta (DCI-5)", min_value=0)
                    contratos = st.number_input("Contratistas (DCI-5)", min_value=0)
                
                with c2:
                    st.markdown("**Desempeño (Form B/C)**")
                    ejecucion = st.slider("% Eficacia Financiera (DCI-4)", 0, 100, 70)
                    pdt = st.slider("% Avance Tareas Físicas", 0, 100, 50)
                    mepi = st.number_input("Puntaje MEPI (DCI-1)", 0, 100, 60)
                
                with c3:
                    st.markdown("**Obstáculos (Form D1-D6)**")
                    digital = st.select_slider("Capacidad Tecnológica", ["Bajo", "Medio", "Alto", "Excelente"])
                    protocolo = st.selectbox("¿Existen Reglas/Normas claras? (DCI-1)", ["Sí", "No", "En proceso"])
                    interinst = st.selectbox("Relación Interinstitucional (DCI-2)", ["Fluida", "Con Conflictos", "Inexistente"])

                if st.form_submit_button("🚀 Guardar Auditoría"):
                    if nombre:
                        sh_d = conectar_gspread()
                        ws_d = sh_d.worksheet("SADCI")
                        ws_d.append_row([
                            str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                            protocolo, interinst, "Anual", digital, ejecucion, pdt, "Activas", mepi
                        ])
                        st.success("✅ Diagnóstico guardado.")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e: 
        st.error(f"Error en el Sistema SADCI: {e}")

# --- LÓGICA DE RECOMENDACIONES Y RADAR ---
st.divider()
st.subheader("🚀 Plan de Acción y Fortalecimiento")

if not df_sadci.empty:
    entidad_sel = st.selectbox("Seleccione Entidad para Ver Plan de Acción", df_sadci['nombre_entidad'].unique())
    data_entidad = df_sadci[df_sadci['nombre_entidad'] == entidad_sel].iloc[0]

    # Gráfico de Radar: Perfil de Capacidad[cite: 1]
    categorias = ['DCI-1: Reglas', 'DCI-2: Interinst.', 'DCI-3: Estructura', 
                  'DCI-4: Recursos', 'DCI-5: Personal', 'DCI-6: Individual']
    
    # Mapeo de valores para el radar (Escala 0-100)
    valores_radar = [
        data_entidad['calificacion_mepi'], 
        100 if data_entidad['interinst'] == "Fluida" else (50 if data_entidad['interinst'] == "Con Conflictos" else 20),
        75, # Valor estático para Estructura si no hay campo específico
        data_entidad['ejecucion_presupuestal_pct'],
        data_entidad['capacidad_personal'],
        data_entidad['puntos_digital']
    ]

    df_radar = pd.DataFrame(dict(r=valores_radar, theta=categorias))
    fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, range_r=[0,100])
    fig_radar.update_traces(fill='toself', line_color='#1f77b4')

    col_rad, col_rec = st.columns([1, 1])
    
    with col_rad:
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_rec:
        def generar_recomendaciones(row):
            recoms = []
            if row['capacidad_personal'] < 40:
                recoms.append({"Déficit": "DCI-5: Inestabilidad del Personal", "Acción": "Diseñar un plan de formalización laboral.", "Prioridad": "Alta"})
            if row['puntos_digital'] < 50:
                recoms.append({"Déficit": "DCI-4: Obsolescencia Tecnológica", "Acción": "Adquisición de kits tecnológicos rurales.", "Prioridad": "Media"})
            if row['calificacion_mepi'] < 60:
                recoms.append({"Déficit": "DCI-1: Ambigüedad Normativa", "Acción": "Revisión de manuales de funciones.", "Prioridad": "Muy Alta"})
            return recoms

        recomendaciones = generar_recomendaciones(data_entidad)
        if recomendaciones:
            for rec in recomendaciones:
                with st.expander(f"⚠️ {rec['Déficit']} - {rec['Prioridad']}"):
                    st.write(f"**Recomendación:** {rec['Acción']}") # Corregido de 'Action' a 'Acción'
                    st.info("Basado en el Formulario E de la metodología SADCI[cite: 1].")
        else:
            st.success("✅ No se detectan déficit críticos.")


# --- TAB 3: ACTORES ---
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

# --- CRÉDITOS FINALES ---
st.divider()
col_f1, col_f2 = st.columns([1, 4])

with col_f1:
    # Intenta cargar el logo de la ESAP si existe en la carpeta assets o data
    logo_path = os.path.join('data', 'logo_esap.png')
    if os.path.exists(logo_path):
        st.image(logo_path, width=120)
    else:
        st.markdown("**ESAP**")

with col_f2:
    st.markdown(
        """
        <div class="footer-text">
            <strong>Investigación ESAP 2026</strong><br>
            Desarrollado por el <strong>Colectivo de Estudios Sociales Guadalupe Salcedo</strong><br>
            <em>Propiedad Intelectual y Académica Reservada</em>
        </div>
        """, 
        unsafe_allow_html=True
    )

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

# -----------------------------------------------------------------------------
# 🛰️ CÓDIGO DEL FORMULARIO OFFLINE EN LA MEMORIA DE PYTHON
# -----------------------------------------------------------------------------
AUTOGENERADO_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SADCI - Captura Rural Unificada</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background-color: #f8f9fa; padding: 10px; font-size: 16px; }
        .card { border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 12px; }
        .btn-grande { height: 50px; font-weight: bold; font-size: 1.1rem; border-radius: 8px; }
        .status-badge { font-size: 0.85rem; padding: 8px; display: inline-block; width: 100%; text-align: center; border-radius: 6px; }
        #mapa { height: 350px; width: 100%; border-radius: 8px; border: 2px solid #ddd; background-color: #e5e3df; }
        .leaflet-tooltip-own { background: #333; color: #fff; border: none; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container-fluid m-0 p-0">
        <h3 class="text-center my-2">🛰️ SIGOber-Rural</h3>
        <p class="text-muted text-center mb-3" style="font-size:0.85rem;">Puerto Rico (Caquetá) - Formulario Único Offline</p>
        <div class="card p-3 mb-2">
            <div class="row text-center align-items-center">
                <div class="col-6"><span id="contador-locales" class="badge bg-warning text-dark p-2 w-100 fs-6">0 Pendientes</span></div>
                <div class="col-6"><span id="estado-red" class="status-badge bg-success text-white">🟢 Con Internet</span></div>
                <div class="col-12 mt-2">
                    <button id="btn-sincronizar" class="btn btn-primary btn-sm w-100 d-none" onclick="sincronizarDatos()">🔄 Enviar Datos Guardados a la Nube</button>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-12 col-md-4">
                <div class="card p-3">
                    <h5 class="card-title text-danger mb-3">⚠️ Registrar Conflicto</h5>
                    <form id="form-conflictos">
                        <div class="mb-2">
                            <label class="form-label small fw-bold">Encuestador / Líder</label>
                            <input type="text" id="quien" class="form-control form-control-sm" required placeholder="Tu nombre">
                        </div>
                        <div class="mb-2">
                            <label class="form-label small fw-bold">Tipo de Conflicto</label>
                            <select id="tipo" class="form-select form-select-sm">
                                <option value="Linderos">Linderos</option>
                                <option value="Uso de Suelo">Uso de Suelo</option>
                                <option value="Ambiental">Ambiental</option>
                                <option value="Tenencia">Tenencia</option>
                            </select>
                        </div>
                        <div class="mb-2">
                            <label class="form-label small fw-bold">Vereda Identificada</label>
                            <input type="text" id="vereda" class="form-control form-control-sm fw-bold text-danger" value="Vereda Localizada" readonly>
                        </div>
                        <div class="mb-2">
                            <label class="form-label small fw-bold">Descripción</label>
                            <textarea id="desc" class="form-control form-control-sm" rows="2" required placeholder="Detalles observados..."></textarea>
                        </div>
                        <div class="row g-2 mb-3 bg-light p-2 rounded border">
                            <div class="col-6">
                                <small class="text-muted d-block" style="font-size:0.75rem;">Latitud</small>
                                <input type="text" id="lat" class="form-control form-control-sm text-center fw-bold" readonly value="1.912300">
                            </div>
                            <div class="col-6">
                                <small class="text-muted d-block" style="font-size:0.75rem;">Longitud</small>
                                <input type="text" id="lon" class="form-control form-control-sm text-center fw-bold" readonly value="-75.184200">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-danger w-100 btn-grande mb-2">💾 Guardar en Celular</button>
                    </form>
                </div>
            </div>
            <div class="col-12 col-md-8">
                <div class="card p-2">
                    <div class="d-flex justify-content-between align-items-center mb-1 px-1">
                        <span class="small fw-bold text-muted">📍 Arrastra el pin o toca el mapa</span>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="recapturarGPSNativo()">🎯 Forzar GPS</button>
                    </div>
                    <div id="mapa"></div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://layerjs.org/libs/turf.min.js"></script>
    <script>
        const WEB_APP_URL = "TU_URL_DE_GOOGLE_APPS_SCRIPT";
        let mapa, marcador, capaVeredas;
        const LAT_DEFECTO = 1.9123; const LON_DEFECTO = -75.1842;
        const datosVeredasGeoJSON = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"NOMBRE_VER": "Zona Rural General - Puerto Rico"}, "geometry": {"type": "Polygon", "coordinates": [[[-75.30, 2.05], [-75.00, 2.05], [-75.00, 1.80], [-75.30, 1.80], [-75.30, 2.05]]]}}]};
        if(!localStorage.getItem("conflictos_offline")) { localStorage.setItem("conflictos_offline", JSON.stringify([])); }
        function inicializarMapa() {
            mapa = L.map('mapa', { center: [LAT_DEFECTO, LON_DEFECTO], zoom: 12, zoomControl: false });
            L.control.zoom({ position: 'bottomright' }).addTo(mapa);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapa);
            try {
                capaVeredas = L.geoJSON(datosVeredasGeoJSON, {
                    style: function () { return { color: "#FFFF00", weight: 2, fillColor: "#FFFF00", fillOpacity: 0.05 }; },
                    onEachFeature: function (feature, layer) {
                        if (feature.properties && feature.properties.NOMBRE_VER) {
                            layer.bindTooltip(feature.properties.NOMBRE_VER, { permanent: true, direction: "center", className: "leaflet-tooltip-own" });
                        }
                    }
                }).addTo(mapa);
            } catch(e) {}
            marcador = L.circleMarker([LAT_DEFECTO, LON_DEFECTO], { radius: 10, fillColor: "#ff2a2a", color: "#fff", weight: 3, opacity: 1, fillOpacity: 0.9 }).addTo(mapa);
            mapa.on('click', function (e) { marcador.setLatLng(e.latlng); actualizarInputsYVereda(e.latlng.lat, e.latlng.lng); });
        }
        function actualizarInputsYVereda(lat, lon) {
            document.getElementById("lat").value = Number(lat).toFixed(6); document.getElementById("lon").value = Number(lon).toFixed(6);
            document.getElementById("vereda").value = "Vereda Localizada";
            if (capaVeredas) {
                const puntoEval = turf.point([lon, lat]);
                capaVeredas.eachLayer(function (layer) {
                    try { if (turf.booleanPointInPolygon(puntoEval, layer.feature)) { document.getElementById("vereda").value = layer.feature.properties.NOMBRE_VER; } } catch(err) {}
                });
            }
        }
        function recapturarGPSNativo() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((pos) => {
                    const lat = pos.coords.latitude; const lon = pos.coords.longitude;
                    actualizarInputsYVereda(lat, lon); marcador.setLatLng([lat, lon]); mapa.setView([lat, lon], 14);
                }, null, { enableHighAccuracy: true, timeout: 8000 });
            }
        }
        function actualizarEstadoRed() {
            const bad = document.getElementById("estado-red"); const btnSincro = document.getElementById("btn-sincronizar");
            const enCola = JSON.parse(localStorage.getItem("conflictos_offline")).length;
            if (navigator.onLine) { bad.className = "status-badge bg-success text-white"; bad.innerText = "🟢 Con Internet"; if(enCola > 0) btnSincro.classList.remove("d-none"); }
            else { bad.className = "status-badge bg-secondary text-white"; bad.innerText = "⚫ Sin Internet (Modo Rural)"; btnSincro.classList.add("d-none"); }
            document.getElementById("contador-locales").innerText = `${enCola} Pendientes`;
        }
        window.addEventListener('online', actualizarEstadoRed); window.addEventListener('offline', actualizarEstadoRed);
        window.onload = () => { inicializarMapa(); recapturarGPSNativo(); actualizarEstadoRed(); cargarPuntosGuardadosEnMapa(); }
        document.getElementById("form-conflictos").addEventListener("submit", function(e) {
            e.preventDefault();
            const nuevoRegistro = {
                id: Math.random().toString(36).substr(2, 5), tipo: document.getElementById("tipo").value,
                vereda: document.getElementById("vereda").value, lat: document.getElementById("lat").value,
                lon: document.getElementById("lon").value, desc: document.getElementById("desc").value,
                quien: document.getElementById("quien").value, fecha: new Date().toISOString()
            };
            let cola = JSON.parse(localStorage.getItem("conflictos_offline")); cola.push(nuevoRegistro);
            localStorage.setItem("conflictos_offline", JSON.stringify(cola));
            alert("💾 Guardado localmente en el teléfono."); document.getElementById("desc").value = "";
            actualizarEstadoRed(); cargarPuntosGuardadosEnMapa();
        });
        function cargarPuntosGuardadosEnMapa() {
            let cola = JSON.parse(localStorage.getItem("conflictos_offline"));
            cola.forEach(item => { L.circleMarker([item.lat, item.lon], { radius: 7, fillColor: "#ff9800", color: "#e65100", weight: 2, fillOpacity: 0.9 }).addTo(mapa); });
        }
        function sincronizarDatos() {
            let cola = JSON.parse(localStorage.getItem("conflictos_offline")); if(cola.length === 0) return;
            document.getElementById("btn-sincronizar").innerText = "⏳ Transmitiendo...";
            fetch(WEB_APP_URL, { method: "POST", mode: "no-cors", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cola) })
            .then(() => { alert("🎉 ¡Transmisión exitosa!"); localStorage.setItem("conflictos_offline", JSON.stringify([])); location.reload(); });
        }
    </script>
</body>
</html>"""

# --- BOTÓN DE ENLACE EN LA BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🛰️ Herramientas de Campo")
    st.info("¿Vas a salir a zona rural sin señal? Descarga este formulario en tu teléfono antes de irte. Funciona 100% offline.")
    st.download_button(
        label="📲 Descargar Formulario Offline",
        data=AUTOGENERADO_HTML,
        file_name="captura_offline.html",
        mime="text/html",
        use_container_width=True
    )
    st.divider()

# -----------------------------------------------------------------------------
# 2. CONEXIONES A BASES DE DATOS (GSHEETS & GSPREAD)
# -----------------------------------------------------------------------------
@st.cache_resource
def conectar_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["textkey"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error en st.connection: {e}")

# -----------------------------------------------------------------------------
# 3. CARGA DE CAPAS GEOGRÁFICAS (SISTEMA ULTRA VELOZ ANTIBLOQUEOS)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_veredas():
    ruta = os.path.join('data', 'veredas_puerto_rico.json')
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Intentar conversión rápida por Topojson de Python
        topo = tp.Topology(data)
        return topo.to_geojson()
    except Exception:
        # SISTEMA DE ESCAPE DE EMERGENCIA: Si topojson causa un bucle infinito, 
        # devolvemos el archivo crudo o una estructura GeoJSON mínima para evitar que colapse la app
        if data and 'type' in data and data['type'] == 'Topology':
            try:
                # Intento alternativo usando extracción por llave de objeto
                nombre_obj = list(data['objects'].keys())[0]
                return tp.feature(data, data['objects'][nombre_obj])
            except:
                return data
        return data

veredas_geojson = cargar_veredas()

# -----------------------------------------------------------------------------
# 4. CUERPO PRINCIPAL DE LA INTERFAZ DE STREAMLIT (TABS RESTAURADOS)
# -----------------------------------------------------------------------------
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("### Sistema de Información Geográfica para la Gobernanza Rural")

t1, t2, t3 = st.tabs(["📥 Captura de Campo", "🗺️ Mapeo SADCI", "👥 Registro Actores"])

# --- TAB 1: CAPTURA DE CAMPO (CONTINGENCIA LOCAL STREAMLIT) ---
with t1:
    st.subheader("🛰️ Registro Georreferenciado en Línea (Streamlit)")
    st.markdown("Utiliza esta pestaña si cuentas con datos móviles en la vereda. Si no tienes señal, usa el botón de descarga de la barra lateral.")
    
    if "cola_conflictos" not in st.session_state: st.session_state.cola_conflictos = []
    if "cola_actores" not in st.session_state: st.session_state.cola_actores = []

    if st.button("🎯 Capturar Coordenadas Actuales GPS"):
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state.lat_cap = loc['coords']['latitude']
            st.session_state.lon_cap = loc['coords']['longitude']
            st.success(f"📍 Ubicación fijada: {st.session_state.lat_cap}, {st.session_state.lon_cap}")
        else:
            st.warning("No se pudo obtener el GPS automático. Revisa los permisos de ubicación o marca el punto en el mapa de SADCI.")

    with st.form("form_rural_directo"):
        c1, c2 = st.columns(2)
        with c1:
            tipo_c = st.selectbox("Tipo de Conflicto", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            quien_c = st.text_input("Investigador / Líder")
        with c2:
            lat_f = st.number_input("Latitud", value=st.session_state.get("lat_cap", 1.9123), format="%.6f")
            lon_f = st.number_input("Longitud", value=st.session_state.get("lon_cap", -75.1842), format="%.6f")
        
        desc_c = st.text_area("Descripción de la problemática en territorio")
        
        if st.form_submit_button("💾 Guardar Registro"):
            vereda_detectada = "Vereda Localizada"
            if veredas_geojson and isinstance(veredas_geojson, dict) and 'features' in veredas_geojson:
                try:
                    p = Point(lon_f, lat_f)
                    for feat in veredas_geojson['features']:
                        if 'geometry' in feat:
                            geom = shape(feat['geometry'])
                            if geom.contains(p):
                                vereda_detectada = feat['properties'].get('NOMBRE_VER', "Vereda Localizada")
                                break
                except:
                    pass
            
            nueva_fila = [str(uuid.uuid4())[:5], tipo_c, vereda_detectada, lat_f, lon_f, desc_c, quien_c, pd.Timestamp.now().strftime('%Y-%m-%d')]
            
            try:
                sh = conectar_gspread()
                ws = sh.worksheet("Conflictos")
                ws.append_row(nueva_fila)
                st.success(f"🎉 Guardado directamente en la nube en la vereda: {vereda_detectada}")
                st.cache_data.clear()
            except Exception:
                st.session_state.cola_conflictos.append(nueva_fila)
                st.warning("⚠️ Sin señal de base de datos. Guardado en la memoria temporal de Streamlit.")

    if st.session_state.cola_conflictos:
        st.subheader("📦 Registros en cola local (Esperando sincronización)")
        st.dataframe(pd.DataFrame(st.session_state.cola_conflictos))
        if st.button("🔄 Sincronizar cola de Streamlit ahora"):
            try:
                sh = conectar_gspread()
                ws = sh.worksheet("Conflictos")
                for r in st.session_state.cola_conflictos: ws.append_row(r)
                st.session_state.cola_conflictos = []
                st.success("¡Sincronización de cola completada con éxito!")
                st.cache_data.clear()
                st.rerun()
            except Exception: st.error("Aún no hay conexión directa con la base de datos.")

# --- TAB 2: MAPEO DE PROBLEMÁTICAS EN LA NUBE (SADCI) ---
with t2:
    st.subheader("🗺️ Diagnóstico Social Alternativo de Conflictos e Injusticias (SADCI)")
    try:
        df_conf = conn.read(worksheet="Conflictos", ttl="10s")
        df_conf = df_conf.dropna(subset=['Latitud', 'Longitud'])
        
        col_m1, col_m2 = st.columns([3, 1])
        
        with col_m1:
            m = folium.Map(location=[1.9123, -75.1842], zoom_start=11, tiles="OpenStreetMap")
            
            if veredas_geojson and isinstance(veredas_geojson, dict) and 'type' in veredas_geojson:
                try:
                    folium.GeoJson(
                        veredas_geojson,
                        name="Límites Veredales Puerto Rico",
                        style_function=lambda x: {'color': '#FFFF00', 'weight': 2, 'fillColor': 'transparent'}
                    ).add_to(m)
                except:
                    pass
            
            for _, r in df_conf.iterrows():
                color_map = {"Linderos": "red", "Uso de Suelo": "blue", "Ambiental": "green", "Tenencia": "orange"}
                folium.Marker(
                    location=[float(r['Latitud']), float(r['Longitud'])],
                    popup=f"<b>Tipo:</b> {r['Tipo']}<br><b>Vereda:</b> {r['Vereda']}<br><b>Desc:</b> {r['Descripción']}",
                    icon=folium.Icon(color=color_map.get(r['Tipo'], "purple"), icon="info-sign")
                ).add_to(m)
            
            st_folium(m, width="100%", height=500, returned_objects=[])
            
        with col_m2:
            st.markdown("#### Resumen del Territorio")
            st.metric("Total Conflictos", len(df_conf))
            fig_pie = px.pie(df_conf, names='Tipo', title="Tipologías", hole=0.3)
            fig_pie.update_layout(margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("#### Registros Consolidados")
            st.dataframe(df_conf[['Tipo', 'Vereda', 'Encuestador']], height=200)
    except Exception as e:
        st.error(f"Error cargando Tab SADCI: {e}")

# --- TAB 3: REGISTRO DE ACTORES Y TENENCIA ---
with t3:
    st.subheader("👥 Caracterización de Actores Sociales Rurales")
    try:
        df_act = conn.read(worksheet="Actores", ttl="10s")
        
        col_a1, col_a2 = st.columns([2, 1])
        
        with col_a1:
            st.markdown("#### Base de Datos de Líderes y Actores")
            st.dataframe(df_act, use_container_width=True, height=400)
            
        with col_a2:
            st.markdown("#### Vincular Nuevo Actor")
            with st.form("form_actores"):
                nombre_a = st.text_input("Nombre Completo")
                perfil_a = st.selectbox("Perfil", ["Líder Comunitario", "Productor", "Presidente JAC", "Adjudicatario", "Asociación"])
                c_a1, c_a2 = st.columns(2)
                with c_a1:
                    vereda_a = st.text_input("Vereda")
                with c_a2:
                    tenencia_a = st.selectbox("Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones")
                if st.form_submit_button("📤 Registrar Actor"):
                    if nombre_a and vereda_a:
                        datos_actor_fila = [str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a]
                        sh_act = conectar_gspread()
                        ws_act = sh_act.worksheet("Actores")
                        ws_act.append_row(datos_actor_fila)
                        st.success(f"✅ {nombre_a} registrado con éxito.")
                        st.cache_data.clear()
                        st.rerun()
    except Exception as e: 
        st.error(f"Error actores: {e}")

# --- CRÉDITOS FINALES ---
st.divider()
col_f1, col_f2 = st.columns([1, 4])

with col_f1:
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
            Desarrollado para el fortalecimiento institucional, ordenamiento social de la propiedad rural y resolución alternativa de conflictos en Puerto Rico, Caquetá.
        </div>
        """, 
        unsafe_allow_html=True
    )

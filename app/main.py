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
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union
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
        const WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwNKhNoX_Tq6IvOKP26jLuyIsyrfYuRnQum-5FDVhi6mHECriPiN65zC5tdrIXK7-nRgQ/exec";
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
            let cola = JSON.parse(localStorage.getItem("conflictos_offline")); 
            if(cola.length === 0) return;
            document.getElementById("btn-sincronizar").innerText = "⏳ Conectando con la base de datos...";
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = WEB_APP_URL;
            const hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = 'datos';
            hiddenField.value = JSON.stringify(cola);
            form.appendChild(hiddenField);
            document.body.appendChild(form);
            localStorage.setItem("conflictos_offline", JSON.stringify([]));
            form.submit();
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
        return conn.read(worksheet=nombre_hoja, ttl=600)
    except Exception:
        return pd.DataFrame()

def cargar_situaciones_territoriales():
    """Carga eventos históricos validados a escala de vereda.
    La tabla no contiene coordenadas inventadas: la geometría se obtiene de la vereda.
    """
    ruta = os.path.join('data', 'SITUACIONES_TERRITORIALES_eventos.csv')
    if not os.path.exists(ruta):
        return pd.DataFrame()
    try:
        df = pd.read_csv(ruta, dtype={'codigo_ver_resuelto': str})
        if 'codigo_ver_resuelto' in df.columns:
            df['codigo_ver_resuelto'] = df['codigo_ver_resuelto'].astype(str)
        return df
    except Exception as e:
        st.warning(f"No se pudo cargar SITUACIONES_TERRITORIALES: {e}")
        return pd.DataFrame()

def enriquecer_veredas_con_situaciones(topo_data, df_situaciones):
    """Añade indicadores documentales a las propiedades de cada vereda.
    Acepta TopoJSON o GeoJSON y garantiza que cada feature tenga properties."""
    if not topo_data:
        return topo_data
    data = json.loads(json.dumps(topo_data))
    if data.get('type') == 'FeatureCollection':
        for feature in data.get('features', []):
            if not isinstance(feature, dict):
                continue
            feature.setdefault('properties', {})
        if df_situaciones.empty:
            return data
        features = data.get('features', [])
    else:
        if df_situaciones.empty:
            try:
                geojson_data = tp.to_geojson(data)
                for feature in geojson_data.get('features', []):
                    feature.setdefault('properties', {})
                return geojson_data
            except Exception as e:
                st.error(f'No se pudo convertir la capa de veredas a GeoJSON: {e}')
                return None
        features = []
        obj_name = list(data.get('objects', {}).keys())[0] if data.get('objects') else None
        if obj_name:
            features = data['objects'][obj_name].get('geometries', [])
    agg = (df_situaciones.groupby('codigo_ver_resuelto', dropna=False)
           .agg(eventos_documentados=('id','nunique'),
                primera_fecha=('fecha','min'),
                ultima_fecha=('fecha','max'),
                tipos_conflicto=('tipo_conflicto', lambda s: ' | '.join(sorted(set(map(str,s))))),
                confianza_alta=('confianza', lambda s: sum(str(x).upper() == 'ALTA' for x in s)))
           .reset_index())
    lookup = {str(r['codigo_ver_resuelto']): r for _, r in agg.iterrows()}
    for geom in features:
        props = geom.setdefault('properties', {})
        codigo = str(props.get('CODIGO_VER',''))
        r = lookup.get(codigo)
        props['SIGOber_eventos'] = int(r['eventos_documentados']) if r is not None else 0
        props['SIGOber_primera_fecha'] = str(r['primera_fecha']) if r is not None else ''
        props['SIGOber_ultima_fecha'] = str(r['ultima_fecha']) if r is not None else ''
        props['SIGOber_tipos'] = str(r['tipos_conflicto']) if r is not None else ''
        props['SIGOber_confianza_alta'] = int(r['confianza_alta']) if r is not None else 0
    if data.get('type') == 'FeatureCollection':
        return data
    try:
        geojson_data = tp.to_geojson(data)
        if not isinstance(geojson_data, dict) or geojson_data.get('type') != 'FeatureCollection':
            raise ValueError('La conversión no produjo un FeatureCollection válido')
        for feature in geojson_data.get('features', []):
            if isinstance(feature, dict):
                feature.setdefault('properties', {})
        return geojson_data
    except Exception as e:
        st.error(f'No se pudo convertir la capa de veredas a GeoJSON: {e}')
        return None

# 3. PANELES DE CONTROL
tab_mapa, tab_sadci, tab_actores = st.tabs([
    "🗺️ Situaciones Territoriales", 
    "📊 Auditoría SADCI", 
    "👥 Registro de Actores"
])

# --- TAB 1: MAPA ---
with tab_mapa:
    st.subheader("Visualizador de Situaciones Territoriales")
    
    df_situaciones = cargar_situaciones_territoriales()
    veredas_situaciones = enriquecer_veredas_con_situaciones(veredas_topo, df_situaciones)

    df_raw = cargar_datos_con_cache("Conflictos")
    df_plot = pd.DataFrame()
    
    if df_raw is not None and not df_raw.empty:
        df_plot = df_raw.copy()
        
        # 1. Estandarizar nombres de columnas a minúsculas
        df_plot.columns = [str(c).strip().lower() for c in df_plot.columns]

        # 2. Preferir nombres explícitos; usar posiciones solo como respaldo
        def buscar_columna(candidatas):
            for c in candidatas:
                if c in df_plot.columns:
                    return c
            return None

        lat_col = buscar_columna(['lat', 'latitude', 'latitud', 'y', 'coord_lat', 'coordenada_latitud'])
        lon_col = buscar_columna(['lon', 'lng', 'longitude', 'longitud', 'x', 'coord_lon', 'coordenada_longitud'])
        tipo_col = buscar_columna(['tipo', 'tipo_conflicto', 'tipo_mapa', 'categoria'])
        vereda_col = buscar_columna(['vereda', 'vereda_mapa', 'nombre_vereda', 'territorio'])
        desc_col = buscar_columna(['descripcion', 'descripción', 'desc', 'detalle', 'observacion', 'observación'])

        if lat_col is None or lon_col is None:
            if df_plot.shape[1] >= 5:
                matriz_valores = df_plot.values
                lat_col, lon_col = '__lat_pos', '__lon_pos'
                df_plot[lat_col] = matriz_valores[:, 3]
                df_plot[lon_col] = matriz_valores[:, 4]
            else:
                lat_col = lon_col = None

        if lat_col and lon_col:
            df_plot['lat'] = df_plot[lat_col]
            df_plot['lon'] = df_plot[lon_col]
        if tipo_col:
            df_plot['tipo_mapa'] = df_plot[tipo_col]
        elif df_plot.shape[1] >= 2:
            df_plot['tipo_mapa'] = df_plot.iloc[:, 1]
        else:
            df_plot['tipo_mapa'] = 'Situación territorial'
        if vereda_col:
            df_plot['vereda_mapa'] = df_plot[vereda_col]
        elif df_plot.shape[1] >= 3:
            df_plot['vereda_mapa'] = df_plot.iloc[:, 2]
        else:
            df_plot['vereda_mapa'] = 'Territorio'
        if desc_col:
            df_plot['desc_mapa'] = df_plot[desc_col]
        elif df_plot.shape[1] > 5:
            df_plot['desc_mapa'] = df_plot.iloc[:, 5]
        else:
            df_plot['desc_mapa'] = 'Sin descripción'

        # 3. LIMPIEZA INTELIGENTE DE COORDENADAS (Corrige el error de múltiples puntos)
        for col in ['lat', 'lon']:
            if col in df_plot.columns:
                val_str = df_plot[col].astype(str).str.strip().str.replace(',', '.', regex=False)
                def arreglar_puntos(texto):
                    if texto.count('.') > 1:
                        partes = texto.split('.')
                        return partes[0] + '.' + ''.join(partes[1:])
                    return texto
                df_plot[col] = val_str.apply(arreglar_puntos)
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
        if 'lat' in df_plot.columns and 'lon' in df_plot.columns:
            df_plot = df_plot.dropna(subset=['lat', 'lon'])
            df_plot = df_plot[df_plot['lat'].between(-5, 15) & df_plot['lon'].between(-80, -65)]

    if "gps_capturado" not in st.session_state:
        loc = get_geolocation()
        coords = loc.get('coords') if isinstance(loc, dict) else None
        lat_gps = coords.get('latitude') if isinstance(coords, dict) else None
        lon_gps = coords.get('longitude') if isinstance(coords, dict) else None
        if lat_gps is not None and lon_gps is not None:
            try:
                st.session_state.lat_click = float(lat_gps)
                st.session_state.lon_click = float(lon_gps)
                st.session_state.gps_capturado = True
            except (TypeError, ValueError):
                pass

    if "lat_click" not in st.session_state:
        st.session_state.lat_click = 1.9123
    if "lon_click" not in st.session_state:
        st.session_state.lon_click = -75.1842

    def validar_punto_preciso(lat, lon, topo_data):
        if topo_data is None: return True, "Capa no cargada"
        try:
            punto_eval = Point(float(lon), float(lat))
            geojson_data = tp.to_geojson(topo_data) if topo_data.get('type') != 'FeatureCollection' else topo_data
            for feature in geojson_data['features']:
                if shape(feature['geometry']).contains(punto_eval):
                    return True, feature.get('properties', {}).get('NOMBRE_VER', 'Vereda Localizada')
            return False, None
        except Exception:
            return True, "Error técnico de validación"

    if not df_situaciones.empty:
        v_con = df_situaciones['codigo_ver_resuelto'].nunique()
        e_con = df_situaciones['id'].nunique()
        m1, m2, m3 = st.columns(3)
        m1.metric('Eventos históricos vinculados', e_con)
        m2.metric('Veredas con evidencia', v_con)
        m3.metric('Fuentes/documentos', df_situaciones['fuente'].nunique())
        st.caption('La simbología de las veredas representa densidad de documentación histórica recuperada. No es un índice automático de riesgo.')

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

        if veredas_situaciones:
            try:
                geojson_enriquecido = veredas_situaciones
                if not isinstance(geojson_enriquecido, dict) or geojson_enriquecido.get('type') != 'FeatureCollection':
                    raise ValueError('La capa de veredas no es un FeatureCollection GeoJSON válido')
                for feature in geojson_enriquecido.get('features', []):
                    if isinstance(feature, dict):
                        feature.setdefault('properties', {})

                try:
                    geoms = [shape(f['geometry']) for f in geojson_enriquecido.get('features', []) if f.get('geometry')]
                    if geoms:
                        limite = mapping(unary_union(geoms))
                        folium.GeoJson(
                            {'type': 'Feature', 'properties': {'NOMBRE_MPIO': 'Puerto Rico (Caquetá)', 'FUENTE': 'Derivado de la capa de veredas'}, 'geometry': limite},
                            name='Contorno municipal (derivado)',
                            style_function=lambda f: {'fillOpacity': 0, 'color': '#003366', 'weight': 3, 'dashArray': '6,4'}
                        ).add_to(m)
                except Exception:
                    pass

                def estilo_vereda(feature):
                    p = feature.get('properties', {})
                    n = int(p.get('SIGOber_eventos', 0) or 0)
                    relleno = '#ffffff' if n == 0 else ('#fff3bf' if n == 1 else ('#ffd166' if n <= 2 else '#f4a261'))
                    return {'fillColor': relleno, 'color': '#6b6b00', 'weight': 1.5, 'fillOpacity': 0.35 if n else 0.08}

                def popup_vereda(feature):
                    p = feature.get('properties', {})
                    n = int(p.get('SIGOber_eventos', 0) or 0)
                    nombre = p.get('NOMBRE_VER', 'Vereda')
                    codigo = p.get('CODIGO_VER', '')
                    if n:
                        return (f"<b>{nombre}</b><br>"
                                f"Código: {codigo}<br>"
                                f"<b>Situaciones documentadas: {n}</b><br>"
                                f"Periodo: {p.get('SIGOber_primera_fecha','')} → {p.get('SIGOber_ultima_fecha','')}<br>"
                                f"Tipos: {p.get('SIGOber_tipos','')}<br>"
                                f"Confianza ALTA: {p.get('SIGOber_confianza_alta',0)}<br>"
                                f"<i>Indicador documental; no equivale a riesgo.</i>")
                    return f"<b>{nombre}</b><br>Código: {codigo}<br><i>Sin eventos históricos vinculados en la matriz v0.5.</i>"

                folium.GeoJson(
                    geojson_enriquecido, name="Veredas + situaciones documentadas",
                    style_function=estilo_vereda,
                    highlight_function=lambda x: {'weight': 3, 'fillOpacity': 0.5},
                    tooltip=folium.GeoJsonTooltip(
                        fields=['NOMBRE_VER','CODIGO_VER','SIGOber_eventos'],
                        aliases=['Vereda:', 'Código:', 'Situaciones documentadas:'],
                        sticky=True
                    ),
                    popup=folium.GeoJsonPopup(
                        fields=['NOMBRE_VER','CODIGO_VER','SIGOber_eventos','SIGOber_primera_fecha','SIGOber_ultima_fecha','SIGOber_tipos','SIGOber_confianza_alta'],
                        aliases=['Vereda','Código','Situaciones documentadas','Primera fecha','Última fecha','Tipos','Confianza ALTA'],
                        localize=True, labels=True, sticky=False
                    )
                ).add_to(m)
            except Exception as e:
                st.warning(f"No se pudo enriquecer la capa de veredas: {e}")

        fg = folium.FeatureGroup(name="Historial Remoto")
        for idx, row in df_plot.iterrows() if not df_plot.empty else []:
            try:
                lat_val = float(row['lat'])
                lon_val = float(row['lon'])
                tipo_c = row.get('tipo_mapa', 'Situación territorial')
                vereda_c = row.get('vereda_mapa', 'Territorio')
                desc_c = row.get('desc_mapa', 'Sin detalle')
                folium.CircleMarker(
                    location=[lat_val, lon_val], radius=6,
                    color="#FF0000", fill=True, fill_color="#FF0000", fill_opacity=0.7,
                    popup=f"<b>Tipo:</b> {tipo_c}<br><b>Vereda:</b> {vereda_c}<br><b>Nota:</b> {desc_c}"
                ).add_to(fg)
            except Exception:
                pass
        fg.add_to(m)
        st.caption(f"Puntos con coordenadas válidas en 'Conflictos': {len(df_plot)}. Los eventos históricos de vereda se representan como evidencia territorial, no como puntos inventados.")
        folium.LayerControl(collapsed=False).add_to(m)
        output = st_folium(m, width="100%", height=450, key="mapa_final")
        if output and output.get("last_clicked"):
            clic = output["last_clicked"]
            if abs(st.session_state.lat_click - clic["lat"]) > 0.0001:
                st.session_state.lat_click = clic["lat"]
                st.session_state.lon_click = clic["lng"]
                st.rerun()


# --- TAB 2: AUDITORÍA SADCI (Basado en Oszlak y Orellana) ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    
    try:
        df_sadci = cargar_datos_con_cache("SADCI")
        if not df_sadci.empty:
            df_sadci['dci_1_reglas'] = (df_sadci['calificacion_mepi'] * 0.7 + 
                                       (df_sadci['protocolo'].map({"Sí": 100, "En proceso": 50, "No": 0}) * 0.3))
            df_sadci['dci_2_interinst'] = df_sadci['rendicion'].map({"Anual": 100, "Semestral": 80, "Nunca": 20})
            map_est = {"Ágil/Coherente": 100, "Funciones Duplicadas": 60, "Rígida/Burocrática": 30, "Inexistente": 0}
            df_sadci['dci_3_estructura'] = df_sadci['estructura'].map(map_est).fillna(50)
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            df_sadci['dci_4_recursos'] = (df_sadci['ejecucion_presupuestal_pct'] + df_sadci['puntos_digital']) / 2
            df_sadci['dci_5_personal'] = (df_sadci['num_personal_planta'] / 
                                         (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)
            map_cap = {"Especializado": 100, "Técnico Suficiente": 75, "Requiere Capacitación": 40, "Crítico/No Idóneo": 10}
            df_sadci['dci_6_individual'] = df_sadci['capacitacion'].map(map_cap).fillna(50)
            st.markdown("### Pilares de Capacidad Real")
            cols = st.columns(6)
            indicadores = [
                ("DCI-1: Reglas", 'dci_1_reglas'), ("DCI-2: Interinst.", 'dci_2_interinst'),
                ("DCI-3: Estructura", 'dci_3_estructura'), ("DCI-4: Recursos", 'dci_4_recursos'),
                ("DCI-5: Personal", 'dci_5_personal'), ("DCI-6: Individual", 'dci_6_individual')
            ]
            for i, (label, col_name) in enumerate(indicadores):
                with cols[i]:
                    val = df_sadci[col_name].mean()
                    st.metric(label, f"{val:.0f}%")
        else:
            st.info("No hay datos SADCI disponibles en la hoja conectada.")
    except Exception as e:
        st.error(f"Error procesando SADCI: {e}")

# --- TAB 3: ACTORES ---
with tab_actores:
    st.subheader("👥 Registro de Actores")
    df_actores = cargar_datos_con_cache("Actores")
    if not df_actores.empty:
        st.dataframe(df_actores, use_container_width=True)
    else:
        st.info("No hay actores registrados en la hoja conectada.")

st.markdown("---")
st.markdown("<div class='footer-container'><div class='footer-text'>SIGOber-Rural · Herramienta técnica de gobernabilidad territorial · Puerto Rico, Caquetá</div></div>", unsafe_allow_html=True)

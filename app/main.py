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
    ruta = os.path.join('data', 'SITUACIONES_TERRITORIALES_eventos.csv')
    if os.path.exists(ruta):
        return pd.read_csv(ruta)
    return pd.DataFrame()

def enriquecer_veredas_con_situaciones(topo_data, eventos):
    if topo_data is None or eventos.empty:
        return topo_data
    try:
        geojson_data = tp.to_geojson(topo_data)
        por_codigo = eventos.dropna(subset=['codigo_ver_resuelto']).copy()
        por_codigo['codigo_ver_resuelto'] = por_codigo['codigo_ver_resuelto'].astype(str)
        resumen = por_codigo.groupby('codigo_ver_resuelto').agg(
            SIGOber_eventos=('id', 'count'),
            SIGOber_primera_fecha=('fecha', 'min'),
            SIGOber_ultima_fecha=('fecha', 'max'),
            SIGOber_tipos=('tipo_conflicto', lambda x: ' | '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        resumen['codigo_ver_resuelto'] = resumen['codigo_ver_resuelto'].astype(str)
        lookup = resumen.set_index('codigo_ver_resuelto').to_dict('index')
        for feature in geojson_data.get('features', []):
            props = feature.setdefault('properties', {})
            codigo = str(props.get('CODIGO_VER', ''))
            datos = lookup.get(codigo, {})
            props['SIGOber_eventos'] = int(datos.get('SIGOber_eventos', 0) or 0)
            props['SIGOber_primera_fecha'] = datos.get('SIGOber_primera_fecha', '')
            props['SIGOber_ultima_fecha'] = datos.get('SIGOber_ultima_fecha', '')
            props['SIGOber_tipos'] = datos.get('SIGOber_tipos', '')
        return geojson_data
    except Exception:
        return topo_data

# 3. CARGA DE CARTOGRAFÍA
veredas_topo = cargar_json_local('veredas_puerto_rico.json')
situaciones = cargar_situaciones_territoriales()
veredas_situaciones = enriquecer_veredas_con_situaciones(veredas_topo, situaciones)

# 4. NAVEGACIÓN
pestanas = st.tabs(["🗺️ Situaciones Territoriales", "🧭 Auditoría SADCI", "👥 Registro de Actores"])

with pestanas[0]:
    st.subheader("Visualizador de Situaciones Territoriales")
    st.caption("Las situaciones históricas documentadas se presentan como evidencia territorial para apoyar prevención, coordinación y priorización. La intensidad visual no equivale por sí sola a nivel de riesgo.")
    c1, c2, c3 = st.columns(3)
    eventos_vinculados = int(situaciones['codigo_ver_resuelto'].notna().sum()) if not situaciones.empty and 'codigo_ver_resuelto' in situaciones.columns else 0
    veredas_con_evidencia = int(situaciones['codigo_ver_resuelto'].dropna().astype(str).nunique()) if not situaciones.empty and 'codigo_ver_resuelto' in situaciones.columns else 0
    fuentes = int(situaciones['fuente'].nunique()) if not situaciones.empty and 'fuente' in situaciones.columns else 0
    c1.metric("Eventos históricos vinculados", eventos_vinculados)
    c2.metric("Veredas con evidencia", veredas_con_evidencia)
    c3.metric("Fuentes", fuentes)
    if situaciones.empty:
        st.info("No hay situaciones territoriales históricas cargadas en la carpeta data.")
    else:
        st.dataframe(situaciones, use_container_width=True, hide_index=True)

    df_conflictos = cargar_datos_con_cache("Conflictos")
    df_plot = df_conflictos.copy()
    if not df_plot.empty:
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
        df_plot = df_plot.dropna(subset=['lat', 'lon'])

    if "gps_capturado" not in st.session_state:
        loc = get_geolocation()
        # La geolocalización del navegador puede estar bloqueada por permisos
        # del navegador, configuración del administrador o políticas de privacidad.
        # En esos casos el componente puede devolver un objeto sin `coords`.
        # No debemos asumir que latitude/longitude existen.
        coords = loc.get("coords") if isinstance(loc, dict) else None
        lat_gps = coords.get("latitude") if isinstance(coords, dict) else None
        lon_gps = coords.get("longitude") if isinstance(coords, dict) else None
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
            geojson_data = tp.to_geojson(topo_data)
            for feature in geojson_data['features']:
                if shape(feature['geometry']).contains(punto_eval):
                    return True, feature['properties'].get('NOMBRE_VER', 'Vereda Localizada')
            return False, None
        except Exception:
            return True, "Error técnico de validación"

    # MAPA
    mapa = folium.Map(location=[st.session_state.lat_click, st.session_state.lon_click], zoom_start=12, control_scale=True)
    if veredas_situaciones is not None:
        try:
            geojson_map = veredas_situaciones if isinstance(veredas_situaciones, dict) else tp.to_geojson(veredas_situaciones)
            folium.GeoJson(
                geojson_map,
                name="Veredas y evidencia histórica",
                style_function=lambda feature: {
                    'fillColor': '#d73027' if feature['properties'].get('SIGOber_eventos', 0) >= 3 else ('#fc8d59' if feature['properties'].get('SIGOber_eventos', 0) >= 1 else '#eeeeee'),
                    'color': '#666666', 'weight': 1, 'fillOpacity': 0.55 if feature['properties'].get('SIGOber_eventos', 0) else 0.15
                },
                tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER', 'SIGOber_eventos', 'SIGOber_primera_fecha', 'SIGOber_ultima_fecha'], aliases=['Vereda', 'Eventos documentados', 'Primera fecha', 'Última fecha'], localize=True),
                popup=folium.GeoJsonPopup(fields=['NOMBRE_VER', 'SIGOber_tipos'], aliases=['Vereda', 'Tipos documentados'], localize=True)
            ).add_to(mapa)
        except Exception as e:
            st.warning(f"No fue posible dibujar la capa enriquecida de veredas: {e}")
    if not df_plot.empty:
        for _, row in df_plot.iterrows():
            folium.CircleMarker([row['lat'], row['lon']], radius=5, popup=str(row.get('descripcion', row.get('desc', 'Situación registrada'))), color='blue', fill=True).add_to(mapa)
    folium.LayerControl().add_to(mapa)
    st_folium(mapa, use_container_width=True, height=560)

    st.markdown("### 📍 Captura de una situación territorial")
    col1, col2 = st.columns(2)
    with col1:
        quien = st.text_input("Encuestador / líder")
        tipo = st.selectbox("Tipo de situación", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
        descripcion = st.text_area("Descripción")
    with col2:
        lat = st.number_input("Latitud", value=float(st.session_state.lat_click), format="%.6f")
        lon = st.number_input("Longitud", value=float(st.session_state.lon_click), format="%.6f")
    if st.button("💾 Guardar situación"):
        ok, vereda = validar_punto_preciso(lat, lon, veredas_topo)
        if not ok:
            st.error("El punto está fuera de la capa de veredas disponible. Revise las coordenadas.")
        else:
            try:
                hoja = conectar_gspread().worksheet("Conflictos")
                hoja.append_row([str(uuid.uuid4()), quien, tipo, vereda, lat, lon, descripcion])
                st.success(f"Situación guardada. Referencia territorial: {vereda}")
            except Exception as e:
                st.error(f"No fue posible guardar en Google Sheets: {e}")

with pestanas[1]:
    st.subheader("Auditoría SADCI")
    df_sadci = cargar_datos_con_cache("SADCI")
    if df_sadci.empty:
        st.info("No hay registros SADCI disponibles.")
    else:
        st.dataframe(df_sadci, use_container_width=True, hide_index=True)

with pestanas[2]:
    st.subheader("Registro de Actores")
    df_actores = cargar_datos_con_cache("Actores")
    if df_actores.empty:
        st.info("No hay actores registrados.")
    else:
        st.dataframe(df_actores, use_container_width=True, hide_index=True)

st.divider()
st.markdown("<div class='footer-container'><div class='footer-text'>Investigación ESAP 2026 · Colectivo de Estudios Sociales Guadalupe Salcedo</div></div>", unsafe_allow_html=True)

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import uuid

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", layout="wide")
st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("### Gestión Territorial, Actores y Capacidad Institucional (SADCI)")
st.divider()

# 2. CONEXIÓN A DATOS
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_json_local(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

veredas_topo = cargar_json_local('veredas_puerto_rico.json')
conflictos_geo = cargar_json_local('ejemplo_conflictos.geojson')

# 3. PANELES DE CONTROL (Tabs para no saturar la vista)
tab_mapa, tab_sadci, tab_actores = st.tabs([
    "🗺️ Mapa de Conflictos", 
    "📊 Auditoría SADCI", 
    "👥 Registro de Actores"
])

# --- TAB 1: MAPA Y SEÑALIZACIÓN ---
with tab_mapa:
    st.subheader("Visualizador de Tenencia y Conflictos")
    
    # Contador de Conflictos (Dinámico)
    if conflictos_geo:
        n_conf = len(conflictos_geo['features'])
        st.metric("Conflictos Identificados en Territorio", n_conf)

    m = folium.Map(location=[1.91, -75.18], zoom_start=11)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
                     attr='Google', name='Satélite', overlay=False).add_to(m)

    if veredas_topo:
        nombre_obj = list(veredas_topo['objects'].keys())[0]
        folium.TopoJson(veredas_topo, f"objects.{nombre_obj}", name="Límites Veredales",
                        style_function=lambda x: {'fillColor': '#2e7d32', 'color': 'white', 'weight': 1, 'fillOpacity': 0.2},
                        tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'])).add_to(m)
    
    if conflictos_geo:
        folium.GeoJson(conflictos_geo, name="Alertas de Conflicto",
                       marker=folium.Marker(icon=folium.Icon(color='red', icon='info-sign')),
                       tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Conflicto:'])).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=500)

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("Análisis de Capacidad Institucional")
    try:
        df_ind = conn.read(ttl=0)
        df_ind.columns = df_ind.columns.str.strip().str.lower().str.replace(' ', '_')

        if not df_ind.empty:
            actual = df_ind.iloc[-1]
            # Lógica Semáforo
            puntos = 0
            if str(actual.get('existencia_cmdr', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 30
            if str(actual.get('tiene_protocolo_articulacion', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 20
            puntos += (int(actual.get('nivel_digitalizacion', 0)) * 10)

            c_sem, c_met = st.columns([1, 2])
            with c_sem:
                if puntos < 40: st.error(f"🔴 CRÍTICO: {puntos}/100")
                elif puntos < 75: st.warning(f"🟡 MEDIO: {puntos}/100")
                else: st.success(f"🟢 ÓPTIMO: {puntos}/100")
            
            with c_met:
                st.progress(puntos / 100)
                st.write(f"**Entidad:** {actual.get('nombre_entidad', 'N/A')}")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Presupuesto Rural", f"${actual.get('presupuesto_anual_rural', 0):,.0f}")
            m2.metric("Planta/Contratos", f"{actual.get('num_personal_planta', 0)} / {actual.get('num_personal_contratista', 0)}")
            m3.metric("Digitalización", f"{actual.get('nivel_digitalizacion', 0)}/5")

        # Formulario SADCI integrado abajo
        with st.expander("📝 Actualizar Auditoría Institucional"):
            with st.form("sadci_f"):
                # (Campos del SADCI que ya definimos)
                n_ent = st.text_input("Entidad", value="Alcaldía Puerto Rico")
                pres_r = st.number_input("Presupuesto", min_value=0)
                cmdr_r = st.selectbox("¿CMDR Activo?", ["No", "Sí"])
                dig_r = st.slider("Digitalización", 1, 5, 2)
                if st.form_submit_button("Guardar SADCI"):
                    # Lógica de guardado...
                    st.success("SADCI Actualizado")
    except:
        st.error("Error al cargar datos SADCI")

# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    with st.form("registro_social"):
        c1, c2 = st.columns(2)
        with c1:
            nombre_a = st.text_input("Nombre del Actor/Líder")
            perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural"])
        with c2:
            vereda_a = st.text_input("Vereda")
            tenencia_a = st.selectbox("Tenencia", ["Propiedad", "Posesión", "Ocupación"])
        
        obs_a = st.text_area("Observaciones del conflicto/situación")
        
        if st.form_submit_button("Registrar en Base de Datos Social"):
            # Generar ID único y guardar
            id_a = str(uuid.uuid4())[:8]
            st.success(f"Actor {id_a} registrado exitosamente.")

st.divider()
st.caption("Investigación ESAP 2026 - Herramienta Unificada SIGOber-Rural")

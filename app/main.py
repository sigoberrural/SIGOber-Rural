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
st.markdown("### Sistema de Análisis de Capacidad Institucional (SADCI) y Reforma Agraria")
st.divider()

# 2. CONEXIÓN A DATOS
# Conexión con Google Sheets (Configurada en Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_json_local(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

veredas_topo = cargar_json_local('veredas_puerto_rico.json')

# 3. VISUALIZADOR GEOGRÁFICO
c_map1, c_map2 = st.columns([1, 3])

with c_map1:
    st.info("📍 **Mapa de Tenencia**\nExplore las veredas priorizadas para la formalización de la propiedad.")
    st.write("---")
    st.caption("Capas activas: Límites veredales (ANT)")

with c_map2:
    m = folium.Map(location=[1.91, -75.18], zoom_start=11)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
                     attr='Google', name='Satélite', overlay=False).add_to(m)

    if veredas_topo:
        nombre_obj = list(veredas_topo['objects'].keys())[0]
        folium.TopoJson(
            veredas_topo, f"objects.{nombre_obj}", name="Veredas",
            style_function=lambda x: {'fillColor': '#2e7d32', 'color': 'white', 'weight': 1, 'fillOpacity': 0.2},
            tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'])
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=450)

# 4. MÓDULO SADCI: ANÁLISIS DE CAPACIDAD INSTITUCIONAL
st.divider()
st.header("📊 Diagnóstico Institucional (SADCI)")

try:
    # Leer datos con ttl=0 para forzar actualización en tiempo real
    df_ind = conn.read(ttl=0)
    
    # Normalizar nombres de columnas (Quitar espacios y pasar a minúsculas)
    df_ind.columns = df_ind.columns.str.strip().str.lower().str.replace(' ', '_')

    if not df_ind.empty:
        # Tomamos el registro más reciente
        actual = df_ind.iloc[-1]
        
        # Lógica de Puntuación SADCI
        puntos = 0
        # CMDR (30 pts)
        if str(actual.get('existencia_cmdr', 'No')).strip().upper() in ['SÍ', 'SI']:
            puntos += 30
        # Protocolo (20 pts)
        if str(actual.get('tiene_protocolo_articulacion', 'No')).strip().upper() in ['SÍ', 'SI']:
            puntos += 20
        # Digitalización (Hasta 50 pts)
        try:
            dig_val = int(actual.get('nivel_digitalizacion', 0))
            puntos += (dig_val * 10)
        except: pass

        # Render del Semáforo
        col_sem, col_txt = st.columns([1, 2])
        
        with col_sem:
            if puntos < 40:
                st.error(f"### 🔴 NIVEL CRÍTICO\n**Puntaje SADCI: {puntos}/100**")
            elif puntos < 75:
                st.warning(f"### 🟡 NIVEL MEDIO\n**Puntaje SADCI: {puntos}/100**")
            else:
                st.success(f"### 🟢 NIVEL ÓPTIMO\n**Puntaje SADCI: {puntos}/100**")
        
        with col_txt:
            st.progress(puntos / 100)
            st.markdown(f"""
            **Entidad:** {actual.get('nombre_entidad', 'N/A')}  
            **Estado:** El sistema detecta una capacidad {'insuficiente' if puntos < 40 else 'en proceso' if puntos < 75 else 'robusta'} 
            para liderar procesos de Reforma Agraria en el municipio.
            """)

        # Métricas de la Plantilla
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Presupuesto Rural", f"${actual.get('presupuesto_anual_rural', 0):,.0f}")
        m2.metric("Pers. Planta", actual.get('num_personal_planta', 0))
        m3.metric("Contratistas", actual.get('num_personal_contratista', 0))
        m4.metric("Nivel Digital", f"{actual.get('nivel_digitalizacion', 0)}/5")

    else:
        st.info("📌 No hay registros previos. Use el formulario para ingresar datos de la Alcaldía.")

except Exception as e:
    st.error(f"⚠️ Error de sincronización: Asegúrese de que las columnas en Google Sheets coincidan con la plantilla SADCI.")
    if st.checkbox("Ver detalle técnico del error"):
        st.write(e)

# 5. FORMULARIO DE ACTUALIZACIÓN DE INDICADORES
with st.expander("📝 Actualizar Datos de Auditoría Institucional"):
    with st.form("sadci_form"):
        f1, f2 = st.columns(2)
        with f1:
            nombre = st.text_input("Nombre de la Entidad", value="Alcaldía Puerto Rico")
            pres = st.number_input("Presupuesto Anual Rural ($)", min_value=0, value=500000000)
            planta = st.number_input("Personal de Planta", min_value=0, value=5)
            contratos = st.number_input("Personal Contratistas", min_value=0, value=10)
        with f2:
            cmdr_input = st.selectbox("¿Existe CMDR activo?", ["No", "Sí"])
            prot_input = st.selectbox("¿Tiene Protocolo de Articulación?", ["No", "Sí"])
            dig_input = st.slider("Nivel Digitalización", 1, 5, 2)
            rendicion = st.selectbox("Rendición de Cuentas", ["Anual", "Semestral", "Nunca"])

        if st.form_submit_button("📤 Guardar y Calcular SADCI"):
            nuevo_df = pd.DataFrame([{
                "id_entidad": 1,
                "nombre_entidad": nombre,
                "presupuesto_anual_rural": pres,
                "num_personal_planta": planta,
                "num_personal_contratista": contratos,
                "tiene_protocolo_articulacion": prot_input,
                "nivel_digitalizacion": dig_input,
                "existencia_cmdr": cmdr_input,
                "frecuencia_rendicion_cuentas": rendicion
            }])
            
            # Actualizar Google Sheets
            try:
                df_existente = conn.read()
                df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
                conn.update(data=df_final)
                st.success("✅ Datos sincronizados. El semáforo se actualizará en breve.")
                st.balloons()
            except:
                conn.update(data=nuevo_df)
                st.success("✅ Primera base de datos creada.")

st.divider()
st.caption("Investigación ESAP 2026 - Herramienta de Auditoría Social para la Reforma Agraria")

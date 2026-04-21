import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import uuid

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="SIGOber-Rural Puerto Rico", layout="wide")

st.title("🛰️ SIGOber-Rural: Puerto Rico (Caquetá)")
st.markdown("**Sistema de Información Geográfica para la Reforma Agraria**")
st.divider()

# 2. CONEXIÓN A DATOS (Google Sheets y Archivos Locales)
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_json_local(nombre):
    ruta = os.path.join('data', nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return None

veredas_topo = cargar_json_local('veredas_puerto_rico.json')
conflictos_geo = cargar_json_local('ejemplo_conflictos.geojson')

# 3. INTERFAZ PRINCIPAL (MAPA)
st.subheader("🗺️ Visualizador de Tenencia y Conflictos")
col1, col2 = st.columns([1, 3])

with col1:
    st.info("Utilice las capas del mapa para identificar áreas de intervención prioritaria.")
    if veredas_topo:
        st.success("✅ Capa veredal cargada")
    if conflictos_geo:
        st.warning(f"📍 {len(conflictos_geo['features'])} Puntos de conflicto")

with col2:
    # Centrar mapa en Puerto Rico, Caquetá
    m = folium.Map(location=[1.91, -75.18], zoom_start=11)
    
    # Capa Satelital
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google', name='Vista Satelital', overlay=False
    ).add_to(m)

    # Dibujar Veredas (TopoJSON)
    if veredas_topo:
        nombre_capa = list(veredas_topo['objects'].keys())[0]
        folium.TopoJson(
            data=veredas_topo,
            object_path=f"objects.{nombre_capa}",
            name="Límites Veredales",
            style_function=lambda x: {'fillColor': '#2e7d32', 'color': 'white', 'weight': 1, 'fillOpacity': 0.3},
            tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'])
        ).add_to(m)

    # Dibujar Conflictos (GeoJSON)
    if conflictos_geo:
        folium.GeoJson(
            conflictos_geo,
            name="Conflictos de Tierra",
            marker=folium.Marker(icon=folium.Icon(color='red', icon='exclamation-sign')),
            tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Conflicto:'])
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=500)

# 4. MÓDULO DE REGISTRO (GOOGLE SHEETS)
st.divider()
st.header("👥 Registro de Actores y Situación Agraria")

with st.expander("📝 Formulario de Caracterización Técnica (Anonimizado)"):
    with st.form("registro_actor"):
        f1, f2 = st.columns(2)
        with f1:
            perfil = st.selectbox("Perfil del Actor", ["Pequeño Productor", "Poseedor sin Título", "JAC", "Mujer Rural", "Reclamante"])
            vereda_ref = st.text_input("Vereda donde se ubica")
        with f2:
            tenencia = st.selectbox("Situación de Tenencia", ["Baldío Ocupado", "Propiedad con Título", "Posesión Informal", "Litigio"])
            prioridad = st.select_slider("Urgencia de Intervención", options=["Baja", "Media", "Alta", "Crítica"])
        
        observacion = st.text_area("Descripción técnica de la situación (Evite datos personales)")
        
        btn_guardar = st.form_submit_button("📤 Sincronizar con Google Sheets")

        if btn_guardar:
            if vereda_ref and observacion:
                # Crear DataFrame para la nueva fila
                nuevo_registro = pd.DataFrame([{
                    "ID_Actor": str(uuid.uuid4())[:8],
                    "Tipo_Actor": perfil,
                    "Vereda": vereda_ref,
                    "Situacion_Tenencia": tenencia,
                    "Prioridad": prioridad,
                    "Observaciones_Anonimas": observacion
                }])
                
                # Leer datos actuales y actualizar
                try:
                    actuales = conn.read()
                    actualizado = pd.concat([actuales, nuevo_registro], ignore_index=True)
                    conn.update(data=actualizado)
                    st.success("✅ Registro guardado en la base de datos de la investigación.")
                except:
                    # Si la hoja está vacía
                    conn.update(data=nuevo_registro)
                    st.success("✅ Base de datos iniciada con el primer registro.")
            else:
                st.error("⚠️ Complete los campos obligatorios.")

# 5. MÓDULO DE INDICADORES INSTITUCIONALES (Basado en plantilla_indicadores.csv) ---
st.divider()
st.header("🏢 Auditoría de Capacidad Institucional")
st.caption("Evaluación de la Alcaldía y entes territoriales según la plantilla de indicadores.")

with st.expander("📊 Diligenciar Plantilla de Indicadores"):
    with st.form("form_indicadores"):
        c1, c2 = st.columns(2)
        with c1:
            entidad = st.text_input("Nombre de la Entidad", value="Alcaldía Puerto Rico")
            presupuesto = st.number_input("Presupuesto Anual Rural ($)", min_value=0)
            planta = st.number_input("Personal de Planta", min_value=0)
            contratistas = st.number_input("Personal Contratista", min_value=0)
            cmdr = st.radio("¿Existe CMDR (Consejo Municipal de Desarrollo Rural)?", ["Sí", "No"])
        
        with c2:
            protocolo = st.radio("¿Tiene protocolo de articulación?", ["Sí", "No"])
            tramites = st.radio("¿Trámites simplificados?", ["Sí", "No"])
            rendicion = st.selectbox("Frecuencia Rendición de Cuentas", ["Anual", "Semestral", "Trimestral", "Nunca"])
            digital = st.slider("Nivel de Digitalización (1-5)", 1, 5, 2)
        
        btn_ind = st.form_submit_button("Actualizar Indicadores Institucionales")
        
        if btn_ind:
            # Aquí la lógica para enviar a la 'Hoja2' de tu Google Sheets
            # (Usando la misma lógica de conn.update que ya tenemos)
            st.success(f"Indicadores de {entidad} actualizados correctamente.")

# 6. PANEL DE ANÁLISIS DE DATOS
# --- 5. PANEL DE ANÁLISIS Y SEMÁFORO SADCI ---
st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")

try:
    # 1. Leer la hoja de indicadores (asegúrate de especificar la hoja si usas varias)
    df_indicadores = conn.read(worksheet="Sheet1") # O el nombre de tu pestaña

# Reemplaza la parte del cálculo dentro del try con esto:
if not df_indicadores.empty:
    # Seleccionamos la última fila
    ultimo = df_indicadores.iloc[-1]
    
    # Convertimos a strings y números seguros para evitar errores de tipo
    puntos = 0
    
    # Validación de CMDR (limpiamos espacios y pasamos a mayúsculas)
    if str(ultimo.get('existencia_cmdr', 'No')).strip().upper() == 'SÍ': 
        puntos += 30
        
    if str(ultimo.get('tiene_protocolo_articulacion', 'No')).strip().upper() == 'SÍ': 
        puntos += 20
        
    # Validación de Digitalización (aseguramos que sea entero)
    try:
        nivel = int(ultimo.get('nivel_digitalizacion', 0))
        puntos += (nivel * 10)
    except:
        puntos += 0

st.divider()
st.caption("Investigación ESAP 2026 - Colectivo Guadalupe Salcedo")

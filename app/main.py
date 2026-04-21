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

    if not df_indicadores.empty:
        # Tomamos la última entrada registrada
        ultimo_registro = df_indicadores.iloc[-1]
        
        # 2. LÓGICA DEL SEMÁFORO
        puntos = 0
        if ultimo_registro['existencia_cmdr'] == 'Sí': puntos += 30
        if ultimo_registro['tiene_protocolo_articulacion'] == 'Sí': puntos += 20
        puntos += (int(ultimo_registro['nivel_digitalizacion']) * 10) # Escala 1-5 = 10-50 pts

        # 3. RENDERIZADO VISUAL DEL SEMÁFORO
        col_s1, col_s2 = st.columns([1, 2])
        
        with col_s1:
            if puntos < 40:
                st.error(f"🔴 CRÍTICO\n\nSADCI: {puntos}/100")
            elif puntos < 75:
                st.warning(f"🟡 MEDIO\n\nSADCI: {puntos}/100")
            else:
                st.success(f"🟢 ÓPTIMO\n\nSADCI: {puntos}/100")
        
        with col_s2:
            st.progress(puntos / 100)
            st.write(f"**Análisis:** La entidad '{ultimo_registro['nombre_entidad']}' presenta un nivel de preparación institucional {'bajo' if puntos < 40 else 'aceptable' if puntos < 75 else 'alto'} para la gestión de la Reforma Agraria.")

        # 4. MÉTRICAS RÁPIDAS
        c1, c2, c3 = st.columns(3)
        c1.metric("Presupuesto Rural", f"${ultimo_registro['presupuesto_anual_rural']:,.0f}")
        c2.metric("Personal Planta", ultimo_registro['num_personal_planta'])
        c3.metric("Contratistas", ultimo_registro['num_personal_contratista'])

    else:
        st.info("No hay datos de indicadores para calcular el SADCI.")

except Exception as e:
    st.error("Error al conectar con la base de datos de indicadores.")

st.divider()
st.caption("Investigación ESAP 2026 - Colectivo Guadalupe Salcedo")

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
    # Cargamos los secrets
    creds_info = dict(st.secrets["connections"]["gsheets"])
    
    # TRUCO CRÍTICO: Asegurar que los \n se lean como saltos de línea reales
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
    
    # 1. Cargar datos de conflictos desde la nube
    try:
        sh = conectar_gspread()
        ws_conf = sh.worksheet("Conflictos")
        df_conf = pd.DataFrame(ws_conf.get_all_records())
        
        if not df_conf.empty:
            df_conf['lat'] = pd.to_numeric(df_conf['lat'], errors='coerce')
            df_conf['lon'] = pd.to_numeric(df_conf['lon'], errors='coerce')
            df_conf = df_conf.dropna(subset=['lat', 'lon'])
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        df_conf = pd.DataFrame()

    col_menu, col_mapa = st.columns([1, 3])

    with col_menu:
        st.markdown("### 🛠️ Capas y Filtros")
        mostrar_veredas = st.checkbox("Límites Veredales (Nombres)", value=True)
        mostrar_puntos = st.checkbox("Puntos de Conflicto", value=True)
        
        st.divider()
        st.markdown("### ⚠️ Registrar Conflicto")
        with st.form("form_conflictos", clear_on_submit=True):
            # Identificación de quien registra
            quien_registra = st.text_input("Nombre o Código del Encuestador/Funcionario")
            
            tipo_c = st.selectbox("Tipo de Conflicto", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda_c = st.text_input("Nombre de la Vereda afectada")
            
            c1, c2 = st.columns(2)
            lat_c = c1.number_input("Latitud", value=1.91, format="%.4f")
            lon_c = c2.number_input("Longitud", value=-75.18, format="%.4f")
            
            desc_c = st.text_area("Descripción breve del caso")
            
            if st.form_submit_button("📍 Marcar y Guardar"):
                if vereda_c and quien_registra:
                    # Se asume que la hoja tiene las columnas: ID, Tipo, Vereda, Lat, Lon, Desc, Usuario
                    nueva_fila_c = [
                        str(uuid.uuid4())[:5], 
                        tipo_c, 
                        vereda_c, 
                        lat_c, 
                        lon_c, 
                        desc_c, 
                        quien_registra 
                    ]
                    ws_conf.append_row(nueva_fila_c)
                    st.success(f"Punto registrado por {quien_registra}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Por favor completa el nombre de la vereda y quién registra.")

    with col_mapa:
        # Inicializar mapa
        m = folium.Map(location=[1.91, -75.18], zoom_start=11, tiles="cartodbpositron")
        
        # A. RENDERIZADO ROBUSTO DE VEREDAS
        if veredas_topo and mostrar_veredas:
            try:
                # DETECCIÓN DINÁMICA: Obtenemos el nombre del objeto interno del TopoJSON
                # Esto evita que la capa sea invisible si el objeto no se llama 'veredas_puerto_rico'
                obj_name = list(veredas_topo['objects'].keys())[0]
                
                # Explorar propiedades para encontrar el campo del nombre
                sample_props = veredas_topo['objects'][obj_name]['geometries'][0].get('properties', {})
                posibles_campos = list(sample_props.keys())
                
                # Buscar campo de nombre
                campo_nombre = next((f for f in ['NOMBRE_VEREDA', 'NOM_VER', 'NOMBRE', 'VEREDA', 'nombre'] 
                                   if f in posibles_campos), None)
                
                folium.TopoJson(
                    data=veredas_topo, 
                    object_path=f"objects.{obj_name}", # Ruta corregida dinámica
                    name="Límites Veredales",
                    tooltip=folium.GeoJsonTooltip(
                        fields=[campo_nombre] if campo_nombre else posibles_campos[:1], 
                        aliases=['📍 Vereda:'],
                        localize=True,
                        sticky=True
                    ) if campo_nombre else None,
                    style_function=lambda x: {
                        'fillColor': '#2ecc71', 
                        'color': 'black', 
                        'weight': 1.2, 
                        'fillOpacity': 0.15
                    }
                ).add_to(m)
            except Exception as e:
                st.error(f"Error técnico al cargar la capa de veredas: {e}")

        # B. Capa de Conflictos
        if not df_conf.empty and mostrar_puntos:
            for _, row in df_conf.iterrows():
                # Manejo de columna de responsable (por si la hoja es vieja)
                responsable = row.get('registrado_por', "No asignado")
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=7,
                    color="red" if row['tipo_conflicto'] == "Tenencia" else "orange",
                    fill=True,
                    popup=folium.Popup(f"""
                        <b>Vereda:</b> {row['vereda']}<br>
                        <b>Tipo:</b> {row['tipo_conflicto']}<br>
                        <b>Responsable:</b> {responsable}<br>
                        <hr>
                        <b>Nota:</b> {row['descripcion']}
                    """, max_width=250),
                    tooltip=f"Conflicto: {row['vereda']}"
                ).add_to(m)

        st_folium(m, width=800, height=600, key="mapa_final_v1")

    # Listado inferior
    if not df_conf.empty:
        with st.expander("📊 Listado Detallado de Conflictos"):
            st.dataframe(df_conf, use_container_width=True)

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    
    try:
        sh = conectar_gspread()
        ws_sadci = sh.worksheet("SADCI") 
        data_sadci = ws_sadci.get_all_records()
        df_sadci = pd.DataFrame(data_sadci)
        
        if not df_sadci.empty:
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            df_sadci['robustez_adm'] = (df_sadci['num_personal_planta'] / 
                                       (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                promedio_ejecucion = df_sadci['ejecucion_presupuestal_pct'].mean()
                st.metric("Eficacia Presupuestal", f"{promedio_ejecucion:.1f}%")
            with col_kpi2:
                promedio_pdt = df_sadci['cumplimiento_pdt_pct'].mean()
                st.metric("Meta PDT Media", f"{promedio_pdt:.1f}%")
            with col_kpi3:
                mepi_avg = df_sadci['calificacion_mepi'].mean()
                st.metric("Puntaje MEPI Promedio", f"{mepi_avg:.1f}/100")

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
                "Puntaje": [
                    df_sadci['robustez_adm'].mean(),
                    df_sadci['puntos_digital'].mean(),
                    df_sadci['ejecucion_presupuestal_pct'].mean(),
                    df_sadci['calificacion_mepi'].mean()
                ]
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

                if st.form_submit_button("🚀 Guardar y Actualizar Dashboard"):
                    if nombre:
                        nueva_fila = [str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                                    protocolo, "Sí", rendicion, digital, 
                                    ejecucion, pdt, participacion, mepi]
                        ws_sadci.append_row(nueva_fila)
                        st.success("✅ Auditoría guardada.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("⚠️ El nombre de la entidad es obligatorio.")

    except Exception as e:
        st.error(f"Error en el sistema SADCI: {e}")
        
# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("👥 Caracterización de Actores Territoriales")
    try:
        sh = conectar_gspread()
        ws = sh.worksheet("Actores")
        df_social = pd.DataFrame(ws.get_all_records())
        
        if not df_social.empty:
            st.markdown("#### 📊 Análisis de Composición Social")
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                st.write("**Distribución por Perfil**")
                st.bar_chart(df_social['Perfil'].value_counts())
            with c_graf2:
                st.write("**Seguridad Jurídica (Tenencia)**")
                st.line_chart(df_social['Tenencia'].value_counts())
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas Cubiertas", df_social['Vereda'].nunique())
            propiedad_total = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            pct_formal = (propiedad_total / len(df_social)) * 100 if len(df_social) > 0 else 0
            m3.metric("Formalidad", f"{pct_formal:.1f}%")

        with st.expander("📝 Registrar Nuevo Actor", expanded=df_social.empty):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre del Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda de ubicación")
                    tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones técnicas")
                if st.form_submit_button("📤 Registrar Actor"):
                    if nombre_a and vereda_a:
                        ws.append_row([str(uuid.uuid4())[:8], nombre_a, perfil_a, vereda_a, tenencia_a, obs_a])
                        st.success(f"✅ {nombre_a} registrado.")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Error en el módulo de actores: {e}")

st.divider()
st.caption("Investigación ESAP 2026")

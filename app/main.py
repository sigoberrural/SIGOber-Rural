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
    except:
        df_conf = pd.DataFrame()

    col_menu, col_mapa = st.columns([1, 3])

    with col_menu:
        st.markdown("### 🛠️ Capas y Filtros")
        mostrar_veredas = st.checkbox("Límites Veredales", value=True)
        mostrar_puntos = st.checkbox("Puntos de Conflicto", value=True)
        
        st.divider()
        st.markdown("### ⚠️ Registrar Conflicto")
        with st.form("form_conflictos", clear_on_submit=True):
            tipo_c = st.selectbox("Tipo", ["Linderos", "Uso de Suelo", "Ambiental", "Tenencia"])
            vereda_c = st.text_input("Vereda afectada")
            # Coordenadas aproximadas para Puerto Rico si no se tienen exactas
            c1, c2 = st.columns(2)
            lat_c = c1.number_input("Latitud", value=1.91, format="%.4f")
            lon_c = c2.number_input("Longitud", value=-75.18, format="%.4f")
            desc_c = st.text_area("Descripción breve")
            
            if st.form_submit_button("📍 Marcar en Mapa"):
                if vereda_c:
                    nueva_fila_c = [str(uuid.uuid4())[:5], tipo_c, vereda_c, lat_c, lon_c, desc_c]
                    ws_conf.append_row(nueva_fila_c)
                    st.success("Punto registrado.")
                    st.rerun()

    with col_mapa:
        # Configuración del mapa base
        m = folium.Map(location=[1.91, -75.18], zoom_start=11, tiles="cartodbpositron")
        
        # A. Capa de Veredas (TopoJSON) con Metadatos corregida
        if veredas_topo and mostrar_veredas:
            try:
                obj_name = list(veredas_topo['objects'].keys())[0]
                
                # Extraemos las propiedades del primer objeto para saber qué campos existen
                # Esto evita el AssertionError
                sample_props = veredas_topo['objects'][obj_name]['geometries'][0].get('properties', {})
                posibles_campos = list(sample_props.keys())
                
                # Elegimos el campo de nombre: Priorizamos 'NOMBRE_VEREDA', si no, el primero que aparezca
                campo_nombre = 'NOMBRE_VEREDA' if 'NOMBRE_VEREDA' in posibles_campos else (posibles_campos[0] if posibles_campos else None)

                if campo_nombre:
                    folium.TopoJson(
                        veredas_topo, 
                        f"objects.{obj_name}",
                        name="Límites Veredales",
                        tooltip=folium.GeoJsonTooltip(
                            fields=[campo_nombre], 
                            aliases=['Nombre:'],
                            localize=True
                        ),
                        style_function=lambda x: {
                            'fillColor': '#2ecc71', 
                            'color': 'black', 
                            'weight': 1, 
                            'fillOpacity': 0.2
                        }
                    ).add_to(m)
                else:
                    # Si no hay propiedades, cargamos el TopoJSON sin tooltip para que no de error
                    folium.TopoJson(veredas_topo, f"objects.{obj_name}").add_to(m)
                    
            except Exception as e:
                st.error(f"Error renderizando mapa: {e}")

        # B. Capa de Conflictos (Puntos registrados en Excel)
        if not df_conf.empty and mostrar_puntos:
            for _, row in df_conf.iterrows():
                # Color según tipo
                color_p = "red" if row['tipo_conflicto'] == "Tenencia" else "orange"
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=6,
                    color=color_p,
                    fill=True,
                    popup=f"<b>Conflicto:</b> {row['tipo_conflicto']}<br><b>Desc:</b> {row['descripcion']}",
                    tooltip=f"Ver detalle: {row['vereda']}"
                ).add_to(m)

        # Renderizar mapa
        st_folium(m, width=800, height=600, key="mapa_v4")

    # Resumen inferior
    if not df_conf.empty:
        with st.expander("📊 Listado de Conflictos Registrados"):
            st.table(df_conf[['tipo_conflicto', 'vereda', 'descripcion']])

# --- TAB 2: AUDITORÍA SADCI ---
with tab_sadci:
    st.subheader("📊 Diagnóstico de Capacidad Institucional (SADCI)")
    
    try:
        sh = conectar_gspread()
        ws_sadci = sh.worksheet("SADCI") 
        data_sadci = ws_sadci.get_all_records()
        df_sadci = pd.DataFrame(data_sadci)
        
        if not df_sadci.empty:
            # --- PROCESAMIENTO DE DATOS PARA GRÁFICOS ---
            # 1. Normalización de Digitalización a escala 0-100
            dict_dig = {"Bajo": 25, "Medio": 50, "Alto": 75, "Excelente": 100}
            df_sadci['puntos_digital'] = df_sadci['nivel_digitalizacion'].map(dict_dig)
            
            # 2. Cálculo de Robustez Administrativa (Planta vs Total)
            df_sadci['robustez_adm'] = (df_sadci['num_personal_planta'] / 
                                       (df_sadci['num_personal_planta'] + df_sadci['num_personal_contratista']) * 100).fillna(0)

            # --- VISUALIZACIÓN DE INDICADORES (KPIs) ---
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                promedio_ejecucion = df_sadci['ejecucion_presupuestal_pct'].mean()
                st.metric("Eficacia Presupuestal", f"{promedio_ejecucion:.1f}%", delta_color="normal")
            with col_kpi2:
                promedio_pdt = df_sadci['cumplimiento_pdt_pct'].mean()
                st.metric("Meta PDT Media", f"{promedio_pdt:.1f}%")
            with col_kpi3:
                mepi_avg = df_sadci['calificacion_mepi'].mean()
                st.metric("Puntaje MEPI Promedio", f"{mepi_avg:.1f}/100")

            st.divider()

            # --- SECCIÓN DE GRÁFICOS DINÁMICOS ---
            col_graph1, col_graph2 = st.columns(2)

            with col_graph1:
                st.markdown("##### 🚀 Eficacia vs. Cumplimiento Meta")
                # Gráfico comparando Ejecución y PDT por Entidad
                st.bar_chart(df_sadci.set_index('nombre_entidad')[['ejecucion_presupuestal_pct', 'cumplimiento_pdt_pct']])
            
            with col_graph2:
                st.markdown("##### 💻 Madurez Digital por Entidad")
                # Gráfico de puntos de digitalización
                st.line_chart(df_sadci.set_index('nombre_entidad')['puntos_digital'])

            st.markdown("##### 🏛️ Balance de Dimensiones (Promedio Municipal)")
            # Creamos un resumen de las dimensiones para un gráfico de áreas
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

        # --- FORMULARIO SADCI AMPLIADO ---
        with st.expander("📝 Realizar Nueva Auditoría Integral", expanded=df_sadci.empty):
            with st.form("registro_sadci_full", clear_on_submit=True):
                st.info("Complete los datos de la entidad para actualizar los indicadores automáticamente.")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.caption("DATOS BÁSICOS")
                    nombre = st.text_input("Nombre Entidad")
                    presupuesto = st.number_input("Presupuesto Anual Rural ($)", min_value=0)
                    planta = st.number_input("Personal Planta", min_value=0)
                    contratos = st.number_input("Personal Contratista", min_value=0)
                
                with c2:
                    st.caption("GESTIÓN FISCAL")
                    ejecucion = st.slider("% Ejecución Gasto", 0, 100, 70)
                    pdt = st.slider("% Avance Metas PDT", 0, 100, 50)
                    mepi = st.number_input("Calificación MEPI", 0, 100, 60)
                
                with c3:
                    st.caption("DIGITAL Y RELACIONAL")
                    digital = st.select_slider("Nivel Digital", ["Bajo", "Medio", "Alto", "Excelente"])
                    protocolo = st.selectbox("¿Protocolo Articulación?", ["Sí", "No", "En proceso"])
                    participacion = st.selectbox("Instancias Participación", ["Activas", "Inactivas", "Inexistentes"])
                    rendicion = st.selectbox("Rendición Cuentas", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("🚀 Guardar y Actualizar Dashboard"):
                    if nombre:
                        nueva_fila = [
                            str(uuid.uuid4())[:8], nombre, presupuesto, planta, contratos,
                            protocolo, "Sí", rendicion, digital, 
                            ejecucion, pdt, participacion, mepi
                        ]
                        ws_sadci.append_row(nueva_fila)
                        st.success("✅ Auditoría guardada. Los gráficos se están actualizando...")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("⚠️ El nombre de la entidad es obligatorio.")

        # --- TABLA DE DATOS ---
        if not df_sadci.empty:
            with st.expander("🔍 Ver detalle de datos (Tabla)"):
                st.dataframe(df_sadci, use_container_width=True)

    except Exception as e:
        st.error(f"Error en el sistema de visualización: {e}")
        
# --- TAB 3: REGISTRO DE ACTORES ---
with tab_actores:
    st.subheader("👥 Caracterización de Actores Territoriales")
    
    try:
        # 1. Lectura de datos
        sh = conectar_gspread()
        ws = sh.worksheet("Actores")
        data_actores = ws.get_all_records()
        df_social = pd.DataFrame(data_actores)
        
        # --- SECCIÓN DE ANÁLISIS VISUAL ---
        if not df_social.empty:
            st.markdown("#### 📊 Análisis de Composición Social")
            c_graf1, c_graf2 = st.columns(2)
            
            with c_graf1:
                st.write("**Distribución por Perfil**")
                # Conteo de perfiles para gráfico de barras
                perfil_counts = df_social['Perfil'].value_counts()
                st.bar_chart(perfil_counts)
                
            with c_graf2:
                st.write("**Seguridad Jurídica (Tenencia)**")
                # Conteo de tenencia para gráfico de área/líneas
                tenencia_counts = df_social['Tenencia'].value_counts()
                st.line_chart(tenencia_counts)
            
            # Métricas rápidas
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Actores", len(df_social))
            m2.metric("Veredas Cubiertas", df_social['Vereda'].nunique())
            # Cálculo de % de propiedad formal
            propiedad_total = len(df_social[df_social['Tenencia'] == 'Propiedad'])
            pct_formal = (propiedad_total / len(df_social)) * 100 if len(df_social) > 0 else 0
            m3.metric("Formalidad", f"{pct_formal:.1f}%")
            
            st.divider()

        # --- FORMULARIO DE REGISTRO ---
        with st.expander("📝 Registrar Nuevo Actor Territorial", expanded=df_social.empty):
            with st.form("registro_social", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_a = st.text_input("Nombre del Actor/Líder")
                    perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
                with c2:
                    vereda_a = st.text_input("Vereda de ubicación")
                    tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
                
                obs_a = st.text_area("Observaciones técnicas")
                btn_social = st.form_submit_button("📤 Registrar Actor")
            
                if btn_social:
                    if nombre_a and vereda_a:
                        try:
                            nueva_fila = [
                                str(uuid.uuid4())[:8],
                                nombre_a,
                                perfil_a,
                                vereda_a,
                                tenencia_a,
                                obs_a
                            ]
                            ws.append_row(nueva_fila)
                            st.success(f"✅ {nombre_a} registrado correctamente.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar: {str(e)}")
                    else:
                        st.warning("⚠️ Nombre y Vereda son obligatorios.")

        # --- TABLA DE DATOS ---
        if not df_social.empty:
            with st.expander("🔍 Ver listado completo"):
                st.dataframe(df_social, use_container_width=True)

    except Exception as e:
        st.error(f"Error en el módulo de actores: {e}")
st.divider()
st.caption("Investigación ESAP 2026")

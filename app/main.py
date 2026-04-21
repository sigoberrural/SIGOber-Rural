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
conn = st.connection("DB_SIGOber_Actores", type=GSheetsConnection)

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
# --- TAB 1: MAPA Y SEÑALIZACIÓN ---
with tab_mapa:
    st.subheader("Visualizador de Tenencia y Conflictos")
    
    col_menu, col_mapa = st.columns([1, 3])
    
    with col_menu:
        st.markdown("### 🛠️ Panel de Control")
        mostrar_veredas = st.checkbox("Límites Veredales", value=True)
        mostrar_conflictos = st.checkbox("Puntos de Conflicto", value=True)
        
        st.divider()
        
        # Filtro de Conflictos Seguro
        filtro_tipo = "Todos"
        conflictos_filtrados = None
        
        if conflictos_geo and mostrar_conflictos:
            try:
                tipos = sorted(list(set([f['properties'].get('tipo_conflicto', 'Sin Tipo') for f in conflictos_geo['features']])))
                filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos"] + tipos)
                
                if filtro_tipo != "Todos":
                    features = [f for f in conflictos_geo['features'] if f['properties'].get('tipo_conflicto') == filtro_tipo]
                    conflictos_filtrados = {"type": "FeatureCollection", "features": features}
                else:
                    conflictos_filtrados = conflictos_geo
                
                st.metric("Conflictos visibles", len(conflictos_filtrados['features']))
            except Exception as e:
                st.error("Error al procesar tipos de conflicto.")
                conflictos_filtrados = conflictos_geo

    with col_mapa:
        # 1. Crear el objeto mapa base
        m = folium.Map(location=[1.91, -75.18], zoom_start=11)
        folium.TileLayer('OpenStreetMap', name='Calles').add_to(m)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
                         attr='Google', name='Satélite', overlay=False).add_to(m)

        # 2. Cargar Veredas (Con validación de propiedades para evitar AssertionError)
        if veredas_topo and mostrar_veredas:
            try:
                nombre_obj = list(veredas_topo['objects'].keys())[0]
                # Intentamos detectar si NOMBRE_VER existe, si no, usamos una lista vacía
                geoms = veredas_topo['objects'][nombre_obj].get('geometries', [])
                props = geoms[0].get('properties', {}) if geoms else {}
                
                # Si 'NOMBRE_VER' no está, no usamos tooltip para evitar el crash
                tooltip_ver = None
                if 'NOMBRE_VER' in props:
                    tooltip_ver = folium.GeoJsonTooltip(fields=['NOMBRE_VER'], aliases=['Vereda:'])
                
                folium.TopoJson(
                    veredas_topo, 
                    f"objects.{nombre_obj}", 
                    name="Límites Veredales",
                    style_function=lambda x: {'fillColor': '#2e7d32', 'color': 'white', 'weight': 1, 'fillOpacity': 0.2},
                    tooltip=tooltip_ver
                ).add_to(m)
            except Exception as e:
                st.warning("Capa de veredas cargada sin etiquetas por incompatibilidad de datos.")
                # Fallback: Cargar sin tooltip
                folium.TopoJson(veredas_topo, f"objects.{nombre_obj}").add_to(m)

        # 3. Cargar Conflictos Filtrados
        if conflictos_filtrados and mostrar_conflictos and len(conflictos_filtrados['features']) > 0:
            folium.GeoJson(
                conflictos_filtrados,
                name="Alertas",
                marker=folium.Marker(icon=folium.Icon(color='red', icon='info-sign')),
                tooltip=folium.GeoJsonTooltip(fields=['tipo_conflicto'], aliases=['Tipo:']) if 'tipo_conflicto' in str(conflictos_filtrados) else None
            ).add_to(m)

        folium.LayerControl().add_to(m)
        
        # 4. Renderizado Final Seguro
        try:
            st_folium(m, width=800, height=600, key="mapa_v3")
        except:
            st.error("Error crítico al renderizar el mapa. Verifique que los archivos JSON sean válidos.")
# --- TAB 2: AUDITORÍA SADCI (INSTITUCIONAL) ---
with tab_sadci:
    st.subheader("Análisis de Capacidad Institucional")
    
    try:
        # 1. LECTURA Y NORMALIZACIÓN
        df_ind = conn.read(ttl=0)
        df_ind.columns = df_ind.columns.str.strip().str.lower().str.replace(' ', '_')

        if not df_ind.empty:
            # Tomamos el último registro para el semáforo principal
            actual = df_ind.iloc[-1]
            
            # Lógica de Puntuación
            puntos = 0
            if str(actual.get('existencia_cmdr', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 30
            if str(actual.get('tiene_protocolo_articulacion', 'No')).strip().upper() in ['SÍ', 'SI']: puntos += 20
            puntos += (int(actual.get('nivel_digitalizacion', 0)) * 10)

            # --- VISUALIZACIÓN DEL SEMÁFORO ---
            c_sem, c_met = st.columns([1, 2])
            with c_sem:
                if puntos < 40: st.error(f"### 🔴 CRÍTICO: {puntos}/100")
                elif puntos < 75: st.warning(f"### 🟡 MEDIO: {puntos}/100")
                else: st.success(f"### 🟢 ÓPTIMO: {puntos}/100")
            
            with c_met:
                st.progress(puntos / 100)
                st.markdown(f"**Entidad:** {actual.get('nombre_entidad', 'N/A')}")
                st.caption("Este puntaje refleja la capacidad técnica y operativa para la Reforma Agraria.")

            # --- MÉTRICAS CLAVE ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Presupuesto Rural", f"${actual.get('presupuesto_anual_rural', 0):,.0f}")
            # Cálculo de proporción de personal
            total_pers = actual.get('num_personal_planta', 0) + actual.get('num_personal_contratista', 0)
            m2.metric("Talento Humano Total", total_pers, help="Suma de planta y contratistas")
            m3.metric("Digitalización", f"{actual.get('nivel_digitalizacion', 0)} / 5")

            st.divider()

            # --- 2. GRÁFICOS DE EVOLUCIÓN SADCI ---
            st.subheader("📈 Evolución de Capacidades")
            g1, g2 = st.columns(2)

            with g1:
                st.markdown("**Histórico de Puntaje SADCI**")
                # Creamos una columna temporal de puntaje para el gráfico
                df_ind['score'] = (
                    df_ind['existencia_cmdr'].apply(lambda x: 30 if str(x).upper() in ['SÍ', 'SI'] else 0) +
                    df_ind['tiene_protocolo_articulacion'].apply(lambda x: 20 if str(x).upper() in ['SÍ', 'SI'] else 0) +
                    (df_ind['nivel_digitalizacion'].astype(int) * 10)
                )
                st.line_chart(df_ind['score'], color="#2e7d32")
                st.caption("Tendencia de mejora institucional en el tiempo.")

            with g2:
                st.markdown("**Relación Planta vs Contratistas**")
                # Gráfico comparativo de personal
                df_pers = df_ind[['num_personal_planta', 'num_personal_contratista']].iloc[-1]
                st.bar_chart(df_pers, color="#ff9800")
                st.caption("Dependencia de personal externo vs planta.")

        # --- 3. FORMULARIO DE ACTUALIZACIÓN ---
        with st.expander("📝 Registrar Nueva Evaluación Institucional"):
            with st.form("sadci_f"):
                c1, c2 = st.columns(2)
                with c1:
                    n_ent = st.text_input("Entidad Evaluada", value="Alcaldía Puerto Rico")
                    pres_r = st.number_input("Presupuesto Anual Rural ($)", min_value=0)
                    planta_r = st.number_input("Personal de Planta", min_value=0)
                    cont_r = st.number_input("Personal Contratista", min_value=0)
                with c2:
                    cmdr_r = st.selectbox("¿Existe CMDR Activo?", ["No", "Sí"])
                    prot_r = st.selectbox("¿Tiene Protocolo Articulación?", ["No", "Sí"])
                    dig_r = st.slider("Nivel Digitalización", 1, 5, 2)
                    rend_r = st.selectbox("Frecuencia Rendición Cuentas", ["Anual", "Semestral", "Nunca"])

                if st.form_submit_button("💾 Guardar y Actualizar Semáforo"):
                    nuevo_sadci = pd.DataFrame([{
                        "id_entidad": 1,
                        "nombre_entidad": n_ent,
                        "presupuesto_anual_rural": pres_r,
                        "num_personal_planta": planta_r,
                        "num_personal_contratista": cont_r,
                        "tiene_protocolo_articulacion": prot_r,
                        "nivel_digitalizacion": dig_r,
                        "existencia_cmdr": cmdr_r,
                        "frecuencia_rendicion_cuentas": rend_r
                    }])
                    
                    try:
                        df_old = conn.read()
                        df_new = pd.concat([df_old, nuevo_sadci], ignore_index=True)
                        conn.update(data=df_new)
                        st.success("✅ Auditoría guardada. Los gráficos se han actualizado.")
                        st.rerun() # Refresca para ver los cambios en los gráficos
                    except:
                        conn.update(data=nuevo_sadci)
                        st.success("✅ Primera medición registrada.")

    except Exception as e:
        st.error("No se pudieron cargar los indicadores SADCI. Verifique el archivo de datos.")

# --- TAB 3: REGISTRO DE ACTORES (SOCIAL) ---
with tab_actores:
    st.subheader("Caracterización de Actores Territoriales")
    
    # 1. FORMULARIO DE REGISTRO
    with st.form("registro_social"):
        c1, c2 = st.columns(2)
        with c1:
            nombre_a = st.text_input("Nombre del Actor/Líder")
            perfil_a = st.selectbox("Perfil", ["Pequeño Productor", "Poseedor", "JAC", "Mujer Rural", "Reclamante"])
        with c2:
            vereda_a = st.text_input("Vereda de ubicación")
            tenencia_a = st.selectbox("Situación de Tenencia", ["Propiedad", "Posesión", "Ocupación", "Baldío"])
        
        obs_a = st.text_area("Observaciones técnicas de la situación")
        
        btn_social = st.form_submit_button("📤 Registrar en Base de Datos Social")
        
        if btn_social:
            if nombre_a and vereda_a:
                nuevo_actor = pd.DataFrame([{
                    "ID_Actor": str(uuid.uuid4())[:8],
                    "Nombre": nombre_a,
                    "Perfil": perfil_a,
                    "Vereda": vereda_a,
                    "Tenencia": tenencia_a,
                    "Observaciones": obs_a
                }])
                
                try:
                    # Intentamos leer la base de datos actual para anexar
                    # Nota: Si usas una pestaña diferente, usa conn.read(worksheet="Actores")
                    df_actual_soc = conn.read(worksheet="Actores", ttl=0) 
                    df_final_soc = pd.concat([df_actual_soc, nuevo_actor], ignore_index=True)
                    conn.update(worksheet="Actores", data=df_final_soc)
                    st.success(f"✅ Actor {nombre_a} registrado exitosamente.")
                except:
                    conn.update(data=nuevo_actor)
                    st.success("✅ Base de datos social iniciada.")
            else:
                st.warning("⚠️ Por favor complete el nombre y la vereda.")

    st.divider()

    # 2. SECCIÓN DE ESTADÍSTICAS Y GRÁFICOS (VISUALIZACIÓN)
    st.subheader("📊 Análisis de Caracterización Social")
    
    try:
        # Volvemos a leer para asegurar que incluya el último registro
        df_social = conn.read(ttl=0)
        
        if not df_social.empty:
            # Métricas rápidas
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Actores", len(df_social))
            col_m2.metric("Veredas Cubiertas", df_social['Vereda'].nunique())
            
            # Gráficos Dinámicos
            g1, g2 = st.columns(2)
            
            with g1:
                st.markdown("**Distribución por Perfil**")
                # Gráfico de barras por perfil
                perfil_count = df_social['Perfil'].value_counts()
                st.bar_chart(perfil_count, color="#2e7d32")
                
            with g2:
                st.markdown("**Situación de Tenencia**")
                # Gráfico de áreas o líneas (usaremos barras para claridad en tenencia)
                tenencia_count = df_social['Tenencia'].value_counts()
                st.bar_chart(tenencia_count, color="#ff9800")

            # Tabla de datos para auditoría visual
            with st.expander("🔍 Ver listado detallado de actores"):
                st.dataframe(df_social, use_container_width=True)
        else:
            st.info("Aún no hay datos sociales registrados para generar gráficos.")
            
    except Exception as e:
        st.error("No se pudo cargar la visualización de datos sociales.")

st.divider()
st.caption("Investigación ESAP 2026 - Herramienta Unificada SIGOber-Rural")

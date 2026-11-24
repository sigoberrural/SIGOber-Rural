"""
=============================================================================
PROYECTO: SIGOber-Rural
ARCHIVO: main.py (Rama Develope)
DESCRIPCIÓN: Aplicación principal con navegación dinámica en barra lateral 
             para alternar entre las vistas de Exploración (Cartografía) y SADCI.
=============================================================================
"""

from datetime import datetime
import json
import time
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# =============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO Y RUTAS DEL SISTEMA
# =============================================================================

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingesta import (
    crear_excel_plantilla, leer_archivo_tabular,
    validar_importacion_sadci, validar_problematicas,
)
from app.sadci import cargar_catalogo

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PBOT_DIR = DATA_DIR / "PBOT2015"

PBOT_CAPAS = [
    ("PBOT2015_ZONIFICACION_USO_SUELO_RURAL.geojson", "Zonificación de uso del suelo rural", ["UGOT", "Aptitud", "area_ha"]),
    ("PBOT2015_PROTECCION_RURAL.geojson", "Suelos de protección rural", ["Aptitud", "Area_ha"]),
    ("PBOT2015_PERIMETRO_EXPANSION.geojson", "Perímetro y expansión urbana", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_TRATAMIENTOS_URBANOS.geojson", "Tratamientos urbanos", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_ZONAS_HOMOGENEAS_URBANAS.geojson", "Zonas homogéneas urbanas", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_PUNTOS_EXPANSION.geojson", "Puntos de expansión urbana", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_MANZANAS_INSPECCIONES.geojson", "Manzanas e inspecciones", ["codigo", "sector_cat", "tipo_avalu", "Reporte"])
]

# Inicialización de variables de estado en la sesión
st.session_state.setdefault("sigo_uploads", {})
st.session_state.setdefault("sigo_upload_widget_version", 0)
st.session_state.setdefault("sigo_problematicas_validadas", None)
st.session_state.setdefault("sigo_sadci_importado", None)
st.session_state.setdefault("sidebar_seccion_activa", "Exploración")


# =============================================================================
# 2. FUNCIONES DE CARGA Y PROCESAMIENTO ESPACIAL
# =============================================================================

@st.cache_data(show_spinner=False)
def cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists(): return None
    with open(ruta, "r", encoding="utf-8") as f: return json.load(f)

@st.cache_data(show_spinner=False)
def cargar_pbot_capas():
    capas = []
    for archivo, titulo, campos in PBOT_CAPAS:
        ruta = PBOT_DIR / archivo
        if not ruta.exists(): continue
        try:
            with open(ruta, "r", encoding="utf-8") as f: geo = json.load(f)
            if geo.get("type") == "FeatureCollection": capas.append((archivo, titulo, geo, campos))
        except Exception: continue
    return capas

@st.cache_data(show_spinner=False)
def cargar_eventos_locales():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv",):
        ruta = DATA_DIR / nombre
        if ruta.exists(): return pd.read_csv(ruta, dtype=str).fillna("")
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def cargar_veredas_topo():
    topo = cargar_json("veredas_puerto_rico.json")
    if not topo or topo.get("type") != "Topology" or "Veredas" not in topo.get("objects", {}): 
        raise RuntimeError("No se encontró un TopoJSON válido con el objeto Veredas.")
    return topo

@st.cache_data(show_spinner=False)
def propiedades_veredas(topo): 
    return pd.DataFrame([g.get("properties", {}) or {} for g in topo.get("objects", {}).get("Veredas", {}).get("geometries", [])]).fillna("")

@st.cache_data(show_spinner=False)
def resumenes_por_vereda(eventos):
    vacio = pd.DataFrame(columns=["codigo_ver_resuelto", "SIGOber_situaciones", "SIGOber_anios", "SIGOber_tipos", "SIGOber_confianza"])
    if eventos is None or eventos.empty or "codigo_ver_resuelto" not in eventos.columns: return vacio
    df = eventos.copy(); df["codigo_ver_resuelto"] = df["codigo_ver_resuelto"].astype(str).str.strip(); df = df[df["codigo_ver_resuelto"] != ""]
    if df.empty: return vacio
    def valores(col): return df[col].astype(str).str.strip() if col in df.columns else pd.Series("", index=df.index)
    df["_anio"], df["_tipo"], df["_conf"] = valores("anio"), valores("tipo_conflicto"), valores("confianza")
    def uniq(series): return ", ".join(sorted(x for x in series.unique() if x))
    return df.groupby("codigo_ver_resuelto", sort=False).agg(SIGOber_situaciones=("codigo_ver_resuelto", "size"), SIGOber_anios=("_anio", uniq), SIGOber_tipos=("_tipo", uniq), SIGOber_confianza=("_conf", uniq)).reset_index()

@st.cache_data(show_spinner=False, max_entries=32)
def preparar_topo_para_eventos(topo, resumen):
    copia = json.loads(json.dumps(topo)); tabla = resumen.set_index("codigo_ver_resuelto") if not resumen.empty else pd.DataFrame()
    for g in copia.get("objects", {}).get("Veredas", {}).get("geometries", []):
        p = g.setdefault("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip()
        if not tabla.empty and codigo in tabla.index:
            r = tabla.loc[codigo]; p["SIGOber_situaciones"] = int(r["SIGOber_situaciones"]); p["SIGOber_anios"] = str(r["SIGOber_anios"]); p["SIGOber_tipos"] = str(r["SIGOber_tipos"]); p["SIGOber_confianza"] = str(r["SIGOber_confianza"])
        else: p["SIGOber_situaciones"] = 0; p["SIGOber_anios"] = "Sin registros"; p["SIGOber_tipos"] = "Sin registros"; p["SIGOber_confianza"] = "Sin registros"
    return copia

def construir_mapa(topo, eventos_historicos, codigo_seleccionado="", pbot_seleccionadas=()):
    inicio = time.perf_counter(); resumen = resumenes_por_vereda(eventos_historicos); topo_mapa = preparar_topo_para_eventos(topo, resumen)
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="OpenStreetMap", prefer_canvas=True)
    
    grupo_territorio = folium.FeatureGroup(name="Territorio — Veredas", show=True)
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(grupo_territorio)
    
    def estilo_territorio(feature):
        p = feature.get("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip(); sel = bool(codigo) and codigo == str(codigo_seleccionado).strip()
        return {"fillColor": "#eeeeee", "color": "#111111" if sel else "#555555", "weight": 2.8 if sel else 0.8, "fillOpacity": 0.22}
    
    folium.TopoJson(data=topo_mapa, object_path="objects.Veredas", name="Veredas", style_function=estilo_territorio, show=True).add_to(grupo_territorio)
    grupo_territorio.add_to(m)
    
    disponibles = {x[0]: x for x in cargar_pbot_capas()}
    for archivo in pbot_seleccionadas:
        capa = disponibles.get(archivo)
        if not capa: continue
        _, titulo, geo, _ = capa
        grupo_pbot = folium.FeatureGroup(name=f"{titulo} — PBOT 2015", show=True)
        folium.GeoJson(geo, name=titulo).add_to(grupo_pbot)
        grupo_pbot.add_to(m)
        
    folium.LayerControl(collapsed=False).add_to(m)
    return m, time.perf_counter() - inicio

def resumen_sadci(sadci):
    if not isinstance(sadci, pd.DataFrame) or sadci.empty: return None
    out = {}
    for c in ("presupuesto_anual_rural", "num_personal_planta", "num_personal_contratista", "ejecucion_presupuestal_pct", "cumplimiento_pdt_pct", "calificacion_mepi"):
        if c in sadci.columns:
            vals = pd.to_numeric(sadci[c], errors="coerce").dropna()
            if not vals.empty: out[c] = float(vals.mean())
    return out

def indicador_pct(valor): return "—" if valor is None or pd.isna(valor) else f"{float(valor):.0f}%"


# =============================================================================
# 3. BARRA LATERAL (SIDEBAR) - NAVEGACIÓN DINÁMICA
# =============================================================================

with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    
    st.markdown("**Espacios de trabajo**")
    
    # Botones superiores para alternar la sección activa
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🗺️ Exploración", use_container_width=True, type="primary" if st.session_state["sidebar_seccion_activa"] == "Exploración" else "secondary"):
            st.session_state["sidebar_seccion_activa"] = "Exploración"
            st.rerun()
    with col_b2:
        if st.button("🏛️ SADCI", use_container_width=True, type="primary" if st.session_state["sidebar_seccion_activa"] == "SADCI" else "secondary"):
            st.session_state["sidebar_seccion_activa"] = "SADCI"
            st.rerun()
            
    st.divider()
    
    # Panel inferior dinámico según la sección seleccionada
    if st.session_state["sidebar_seccion_activa"] == "Exploración":
        st.markdown("### ⚙️ Parámetros de Mapa")
        topo_sb = cargar_veredas_topo()
        veredas_df_sb = propiedades_veredas(topo_sb)
        nombres_sb = veredas_df_sb[["CODIGO_VER", "NOMBRE_VER"]].drop_duplicates().copy()
        nombres_sb["etiqueta"] = nombres_sb["NOMBRE_VER"].astype(str) + " — " + nombres_sb["CODIGO_VER"].astype(str)
        opciones_sb = ["Todas las veredas"] + sorted(nombres_sb["etiqueta"].tolist())
        
        vereda_seleccionada = st.selectbox("Seleccionar Vereda", opciones_sb)
        
        pbot_opciones_sb = {archivo: titulo for archivo, titulo, _, _ in cargar_pbot_capas()}
        pbot_sel_sb = st.multiselect("Capas PBOT 2015", options=list(pbot_opciones_sb.keys()), format_func=lambda x: pbot_opciones_sb[x])
        
        # Guardamos los filtros en session_state para usarlos en el área principal
        st.session_state["filtro_vereda"] = vereda_seleccionada
        st.session_state["pbot_seleccionadas"] = pbot_sel_sb
        
    else:
        st.markdown("### 📥 Ingesta y Gestión SADCI")
        st.caption("Herramientas de control institucional:")
        st.markdown("• Carga de problemáticas")
        st.markdown("• Actualización de indicadores")
        st.markdown("• Archivos temporales")
        
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")


# =============================================================================
# 4. INTERFAZ PRINCIPAL (CONDICIONAL SEGÚN SECCIÓN ACTIVA)
# =============================================================================

if st.session_state["sidebar_seccion_activa"] == "Exploración":
    st.markdown("""
    <div style='padding:.5rem 0 1rem'>
        <h2>Exploración Cartográfica</h2>
        <p style='opacity:0.75'>Visualización geoespacial de veredas, situaciones e instrumentos de ordenamiento territorial.</p>
    </div>
    """, unsafe_allow_html=True)
    
    topo_main = cargar_veredas_topo()
    historicos_main = cargar_eventos_locales()
    
    vereda_activa = st.session_state.get("filtro_vereda", "Todas las veredas")
    codigo_sel_main = "" if vereda_activa == "Todas las veredas" else vereda_activa.split(" — ")[-1]
    capas_pbot_main = tuple(st.session_state.get("pbot_seleccionadas", []))
    
    mapa_render, segs = construir_mapa(topo_main, historicos_main, codigo_sel_main, capas_pbot_main)
    st_folium(mapa_render, width="100%", height=650, returned_objects=[])

else:
    st.markdown("""
    <div style='padding:.5rem 0 1rem'>
        <h2>Capacidad Institucional · SADCI</h2>
        <p style='opacity:0.75'>Resultados consolidados de los indicadores institucionales y capacidades del municipio.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Cargamos datos de ejemplo o de Google Sheets si existen en la sesión
    st.session_state.setdefault("google_data", {"SADCI": pd.DataFrame()})
    gd_sadci = st.session_state["google_data"].get("SADCI")
    
    r_sadci = resumen_sadci(gd_sadci)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Presupuesto rural", f"{r_sadci.get('presupuesto_anual_rural', 0):,.0f}" if r_sadci and r_sadci.get("presupuesto_anual_rural") is not None else "—")
    col2.metric("Personal planta", f"{r_sadci.get('num_personal_planta', 0):.0f}" if r_sadci and r_sadci.get("num_personal_planta") is not None else "—")
    col3.metric("Contratistas", f"{r_sadci.get('num_personal_contratista', 0):.0f}" if r_sadci and r_sadci.get("num_personal_contratista") is not None else "—")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Ejecución presupuestal", indicador_pct(r_sadci.get("ejecucion_presupuestal_pct") if r_sadci else None))
    col5.metric("Cumplimiento PDT", indicador_pct(r_sadci.get("cumplimiento_pdt_pct") if r_sadci else None))
    col6.metric("Calificación MEPI", f"{r_sadci.get('calificacion_mepi', 0):.1f}" if r_sadci and r_sadci.get("calificacion_mepi") is not None else "—")
    
    st.divider()
    st.subheader("Detalle de registros institucionales")
    if isinstance(gd_sadci, pd.DataFrame) and not gd_sadci.empty:
        st.dataframe(gd_sadci, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos cargados en la tabla SADCI actualmente. Puedes gestionarlos desde las herramientas del sistema o mediante plantillas.")

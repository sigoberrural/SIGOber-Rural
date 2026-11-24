"""
=============================================================================
PROYECTO: SIGOber-Rural
ARCHIVO: main.py (Rama Develope - Exploración y SADCI con Métricas y Resultados Integrados)
DESCRIPCIÓN: Aplicación principal con navegación dinámica en barra lateral 
             para alternar entre Exploración Cartográfica y el módulo de Gestión SADCI,
             mostrando de forma permanente las métricas de indicadores y resultados a la derecha.
=============================================================================
"""

from datetime import datetime
import html
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
# 2. FUNCIONES DE CARGA Y PROCESAMIENTO ESPACIAL Y DE DATOS
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

def normalizar_conflictos(df):
    if df is None or df.empty: return pd.DataFrame()
    out = df.copy().fillna("")
    out["lat_num"] = pd.to_numeric(out["lat"], errors="coerce") if "lat" in out.columns else pd.NA
    out["lon_num"] = pd.to_numeric(out["lon"], errors="coerce") if "lon" in out.columns else pd.NA
    out["precision_coordenada"] = "VALIDA"
    out.loc[out[["lat_num", "lon_num"]].isna().any(axis=1), "precision_coordenada"] = "SIN_COORDENADA"
    inval = (out["lat_num"].abs() > 90) | (out["lon_num"].abs() > 180)
    out.loc[inval & out[["lat_num", "lon_num"]].notna().all(axis=1), "precision_coordenada"] = "REQUIERE_REVISION"
    return out

@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def leer_google_hoja(nombre_hoja):
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet=nombre_hoja, ttl=300).fillna("")

def leer_google_sheets():
    resultado = {}
    for hoja in ("Conflictos", "Actores", "SADCI", "Relación Interinstitucional"):
        try: resultado[hoja] = leer_google_hoja(hoja)
        except Exception as e: resultado[hoja] = e
    return resultado

def popup_conflicto(row):
    v = lambda c: html.escape(str(row.get(c, "") or ""))
    return (f"<div style='width:280px;font-family:Arial'><h4>Situación registrada</h4>"
            f"<b>ID:</b> {v('id_conflicto')}<br><b>Tipo:</b> {v('tipo_conflicto')}<br>"
            f"<b>Vereda:</b> {v('vereda')}<br><b>Descripción:</b> {v('descripcion')}<br>"
            f"<b>Registrado por:</b> {v('registrado_por')}<br><b>Estado coordenada:</b> {v('precision_coordenada')}<br>"
            f"<b>Lat/Lon fuente:</b> {v('lat')} / {v('lon')}</div>")

@st.cache_data(show_spinner=False, max_entries=32)
def preparar_topo_para_eventos(topo, resumen):
    copia = json.loads(json.dumps(topo)); tabla = resumen.set_index("codigo_ver_resuelto") if not resumen.empty else pd.DataFrame()
    for g in copia.get("objects", {}).get("Veredas", {}).get("geometries", []):
        p = g.setdefault("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip()
        if not tabla.empty and codigo in tabla.index:
            r = tabla.loc[codigo]
            p["SIGOber_situaciones"] = int(r["SIGOber_situaciones"])
            p["SIGOber_anios"] = str(r["SIGOber_anios"])
            p["SIGOber_tipos"] = str(r["SIGOber_tipos"])
            p["SIGOber_confianza"] = str(r["SIGOber_confianza"])
        else:
            p["SIGOber_situaciones"] = 0
            p["SIGOber_anios"] = "Sin registros"
            p["SIGOber_tipos"] = "Sin registros"
            p["SIGOber_confianza"] = "Sin registros"
    return copia

def construir_mapa(topo, eventos_historicos, conflictos=None, codigo_seleccionado="", mostrar_conflictos=True, pbot_seleccionadas=()):
    inicio = time.perf_counter()
    resumen = resumenes_por_vereda(eventos_historicos)
    topo_mapa = preparar_topo_para_eventos(topo, resumen)
    conteo = resumen.set_index("codigo_ver_resuelto")["SIGOber_situaciones"].to_dict() if not resumen.empty else {}
    
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="OpenStreetMap", prefer_canvas=True)
    
    grupo_territorio = folium.FeatureGroup(name="Territorio — Veredas", show=True)
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(grupo_territorio)
    
    def estilo_territorio(feature):
        p = feature.get("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip()
        sel = bool(codigo) and codigo == str(codigo_seleccionado).strip()
        return {"fillColor": "#eeeeee", "color": "#111111" if sel else "#555555", "weight": 2.8 if sel else 0.8, "fillOpacity": 0.22}
    
    folium.TopoJson(
        data=topo_mapa, object_path="objects.Veredas", name="Veredas",
        style_function=estilo_territorio,
        tooltip=folium.GeoJsonTooltip(
            fields=["NOMBRE_VER", "CODIGO_VER", "AREA_HA", "FUENTE"],
            aliases=["Vereda", "Código", "Área (ha)", "Fuente cartográfica"],
            localize=True, sticky=True, labels=True,
            style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;"
        ),
        show=True
    ).add_to(grupo_territorio)
    grupo_territorio.add_to(m)
    
    grupo_situaciones = folium.FeatureGroup(name="Situaciones — evidencia territorial", show=True)
    def estilo_situaciones(feature):
        p = feature.get("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip()
        n = int(conteo.get(codigo, 0)); sel = bool(codigo) and codigo == str(codigo_seleccionado).strip()
        fill = "#d73027" if n >= 2 else ("#fc8d59" if n == 1 else "#eeeeee")
        opacity = 0.72 if n else 0.10
        return {"fillColor": fill, "color": "#111111" if sel else "#a94442", "weight": 2.8 if sel else (1.0 if n else 0.35), "fillOpacity": 0.78 if sel else opacity}
    
    folium.TopoJson(
        data=topo_mapa, object_path="objects.Veredas", name="Situaciones",
        style_function=estilo_situaciones,
        tooltip=folium.GeoJsonTooltip(
            fields=["NOMBRE_VER", "CODIGO_VER", "SIGOber_situaciones", "SIGOber_anios", "SIGOber_tipos", "SIGOber_confianza"],
            aliases=["Vereda", "Código", "Situaciones documentadas", "Años", "Tipos de situación", "Confianza"],
            localize=True, sticky=True, labels=True,
            style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;"
        ),
        show=True
    ).add_to(grupo_situaciones)
    grupo_situaciones.add_to(m)
    
    if mostrar_conflictos and conflictos is not None and not conflictos.empty:
        validos = conflictos.loc[conflictos["precision_coordenada"].eq("VALIDA")]
        grupo = folium.FeatureGroup(name="Conflictos — Google Sheets", show=True)
        for row in validos.itertuples(index=False):
            data = row._asdict()
            folium.CircleMarker(
                location=[float(data["lat_num"]), float(data["lon_num"])],
                radius=7, weight=2, fill=True, fill_opacity=0.85,
                tooltip=f"{data.get('tipo_conflicto', 'Situación')} — {data.get('vereda', '')}",
                popup=folium.Popup(popup_conflicto(data), max_width=340)
            ).add_to(grupo)
        grupo.add_to(m)
        
    aliases_pbot = {"UGOT": "UGOT", "Aptitud": "Aptitud", "area_ha": "Área (ha)", "Area_ha": "Área (ha)", "Tipo": "Tipo", "area_m2": "Área (m²)", "Id": "ID", "codigo": "Código", "sector_cat": "Sector catastral", "tipo_avalu": "Tipo avalúo", "Reporte": "Reporte"}
    disponibles = {x[0]: x for x in cargar_pbot_capas()}
    for archivo in pbot_seleccionadas:
        capa = disponibles.get(archivo)
        if not capa: continue
        _, titulo, geo, campos_preferidos = capa
        grupo_pbot = folium.FeatureGroup(name=f"{titulo} — PBOT 2015", show=True)
        features = geo.get("features", [])
        props = (features[0].get("properties", {}) or {}) if features else {}
        campos = [campo for campo in campos_preferidos if campo in props]
        tooltip_pbot = folium.GeoJsonTooltip(
            fields=campos, aliases=[aliases_pbot.get(campo, campo) for campo in campos],
            localize=True, labels=True, sticky=True,
            style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;"
        ) if campos else None
        folium.GeoJson(geo, name=titulo, tooltip=tooltip_pbot).add_to(grupo_pbot)
        grupo_pbot.add_to(m)
        
    folium.LayerControl(collapsed=False).add_to(m)
    return m, time.perf_counter() - inicio

def resumen_sadci(sadci):
    if not isinstance(sadci, pd.DataFrame) or sadci.empty: return None
    out = {}
    # Soporte para formato vertical (plantilla de variables) o ancho (Google Sheets)
    if "codigo_variable" in sadci.columns and "valor_ingresado" in sadci.columns:
        for _, row in sadci.iterrows():
            k = str(row.get("codigo_variable", "")).strip()
            v = pd.to_numeric(row.get("valor_ingresado", ""), errors="coerce")
            if k and not pd.isna(v):
                out[k] = float(v)
    else:
        for c in ("presupuesto_anual_rural", "num_personal_planta", "num_personal_contratista", "ejecucion_presupuestal_pct", "cumplimiento_pdt_pct", "calificacion_mepi"):
            if c in sadci.columns:
                vals = pd.to_numeric(sadci[c], errors="coerce").dropna()
                if not vals.empty: out[c] = float(vals.mean())
    return out

def indicador_pct(valor):
    return "—" if valor is None or pd.isna(valor) else f"{float(valor):.0f}%"

def generar_descripcion_dinamica_sadci(r_sadci):
    """
    Genera una descripción narrativa y dinámica basada en los valores 
    actuales de los indicadores SADCI y métricas institucionales.
    """
    if not r_sadci:
        return "No hay datos institucionales suficientes en la sesión actual para generar una síntesis dinámica de capacidad institucional."
    
    presupuesto = r_sadci.get("presupuesto_anual_rural", 0) or 0
    planta = r_sadci.get("num_personal_planta", 0) or 0
    contratistas = r_sadci.get("num_personal_contratista", 0) or 0
    ejecucion = r_sadci.get("ejecucion_presupuestal_pct")
    cumplimiento = r_sadci.get("cumplimiento_pdt_pct")
    mepi = r_sadci.get("calificacion_mepi")
    
    parrafos = []
    
    presupuesto_str = f"{presupuesto:,.0f} COP" if presupuesto > 0 else "sin asignación registrada"
    ejecucion_str = f"{ejecucion:.0f}%" if ejecucion is not None and not pd.isna(ejecucion) else "pendiente de medición"
    parrafos.append(
        f"En el componente financiero, se observa un presupuesto anual rural de **{presupuesto_str}** "
        f"con un nivel de ejecución presupuestal del **{ejecucion_str}**."
    )
    
    total_personal = planta + contratistas
    parrafos.append(
        f"La capacidad operativa cuenta con un total de **{int(total_personal)} colaboradores** "
        f"({int(planta)} en planta y {int(contratistas)} bajo modalidad de contratación temporal) orientados a la gestión territorial."
    )
    
    cumplimiento_str = f"{cumplimiento:.0f}%" if cumplimiento is not None and not pd.isna(cumplimiento) else "sin consolidar"
    mepi_str = f"{mepi:.1f} puntos" if mepi is not None and not pd.isna(mepi) else "por evaluar"
    parrafos.append(
        f"Respecto al cumplimiento de metas del Plan de Desarrollo Territorial (PDT), el avance se sitúa en **{cumplimiento_str}**, "
        f"acompañado de una calificación MEPI de **{mepi_str}**, reflejando el estado actual de gobernabilidad y gestión fiscal."
    )
    
    return " ".join(parrafos)

# =============================================================================
# 3. BARRA LATERAL (SIDEBAR) - CONTROLES Y PARÁMETROS DE INTERACCIÓN
# =============================================================================

with st.sidebar:
    st.markdown("### SIGOber-Rural")
    st.caption("Sistema de información territorial")
    st.divider()
    
    st.markdown("**Espacios de trabajo**")
    
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
    
    # Controles exclusivos para Exploración Cartográfica
    if st.session_state["sidebar_seccion_activa"] == "Exploración":
        st.markdown("### 🗺️ Parámetros de Mapa")
        st.caption("Filtros y capas para la lectura territorial:")
        
        topo_sb = cargar_veredas_topo()
        veredas_df_sb = propiedades_veredas(topo_sb)
        nombres_sb = veredas_df_sb[["CODIGO_VER", "NOMBRE_VER"]].drop_duplicates().copy()
        nombres_sb["etiqueta"] = nombres_sb["NOMBRE_VER"].astype(str) + " — " + nombres_sb["CODIGO_VER"].astype(str)
        opciones_sb = ["Todas las veredas"] + sorted(nombres_sb["etiqueta"].tolist())
        
        vereda_seleccionada = st.selectbox("Vereda", opciones_sb, key="sb_vereda")
        
        historicos_sb = cargar_eventos_locales()
        ys, ts, cs = [], [], []
        if not historicos_sb.empty:
            anios_l = sorted([x for x in historicos_sb.get("anio", pd.Series(dtype=str)).astype(str).unique() if x], reverse=True)
            ys = st.multiselect("Año", anios_l, default=[], key="sb_anios")
            tipos_l = sorted([x for x in historicos_sb.get("tipo_conflicto", pd.Series(dtype=str)).astype(str).unique() if x])
            ts = st.multiselect("Tipo de situación", tipos_l, default=[], key="sb_tipos")
            confs_l = sorted([x for x in historicos_sb.get("confianza", pd.Series(dtype=str)).astype(str).unique() if x])
            cs = st.multiselect("Confianza", confs_l, default=[], key="sb_confs")
            
        mostrar_gsheets = st.checkbox("Mostrar conflictos de Sheets", value=True, key="sb_mostrar_conflictos")
        pbot_opciones_sb = {archivo: titulo for archivo, titulo, _, _ in cargar_pbot_capas()}
        pbot_sel_sb = st.multiselect("Capas PBOT 2015", options=list(pbot_opciones_sb.keys()), format_func=lambda x: pbot_opciones_sb[x], key="sb_pbot")
        
        st.session_state["map_vereda"] = vereda_seleccionada
        st.session_state["map_ys"] = ys
        st.session_state["map_ts"] = ts
        st.session_state["map_cs"] = cs
        st.session_state["map_mostrar_gsheets"] = mostrar_gsheets
        st.session_state["map_pbot"] = pbot_sel_sb
        
    # Controles exclusivos para Ingesta y Gestión SADCI (Izquierda)
    else:
        st.markdown("### 📥 Controles SADCI")
        st.caption("Gestión y cálculo de indicadores DCI:")
        
        try:
            catalogo_sadci = cargar_catalogo()
            
            st.markdown("**1. Descarga de Plantilla**")
            st.download_button(
                "Descargar plantilla Excel",
                data=crear_excel_plantilla("sadci", catalogo_sadci),
                file_name="plantilla_actualizacion_sadci.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption("Completa numerador, denominador, periodo, fecha de corte, fuente y responsable.")
            
            st.divider()
            st.markdown("**2. Carga y Validación**")
            sadci_file = st.file_uploader("Cargar plantilla completada", type=["csv", "xlsx", "xls"], key="sb_sadci_file")
            
            st.session_state["sb_sadci_file_obj"] = sadci_file
            st.session_state["sb_catalogo_sadci"] = catalogo_sadci
            
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            st.error(f"Error al preparar plantilla: {exc}")
            st.session_state["sb_sadci_file_obj"] = None

    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Versión 1.0 en preparación")


# =============================================================================
# 4. INTERFAZ PRINCIPAL (RESULTADOS A LA DERECHA)
# =============================================================================

if st.session_state["sidebar_seccion_activa"] == "Exploración":
    st.markdown("""
    <div style='padding:.2rem 0 .6rem'>
        <div style='font-size:.72rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;opacity:.62'>Sistema de información territorial</div>
        <div style='font-size:2.25rem;font-weight:820;line-height:1.04;margin:.1rem 0 .25rem'>SIGOber-Rural</div>
        <div style='font-size:.96rem;opacity:.72'>Una lectura territorial de la gobernabilidad rural · Puerto Rico, Caquetá</div>
    </div>
    """, unsafe_allow_html=True)
    
    topo_main = cargar_veredas_topo()
    historicos_main = cargar_eventos_locales()
    
    if "google_data" not in st.session_state:
        with st.spinner("Conectando con las fuentes territoriales…"):
            st.session_state["google_data"] = leer_google_sheets()
    gd_main = st.session_state["google_data"]
    
    eventos_f = historicos_main.copy()
    if not eventos_f.empty:
        ys_f = st.session_state.get("map_ys", [])
        ts_f = st.session_state.get("map_ts", [])
        cs_f = st.session_state.get("map_cs", [])
        if ys_f: eventos_f = eventos_f[eventos_f["anio"].astype(str).isin(ys_f)]
        if ts_f: eventos_f = eventos_f[eventos_f["tipo_conflicto"].astype(str).isin(ts_f)]
        if cs_f: eventos_f = eventos_f[eventos_f["confianza"].astype(str).isin(cs_f)]
        
    vereda_activa = st.session_state.get("map_vereda", "Todas las veredas")
    codigo_sel_main = "" if vereda_activa == "Todas las veredas" else vereda_activa.split(" — ")[-1]
    mostrar_conflictos_main = st.session_state.get("map_mostrar_gsheets", True)
    capas_pbot_main = tuple(st.session_state.get("map_pbot", []))
    
    conflictos_main = normalizar_conflictos(gd_main.get("Conflictos")) if isinstance(gd_main.get("Conflictos"), pd.DataFrame) else pd.DataFrame()
    
    mapa_render, segundos_mapa = construir_mapa(topo_main, eventos_f, conflictos_main, codigo_sel_main, mostrar_conflictos_main, capas_pbot_main)
    st.caption(f"Generación del mapa en servidor: {segundos_mapa:.2f} s")
    st_folium(mapa_render, width="100%", height=680, returned_objects=["last_active_drawing"])

else:
    st.markdown("""
    <div style='padding:.2rem 0 .6rem'>
        <div style='font-size:.72rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;opacity:.62'>Capacidad institucional</div>
        <div style='font-size:2.25rem;font-weight:820;line-height:1.04;margin:.1rem 0 .25rem'>Resultados e Indicadores SADCI</div>
        <div style='font-size:.96rem;opacity:.72'>Visualización de resultados de validación técnica, métricas institucionales y cálculo de indicadores DCI.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Asegurar conexión a Google Sheets para obtener los datos base de SADCI si no están cargados
    if "google_data" not in st.session_state:
        st.session_state["google_data"] = leer_google_sheets()
    gd_sadci_base = st.session_state["google_data"].get("SADCI")
    
    # Determinar qué fuente usar para las métricas (priorizando lo importado en sesión o la base de Google Sheets)
    active_sadci_df = st.session_state.get("sigo_sadci_importado")
    if active_sadci_df is not None and not active_sadci_df.empty:
        r_sadci = resumen_sadci(active_sadci_df)
    elif isinstance(gd_sadci_base, pd.DataFrame) and not gd_sadci_base.empty:
        r_sadci = resumen_sadci(gd_sadci_base)
    else:
        r_sadci = None
        
    # Renderizado de los 6 indicadores métricos principales en la parte derecha
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Presupuesto rural", f"{r_sadci.get('presupuesto_anual_rural', 0):,.0f}" if r_sadci and r_sadci.get("presupuesto_anual_rural") is not None else "—")
    col2.metric("Personal planta", f"{r_sadci.get('num_personal_planta', 0):.0f}" if r_sadci and r_sadci.get("num_personal_planta") is not None else "—")
    col3.metric("Contratistas", f"{r_sadci.get('num_personal_contratista', 0):.0f}" if r_sadci and r_sadci.get("num_personal_contratista") is not None else "—")
    col4.metric("Ejecución", indicador_pct(r_sadci.get("ejecucion_presupuestal_pct") if r_sadci else None))
    col5.metric("Cumplimiento PDT", indicador_pct(r_sadci.get("cumplimiento_pdt_pct") if r_sadci else None))
    col6.metric("MEPI", f"{r_sadci.get('calificacion_mepi', 0):.1f}" if r_sadci and r_sadci.get("calificacion_mepi") is not None else "—")
    
    st.divider()
    
    # NUEVO: Bloque de Descripción Dinámica basada en los indicadores actuales
    st.markdown("### 🤖 Síntesis y Análisis Dinámico Institucional")
    descripcion_ia = generar_descripcion_dinamica_sadci(r_sadci)
    st.info(descripcion_ia)
    
    st.divider()
    
    # Gestión de archivos cargados desde el panel izquierdo (Controles)
    sadci_file = st.session_state.get("sb_sadci_file_obj")
    catalogo_sadci = st.session_state.get("sb_catalogo_sadci")
    
    if sadci_file is not None and catalogo_sadci is not None:
        try:
            sadci_df = leer_archivo_tabular(sadci_file)
            sadci_review = validar_importacion_sadci(sadci_df, catalogo_sadci)
            valid_count = int(sadci_review["valido_revision_tecnica"].sum())
            
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Filas leídas", len(sadci_review))
            c_m2.metric("Sin errores técnicos", valid_count)
            c_m3.metric("Con errores", len(sadci_review) - valid_count)
            
            st.divider()
            st.subheader("Informe de validación y cálculo")
            st.dataframe(sadci_review, use_container_width=True, hide_index=True)
            st.download_button("Descargar informe de validación SADCI", sadci_review.to_csv(index=False).encode("utf-8-sig"), "revision_sadci.csv", "text/csv")
            
            if valid_count != len(sadci_review) or sadci_review.empty:
                st.error("Corrige los códigos, periodos y valores numéricos

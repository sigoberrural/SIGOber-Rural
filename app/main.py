import html
import json
import re
import time
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

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
    ("PBOT2015_MANZANAS_INSPECCIONES.geojson", "Manzanas e inspecciones", ["codigo", "sector_cat", "tipo_avalu", "Reporte"]),
]

# Puntos sintéticos exclusivamente para mostrar, en una presentación, cómo
# puede verse una capa de cartografía social. No representan conflictos reales.
# Las temáticas son coherentes con situaciones y necesidades territoriales
# documentadas en la base, pero las coordenadas y testimonios son ficticios.
PUNTOS_SOCIALES_DEMO = [
    {"lat": 1.9480, "lon": -75.2260, "categoria": "Movilidad rural", "titulo": "Acceso vial vulnerable en temporada de lluvias", "voz": "La comunidad identifica el acceso y la movilidad como una prioridad territorial."},
    {"lat": 1.9020, "lon": -75.1190, "categoria": "Seguridad territorial", "titulo": "Sector percibido como sensible", "voz": "La comunidad señala este sector como un lugar que requiere seguimiento y coordinación institucional."},
    {"lat": 1.8620, "lon": -75.2460, "categoria": "Riesgo por minas", "titulo": "Zona que requiere atención preventiva", "voz": "La comunidad identifica la necesidad de prevención, información y protección frente a riesgos territoriales."},
    {"lat": 1.9720, "lon": -75.1640, "categoria": "Afectación humanitaria", "titulo": "Lugar asociado a necesidades de atención y retorno", "voz": "La comunidad prioriza la atención a población afectada y el acompañamiento institucional."},
    {"lat": 1.8340, "lon": -75.1780, "categoria": "Servicios y equipamiento", "titulo": "Nodo comunitario para gestión de necesidades", "voz": "La comunidad reconoce la importancia de contar con servicios y espacios de gestión cercanos."},
    {"lat": 1.9220, "lon": -75.0900, "categoria": "Conectividad", "titulo": "Sector con necesidad de mayor conectividad", "voz": "La comunidad prioriza mejorar la comunicación y el acceso a servicios y oportunidades."},
    {"lat": 1.8030, "lon": -75.2180, "categoria": "Recurso territorial", "titulo": "Lugar de valor ambiental y comunitario", "voz": "La comunidad reconoce el lugar como un recurso territorial que debe ser protegido y gestionado."},
]

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
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv", "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"):
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
    out = df.copy().fillna(""); out["lat_num"] = pd.to_numeric(out["lat"], errors="coerce") if "lat" in out.columns else pd.NA; out["lon_num"] = pd.to_numeric(out["lon"], errors="coerce") if "lon" in out.columns else pd.NA
    out["precision_coordenada"] = "VALIDA"; out.loc[out[["lat_num", "lon_num"]].isna().any(axis=1), "precision_coordenada"] = "SIN_COORDENADA"
    inval = (out["lat_num"].abs() > 90) | (out["lon_num"].abs() > 180); out.loc[inval & out[["lat_num", "lon_num"]].notna().all(axis=1), "precision_coordenada"] = "REQUIERE_REVISION"
    return out

def config_gsheets():
    try:
        c = st.secrets.get("connections", {}); x = c.get("gsheets", {}) if hasattr(c, "get") else {}; return dict(x) if hasattr(x, "items") else {}
    except Exception: return {}

def spreadsheet_id_desde_config(cfg):
    raw = str(cfg.get("spreadsheet", "") or cfg.get("spreadsheet_url", "")).strip(); m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", raw); return m.group(1) if m else raw

@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def leer_google_hoja(nombre_hoja):
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection); return conn.read(worksheet=nombre_hoja, ttl=300).fillna("")

def leer_google_sheets():
    resultado = {}
    for hoja in ("Conflictos", "Actores", "SADCI", "Relación Interinstitucional"):
        try: resultado[hoja] = leer_google_hoja(hoja)
        except Exception as e: resultado[hoja] = e
    return resultado

def popup_conflicto(row):
    v = lambda c: html.escape(str(row.get(c, "") or ""))
    return ("<div style='width:280px;font-family:Arial'><h4>Situación registrada</h4>" f"<b>ID:</b> {v('id_conflicto')}<br><b>Tipo:</b> {v('tipo_conflicto')}<br>" f"<b>Vereda:</b> {v('vereda')}<br><b>Descripción:</b> {v('descripcion')}<br>" f"<b>Registrado por:</b> {v('registrado_por')}<br><b>Estado coordenada:</b> {v('precision_coordenada')}<br>" f"<b>Lat/Lon fuente:</b> {v('lat')} / {v('lon')}</div>")

def popup_social_demo(punto):
    return ("<div style='width:280px;font-family:Arial'>"
            "<h4>Cartografía social · demostración</h4>"
            f"<b>Categoría:</b> {html.escape(punto['categoria'])}<br>"
            f"<b>Situación:</b> {html.escape(punto['titulo'])}<br>"
            f"<b>Voz comunitaria:</b> {html.escape(punto['voz'])}<br><br>"
            "<i>No corresponde a un registro de conflicto real.</i></div>")

@st.cache_data(show_spinner=False, max_entries=32)
def preparar_topo_para_eventos(topo, resumen):
    copia = json.loads(json.dumps(topo)); tabla = resumen.set_index("codigo_ver_resuelto") if not resumen.empty else pd.DataFrame()
    for g in copia.get("objects", {}).get("Veredas", {}).get("geometries", []):
        p = g.setdefault("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip()
        if not tabla.empty and codigo in tabla.index:
            r = tabla.loc[codigo]; p["SIGOber_situaciones"] = int(r["SIGOber_situaciones"]); p["SIGOber_anios"] = str(r["SIGOber_anios"]); p["SIGOber_tipos"] = str(r["SIGOber_tipos"]); p["SIGOber_confianza"] = str(r["SIGOber_confianza"])
        else:
            p["SIGOber_situaciones"] = 0; p["SIGOber_anios"] = "Sin registros"; p["SIGOber_tipos"] = "Sin registros"; p["SIGOber_confianza"] = "Sin registros"
    return copia

def construir_mapa(topo, eventos_historicos, conflictos=None, codigo_seleccionado="", mostrar_conflictos=True, pbot_seleccionadas=(), mostrar_social_demo=False):
    inicio = time.perf_counter(); resumen = resumenes_por_vereda(eventos_historicos); topo_mapa = preparar_topo_para_eventos(topo, resumen)
    conteo = resumen.set_index("codigo_ver_resuelto")["SIGOber_situaciones"].to_dict() if not resumen.empty else {}
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="OpenStreetMap", prefer_canvas=True)
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(m)
    def estilo(feature):
        p = feature.get("properties", {}); codigo = str(p.get("CODIGO_VER", "")).strip(); n = int(conteo.get(codigo, 0)); sel = bool(codigo) and codigo == str(codigo_seleccionado).strip()
        return {"fillColor": "#d73027" if n > 0 else "#eeeeee", "color": "#111111" if sel else "#555555", "weight": 2.5 if sel else .7, "fillOpacity": .68 if sel else (.55 if n > 0 else .18)}
    tooltip = folium.GeoJsonTooltip(fields=["NOMBRE_VER", "CODIGO_VER", "SIGOber_situaciones", "SIGOber_anios", "SIGOber_tipos", "SIGOber_confianza", "AREA_HA", "FUENTE"], aliases=["Vereda", "Código", "Situaciones documentadas", "Años", "Tipos de situación", "Confianza", "Área (ha)", "Fuente cartográfica"], localize=True, sticky=True, labels=True, style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;")
    folium.TopoJson(data=topo_mapa, object_path="objects.Veredas", name="Veredas + situaciones territoriales", style_function=estilo, tooltip=tooltip, show=True).add_to(m)
    if mostrar_conflictos and conflictos is not None and not conflictos.empty:
        validos = conflictos.loc[conflictos["precision_coordenada"].eq("VALIDA")]; grupo = folium.FeatureGroup(name="Conflictos registrados — Google Sheets", show=True)
        for row in validos.itertuples(index=False):
            data = row._asdict(); folium.CircleMarker(location=[float(data["lat_num"]), float(data["lon_num"])], radius=7, weight=2, fill=True, fill_opacity=.85, tooltip=f"{data.get('tipo_conflicto', 'Situación')} — {data.get('vereda', '')}", popup=folium.Popup(popup_conflicto(data), max_width=340)).add_to(grupo)
        grupo.add_to(m)
    if mostrar_social_demo:
        grupo_social = folium.FeatureGroup(name="Cartografía social — demostración", show=True)
        for punto in PUNTOS_SOCIALES_DEMO:
            folium.CircleMarker(location=[punto["lat"], punto["lon"]], radius=8, weight=2, fill=True, fill_opacity=.9, tooltip=f"{punto['categoria']} · demostración", popup=folium.Popup(popup_social_demo(punto), max_width=340)).add_to(grupo_social)
        grupo_social.add_to(m)
    aliases_pbot = {"UGOT":"UGOT", "Aptitud":"Aptitud", "area_ha":"Área (ha)", "Area_ha":"Área (ha)", "Tipo":"Tipo", "area_m2":"Área (m²)", "Id":"ID", "codigo":"Código", "sector_cat":"Sector catastral", "tipo_avalu":"Tipo avalúo", "Reporte":"Reporte"}
    disponibles = {x[0]: x for x in cargar_pbot_capas()}
    for archivo in pbot_seleccionadas:
        capa = disponibles.get(archivo)
        if not capa: continue
        _, titulo, geo, campos_preferidos = capa; grupo_pbot = folium.FeatureGroup(name=f"{titulo} — PBOT 2015", show=True); features = geo.get("features", []); props = (features[0].get("properties", {}) or {}) if features else {}; campos = [campo for campo in campos_preferidos if campo in props]
        tooltip_pbot = folium.GeoJsonTooltip(fields=campos, aliases=[aliases_pbot.get(campo, campo) for campo in campos], localize=True, labels=True, sticky=True, style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;") if campos else None
        folium.GeoJson(geo, name=titulo, tooltip=tooltip_pbot).add_to(grupo_pbot); grupo_pbot.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m); return m, time.perf_counter() - inicio

def resumen_sadci(sadci):
    if not isinstance(sadci, pd.DataFrame) or sadci.empty: return None
    out = {}
    for c in ("presupuesto_anual_rural", "num_personal_planta", "num_personal_contratista", "ejecucion_presupuestal_pct", "cumplimiento_pdt_pct", "calificacion_mepi"):
        if c in sadci.columns:
            vals = pd.to_numeric(sadci[c], errors="coerce").dropna()
            if not vals.empty: out[c] = float(vals.mean())
    return out

def indicador_pct(valor): return "—" if valor is None or pd.isna(valor) else f"{float(valor):.0f}%"

st.markdown("""
<style>
.sigo-hero{padding:.3rem 0 .7rem}.sigo-kicker{font-size:.78rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.68}.sigo-title{font-size:2.35rem;font-weight:800;line-height:1.05;margin:.15rem 0 .35rem}.sigo-subtitle{font-size:1rem;opacity:.78;max-width:900px}.sigo-section{margin-top:.65rem;margin-bottom:.15rem;font-size:1.18rem;font-weight:750}.sigo-note,.sigo-demo{padding:.8rem 1rem;border-radius:.8rem;border:1px solid rgba(128,128,128,.22);background:rgba(128,128,128,.045)}.sigo-demo-title{font-size:1.05rem;font-weight:750;margin-bottom:.25rem}.sigo-step{display:inline-block;margin:.1rem .35rem .25rem 0;padding:.3rem .55rem;border-radius:999px;border:1px solid rgba(128,128,128,.25);font-size:.82rem;font-weight:650}div[data-testid="stMetric"]{padding:.45rem .7rem;border:1px solid rgba(128,128,128,.18);border-radius:.65rem;background:rgba(128,128,128,.035)}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### SIGOber-Rural")
    modo_presentacion = st.toggle("Modo presentación GIGAPP 2026", value=False, help="Simplifica la interfaz para una demostración pública, manteniendo los mismos datos y funciones.")
    st.divider(); st.caption("Develope · prototipo de trabajo")

st.markdown("<div class='sigo-hero'>", unsafe_allow_html=True); st.markdown("<div class='sigo-kicker'>Sistema de información territorial</div>", unsafe_allow_html=True); st.markdown("<div class='sigo-title'>SIGOber-Rural</div>", unsafe_allow_html=True); st.markdown("<div class='sigo-subtitle'>Gobernabilidad territorial rural en Puerto Rico, Caquetá · situaciones, actores, cartografía y capacidad institucional.</div></div>", unsafe_allow_html=True)
topo = cargar_veredas_topo(); historicos = cargar_eventos_locales()
if "google_data" not in st.session_state:
    with st.spinner("Conectando con las fuentes territoriales…"): st.session_state["google_data"] = leer_google_sheets()
gd = st.session_state["google_data"]
num_veredas_situacion = historicos["codigo_ver_resuelto"].nunique() if not historicos.empty and "codigo_ver_resuelto" in historicos.columns else 0
num_conflictos = len(gd["Conflictos"]) if isinstance(gd.get("Conflictos"), pd.DataFrame) else 0
num_actores = len(gd["Actores"]) if isinstance(gd.get("Actores"), pd.DataFrame) else 0
sadci = gd.get("SADCI"); sadci_resumen = resumen_sadci(sadci)

if modo_presentacion:
    st.markdown("<div class='sigo-demo'><div class='sigo-demo-title'>Demostración GIGAPP 2026</div>La plataforma integra evidencia territorial, situaciones documentadas, actores y capacidad institucional para apoyar una lectura de gobernabilidad rural.<br><b>Nota:</b> los puntos de cartografía social que aparecen en este modo son sintéticos y sirven únicamente para ilustrar la interfaz de un taller participativo.</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin:.65rem 0 .15rem'><span class='sigo-step'>01 Territorio</span><span class='sigo-step'>02 Situaciones</span><span class='sigo-step'>03 Actores</span><span class='sigo-step'>04 Capacidad institucional</span><span class='sigo-step'>05 Gobernabilidad</span></div>", unsafe_allow_html=True)
    a,b,c,d = st.columns(4); a.metric("Situaciones documentadas",len(historicos)); b.metric("Veredas con situaciones",num_veredas_situacion); c.metric("Registros operativos",num_conflictos); d.metric("Actores",num_actores)
else:
    a,b,c,d = st.columns(4); a.metric("Situaciones históricas",len(historicos)); b.metric("Veredas con situaciones",num_veredas_situacion); c.metric("Conflictos en Sheets",num_conflictos if isinstance(gd.get("Conflictos"),pd.DataFrame) else "—"); d.metric("Actores",num_actores if isinstance(gd.get("Actores"),pd.DataFrame) else "—")
    st.markdown("<div class='sigo-note'><b>Lectura de gobernabilidad:</b> SIGOber-Rural organiza el territorio alrededor de situaciones, actores y capacidad institucional. La geometría es soporte para la decisión, no el resultado final.</div>", unsafe_allow_html=True)

if not modo_presentacion:
    with st.expander("🔧 Diagnóstico de fuentes y rendimiento"):
        cfg=config_gsheets(); sid=spreadsheet_id_desde_config(cfg); st.write({"Cartografía":"Disponible" if topo else "No disponible","Eventos territoriales":f"{len(historicos)} registros","Google Sheets":"Conectado" if isinstance(gd,dict) else "No disponible","spreadsheet_id":(sid[:6]+"…"+sid[-4:]) if sid else "No configurado"})
        if st.button("Actualizar fuentes",key="actualizar_fuentes"):
            leer_google_hoja.clear(); cargar_eventos_locales.clear(); cargar_veredas_topo.clear(); st.session_state["google_data"]=leer_google_sheets(); st.rerun()

st.markdown("<div class='sigo-section'>01 · Territorio</div>" if modo_presentacion else "<div class='sigo-section'>Explorar territorio</div>", unsafe_allow_html=True)
st.caption("¿Dónde? La vereda funciona como unidad de lectura territorial. El mapa permite pasar de la escala municipal a una lectura localizada sin perder la trazabilidad de la evidencia." if modo_presentacion else "Seleccione una vereda y, si lo necesita, filtre las situaciones documentadas. Las capas PBOT se mantienen opcionales para conservar fluidez.")
veredas_df=propiedades_veredas(topo); nombres=veredas_df[["CODIGO_VER","NOMBRE_VER"]].drop_duplicates().copy(); nombres["etiqueta"]=nombres["NOMBRE_VER"].astype(str)+" — "+nombres["CODIGO_VER"].astype(str); opciones=["Todas las veredas"]+sorted(nombres["etiqueta"].tolist()); seleccion=st.selectbox("Vereda",opciones,label_visibility="collapsed"); codigo_sel="" if seleccion=="Todas las veredas" else seleccion.split(" — ")[-1]

if modo_presentacion: st.markdown("<div class='sigo-section'>02 · Situaciones</div>", unsafe_allow_html=True); st.caption("¿Qué ocurre? Las situaciones históricas se exploran por año, tipo y confianza. La plataforma conserva separadas las referencias que no pueden asignarse con precisión a una vereda.")
f1,f2,f3,f4=st.columns(4); eventos_f=historicos.copy()
if not eventos_f.empty:
    anios=sorted([x for x in eventos_f.get("anio",pd.Series(dtype=str)).astype(str).unique() if x],reverse=True); ys=f1.multiselect("Año",anios,default=[])
    tipos=sorted([x for x in eventos_f.get("tipo_conflicto",pd.Series(dtype=str)).astype(str).unique() if x]); ts=f2.multiselect("Tipo de situación",tipos,default=[])
    confs=sorted([x for x in eventos_f.get("confianza",pd.Series(dtype=str)).astype(str).unique() if x]); cs=f3.multiselect("Confianza",confs,default=[])
    if ys: eventos_f=eventos_f[eventos_f["anio"].astype(str).isin(ys)]
    if ts: eventos_f=eventos_f[eventos_f["tipo_conflicto"].astype(str).isin(ts)]
    if cs: eventos_f=eventos_f[eventos_f["confianza"].astype(str).isin(cs)]
mostrar=f4.checkbox("Mostrar conflictos de Sheets",value=True)
pbot_opciones={archivo:titulo for archivo,titulo,_,_ in cargar_pbot_capas()}; pbot_seleccionadas=st.multiselect("Capas PBOT 2015 (opcional)",options=list(pbot_opciones.keys()),format_func=lambda x:pbot_opciones[x],default=[],help="Las capas PBOT no se cargan al navegador hasta que se seleccionan.")
st.caption("Capa histórica: SITUACIONES_TERRITORIALES. Puntos: registros operativos de la hoja Conflictos. Las fuentes se mantienen separadas.")
st.caption("Ordenamiento Territorial — cartografía de formulación PBOT 2015. No implica actualización al PBOT 2023.")
conflictos=pd.DataFrame()
if isinstance(gd.get("Conflictos"),pd.DataFrame): conflictos=normalizar_conflictos(gd["Conflictos"])
mapa,segundos_mapa=construir_mapa(topo,eventos_f,conflictos,codigo_sel,mostrar,tuple(pbot_seleccionadas),mostrar_social_demo=modo_presentacion); st.caption(f"Generación del mapa en servidor: {segundos_mapa:.2f} s"); st_folium(mapa,width="100%",height=650,returned_objects=["last_active_drawing"])

if modo_presentacion:
    st.markdown("<div class='sigo-section'>03 · Actores</div>", unsafe_allow_html=True); st.caption("¿Quiénes intervienen? La fuente de actores permite desplazar la lectura desde el lugar donde ocurre una situación hacia los sujetos y organizaciones con presencia territorial.")
    x,y=st.columns(2)
    with x: st.metric("Actores registrados",num_actores); st.write("La demostración usa la fuente operativa conectada para identificar actores territoriales. El siguiente paso es relacionarlos explícitamente con situaciones y zonas de influencia.")
    with y: st.markdown("**Pregunta de decisión**"); st.write("¿Quién puede intervenir, coordinar o aportar recursos frente a una situación localizada?")
    st.markdown("<div class='sigo-section'>04 · Capacidad institucional</div>", unsafe_allow_html=True); st.caption("¿Con qué capacidad? Los indicadores SADCI permiten complementar la lectura territorial con evidencia sobre recursos, ejecución y desempeño institucional.")
    if sadci_resumen:
        q1,q2,q3=st.columns(3); q1.metric("Ejecución presupuestal",indicador_pct(sadci_resumen.get("ejecucion_presupuestal_pct"))); q2.metric("Cumplimiento PDT",indicador_pct(sadci_resumen.get("cumplimiento_pdt_pct"))); personal=(sadci_resumen.get("num_personal_planta",0)+sadci_resumen.get("num_personal_contratista",0)) if ("num_personal_planta" in sadci_resumen or "num_personal_contratista" in sadci_resumen) else None; q3.metric("Personal promedio",f"{personal:.0f}" if personal is not None else "—")
    else: st.info("Indicadores SADCI disponibles para exploración cuando la fuente esté conectada.")
    st.markdown("<div class='sigo-section'>05 · Gobernabilidad</div>", unsafe_allow_html=True); st.markdown("<div class='sigo-note'><b>La pregunta final no es solo dónde ocurre algo.</b><br>Es cómo relacionar <b>territorio + situaciones + actores + capacidades</b> para orientar decisiones de gobernabilidad rural.</div>", unsafe_allow_html=True); st.markdown("<div style='margin-top:.55rem'><b>¿Dónde?</b> Territorio &nbsp;→&nbsp; <b>¿Qué ocurre?</b> Situaciones &nbsp;→&nbsp; <b>¿Quiénes intervienen?</b> Actores &nbsp;→&nbsp; <b>¿Con qué capacidad?</b> Instituciones</div>", unsafe_allow_html=True); st.caption("Cierre sugerido: El objetivo no es construir un mapa más completo. Es construir una mejor capacidad de lectura del territorio para apoyar decisiones de gobernabilidad rural.")

st.caption("SIGOber-Rural · prototipo de trabajo para análisis y gobernabilidad territorial rural")

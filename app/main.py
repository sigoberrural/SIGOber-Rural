import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os
import re
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

# ============================================================
# SIGOber-Rural — integración SITUACIONES_TERRITORIALES v0.1
# ============================================================

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def cargar_json_local(nombre):
    """Carga JSON/TopoJSON desde data/."""
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        st.error(f"No se encontró el archivo territorial: {ruta}")
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error leyendo {nombre}: {e}")
        return None


def cargar_situaciones_territoriales():
    """Carga la capa tabular de situaciones territoriales documentadas."""
    ruta = DATA_DIR / "SITUACIONES_TERRITORIALES_eventos.csv"
    if not ruta.exists():
        # Compatibilidad con el nombre de la versión inicial.
        ruta = DATA_DIR / "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"
    if not ruta.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(ruta, dtype=str).fillna("")
    except Exception as e:
        st.warning(f"No fue posible cargar SITUACIONES_TERRITORIALES: {e}")
        return pd.DataFrame()


def topojson_a_geojson(topo_data):
    """Convierte TopoJSON a GeoJSON usando topojson cuando está disponible."""
    if not topo_data:
        return None
    if topo_data.get("type") == "FeatureCollection":
        return topo_data
    if topo_data.get("type") != "Topology":
        return None
    try:
        import topojson
        converted = topojson.Topology(topo_data).to_geojson()
        if isinstance(converted, str):
            converted = json.loads(converted)
        return converted
    except Exception as e:
        st.error(f"No se pudo convertir la capa de veredas TopoJSON a GeoJSON: {e}")
        return None


def enriquecer_veredas_con_situaciones(topo_data, df_situaciones):
    """Agrega indicadores documentales a cada polígono de vereda.

    No crea geometrías nuevas ni asigna eventos sin correspondencia validada.
    """
    geojson = topojson_a_geojson(topo_data)
    if not geojson or geojson.get("type") != "FeatureCollection":
        return None

    features = geojson.get("features", [])
    # Índice por código: es la llave territorial preferida.
    conteo = {}
    if isinstance(df_situaciones, pd.DataFrame) and not df_situaciones.empty:
        for _, row in df_situaciones.iterrows():
            codigo = str(row.get("codigo_ver_resuelto", "")).strip()
            if codigo:
                conteo[codigo] = conteo.get(codigo, 0) + 1

    for feature in features:
        props = feature.setdefault("properties", {})
        codigo = str(props.get("CODIGO_VER", "")).strip()
        props["eventos_documentados"] = int(conteo.get(codigo, 0))
        props["FUENTE_SITUACIONES"] = (
            "SIGOber — SITUACIONES_TERRITORIALES v0.1"
            if codigo in conteo else "Sin evento documentado en la capa v0.1"
        )
    geojson["features"] = features
    return geojson


def limpiar_numero(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip().replace(",", ".")
    # Evita cadenas con más de un separador decimal.
    if texto.count(".") > 1:
        partes = texto.split(".")
        texto = partes[0] + "." + "".join(partes[1:])
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def columnas_coord(df):
    lat_aliases = ["lat", "latitude", "latitud", "y", "coord_lat", "coordenada_latitud"]
    lon_aliases = ["lon", "lng", "longitude", "longitud", "x", "coord_lon", "coordenada_longitud"]
    normalizadas = {str(c).strip().lower(): c for c in df.columns}
    lat = next((normalizadas[a] for a in lat_aliases if a in normalizadas), None)
    lon = next((normalizadas[a] for a in lon_aliases if a in normalizadas), None)
    return lat, lon


def validar_punto_preciso(lat, lon, veredas):
    # Se mantiene la función para validaciones posteriores; no inventa coordenadas.
    return True, None


# ------------------------------------------------------------
# Carga inicial de datos territoriales ANTES de construir el mapa
# ------------------------------------------------------------
veredas_topo = cargar_json_local("veredas_puerto_rico.json")
df_situaciones = cargar_situaciones_territoriales()
veredas_situaciones = enriquecer_veredas_con_situaciones(veredas_topo, df_situaciones)

st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")

# ------------------------------------------------------------
# Indicadores
# ------------------------------------------------------------
if not df_situaciones.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Situaciones documentadas", len(df_situaciones))
    c2.metric("Veredas con eventos", df_situaciones["codigo_ver_resuelto"].nunique() if "codigo_ver_resuelto" in df_situaciones.columns else 0)
    c3.metric("Confianza alta", int((df_situaciones.get("confianza", pd.Series(dtype=str)).astype(str).str.upper() == "ALTA").sum()))

# ------------------------------------------------------------
# Mapa
# ------------------------------------------------------------
lat_centro, lon_centro = 1.9123, -75.1842
m = folium.Map(location=[lat_centro, lon_centro], zoom_start=10, tiles="CartoDB positron")

if veredas_situaciones and isinstance(veredas_situaciones, dict) and veredas_situaciones.get("type") == "FeatureCollection":
    # Contorno derivado: unión de los polígonos disponibles, NO frontera municipal oficial.
    try:
        geoms = [shape(f["geometry"]) for f in veredas_situaciones.get("features", []) if f.get("geometry")]
        if geoms:
            union_geom = unary_union(geoms)
            folium.GeoJson(
                mapping(union_geom),
                name="Contorno municipal (derivado)",
                style_function=lambda _: {"fillOpacity": 0, "weight": 2},
                tooltip=folium.GeoJsonTooltip(fields=[], aliases=[]),
            ).add_to(m)
    except Exception as e:
        st.warning(f"No se pudo generar el contorno derivado de veredas: {e}")

    folium.GeoJson(
        veredas_situaciones,
        name="Veredas + situaciones territoriales",
        style_function=lambda feature: {
            "fillColor": "#d73027" if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else "#eeeeee",
            "color": "#555555",
            "weight": 0.7,
            "fillOpacity": 0.55 if int(feature.get("properties", {}).get("eventos_documentados", 0)) > 0 else 0.18,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["NOMBRE_VER", "CODIGO_VER", "eventos_documentados", "FUENTE"],
            aliases=["Vereda", "Código", "Situaciones documentadas", "Fuente cartográfica"],
            localize=True,
            sticky=False,
        ),
    ).add_to(m)
else:
    st.warning("La capa de veredas no pudo convertirse a GeoJSON; el mapa base se mantiene disponible.")

# Puntos de la hoja Conflictos, solamente si existen coordenadas válidas.
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_conflictos = conn.read(worksheet="Conflictos", ttl=300)
except Exception:
    df_conflictos = pd.DataFrame()

if isinstance(df_conflictos, pd.DataFrame) and not df_conflictos.empty:
    lat_col, lon_col = columnas_coord(df_conflictos)
    if lat_col and lon_col:
        validos = 0
        for _, row in df_conflictos.iterrows():
            lat = limpiar_numero(row.get(lat_col))
            lon = limpiar_numero(row.get(lon_col))
            if lat is None or lon is None:
                continue
            if not (-5 <= lat <= 15 and -80 <= lon <= -65):
                continue
            validos += 1
            folium.CircleMarker(
                location=[lat, lon],
                radius=5,
                popup=str(row.to_dict()),
                fill=True,
            ).add_to(m)
        st.caption(f"Puntos válidos mostrados desde Conflictos: {validos}")

folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, width=None, height=650)

# ------------------------------------------------------------
# GPS: captura tolerante, sin asumir estructura de respuesta
# ------------------------------------------------------------
try:
    from streamlit_js_eval import get_geolocation
    if "gps_capturado" not in st.session_state:
        loc = get_geolocation()
        coords = loc.get("coords") if isinstance(loc, dict) else None
        lat_gps = coords.get("latitude") if isinstance(coords, dict) else None
        lon_gps = coords.get("longitude") if isinstance(coords, dict) else None
        if lat_gps is not None and lon_gps is not None:
            try:
                st.session_state.lat_click = float(lat_gps)
                st.session_state.lon_click = float(lon_gps)
                st.session_state.gps_capturado = True
            except (TypeError, ValueError):
                pass
except Exception:
    pass

if "lat_click" not in st.session_state:
    st.session_state.lat_click = lat_centro
if "lon_click" not in st.session_state:
    st.session_state.lon_click = lon_centro

st.caption(
    f"Ubicación de referencia: {st.session_state.lat_click:.6f}, {st.session_state.lon_click:.6f}"
)

st.info(
    "SIGOber-Rural integra situaciones territoriales documentadas para apoyar prevención, "
    "priorización y coordinación institucional. La capa no debe interpretarse como un mapa "
    "exclusivo de conflicto ni como sustituto de las fuentes oficiales."
)

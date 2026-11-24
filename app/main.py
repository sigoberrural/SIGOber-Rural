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
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import altair as alt
import folium
from branca.element import MacroElement, Template
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
from app.territorio import leer_eventos_territoriales, resumir_eventos_por_vereda

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

# Servicios OGC/WMS con capas identificadas en los directorios oficiales.
CARTOGRAFIA_WMS = {
    "SGC — Amenaza sísmica nacional (PGA75)": {
        "url": "https://geoportal.sgc.gov.co/arcgis/services/Amenaza_Sismica/Amenaza_Sismica_Nacional/MapServer/WMSServer",
        "layers": "10", "attribution": "Servicio Geológico Colombiano · Amenaza sísmica nacional"
    },
    "SGC — Amenaza por movimientos en masa (1:100.000)": {
        "url": "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Nacional_Amenaza_Mov_Masa_100K/Mapa_Nacional_Amenaza_Movimientos_Masa_100K/MapServer/WMSServer",
        "layers": "3,4", "attribution": "Servicio Geológico Colombiano · Mapa nacional 2015 · 1:100.000"
    },
    "SGC — Amenaza volcánica del Nevado del Huila": {
        "url": "https://srvags.sgc.gov.co/arcgis/services/Amenaza_Volcanica/Amenaza_Volcanica/MapServer/WMSServer",
        "layers": "35,36", "attribution": "Servicio Geológico Colombiano · Amenaza volcánica · Nevado del Huila"
    },
    "Parques Nacionales — Áreas protegidas (RUNAP)": {
        "url": "https://mapas.parquesnacionales.gov.co/arcgis/rest/services/pnn/Limites_oficiales_Poligono/MapServer/WMSServer",
        "layers": "0", "attribution": "Parques Nacionales Naturales de Colombia · Límites oficiales de áreas protegidas"
    },
}

# UPRA publica estos productos como servicios ArcGIS MapServer con caché de teselas,
# no se presentan como WMS. Se mantienen en un selector independiente.
IGAC_MAPSERVER_URL = "https://mapas2.igac.gov.co/server3/rest/services/carto/carto10000puertorico18592/MapServer"
CARTOGRAFIA_IGAC = {
    "IGAC — Vías, puentes y límites viales (1:10.000)": "6,8,9,10",
    "IGAC — Drenajes y cuerpos de agua (1:10.000)": "13,14,17,18",
    "IGAC — Construcciones y zonas duras (1:10.000)": "0,15,16",
    "IGAC — Curvas de nivel, piscinas y bosque (1:10.000)": "7,19,20",
    "IGAC — Nombres geográficos y unidades administrativas (1:10.000)": "1,2",
    "IGAC — Elementos de servicios públicos (1:10.000)": "3,4",
}

class ArcGISExportLayer(folium.map.Layer):
    """Capa dinámica ArcGIS REST: solicita una imagen por tesela y reproyecta a EPSG:3857."""
    _template = Template(r"""
    {% macro script(this, kwargs) %}
    var {{ this.get_name() }} = L.gridLayer({
        tileSize: 256,
        opacity: {{ this.opacity }},
        attribution: {{ this.attribution|tojson }}
    });
    {{ this.get_name() }}.createTile = function(coords, done) {
        var tile = document.createElement('img');
        tile.alt = {{ this.layer_name|tojson }};
        tile.setAttribute('role', 'presentation');
        var map = {{ this._parent.get_name() }};
        var nw = map.unproject(L.point(coords.x * 256, coords.y * 256), coords.z);
        var se = map.unproject(L.point((coords.x + 1) * 256, (coords.y + 1) * 256), coords.z);
        // El servicio IGAC trabaja nativamente en MAGNA-SIRGAS / Origen-Nacional (EPSG:9377).
        // Se envía el BBOX geográfico y se solicita la imagen final en Web Mercator.
        var bbox = [
            Math.min(nw.lng, se.lng),
            Math.min(nw.lat, se.lat),
            Math.max(nw.lng, se.lng),
            Math.max(nw.lat, se.lat)
        ].join(',');
        var params = new URLSearchParams({
            bbox: bbox,
            bboxSR: '4326',
            imageSR: '3857',
            size: '256,256',
            format: 'png32',
            transparent: 'true',
            layers: 'show:' + {{ this.layers|tojson }},
            dpi: '96',
            f: 'image'
        });
        tile.onload = function() { done(null, tile); };
        tile.onerror = function(error) { done(error, tile); };
        tile.src = {{ this.service_url|tojson }} + '/export?' + params.toString();
        return tile;
    };
    {{ this.get_name() }}.addTo({{ this._parent.get_name() }});
    {% endmacro %}
    """)

    def __init__(self, name, layers, service_url=IGAC_MAPSERVER_URL, attribution="IGAC · Cartografía básica 1:10.000", opacity=0.82, overlay=True, control=True, show=True):
        super().__init__(name=name, overlay=overlay, control=control, show=show)
        self.layer_name = name
        self.layers = layers
        self.service_url = service_url
        self.attribution = attribution
        self.opacity = opacity


CARTOGRAFIA_ARCGIS = {
    "UPRA — Frontera agrícola nacional (1:100.000)": {
        "url": "https://sig.upra.gov.co/server/rest/services/ordenamiento_productivo/frontera_agricola/MapServer",
        "attribution": "UPRA · Frontera agrícola nacional · 1:100.000", "modo": "teselas"
    },
    "UPRA — Frontera agrícola condicionada": {
        "url": "https://sig.upra.gov.co/server/rest/services/ordenamiento_productivo/frontera_agricola_condicionada/MapServer",
        "attribution": "UPRA · Frontera agrícola y frontera agrícola condicionada", "modo": "teselas"
    },
    "SGC — Amenaza sísmica nacional (PGA 475 años)": {
        "url": "https://srvags.sgc.gov.co/arcgis/rest/services/Amenaza_Sismica/Mapa_Amenaza_Sismica_Nacional_PGA475/MapServer",
        "layers": "10", "attribution": "Servicio Geológico Colombiano · PGA 475 años", "modo": "export"
    },
    "Parques Nacionales — Áreas protegidas RUNAP": {
        "url": "https://mapas.parquesnacionales.gov.co/arcgis/rest/services/pnn/runap/MapServer",
        "layers": "0", "attribution": "Parques Nacionales Naturales · Registro Único Nacional de Áreas Protegidas", "modo": "export"
    },
    "UPRA — Determinantes: frontera agrícola": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "4", "attribution": "UPRA · Determinantes territoriales · MIGO", "modo": "export"
    },
    "UPRA — Restricciones agropecuarias de frontera": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "5", "attribution": "UPRA · Restricciones agropecuarias · MIGO", "modo": "export"
    },
    "UPRA — Frontera agrícola condicionada": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "6,12", "attribution": "UPRA · Frontera agrícola condicionada · MIGO", "modo": "export"
    },
    "UPRA — Distritos de adecuación de tierras": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "7,8", "attribution": "UPRA · Distritos de adecuación de tierras · MIGO", "modo": "export"
    },
    "UPRA — Áreas de referencia ZIDRES": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "9", "attribution": "UPRA · Áreas de referencia ZIDRES · MIGO", "modo": "export"
    },
    "UPRA — Adjudicabilidad UAF": {
        "url": "https://geoportal.ant.gov.co/servidor/rest/services/MIGO/Determinantes_UPRA/MapServer",
        "layers": "11", "attribution": "UPRA · Adjudicabilidad UAF · MIGO", "modo": "export"
    },
    "SGC — Amenaza por movimientos en masa (mapa nacional 1:100.000)": {
        "url": "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Nacional_Amenaza_Mov_Masa_100K/Mapa_Nacional_Amenaza_Movimientos_Masa_100K/MapServer",
        "layers": "3", "attribution": "Servicio Geológico Colombiano · mapa nacional 2015 · escala 1:100.000", "modo": "export"
    },
    "IGAC — Atlas 2024: remoción en masa": {
        "url": "https://mapas.igac.gov.co/server/rest/services/atlas/geologicogeomorfologico/MapServer",
        "layers": "2", "attribution": "IGAC · Atlas de Colombia 2024 · fenómenos geológicos", "modo": "teselas"
    },
}

CARTOGRAFIA_LOCAL = {
    "IGAC local — Vías y puentes": ("igac_vias.geojson", "#1769aa", 2.4),
    "IGAC local — Drenajes": ("igac_drenajes.geojson", "#168aad", 1.8),
    "IGAC local — Construcciones": ("igac_construcciones.geojson", "#9c2f2f", 1.2),
    "IGAC local — Curvas y piscinas": ("igac_curvas_piscinas.geojson", "#8c6d31", 1.0),
    "IGAC local — Bosque": ("igac_bosque.geojson", "#2e7d32", 1.0),
}

def nombres_cartografia_local_disponible():
    carpeta = DATA_DIR / "cartografia_oficial" / "igac"
    return [
        nombre for nombre, (archivo, _, _) in CARTOGRAFIA_LOCAL.items()
        if (carpeta / archivo).is_file()
    ]

@st.cache_data(show_spinner=False, ttl=3600, max_entries=32)
def comprobar_capacidades_wms(url):
    """Devuelve nombres WMS publicados por el servicio; cachea 1 hora."""
    try:
        parametros = urllib.parse.urlencode({
            "service": "WMS", "request": "GetCapabilities", "version": "1.1.1"
        })
        separador = "&" if "?" in url else "?"
        solicitud = urllib.request.Request(
            url + separador + parametros,
            headers={"User-Agent": "SIGOber-Rural/1.0"},
        )
        with urllib.request.urlopen(solicitud, timeout=8) as respuesta:
            xml = respuesta.read(3_000_000)
        raiz = ET.fromstring(xml)
        nombres = set()
        for nodo in raiz.iter():
            if nodo.tag.split("}")[-1] == "Layer":
                for hijo in nodo:
                    if hijo.tag.split("}")[-1] == "Name" and hijo.text:
                        nombres.add(hijo.text.strip())
        if not nombres:
            return {"ok": False, "layers": [], "error": "El servicio no publicó nombres de capa WMS."}
        return {"ok": True, "layers": sorted(nombres), "error": ""}
    except Exception as exc:
        return {"ok": False, "layers": [], "error": f"{type(exc).__name__}: {exc}"}


def validar_catalogo_wms():
    """Comprueba servicios y nombres de capa; excluye del selector lo no publicado."""
    estados = {}
    for nombre, config in CARTOGRAFIA_WMS.items():
        url = config["url"]
        if url not in estados:
            estados[url] = comprobar_capacidades_wms(url)
        estado = estados[url]
        solicitadas = {x.strip() for x in config["layers"].split(",") if x.strip()}
        publicadas = set(estado["layers"])
        faltantes = sorted(solicitadas - publicadas) if estado["ok"] else sorted(solicitadas)
        config["capas_disponibles"] = estado["ok"] and not faltantes
        config["detalle_validacion"] = (
            "" if config["capas_disponibles"] else
            (estado["error"] or "El servidor no publica los identificadores: " + ", ".join(faltantes))
        )
    return {
        nombre: config for nombre, config in CARTOGRAFIA_WMS.items()
        if config.get("capas_disponibles", False)
    }, {
        url: estado for url, estado in estados.items()
    }



# Inicialización de variables de estado en la sesión
st.session_state.setdefault("sigo_uploads", {})
st.session_state.setdefault("sigo_upload_widget_version", 0)
st.session_state.setdefault("sigo_problematicas_validadas", None)
st.session_state.setdefault("sigo_sadci_importado", None)
st.session_state.setdefault("sidebar_seccion_activa", "Exploración")
st.session_state.setdefault("map_mostrar_conflictos", False)


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
def _leer_eventos_locales():
    ruta = DATA_DIR / "SITUACIONES_TERRITORIALES_eventos.csv"
    if not ruta.exists():
        return pd.DataFrame(), {"filas_leidas": 0, "filas_validas_estructura": 0, "filas_incompletas": []}
    return leer_eventos_territoriales(ruta)

def cargar_eventos_locales():
    eventos, auditoria = _leer_eventos_locales()
    st.session_state["sigo_auditoria_eventos"] = auditoria
    return eventos

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
def resumenes_por_vereda(eventos, codigos_veredas):
    return resumir_eventos_por_vereda(eventos, codigos_veredas)

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

def construir_mapa(
    topo, eventos_historicos, conflictos=None, codigo_seleccionado="",
    mostrar_veredas=True, mostrar_situaciones=False, mostrar_conflictos=False,
    pbot_seleccionadas=(), wms_seleccionadas=(), igac_seleccionadas=(), arcgis_seleccionadas=(),
    cartografia_local_seleccionada=(),
):
    inicio = time.perf_counter()
    codigos_veredas = {
        str(g.get("properties", {}).get("CODIGO_VER", "")).strip()
        for g in topo.get("objects", {}).get("Veredas", {}).get("geometries", [])
        if str(g.get("properties", {}).get("CODIGO_VER", "")).strip()
    }
    resumen = resumenes_por_vereda(eventos_historicos, tuple(sorted(codigos_veredas)))
    topo_mapa = preparar_topo_para_eventos(topo, resumen)
    conteo = resumen.set_index("codigo_ver_resuelto")["SIGOber_situaciones"].to_dict() if not resumen.empty else {}
    
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="OpenStreetMap", prefer_canvas=True)
    
    grupo_territorio = folium.FeatureGroup(name="01 · Base territorial — Veredas", show=True)
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
    if mostrar_veredas:
        grupo_territorio.add_to(m)
    
    grupo_situaciones = folium.FeatureGroup(name="03 · Situaciones documentadas — evidencia validada", show=True)
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
    if mostrar_situaciones:
        grupo_situaciones.add_to(m)
    
    if mostrar_conflictos and conflictos is not None and not conflictos.empty:
        validos = conflictos.loc[conflictos["precision_coordenada"].eq("VALIDA")]
        grupo = folium.FeatureGroup(name="04 · Puntos de conflictos — fuente institucional", show=True)
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
        grupo_pbot = folium.FeatureGroup(name=f"02 · PBOT 2015 — {titulo}", show=True)
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
        
    # Capas IGAC descargadas en el repositorio (se ofrecen solo si el archivo existe).
    for nombre_capa in cartografia_local_seleccionada:
        config_local = CARTOGRAFIA_LOCAL.get(nombre_capa)
        if not config_local:
            continue
        archivo_local, color_local, grosor_local = config_local
        ruta_local = DATA_DIR / "cartografia_oficial" / "igac" / archivo_local
        try:
            with open(ruta_local, "r", encoding="utf-8") as archivo:
                geo_local = json.load(archivo)
            if geo_local.get("type") != "FeatureCollection" or not geo_local.get("features"):
                continue
            grupo_local = folium.FeatureGroup(name=f"05 · {nombre_capa}", show=True)
            propiedades = geo_local["features"][0].get("properties") or {}
            tooltip_local = folium.GeoJsonTooltip(
                fields=["_igac_layer_name"], aliases=["Capa IGAC"], sticky=True
            ) if "_igac_layer_name" in propiedades else None
            folium.GeoJson(
                geo_local, name=nombre_capa,
                style_function=lambda feature, color=color_local, weight=grosor_local: {
                    "color": color, "weight": weight, "opacity": 0.9,
                    "fillColor": color, "fillOpacity": 0.18,
                },
                tooltip=tooltip_local,
            ).add_to(grupo_local)
            grupo_local.add_to(m)
        except (OSError, ValueError, TypeError):
            continue

    # =========================================================================
    # RENDERIZADO DINÁMICO DE CAPAS OFICIALES REMOTAS
    # =========================================================================

    for nombre_capa in wms_seleccionadas:
        config = CARTOGRAFIA_WMS.get(nombre_capa)
        if not config or not config.get("capas_disponibles", False):
            continue
        folium.raster_layers.WmsTileLayer(
            url=config["url"], name=nombre_capa, layers=config["layers"],
            fmt="image/png", transparent=True, overlay=True, control=True,
            version="1.1.1", attr=config["attribution"], show=True,
            opacity=0.78,
        ).add_to(m)

    # Cartografía IGAC: MapServer dinámico sin caché XYZ; se consume con Export Map.
    for nombre_capa in igac_seleccionadas:
        ids_capa = CARTOGRAFIA_IGAC.get(nombre_capa)
        if ids_capa:
            ArcGISExportLayer(
                name=nombre_capa, layers=ids_capa,
                attribution="IGAC · Cartografía básica Puerto Rico, Caquetá · escala 1:10.000",
                opacity=0.82,
            ).add_to(m)

    # Servicios UPRA servidos como teselas ArcGIS REST (no son WMS).
    for nombre_capa in arcgis_seleccionadas:
        config = CARTOGRAFIA_ARCGIS.get(nombre_capa)
        if not config:
            continue
        if config.get("modo") == "export":
            ArcGISExportLayer(
                name=nombre_capa, layers=config["layers"],
                service_url=config["url"], attribution=config["attribution"],
                opacity=0.72,
            ).add_to(m)
        else:
            folium.TileLayer(
                tiles=config["url"].rstrip("/") + "/tile/{z}/{y}/{x}",
                name=nombre_capa, attr=config["attribution"],
                overlay=True, control=True, show=True, opacity=0.68,
                min_zoom=5, max_zoom=14,
            ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m, time.perf_counter() - inicio

def resumen_sadci(sadci):
    if not isinstance(sadci, pd.DataFrame) or sadci.empty: return None
    out = {}
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

def calcular_indicadores_dci_avanzados(r_sadci):
    """
    Calcula nuevos indicadores y ratios derivados de los datos ingresados en el formulario,
    fundamentado en la teoría de capacidades institucionales de Oszlak y Orellana.
    """
    if not r_sadci:
        return {}
    
    presupuesto = r_sadci.get("presupuesto_anual_rural", 0) or 0
    planta = r_sadci.get("num_personal_planta", 0) or 0
    contratistas = r_sadci.get("num_personal_contratista", 0) or 0
    ejecucion = r_sadci.get("ejecucion_presupuestal_pct", 0) or 0
    cumplimiento = r_sadci.get("cumplimiento_pdt_pct", 0) or 0
    
    total_personal = planta + contratistas
    
    presupuesto_por_colaborador = (presupuesto / total_personal) if total_personal > 0 else 0
    pct_contratistas = (contratistas / total_personal * 100) if total_personal > 0 else 0
    monto_ejecutado = presupuesto * (ejecucion / 100.0)
    indice_deficit = 100.0 - ((ejecucion + cumplimiento) / 2.0)
    
    return {
        "total_personal": total_personal,
        "pct_contratistas": pct_contratistas,
        "presupuesto_por_colaborador": presupuesto_por_colaborador,
        "monto_ejecutado": monto_ejecutado,
        "indice_deficit": indice_deficit
    }

def generar_analisis_dci_oszlak(r_sadci):
    """
    Genera un diagnóstico analítico detallado indicador por indicador y muestra 
    los indicadores calculados basados estrictamente en los datos del formulario.
    """
    if not r_sadci:
        return "⚠️ Sin datos institucionales suficientes en la sesión actual para auditar los déficits de capacidad institucional (DCI)."
    
    calc = calcular_indicadores_dci_avanzados(r_sadci)
    
    presupuesto = r_sadci.get("presupuesto_anual_rural", 0) or 0
    planta = r_sadci.get("num_personal_planta", 0) or 0
    contratistas = r_sadci.get("num_personal_contratista", 0) or 0
    ejecucion = r_sadci.get("ejecucion_presupuestal_pct")
    cumplimiento = r_sadci.get("cumplimiento_pdt_pct")
    mepi = r_sadci.get("calificacion_mepi")
    
    bloques = []
    
    bloques.append(
        "### 🔍 Indicadores Calculados del Sistema (Formulario SADCI)\n"
        f"- **Total Fuerza de Trabajo Institucional:** {int(calc.get('total_personal', 0))} personas "
        f"(*{calc.get('pct_contratistas', 0):.1f}% contratistas* / *{100 - calc.get('pct_contratistas', 0):.1f}% planta*).\n"
        f"- **Presupuesto Asignado por Colaborador:** ${calc.get('presupuesto_por_colaborador', 0):,.2f} COP.\n"
        f"- **Monto Financiero Ejecutado Real:** ${calc.get('monto_ejecutado', 0):,.2f} COP.\n"
        f"- **Índice Sintético de Déficit Institucional (DCI):** **{calc.get('indice_deficit', 0):.1f}/100** "
        f"(*{'Riesgo Crítico' if calc.get('indice_deficit', 0) > 40 else 'Estabilidad Aceptable'}*).\n"
    )
    
    presupuesto_str = f"{presupuesto:,.0f} COP" if presupuesto > 0 else "sin asignación registrada"
    if presupuesto > 0:
        fin_val = f"- **Presupuesto Asignado ({presupuesto_str}):** Suficiente en términos formales. Oszlak y Orellana señalan que la materialización de políticas rurales requiere recursos monetarios estables y liquidez oportuna."
    else:
        fin_val = f"- **Presupuesto Asignado ({presupuesto_str}):** Configura un *déficit financiero estructural crítico* al carecer de recursos monetarios base para la intervención estatal."
    bloques.append("### 🏛️ 1. Dimensión de Capacidad Material y Financiera\n" + fin_val)
    
    if ejecucion is not None and not pd.isna(ejecucion):
        estado_ejec = "Óptima capacidad de absorción y conversión de recursos" if ejecucion >= 70 else "Déficit crítico de gestión y absorción financiera"
        bloques.append(
            "\n### ⚙️ 2. Dimensión de Eficiencia Operativa y Gestión\n"
            f"- **Ejecución Presupuestal ({ejecucion:.0f}%):** Evaluado como *{estado_ejec}*. "
            "Un porcentaje bajo refleja cuellos de botella burocráticos o limitaciones técnicas en la formulación de proyectos para ejecutar el gasto programado."
        )
        
    if calc.get('total_personal', 0) > 0:
        pct_c = calc.get('pct_contratistas', 0)
        fragilidad_bureau = "alta fragilidad institucional y baja profesionalización" if pct_c > 50 else "adecuado arraigo y estabilidad burocrática"
        bloques.append(
            "\n### 👥 3. Dimensión Burocrática y Arreglos Organizacionales\n"
            f"- **Talento Humano ({int(planta)} planta, {int(contratistas)} contratistas):** "
            f"La dependencia de contratistas está en **{pct_c:.1f}%**, lo que denota **{fragilidad_bureau}**. "
            "Según la perspectiva de Oszlak, la tercerización excesiva erosiona la memoria institucional y la estabilidad de la carrera administrativa."
        )
        
    if cumplimiento is not None and not pd.isna(cumplimiento):
        eficacia_estado = "alta capacidad de co-producción de valor público" if cumplimiento >= 70 else "déficit de efectividad en el cumplimiento de metas"
        bloques.append(
            "\n### 📈 4. Dimensión Estratégica y de Resultados (Eficacia)\n"
            f"- **Cumplimiento del PDT ({cumplimiento:.0f}%):** Diagnóstico de *{eficacia_estado}*. "
            "Mide el grado en que la burocracia estatal logra incidir en la transformación de las condiciones socioeconómicas y territoriales."
        )
        
    if mepi is not None and not pd.isna(mepi):
        bloques.append(
            f"\n- **Desempeño Institucional Global (MEPI: {mepi:.1f}/100):** Sintetiza la capacidad global de gestión fiscal y administrativa de la entidad territorial."
        )
        
    return "\n".join(bloques)

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
    
    if st.session_state["sidebar_seccion_activa"] == "Exploración":
        st.markdown("### 🗺️ Configuración del mapa")
        st.caption("Activa y combina las capas que quieras consultar. Ninguna vista apaga las demás.")

        with st.expander("01 · Base territorial", expanded=True):
            mostrar_veredas = st.checkbox(
                "Límites y nombres de veredas",
                value=True, key="map_mostrar_veredas",
                help="Capa base independiente. Puedes mantenerla visible junto con PBOT y situaciones.",
            )
            topo_sb = cargar_veredas_topo()
            veredas_df_sb = propiedades_veredas(topo_sb)
            nombres_sb = veredas_df_sb[["CODIGO_VER", "NOMBRE_VER"]].drop_duplicates().copy()
            nombres_sb["etiqueta"] = nombres_sb["NOMBRE_VER"].astype(str) + " — " + nombres_sb["CODIGO_VER"].astype(str)
            opciones_sb = ["Todas las veredas"] + sorted(nombres_sb["etiqueta"].tolist())
            vereda_seleccionada = st.selectbox("Resaltar vereda", opciones_sb, key="sb_vereda")

        with st.expander("02 · Ordenamiento territorial · PBOT 2015", expanded=False):
            pbot_opciones_sb = {archivo: titulo for archivo, titulo, _, _ in cargar_pbot_capas()}
            pbot_sel_sb = st.multiselect(
                "Capas PBOT disponibles",
                options=list(pbot_opciones_sb.keys()),
                format_func=lambda x: pbot_opciones_sb[x],
                key="sb_pbot",
                help="Puedes activar varias capas PBOT al mismo tiempo.",
            )
            if not pbot_opciones_sb:
                st.info("No hay archivos PBOT locales disponibles.")

        with st.expander("03 · Situaciones documentadas", expanded=False):
            mostrar_situaciones = st.checkbox(
                "Mostrar situaciones validadas por vereda",
                value=False, key="map_mostrar_situaciones",
                help="Solo evidencia validada explícitamente a escala de vereda.",
            )
            historicos_sb = cargar_eventos_locales()
            ys, ts, cs = [], [], []
            if not historicos_sb.empty:
                anios_l = sorted([x for x in historicos_sb.get("anio", pd.Series(dtype=str)).astype(str).unique() if x], reverse=True)
                ys = st.multiselect("Año", anios_l, default=[], key="sb_anios")
                tipos_l = sorted([x for x in historicos_sb.get("tipo_conflicto", pd.Series(dtype=str)).astype(str).unique() if x])
                ts = st.multiselect("Tipo de situación", tipos_l, default=[], key="sb_tipos")
                confs_l = sorted([x for x in historicos_sb.get("confianza", pd.Series(dtype=str)).astype(str).unique() if x])
                cs = st.multiselect("Confianza", confs_l, default=[], key="sb_confs")
            else:
                st.info("No hay registros estructurados disponibles para esta capa.")

        with st.expander("04 · Puntos de conflictos institucionales", expanded=False):
            mostrar_gsheets = st.checkbox(
                "Mostrar puntos con coordenadas válidas",
                value=False, key="sb_mostrar_conflictos",
                help="Fuente Google Sheets independiente de las situaciones documentadas por vereda.",
            )

        with st.expander("05 · Cartografía oficial complementaria", expanded=False):
            st.caption("Selecciona cartografía oficial. IGAC se consulta mediante imágenes dinámicas ArcGIS REST; SGC y Parques Nacionales mediante WMS. Cada capa es independiente.")

            catalogo_wms_disponible, estados_wms = validar_catalogo_wms()
            opciones_igac = list(CARTOGRAFIA_IGAC.keys())
            opciones_sgc = [n for n in catalogo_wms_disponible if n.startswith("SGC —")]
            opciones_pnn = [n for n in catalogo_wms_disponible if n.startswith("Parques Nacionales —")]

            capas_igac = st.multiselect(
                "IGAC · cartografía básica municipal 1:10.000 (servicio dinámico)",
                options=opciones_igac,
                key="sb_cartografia_igac_export_v1",
                help="Servicio oficial ArcGIS MapServer dinámico. Cada capa solicita imágenes reproyectadas a EPSG:3857 para el visor.",
            )
            capas_sgc = st.multiselect(
                "SGC · geología y amenazas",
                options=opciones_sgc,
                key="sb_cartografia_wms_sgc_v3",
                help="Solo se ofrecen capas WMS publicadas por el servicio.",
            )
            capas_pnn = st.multiselect(
                "Parques Nacionales · áreas protegidas",
                options=opciones_pnn,
                key="sb_cartografia_wms_pnn_v3",
            )
            wms_sel_sb = capas_igac + capas_sgc + capas_pnn

            if not catalogo_wms_disponible:
                st.warning("No se pudo validar ningún servicio WMS en este momento. Comprueba la conexión o inténtalo más tarde.")
            for url, estado in estados_wms.items():
                if not estado["ok"]:
                    st.caption(f"Servicio WMS no disponible: {url} — {estado['error']}")
            for nombre, config in CARTOGRAFIA_WMS.items():
                if not config.get("capas_disponibles", False):
                    st.caption(f"Capa no ofrecida: {nombre}. {config.get('detalle_validacion', 'No validada')}")

            capas_upra = st.multiselect(
                "Servicios oficiales ArcGIS REST (teselas y exportación dinámica)",
                options=list(CARTOGRAFIA_ARCGIS.keys()),
                key="sb_cartografia_arcgis_upra_v2",
                help="UPRA usa teselas; SGC y RUNAP generan imágenes dinámicas desde MapServer. Capas independientes y acumulables.",
            )
            cartografia_local_disponible = nombres_cartografia_local_disponible()
            capas_locales_sb = st.multiselect(
                "IGAC · archivos descargados disponibles en el proyecto",
                options=cartografia_local_disponible,
                key="sb_cartografia_local",
                help="Solo aparecen archivos GeoJSON realmente presentes en data/cartografia_oficial/igac.",
            )
            if not cartografia_local_disponible:
                st.caption("No hay capas IGAC descargadas localmente en el repositorio; el selector se habilitará cuando se incorporen los archivos.")

        st.session_state["map_vereda"] = vereda_seleccionada
        st.session_state["map_ys"] = ys
        st.session_state["map_ts"] = ts
        st.session_state["map_cs"] = cs
        st.session_state["map_pbot"] = pbot_sel_sb
        st.session_state["map_wms"] = wms_sel_sb
        st.session_state["map_igac_export"] = capas_igac
        st.session_state["map_arcgis"] = capas_upra
        st.session_state["map_cartografia_local"] = capas_locales_sb
        # Los widgets con key propia actualizan session_state automáticamente.
        # Solo copiamos el control cuyo key histórico es distinto.
        st.session_state["map_mostrar_gsheets"] = mostrar_gsheets
        
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
        # Los filtros de fecha/tipo/confianza se aplican sobre el conjunto legible.
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
    capas_wms_main = tuple(st.session_state.get("map_wms", []))
    
    conflictos_main = normalizar_conflictos(gd_main.get("Conflictos")) if isinstance(gd_main.get("Conflictos"), pd.DataFrame) else pd.DataFrame()
    
    capas_pbot_main = tuple(st.session_state.get("map_pbot", []))
    mostrar_veredas_main = st.session_state.get("map_mostrar_veredas", True)
    mostrar_situaciones_main = st.session_state.get("map_mostrar_situaciones", False)
    mapa_render, segundos_mapa = construir_mapa(
        topo_main, eventos_f, conflictos_main, codigo_sel_main,
        mostrar_veredas=mostrar_veredas_main,
        mostrar_situaciones=mostrar_situaciones_main,
        mostrar_conflictos=mostrar_conflictos_main,
        pbot_seleccionadas=capas_pbot_main,
        wms_seleccionadas=capas_wms_main,
        igac_seleccionadas=tuple(st.session_state.get("map_igac_export", [])),
        arcgis_seleccionadas=tuple(st.session_state.get("map_arcgis", [])),
        cartografia_local_seleccionada=tuple(st.session_state.get("map_cartografia_local", [])),
    )
    auditoria = st.session_state.get("sigo_auditoria_eventos", {})
    incompletas = auditoria.get("filas_incompletas", [])
    if incompletas:
        st.warning(
            f"Se excluyeron {len(incompletas)} filas con estructura CSV incompleta "
            "para evitar interpretar campos desplazados. No se modificó el archivo fuente."
        )
    if mostrar_situaciones_main:
        st.caption(
            "Situaciones documentadas: solo registros con estado VALIDADA_EN_CAPA, "
            "precisión VEREDA y código presente en la capa base. El conteo refleja "
            "documentación disponible, no incidencia, prevalencia ni ausencia de conflicto."
        )
        st.caption("Leyenda: gris = sin registros veredales validados; naranja = 1 registro; rojo = 2 o más registros. Los colores expresan volumen documental, no nivel de riesgo.")
    if capas_pbot_main:
        st.caption("PBOT: cartografía de formulación 2015. No implica actualización al PBOT 2023.")
    st.caption("Las capas pueden combinarse desde el panel izquierdo y activarse o desactivarse individualmente desde el control de capas del mapa.")

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
    
    if "google_data" not in st.session_state:
        st.session_state["google_data"] = leer_google_sheets()
    gd_sadci_base = st.session_state["google_data"].get("SADCI")
    
    active_sadci_df = st.session_state.get("sigo_sadci_importado")
    if active_sadci_df is not None and not active_sadci_df.empty:
        r_sadci = resumen_sadci(active_sadci_df)
    elif isinstance(gd_sadci_base, pd.DataFrame) and not gd_sadci_base.empty:
        r_sadci = resumen_sadci(gd_sadci_base)
    else:
        r_sadci = None
        
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Presupuesto rural", f"{r_sadci.get('presupuesto_anual_rural', 0):,.0f}" if r_sadci and r_sadci.get("presupuesto_anual_rural") is not None else "—")
    col2.metric("Personal planta", f"{r_sadci.get('num_personal_planta', 0):.0f}" if r_sadci and r_sadci.get("num_personal_planta") is not None else "—")
    col3.metric("Contratistas", f"{r_sadci.get('num_personal_contratista', 0):.0f}" if r_sadci and r_sadci.get("num_personal_contratista") is not None else "—")
    col4.metric("Ejecución", indicador_pct(r_sadci.get("ejecucion_presupuestal_pct") if r_sadci else None))
    col5.metric("Cumplimiento PDT", indicador_pct(r_sadci.get("cumplimiento_pdt_pct") if r_sadci else None))
    col6.metric("MEPI", f"{r_sadci.get('calificacion_mepi', 0):.1f}" if r_sadci and r_sadci.get("calificacion_mepi") is not None else "—")
    
    st.divider()
    
    # Análisis detallado indicador por indicador y métricas calculadas (Oszlak y Orellana)
    st.markdown("### 🤖 Síntesis y Análisis Dinámico de Déficits de Capacidad Institucional (DCI)")
    st.caption("Auditoría basada en datos del formulario y cálculo de ratios de gobernanza (Oscar Oszlak y Edgardo Orellana).")
    
    analisis_dci_texto = generar_analisis_dci_oszlak(r_sadci)
    st.info(analisis_dci_texto)
    
    # Gráfico de Estado y Umbrales DCI (Versión compatible y optimizada con Altair)
    st.markdown("#### 📊 Gráfico de Dimensiones y Umbrales DCI")
    if r_sadci:
        df_radar_base = pd.DataFrame([
            {"Dimensión": "Ejecución Presupuestal", "Valor": r_sadci.get("ejecucion_presupuestal_pct", 0) or 0},
            {"Dimensión": "Cumplimiento PDT", "Valor": r_sadci.get("cumplimiento_pdt_pct", 0) or 0},
            {"Dimensión": "Calificación MEPI", "Valor": r_sadci.get("calificacion_mepi", 0) or 0}
        ])
        
        bar_chart = alt.Chart(df_radar_base).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
            x=alt.X('Valor:Q', scale=alt.Scale(domain=[0, 100]), title="Grado de Cumplimiento (%)"),
            y=alt.Y('Dimensión:N', sort='-x', title="Dimensión Institucional"),
            color=alt.condition(
                alt.datum.Valor < 70,
                alt.value('#d73027'),  # Rojo si hay déficit crítico (< 70%)
                alt.value('#26694E')   # Verde institucional si es favorable
            ),
            tooltip=['Dimensión', 'Valor']
        ).properties(
            height=240
        )
        
        linea_meta = alt.Chart(pd.DataFrame({'x': [70]})).mark_rule(strokeDash=[5, 5], color='orange').encode(x='x')

        st.altair_chart(bar_chart + linea_meta, use_container_width=True)
        st.caption("🟠 *La línea naranja discontinua (70%) marca el umbral mínimo aceptable de gestión y efectividad estatal según Oszlak y Orellana.*")
    else:
        st.warning("No hay registros suficientes para renderizar el gráfico de capacidades.")
    
    st.divider()
    
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
            
            # Distribución en columnas: Informe de validación a la izquierda y Botón de confirmación a la derecha
            col_inf_izq, col_inf_der = st.columns([2, 1])
            with col_inf_izq:
                st.subheader("Informe de validación y cálculo")
                st.dataframe(sadci_review, use_container_width=True, hide_index=True)
                st.download_button("Descargar informe de validación SADCI", sadci_review.to_csv(index=False).encode("utf-8-sig"), "revision_sadci.csv", "text/csv")
            
            with col_inf_der:
                st.markdown("### 📥 Confirmación")
                if valid_count != len(sadci_review) or sadci_review.empty:
                    st.error("Corrige los códigos, periodos y valores numéricos indicados en el informe antes de confirmar.")
                else:
                    st.info("Los valores importados están listos para ser incorporados.")
                    if st.button("Confirmar actualización SADCI en esta sesión", key="confirm_sadci_import", type="primary", use_container_width=True):
                        st.session_state.sigo_sadci_importado = sadci_review.drop(columns=["errores_validacion", "valido_revision_tecnica"]).copy()
                        st.success(f"Se incorporaron {len(sadci_review)} filas SADCI a la sesión actual.")
                        st.rerun()
                    
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            st.error(f"No se pudo leer la plantilla cargada: {exc}")
    else:
        st.info("👈 Selecciona y carga tu plantilla completada en el panel izquierdo (Controles SADCI) para visualizar aquí los resultados detallados e informe de validación técnica.")
        
    if st.session_state.sigo_sadci_importado is not None:
        st.divider()
        st.subheader("Registros SADCI activos en la sesión actual")
        current = st.session_state.sigo_sadci_importado
        st.dataframe(current, use_container_width=True, hide_index=True)
        if st.button("Retirar actualización SADCI de esta sesión", key="clear_sadci_import"):
            st.session_state.sigo_sadci_importado = None
            st.rerun()

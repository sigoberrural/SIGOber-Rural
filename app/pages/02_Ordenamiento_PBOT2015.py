import base64
import gzip
import json
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="PBOT 2015 — SIGOber-Rural", page_icon="🗺️", layout="wide")
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "PBOT2015"

CAPAS = [
    ("PBOT2015_ZONIFICACION_USO_SUELO_RURAL.geojson", "Zonificación de uso del suelo rural", ["UGOT", "Aptitud", "area_ha"]),
    ("PBOT2015_PROTECCION_RURAL.geojson", "Suelos de protección rural", ["Aptitud", "Area_ha"]),
    ("PBOT2015_PERIMETRO_EXPANSION.geojson", "Perímetro y expansión urbana", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_TRATAMIENTOS_URBANOS.geojson", "Tratamientos urbanos", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_ZONAS_HOMOGENEAS_URBANAS.geojson", "Zonas homogéneas urbanas", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_PUNTOS_EXPANSION.geojson", "Puntos de expansión urbana", ["Tipo", "area_m2", "Id"]),
    ("PBOT2015_MANZANAS_INSPECCIONES.geojson", "Manzanas e inspecciones", ["codigo", "sector_cat", "tipo_avalu", "Reporte"]),
]

st.title("Ordenamiento Territorial — PBOT 2015")
st.caption("Cartografía de formulación PBOT 2015. No implica actualización al PBOT 2023.")
st.warning("Las capas se presentan como cartografía de ordenamiento. No se asignan situaciones territoriales a categorías PBOT por inferencia espacial.")

@st.cache_data(show_spinner=False)
def cargar_geojson(nombre):
    ruta = DATA_DIR / nombre
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    comprimido = DATA_DIR / (ruta.stem + ".geojson.gz.b64")
    if comprimido.exists():
        texto = comprimido.read_text(encoding="utf-8").strip()
        return json.loads(gzip.decompress(base64.b64decode(texto)).decode("utf-8"))
    return None

capas_disponibles = []
for archivo, titulo, campos_preferidos in CAPAS:
    geo = cargar_geojson(archivo)
    if geo is not None:
        capas_disponibles.append((titulo, geo, campos_preferidos))

st.markdown("### Capas disponibles")
cols = st.columns(4)
for i, (titulo, geo, _) in enumerate(capas_disponibles):
    n = len(geo.get("features", []))
    cols[i % 4].success(f"{titulo}: {n} geometrías")

m = folium.Map(location=[1.91, -75.18], zoom_start=10, tiles="CartoDB positron")
for titulo, geo, campos_preferidos in capas_disponibles:
    fg = folium.FeatureGroup(name=f"{titulo} — PBOT 2015", show=False)
    props = (geo.get("features", [{}])[0].get("properties", {}) or {}) if geo.get("features") else {}
    campos = [c for c in campos_preferidos if c in props]
    aliases_map = {"UGOT":"UGOT", "Aptitud":"Aptitud", "area_ha":"Área (ha)", "Area_ha":"Área (ha)", "Tipo":"Tipo", "area_m2":"Área (m²)", "Id":"ID", "codigo":"Código", "sector_cat":"Sector catastral", "tipo_avalu":"Tipo avalúo", "Reporte":"Reporte"}
    tooltip = folium.GeoJsonTooltip(fields=campos, aliases=[aliases_map.get(c, c) for c in campos], localize=True, labels=True, sticky=True) if campos else None
    folium.GeoJson(geo, name=titulo, tooltip=tooltip).add_to(fg)
    fg.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, width="100%", height=700)

if not capas_disponibles:
    st.error("No hay capas PBOT 2015 disponibles en formato web en el repositorio.")
else:
    st.info(f"{len(capas_disponibles)} capas PBOT 2015 disponibles en esta vista. La procedencia y geometría de cada capa se conserva sin crear polígonos nuevos.")

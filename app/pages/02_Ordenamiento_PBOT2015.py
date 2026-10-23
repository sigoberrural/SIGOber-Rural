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

st.markdown("""
<style>
.pbot-hero{padding:1.05rem 1.25rem 1.1rem;border:1px solid rgba(128,128,128,.22);border-radius:1rem;background:linear-gradient(115deg,rgba(31,91,75,.12),rgba(91,128,108,.025));margin:.2rem 0 1rem}
.pbot-eyebrow{font-size:.73rem;letter-spacing:.13em;text-transform:uppercase;font-weight:750;opacity:.65}
.pbot-hero h1{font-size:2rem;line-height:1.1;margin:.2rem 0 .4rem}
.pbot-hero p{margin:0;opacity:.78;max-width:850px}
div[data-testid="stMetric"]{padding:.55rem .7rem;border:1px solid rgba(128,128,128,.17);border-radius:.72rem;background:rgba(128,128,128,.03)}
</style>
<div class="pbot-hero">
  <div class="pbot-eyebrow">SIGOber-Rural · ordenamiento territorial</div>
  <h1>PBOT 2015</h1>
  <p>Consulta de las capas de ordenamiento disponibles para Puerto Rico, Caquetá, con su procedencia y atributos cartográficos.</p>
</div>
""", unsafe_allow_html=True)
st.warning("Estas capas corresponden a la cartografía de formulación del PBOT 2015; no representan una actualización del instrumento. La superposición espacial puede orientar preguntas, pero no demuestra por sí sola relaciones causales ni asigna automáticamente situaciones a categorías de ordenamiento.")

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

total_geometrias = sum(len(geo.get("features", [])) for _, geo, _ in capas_disponibles)
m1, m2, m3 = st.columns(3)
m1.metric("Capas disponibles", len(capas_disponibles), help="Capas locales cargadas correctamente en esta sesión.")
m2.metric("Geometrías cargadas", f"{total_geometrias:,}")
m3.metric("Año de referencia", "2015", help="Año del instrumento cartográfico consultado, no fecha de actualización.")
st.markdown("### Capas disponibles")
if capas_disponibles:
    filas_capas = []
    for titulo, geo, campos_preferidos in capas_disponibles:
        features = geo.get("features", [])
        props = (features[0].get("properties", {}) or {}) if features else {}
        filas_capas.append({
            "Capa": titulo,
            "Geometrías": len(features),
            "Atributos destacados": ", ".join(c for c in campos_preferidos if c in props) or "Sin campos destacados detectados",
            "Procedencia": "PBOT 2015",
        })
    st.dataframe(filas_capas, use_container_width=True, hide_index=True)
else:
    st.error("No se encontraron capas PBOT 2015 locales en formato GeoJSON o comprimido compatible.")

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

if capas_disponibles:
    st.success(f"El mapa contiene {len(capas_disponibles)} capas locales y {total_geometrias:,} geometrías. Activa o desactiva cada capa desde el control situado en el mapa.")
    st.caption("Las capas se cargan inicialmente ocultas para evitar superposiciones visuales excesivas. Los atributos disponibles se consultan al pasar el cursor sobre las geometrías.")
    st.info("La disponibilidad de un archivo no certifica su vigencia jurídica ni su correspondencia con cambios territoriales posteriores a 2015.")

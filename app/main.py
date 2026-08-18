import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def cargar_eventos():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv", "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"):
        ruta = DATA_DIR / nombre
        if ruta.exists():
            return pd.read_csv(ruta, dtype=str).fillna("")
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def cargar_veredas_topo():
    topo = cargar_json("veredas_puerto_rico.json")
    if not topo:
        raise RuntimeError("No se encontró data/veredas_puerto_rico.json en el repositorio.")
    if topo.get("type") != "Topology":
        raise RuntimeError(f"La capa de veredas no tiene formato TopoJSON: {topo.get('type')}")
    objetos = topo.get("objects", {})
    if "Veredas" not in objetos:
        raise RuntimeError(f"El TopoJSON no contiene el objeto 'Veredas'. Objetos encontrados: {list(objetos.keys())}")
    return topo


def construir_mapa(topo=None, eventos=None):
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="CartoDB positron")
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(m)

    if topo:
        conteo = {}
        if eventos is not None and not eventos.empty and "codigo_ver_resuelto" in eventos.columns:
            conteo = eventos["codigo_ver_resuelto"].astype(str).str.strip().value_counts().to_dict()

        def estilo(feature):
            props = feature.get("properties", {})
            codigo = str(props.get("CODIGO_VER", "")).strip()
            n = int(conteo.get(codigo, 0))
            return {
                "fillColor": "#d73027" if n > 0 else "#eeeeee",
                "color": "#555555",
                "weight": 0.7,
                "fillOpacity": 0.55 if n > 0 else 0.18,
            }

        # TopoJSON directo: evita la conversión pesada en Python.
        # GeoJsonTooltip funciona también con propiedades del TopoJSON.
        tooltip = folium.GeoJsonTooltip(
            fields=["NOMBRE_VER", "CODIGO_VER", "AREA_HA", "FUENTE", "VIGENCIA"],
            aliases=["Vereda", "Código", "Área (ha)", "Fuente cartográfica", "Vigencia"],
            localize=True,
            sticky=True,
            labels=True,
        )

        folium.TopoJson(
            data=topo,
            object_path="objects.Veredas",
            name="Veredas + situaciones territoriales",
            style_function=estilo,
            tooltip=tooltip,
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")

eventos = cargar_eventos()

c1, c2, c3 = st.columns(3)
c1.metric("Situaciones documentadas", len(eventos))
c2.metric("Veredas con eventos", eventos["codigo_ver_resuelto"].nunique() if "codigo_ver_resuelto" in eventos.columns and not eventos.empty else 0)
c3.metric("Estado", "Operativo")

st.success("La aplicación inició correctamente con datos locales. Las fuentes externas se cargan solo bajo demanda.")

if "veredas_topo" not in st.session_state:
    st.session_state["veredas_topo"] = None

if st.button("Cargar capa de veredas", type="primary", disabled=st.session_state["veredas_topo"] is not None):
    with st.spinner("Cargando la capa de veredas…"):
        try:
            st.session_state["veredas_topo"] = cargar_veredas_topo()
            st.success("Capa de veredas cargada. Pase el cursor sobre una vereda para consultar sus atributos.")
        except Exception as e:
            st.error(f"No se pudo cargar la capa de veredas: {type(e).__name__}: {e}")

m = construir_mapa(st.session_state["veredas_topo"], eventos)
st_folium(m, width="100%", height=620)

st.divider()
st.subheader("Fuentes externas")
st.write("Google Sheets permanece separado del arranque de la aplicación.")

if st.button("Probar conexión con Google Sheets"):
    try:
        from streamlit_gsheets import GSheetsConnection

        # Diagnóstico sin mostrar valores sensibles.
        conexiones = st.secrets.get("connections", {})
        config = conexiones.get("gsheets", {}) if hasattr(conexiones, "get") else {}
        tiene_spreadsheet = bool(config.get("spreadsheet")) if hasattr(config, "get") else False
        tiene_worksheet_config = bool(config.get("worksheet")) if hasattr(config, "get") else False

        with st.spinner("Consultando Google Sheets…"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Conflictos", ttl=300)

        if isinstance(df, pd.DataFrame):
            st.success(f"Google Sheets respondió correctamente: {len(df)} registros.")
        else:
            st.warning(f"Google Sheets respondió, pero el resultado no es una tabla pandas sino {type(df).__name__}.")

    except Exception as e:
        st.error(
            "No se pudo leer la hoja 'Conflictos'. "
            f"Tipo de error: {type(e).__name__}. Detalle: {e}"
        )
        if type(e).__name__ == "SpreadsheetNotFound":
            st.warning(
                "La autenticación llegó hasta Google, pero no se encontró el SPREADSHEET. "
                "Revisa en Streamlit Cloud → Settings → Secrets que exista [connections.gsheets] "
                "con la clave 'spreadsheet' y que la URL/ID corresponda al archivo correcto."
            )
            st.write({
                "config_connections_gsheets_presente": bool(config),
                "spreadsheet_configurado": tiene_spreadsheet,
                "worksheet_configurado": tiene_worksheet_config,
                "worksheet_solicitado": "Conflictos",
            })
            st.info(
                "Importante: 'spreadsheet' identifica el archivo de Google Sheets; 'worksheet' identifica una pestaña dentro de ese archivo. "
                "Además, si se usa una cuenta de servicio, el archivo debe estar compartido con el client_email de esa cuenta."
            )
        else:
            st.info("La capa cartográfica es independiente de Google Sheets; este error no afecta el mapa.")

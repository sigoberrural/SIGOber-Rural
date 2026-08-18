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
def cargar_eventos_locales():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv", "SITUACIONES_TERRITORIALES_eventos_v0_1.csv"):
        ruta = DATA_DIR / nombre
        if ruta.exists():
            return pd.read_csv(ruta, dtype=str).fillna("")
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def cargar_veredas_topo():
    topo = cargar_json("veredas_puerto_rico.json")
    if not topo:
        raise RuntimeError("No se encontró data/veredas_puerto_rico.json.")
    if topo.get("type") != "Topology":
        raise RuntimeError(f"La capa de veredas no tiene formato TopoJSON: {topo.get('type')}")
    if "Veredas" not in topo.get("objects", {}):
        raise RuntimeError("El TopoJSON no contiene el objeto 'Veredas'.")
    return topo


def propiedades_veredas(topo):
    filas = []
    for g in topo.get("objects", {}).get("Veredas", {}).get("geometries", []):
        p = g.get("properties", {}) or {}
        filas.append(p)
    return pd.DataFrame(filas).fillna("")


def contar_eventos(eventos):
    if eventos.empty or "codigo_ver_resuelto" not in eventos.columns:
        return {}
    return eventos["codigo_ver_resuelto"].astype(str).str.strip().value_counts().to_dict()


def construir_mapa(topo=None, eventos=None, codigo_seleccionado=""):
    m = folium.Map(location=[1.9123, -75.1842], zoom_start=10, tiles="CartoDB positron")
    folium.Marker([1.9123, -75.1842], tooltip="Puerto Rico, Caquetá").add_to(m)

    if topo:
        conteo = contar_eventos(eventos if eventos is not None else pd.DataFrame())

        def estilo(feature):
            props = feature.get("properties", {})
            codigo = str(props.get("CODIGO_VER", "")).strip()
            n = int(conteo.get(codigo, 0))
            seleccionado = codigo and codigo == str(codigo_seleccionado).strip()
            return {
                "fillColor": "#d73027" if n > 0 else "#eeeeee",
                "color": "#111111" if seleccionado else "#555555",
                "weight": 2.2 if seleccionado else 0.7,
                "fillOpacity": 0.68 if seleccionado else (0.55 if n > 0 else 0.18),
            }

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
            name="Veredas",
            style_function=estilo,
            tooltip=tooltip,
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def normalizar_conflictos(df):
    if df.empty:
        return df
    out = df.copy().fillna("")
    for c in ["lat", "lon"]:
        if c in out.columns:
            out[c + "_num"] = pd.to_numeric(out[c], errors="coerce")
    if "lat_num" in out.columns and "lon_num" in out.columns:
        out["precision_coordenada"] = "VALIDA"
        out.loc[(out["lat_num"].abs() > 90) | (out["lon_num"].abs() > 180), "precision_coordenada"] = "REQUIERE_REVISION"
        out.loc[out[["lat_num", "lon_num"]].isna().any(axis=1), "precision_coordenada"] = "SIN_COORDENADA"
    return out


@st.cache_data(ttl=300, show_spinner=False)
def leer_google_sheets():
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    resultado = {}
    for hoja in ["Conflictos", "Actores", "SADCI", "Relación Interinstitucional"]:
        try:
            resultado[hoja] = conn.read(worksheet=hoja, ttl=300).fillna("")
        except Exception as e:
            resultado[hoja] = e
    return resultado


st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")

eventos_locales = cargar_eventos_locales()

if "veredas_topo" not in st.session_state:
    st.session_state["veredas_topo"] = None
if "google_data" not in st.session_state:
    st.session_state["google_data"] = None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Situaciones documentadas", len(eventos_locales))
c2.metric("Veredas con eventos", eventos_locales["codigo_ver_resuelto"].nunique() if "codigo_ver_resuelto" in eventos_locales.columns and not eventos_locales.empty else 0)
c3.metric("Actores", "—" if st.session_state["google_data"] is None else (len(st.session_state["google_data"].get("Actores", [])) if isinstance(st.session_state["google_data"].get("Actores"), pd.DataFrame) else "—"))
c4.metric("SADCI", "—" if st.session_state["google_data"] is None else (len(st.session_state["google_data"].get("SADCI", [])) if isinstance(st.session_state["google_data"].get("SADCI"), pd.DataFrame) else "—"))

st.info("SIGOber-Rural organiza la lectura del territorio alrededor de situaciones, actores y capacidad institucional. La geometría es un soporte para la gobernabilidad, no el resultado final.")

col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("Cargar capa de veredas", type="primary", disabled=st.session_state["veredas_topo"] is not None):
        with st.spinner("Cargando cartografía…"):
            try:
                st.session_state["veredas_topo"] = cargar_veredas_topo()
                st.success("Cartografía cargada.")
            except Exception as e:
                st.error(f"No se pudo cargar la capa: {type(e).__name__}: {e}")

with col_b:
    st.caption("Las situaciones se visualizan por vereda y se pueden explorar mediante filtros y ficha territorial.")

veredas_df = propiedades_veredas(st.session_state["veredas_topo"]) if st.session_state["veredas_topo"] else pd.DataFrame()

if not veredas_df.empty:
    nombres = veredas_df[["CODIGO_VER", "NOMBRE_VER"]].drop_duplicates().copy()
    nombres["etiqueta"] = nombres["NOMBRE_VER"].astype(str) + " — " + nombres["CODIGO_VER"].astype(str)
    opciones = ["Todas las veredas"] + sorted(nombres["etiqueta"].tolist())
    seleccion = st.selectbox("Explorar territorio", opciones)
    codigo_sel = ""
    if seleccion != "Todas las veredas":
        codigo_sel = seleccion.split(" — ")[-1]

    f1, f2, f3 = st.columns(3)
    eventos_f = eventos_locales.copy()
    if not eventos_f.empty:
        if "anio" in eventos_f.columns:
            anios = sorted([x for x in eventos_f["anio"].astype(str).unique() if x], reverse=True)
            anio_sel = f1.multiselect("Año", anios, default=[])
            if anio_sel:
                eventos_f = eventos_f[eventos_f["anio"].astype(str).isin(anio_sel)]
        if "tipo_conflicto" in eventos_f.columns:
            tipos = sorted([x for x in eventos_f["tipo_conflicto"].astype(str).unique() if x])
            tipo_sel = f2.multiselect("Tipo de situación", tipos, default=[])
            if tipo_sel:
                eventos_f = eventos_f[eventos_f["tipo_conflicto"].astype(str).isin(tipo_sel)]
        if "confianza" in eventos_f.columns:
            confs = sorted([x for x in eventos_f["confianza"].astype(str).unique() if x])
            conf_sel = f3.multiselect("Confianza", confs, default=[])
            if conf_sel:
                eventos_f = eventos_f[eventos_f["confianza"].astype(str).isin(conf_sel)]

    m = construir_mapa(st.session_state["veredas_topo"], eventos_f, codigo_sel)
    mapa_resultado = st_folium(m, width="100%", height=620, returned_objects=["last_active_drawing"])

    if codigo_sel:
        fila = veredas_df[veredas_df["CODIGO_VER"].astype(str) == str(codigo_sel)].head(1)
        if not fila.empty:
            p = fila.iloc[0]
            st.subheader(f"Ficha territorial — {p.get('NOMBRE_VER', '')}")
            eventos_vereda = eventos_f[eventos_f["codigo_ver_resuelto"].astype(str).str.strip() == str(codigo_sel).strip()] if "codigo_ver_resuelto" in eventos_f.columns else pd.DataFrame()
            a, b, c, d = st.columns(4)
            a.metric("Situaciones", len(eventos_vereda))
            b.metric("Primera referencia", eventos_vereda["anio"].min() if not eventos_vereda.empty and "anio" in eventos_vereda.columns else "—")
            c.metric("Última referencia", eventos_vereda["anio"].max() if not eventos_vereda.empty and "anio" in eventos_vereda.columns else "—")
            d.metric("Área (ha)", p.get("AREA_HA", "—"))

            st.markdown("**Identificación cartográfica**")
            st.write({"Vereda": p.get("NOMBRE_VER", ""), "Código": p.get("CODIGO_VER", ""), "Fuente": p.get("FUENTE", ""), "Vigencia": p.get("VIGENCIA", "")})

            if eventos_vereda.empty:
                st.info("No hay situaciones documentadas para esta vereda con los filtros actuales.")
            else:
                st.markdown("**Situaciones documentadas**")
                cols = [c for c in ["id", "anio", "tipo_conflicto", "subtipo", "confianza", "precision_espacial", "fuente", "estado_territorial"] if c in eventos_vereda.columns]
                st.dataframe(eventos_vereda[cols], use_container_width=True, hide_index=True)

            if st.session_state["google_data"]:
                actores = st.session_state["google_data"].get("Actores")
                if isinstance(actores, pd.DataFrame) and not actores.empty and "Vereda" in actores.columns:
                    actores_v = actores[actores["Vereda"].astype(str).str.strip().str.upper() == str(p.get("NOMBRE_VER", "")).strip().upper()]
                    st.markdown("**Actores registrados**")
                    if actores_v.empty:
                        st.caption("No hay actores asociados en la hoja cargada.")
                    else:
                        st.dataframe(actores_v, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Capacidad institucional y fuentes externas")
st.write("La conexión con Google Sheets se carga bajo demanda para evitar bloquear el arranque cartográfico.")

if st.button("Cargar / actualizar Google Sheets"):
    with st.spinner("Leyendo Conflictos, Actores, SADCI y Relación Interinstitucional…"):
        try:
            datos = leer_google_sheets()
            st.session_state["google_data"] = datos
            ok = [k for k, v in datos.items() if isinstance(v, pd.DataFrame)]
            errores = {k: f"{type(v).__name__}: {v}" for k, v in datos.items() if not isinstance(v, pd.DataFrame)}
            st.success(f"Hojas leídas correctamente: {', '.join(ok) if ok else 'ninguna'}.")
            if errores:
                st.warning("Algunas hojas no pudieron leerse.")
                st.json(errores)
        except Exception as e:
            st.error(f"No se pudo inicializar Google Sheets: {type(e).__name__}: {e}")

if st.session_state["google_data"]:
    datos = st.session_state["google_data"]
    tabs = st.tabs(["Conflictos", "Actores", "SADCI", "Relación interinstitucional"])
    for tab, nombre in zip(tabs, ["Conflictos", "Actores", "SADCI", "Relación Interinstitucional"]):
        with tab:
            df = datos.get(nombre)
            if isinstance(df, pd.DataFrame):
                if nombre == "Conflictos":
                    df2 = normalizar_conflictos(df)
                    st.dataframe(df2, use_container_width=True, hide_index=True)
                    if "precision_coordenada" in df2.columns:
                        st.caption("Las coordenadas fuera de rango se marcan como REQUIERE_REVISION; no se corrigen automáticamente.")
                elif df.empty:
                    st.info("La hoja existe pero actualmente no contiene registros.")
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No se pudo leer {nombre}: {type(df).__name__}: {df}")

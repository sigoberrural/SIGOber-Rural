import html
import json
import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists(): return None
    with open(ruta, "r", encoding="utf-8") as f: return json.load(f)

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

def propiedades_veredas(topo):
    return pd.DataFrame([g.get("properties", {}) or {} for g in topo.get("objects", {}).get("Veredas", {}).get("geometries", [])]).fillna("")

def resumen_vereda(codigo, eventos):
    vacio={"n":0,"anios":"Sin registros","tipos":"Sin registros","conf":"Sin registros"}
    if eventos.empty or "codigo_ver_resuelto" not in eventos.columns: return vacio
    ev=eventos[eventos["codigo_ver_resuelto"].astype(str).str.strip()==str(codigo).strip()]
    if ev.empty: return vacio
    return {"n":len(ev),"anios":", ".join(sorted([x for x in ev.get("anio",pd.Series(dtype=str)).astype(str).unique() if x])) or "Sin fecha","tipos":", ".join(sorted([x for x in ev.get("tipo_conflicto",pd.Series(dtype=str)).astype(str).unique() if x])) or "No especificado","conf":", ".join(sorted([x for x in ev.get("confianza",pd.Series(dtype=str)).astype(str).unique() if x])) or "No especificada"}

def normalizar_conflictos(df):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy().fillna("")
    for c in ("lat","lon"): out[c+"_num"]=pd.to_numeric(out[c],errors="coerce") if c in out.columns else pd.NA
    out["precision_coordenada"]="VALIDA"
    out.loc[out[["lat_num","lon_num"]].isna().any(axis=1),"precision_coordenada"]="SIN_COORDENADA"
    inval=(out["lat_num"].abs()>90)|(out["lon_num"].abs()>180)
    out.loc[inval & out[["lat_num","lon_num"]].notna().all(axis=1),"precision_coordenada"]="REQUIERE_REVISION"
    return out

def config_gsheets():
    try:
        c=st.secrets.get("connections",{}); x=c.get("gsheets",{}) if hasattr(c,"get") else {}
        return dict(x) if hasattr(x,"items") else {}
    except Exception: return {}

def spreadsheet_id_desde_config(cfg):
    raw=str(cfg.get("spreadsheet","") or cfg.get("spreadsheet_url","")).strip(); m=re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)",raw)
    return m.group(1) if m else raw

@st.cache_data(ttl=300,show_spinner=False)
def leer_google_sheets():
    from streamlit_gsheets import GSheetsConnection
    conn=st.connection("gsheets",type=GSheetsConnection); r={}
    for hoja in ("Conflictos","Actores","SADCI","Relación Interinstitucional"):
        try: r[hoja]=conn.read(worksheet=hoja,ttl=300).fillna("")
        except Exception as e: r[hoja]=e
    return r

def popup_conflicto(row):
    v=lambda c: html.escape(str(row.get(c,"") or ""))
    return f"<div style='width:280px;font-family:Arial'><h4>Situación registrada</h4><b>ID:</b> {v('id_conflicto')}<br><b>Tipo:</b> {v('tipo_conflicto')}<br><b>Vereda:</b> {v('vereda')}<br><b>Descripción:</b> {v('descripcion')}<br><b>Registrado por:</b> {v('registrado_por')}<br><b>Estado coordenada:</b> {v('precision_coordenada')}<br><b>Lat/Lon fuente:</b> {v('lat')} / {v('lon')}</div>"

def construir_mapa(topo,eventos_historicos,conflictos=None,codigo_seleccionado="",mostrar_conflictos=True):
    m=folium.Map(location=[1.9123,-75.1842],zoom_start=10,tiles="CartoDB positron")
    folium.Marker([1.9123,-75.1842],tooltip="Puerto Rico, Caquetá").add_to(m)
    conteo=eventos_historicos["codigo_ver_resuelto"].astype(str).str.strip().value_counts().to_dict() if not eventos_historicos.empty and "codigo_ver_resuelto" in eventos_historicos.columns else {}
    topo_mapa=json.loads(json.dumps(topo))
    for g in topo_mapa.get("objects",{}).get("Veredas",{}).get("geometries",[]):
        p=g.setdefault("properties",{}); codigo=str(p.get("CODIGO_VER","")).strip(); r=resumen_vereda(codigo,eventos_historicos)
        p.update({"SIGOber_situaciones":r["n"],"SIGOber_anios":r["anios"],"SIGOber_tipos":r["tipos"],"SIGOber_confianza":r["conf"]})
    def estilo(feature):
        p=feature.get("properties",{}); codigo=str(p.get("CODIGO_VER","")).strip(); n=int(conteo.get(codigo,0)); sel=codigo and codigo==str(codigo_seleccionado).strip()
        return {"fillColor":"#d73027" if n>0 else "#eeeeee","color":"#111111" if sel else "#555555","weight":2.5 if sel else .7,"fillOpacity":.68 if sel else (.55 if n>0 else .18)}
    tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_VER","CODIGO_VER","SIGOber_situaciones","SIGOber_anios","SIGOber_tipos","SIGOber_confianza","AREA_HA","FUENTE"],aliases=["Vereda","Código","Situaciones documentadas","Años","Tipos de situación","Confianza","Área (ha)","Fuente cartográfica"],localize=True,sticky=True,labels=True,style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;")
    folium.TopoJson(data=topo_mapa,object_path="objects.Veredas",name="Veredas + situaciones territoriales",style_function=estilo,tooltip=tooltip,show=True).add_to(m)
    if mostrar_conflictos and conflictos is not None and not conflictos.empty:
        grupo=folium.FeatureGroup(name="Conflictos registrados — Google Sheets",show=True)
        for _,row in conflictos[conflictos["precision_coordenada"]=="VALIDA"].iterrows():
            folium.CircleMarker(location=[float(row["lat_num"]),float(row["lon_num"])],radius=7,weight=2,fill=True,fill_opacity=.85,tooltip=f"{row.get('tipo_conflicto','Situación')} — {row.get('vereda','')}",popup=folium.Popup(popup_conflicto(row),max_width=340)).add_to(grupo)
        grupo.add_to(m)
            # ============================================================
    # ORDENAMIENTO TERRITORIAL — PBOT 2015
    # Cartografía de formulación PBOT 2015.
    # No implica actualización al PBOT 2023.
    # No se asignan situaciones territoriales por inferencia espacial.
    # ============================================================

    aliases_pbot = {
        "UGOT": "UGOT",
        "Aptitud": "Aptitud",
        "area_ha": "Área (ha)",
        "Area_ha": "Área (ha)",
        "Tipo": "Tipo",
        "area_m2": "Área (m²)",
        "Id": "ID",
        "codigo": "Código",
        "sector_cat": "Sector catastral",
        "tipo_avalu": "Tipo avalúo",
        "Reporte": "Reporte",
    }

    for titulo, geo, campos_preferidos in cargar_pbot_capas():

        grupo_pbot = folium.FeatureGroup(
            name=f"{titulo} — PBOT 2015",
            show=False,
        )

        features = geo.get("features", [])

        props = (
            features[0].get("properties", {}) or {}
            if features
            else {}
        )

        campos = [
            campo
            for campo in campos_preferidos
            if campo in props
        ]

        tooltip = None

        if campos:
            tooltip = folium.GeoJsonTooltip(
                fields=campos,
                aliases=[
                    aliases_pbot.get(campo, campo)
                    for campo in campos
                ],
                localize=True,
                labels=True,
                sticky=True,
                style=(
                    "background-color:white;"
                    "color:#222;"
                    "font-family:Arial;"
                    "font-size:12px;"
                    "padding:8px;"
                ),
            )

        folium.GeoJson(
            geo,
            name=titulo,
            tooltip=tooltip,
        ).add_to(grupo_pbot)

        grupo_pbot.add_to(m)
   
    folium.LayerControl(collapsed=False).add_to(m); return m

def resumen_sadci(sadci):
    if not isinstance(sadci,pd.DataFrame) or sadci.empty: return None
    out={}
    for c in ("presupuesto_anual_rural","num_personal_planta","num_personal_contratista","ejecucion_presupuestal_pct","cumplimiento_pdt_pct","calificacion_mepi"):
        if c in sadci.columns:
            vals=pd.to_numeric(sadci[c],errors="coerce").dropna()
            if not vals.empty: out[c]=float(vals.mean())
    return out

def indicador_pct(valor):
    return "—" if valor is None or pd.isna(valor) else f"{float(valor):.0f}%"

st.title("SIGOber-Rural")
st.caption("Sistema de Información para la Gobernabilidad Territorial Rural — Puerto Rico, Caquetá")
if "veredas_topo" not in st.session_state:
    st.session_state["veredas_topo"]=cargar_veredas_topo()
if "google_data" not in st.session_state:
    with st.spinner("Conectando con las fuentes territoriales…"):
        st.session_state["google_data"]=leer_google_sheets()
historicos=cargar_eventos_locales(); gd=st.session_state["google_data"]
a,b,c,d=st.columns(4); a.metric("Situaciones históricas",len(historicos)); b.metric("Veredas con situaciones",historicos["codigo_ver_resuelto"].nunique() if not historicos.empty and "codigo_ver_resuelto" in historicos.columns else 0); c.metric("Conflictos en Sheets",len(gd["Conflictos"]) if isinstance(gd,dict) and isinstance(gd.get("Conflictos"),pd.DataFrame) else "—"); d.metric("Actores",len(gd["Actores"]) if isinstance(gd,dict) and isinstance(gd.get("Actores"),pd.DataFrame) else "—")
st.info("SIGOber-Rural organiza la lectura del territorio alrededor de situaciones, actores y capacidad institucional. La geometría es soporte para la gobernabilidad, no el resultado final.")
with st.expander("🔧 Diagnóstico de fuentes"):
    cfg=config_gsheets(); sid=spreadsheet_id_desde_config(cfg); st.write({"Cartografía":"Disponible" if st.session_state.get("veredas_topo") else "No disponible","Google Sheets":"Conectado" if isinstance(gd,dict) else "No disponible","spreadsheet_id":(sid[:6]+"…"+sid[-4:]) if sid else "No configurado"})
    st.caption("Las fuentes se cargan automáticamente al iniciar la aplicación. Este diagnóstico es únicamente para revisión técnica.")
    if st.button("Actualizar fuentes"):
        cargar_veredas_topo.clear(); leer_google_sheets.clear(); st.session_state["veredas_topo"]=cargar_veredas_topo(); st.session_state["google_data"]=leer_google_sheets(); st.rerun()
if st.session_state["google_data"] is not None:
    st.markdown("### Estado de las fuentes")
    cols=st.columns(4)
    for col,hoja in zip(cols,("Conflictos","Actores","SADCI","Relación Interinstitucional")):
        x=st.session_state["google_data"].get(hoja)
        if isinstance(x,pd.DataFrame):
            col.success(f"{hoja}: {len(x)} registros")
        else:
            col.error(f"{hoja}: no disponible")
topo=st.session_state["veredas_topo"]; veredas_df=propiedades_veredas(topo); conflictos=pd.DataFrame(); gd=st.session_state.get("google_data") or {}
if isinstance(gd.get("Conflictos"),pd.DataFrame): conflictos=normalizar_conflictos(gd["Conflictos"])
nombres=veredas_df[["CODIGO_VER","NOMBRE_VER"]].drop_duplicates().copy(); nombres["etiqueta"]=nombres["NOMBRE_VER"].astype(str)+" — "+nombres["CODIGO_VER"].astype(str); opciones=["Todas las veredas"]+sorted(nombres["etiqueta"].tolist()); seleccion=st.selectbox("Explorar territorio",opciones); codigo_sel="" if seleccion=="Todas las veredas" else seleccion.split(" — ")[-1]
f1,f2,f3,f4=st.columns(4); eventos_f=historicos.copy()
if not eventos_f.empty:
    anios=sorted([x for x in eventos_f.get("anio",pd.Series(dtype=str)).astype(str).unique() if x],reverse=True); ys=f1.multiselect("Año",anios,default=[]); tipos=sorted([x for x in eventos_f.get("tipo_conflicto",pd.Series(dtype=str)).astype(str).unique() if x]); ts=f2.multiselect("Tipo de situación",tipos,default=[]); confs=sorted([x for x in eventos_f.get("confianza",pd.Series(dtype=str)).astype(str).unique() if x]); cs=f3.multiselect("Confianza",confs,default=[])
    if ys: eventos_f=eventos_f[eventos_f["anio"].astype(str).isin(ys)]
    if ts: eventos_f=eventos_f[eventos_f["tipo_conflicto"].astype(str).isin(ts)]
    if cs: eventos_f=eventos_f[eventos_f["confianza"].astype(str).isin(cs)]
mostrar=f4.checkbox("Mostrar conflictos de Sheets",value=True)
st.caption(     "Capa histórica: SITUACIONES_TERRITORIALES. "     "Puntos: registros operativos de la hoja Conflictos. "     "Las fuentes se mantienen separadas." )  st.caption(     "Ordenamiento Territorial — cartografía de formulación PBOT 2015. "     "No implica actualización al PBOT 2023." )  st_folium(     construir_mapa(         topo,         eventos_f,         conflictos,         codigo_sel,         mostrar,     ),     width="100%",     height=650,     returned_objects=["last_active_drawing"], )
st_folium(construir_mapa(topo,eventos_f,conflictos,codigo_sel,mostrar),width="100%",height=650,returned_objects=["last_active_drawing"])
if not conflictos.empty:
    bad=conflictos[conflictos["precision_coordenada"]!="VALIDA"]
    if not bad.empty:
        with st.expander(f"⚠️ Conflictos no dibujados por calidad de coordenadas ({len(bad)})"):
            st.warning("Los valores originales se conservan. No se corrigen automáticamente."); st.dataframe(bad[[c for c in ["id_conflicto","tipo_conflicto","vereda","lat","lon","precision_coordenada","descripcion"] if c in bad.columns]],use_container_width=True,hide_index=True)
if codigo_sel:
    fila=veredas_df[veredas_df["CODIGO_VER"].astype(str)==str(codigo_sel)].head(1)
    if not fila.empty:
        p=fila.iloc[0]; ev=eventos_f[eventos_f["codigo_ver_resuelto"].astype(str).str.strip()==str(codigo_sel).strip()] if "codigo_ver_resuelto" in eventos_f.columns else pd.DataFrame(); st.subheader(f"Ficha territorial — {p.get('NOMBRE_VER','')}"); q=st.columns(4); q[0].metric("Situaciones históricas",len(ev)); q[1].metric("Primera referencia",ev["anio"].min() if not ev.empty and "anio" in ev.columns else "—"); q[2].metric("Última referencia",ev["anio"].max() if not ev.empty and "anio" in ev.columns else "—"); q[3].metric("Área (ha)",p.get("AREA_HA","—")); st.write({"Vereda":p.get("NOMBRE_VER",""),"Código":p.get("CODIGO_VER",""),"Fuente":p.get("FUENTE",""),"Vigencia":p.get("VIGENCIA","")})
        if not conflictos.empty and "vereda" in conflictos.columns:
            cv=conflictos[conflictos["vereda"].astype(str).str.strip().str.upper()==str(p.get("NOMBRE_VER","")).strip().upper()]; st.markdown("**Conflictos operativos registrados en Google Sheets**")
            if not cv.empty:
                st.dataframe(cv[[c for c in ["id_conflicto","tipo_conflicto","vereda","descripcion","precision_coordenada","registrado_por"] if c in cv.columns]],use_container_width=True,hide_index=True)
            else:
                st.caption("No hay registros operativos asociados por nombre de vereda.")

st.divider()
st.subheader("Capacidad institucional — SADCI")
st.caption("Lectura sintética de la capacidad institucional disponible para responder, coordinar y sostener la gobernabilidad territorial.")
gd=st.session_state.get("google_data") or {}
sadci=gd.get("SADCI")
if isinstance(sadci,pd.DataFrame) and not sadci.empty:
    s=resumen_sadci(sadci) or {}
    k1,k2,k3,k4,k5=st.columns(5)
    k1.metric("Entidades",len(sadci)); k2.metric("Ejecución presupuestal",indicador_pct(s.get("ejecucion_presupuestal_pct"))); k3.metric("Cumplimiento PDT",indicador_pct(s.get("cumplimiento_pdt_pct"))); k4.metric("MEPI promedio",indicador_pct(s.get("calificacion_mepi"))); k5.metric("Personal",int(s.get("num_personal_planta",0)+s.get("num_personal_contratista",0)) if "num_personal_planta" in s or "num_personal_contratista" in s else "—")
    st.markdown("**Estado institucional por entidad**")
    vista=sadci.copy(); cols_vista=[c for c in ["id_entidad","nombre_entidad","presupuesto_anual_rural","num_personal_planta","num_personal_contratista","tiene_protocolo_articulacion","tramites_simplificados","frecuencia_rendicion_cuentas","nivel_digitalizacion","ejecucion_presupuestal_pct","cumplimiento_pdt_pct","existencia_instancias_participacion","calificacion_mepi"] if c in vista.columns]; st.dataframe(vista[cols_vista],use_container_width=True,hide_index=True)
    with st.expander("Ver detalle de capacidades y necesidades"):
        detalle=[c for c in ["nombre_entidad","protocolo","rendicion","estructura","capacitacion"] if c in sadci.columns]
        if detalle: st.dataframe(sadci[detalle],use_container_width=True,hide_index=True)
else:
    st.caption("Cargue Google Sheets para consultar SADCI.")

st.subheader("Articulación interinstitucional")
rel=gd.get("Relación Interinstitucional")
if isinstance(rel,pd.DataFrame):
    if rel.empty:
        st.info("La hoja está disponible pero todavía no contiene registros. Este espacio queda preparado para documentar relaciones, coordinación y rutas de respuesta entre actores institucionales.")
    else:
        st.caption("Registros disponibles para analizar coordinación, complementariedad y rutas de respuesta institucional.")
        st.dataframe(rel,use_container_width=True,hide_index=True)
else:
    st.caption("Cargue Google Sheets para consultar la relación interinstitucional.")

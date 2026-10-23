import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="SIGOber-Rural", page_icon="🗺️", layout="wide")
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PBOT_DIR = DATA_DIR / "PBOT2015"

PBOT_CAPAS = [("PBOT2015_ZONIFICACION_USO_SUELO_RURAL.geojson", "Zonificación de uso del suelo rural", ["UGOT", "Aptitud", "area_ha"]),("PBOT2015_PROTECCION_RURAL.geojson", "Suelos de protección rural", ["Aptitud", "Area_ha"]),("PBOT2015_PERIMETRO_EXPANSION.geojson", "Perímetro y expansión urbana", ["Tipo", "area_m2", "Id"]),("PBOT2015_TRATAMIENTOS_URBANOS.geojson", "Tratamientos urbanos", ["Tipo", "area_m2", "Id"]),("PBOT2015_ZONAS_HOMOGENEAS_URBANAS.geojson", "Zonas homogéneas urbanas", ["Tipo", "area_m2", "Id"]),("PBOT2015_PUNTOS_EXPANSION.geojson", "Puntos de expansión urbana", ["Tipo", "area_m2", "Id"]),("PBOT2015_MANZANAS_INSPECCIONES.geojson", "Manzanas e inspecciones", ["codigo", "sector_cat", "tipo_avalu", "Reporte"])]
GIGAPP_DIMENSIONES = {
    "Territorio": {"pregunta":"¿Dónde?", "descripcion":"Veredas como unidad de lectura territorial."},
    "Situaciones": {"pregunta":"¿Qué ocurre?", "descripcion":"Evidencia territorial documentada."},
    "Ordenamiento territorial": {"pregunta":"¿Qué territorio tenemos previsto?", "descripcion":"Lectura de las capas PBOT 2015."},
    "Cartografía social": {"pregunta":"¿Cómo lo interpreta la comunidad?", "descripcion":"Problemas, recursos y percepciones participativas."},
}
PBOT_PERSPECTIVA_DEFAULT = "PBOT2015_ZONIFICACION_USO_SUELO_RURAL.geojson"

CARTOGRAFIA_LOCAL = {
    "IGAC local — Vías y puentes": ("igac_vias.geojson", "#1769aa", 2.4),
    "IGAC local — Drenajes": ("igac_drenajes.geojson", "#168aad", 1.8),
    "IGAC local — Construcciones": ("igac_construcciones.geojson", "#9c2f2f", 1.2),
    "IGAC local — Curvas y piscinas": ("igac_curvas_piscinas.geojson", "#8c6d31", 1.0),
    "IGAC local — Bosque": ("igac_bosque.geojson", "#2e7d32", 1.0),
}

CARTOGRAFIA_OFICIAL = {
    # El servicio WMS de IGAC se publica bajo /server/services (no /server3/rest/services).
    "IGAC — Vías, puentes y límites viales (1:10.000)": {"tipo": "wms", "url": "https://mapas2.igac.gov.co/server3/services/carto/carto10000puertorico18592/MapServer/WMSServer", "layers": "6,8,9,10", "attribution": "IGAC · Cartografía básica Puerto Rico, Caquetá · 1:10.000"},
    "IGAC — Drenajes y cuerpos de agua (1:10.000)": {"tipo": "wms", "url": "https://mapas2.igac.gov.co/server3/services/carto/carto10000puertorico18592/MapServer/WMSServer", "layers": "13,14,17,18,20", "attribution": "IGAC · Cartografía básica Puerto Rico, Caquetá · 1:10.000"},
    "IGAC — Construcciones y zonas duras (1:10.000)": {"tipo": "wms", "url": "https://mapas2.igac.gov.co/server3/services/carto/carto10000puertorico18592/MapServer/WMSServer", "layers": "0,15,16", "attribution": "IGAC · Cartografía básica Puerto Rico, Caquetá · 1:10.000"},
    "IGAC — Curvas de nivel y bosque (1:10.000)": {"tipo": "wms", "url": "https://mapas2.igac.gov.co/server3/services/carto/carto10000puertorico18592/MapServer/WMSServer", "layers": "7,19", "attribution": "IGAC · Cartografía básica Puerto Rico, Caquetá · 1:10.000"},
    # UPRA publica caché de teselas ArcGIS; se consume como /tile/{z}/{y}/{x}, no como WMS.
    "UPRA — Frontera agrícola nacional (1:100.000)": {"tipo": "arcgis_tiles", "url": "https://geoservicios.upra.gov.co/arcgis/rest/services/ordenamiento_productivo/frontera_agricola/MapServer", "layers": "0", "attribution": "UPRA · Frontera agrícola nacional · 1:100.000"},
    "UPRA — Frontera agrícola condicionada": {"tipo": "arcgis_tiles", "url": "https://geoservicios.upra.gov.co/arcgis/rest/services/ordenamiento_productivo/frontera_agricola_frontera_agricola_condicionada/MapServer", "layers": "0", "attribution": "UPRA · Frontera agrícola y frontera agrícola condicionada"},
}


def comprobar_wms(url):
    """Comprueba capacidades WMS sin bloquear el mapa si falla el proveedor."""
    from urllib.parse import urlencode
    import xml.etree.ElementTree as ET
    separador = "&" if "?" in url else "?"
    consulta = urlencode({"service": "WMS", "request": "GetCapabilities", "version": "1.3.0"})
    req = urllib.request.Request(
        url + separador + consulta,
        headers={"User-Agent": "SIGOber-Rural/1.0 (catalogo cartografico)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as respuesta:
            contenido = respuesta.read(2_000_000)
        raiz = ET.fromstring(contenido)
        nombres = []
        for nodo in raiz.iter():
            if nodo.tag.endswith("}Layer") or nodo.tag == "Layer":
                nombre = next((h.text for h in nodo if h.tag.endswith("}Name") or h.tag == "Name"), None)
                if nombre:
                    nombres.append(nombre)
        return {"disponible": True, "capas": sorted(set(nombres)), "error": ""}
    except Exception as exc:
        return {"disponible": False, "capas": [], "error": f"{type(exc).__name__}: {exc}"}


def comprobar_servicio_cartografico(config):
    """Prueba el servicio real (metadatos y una imagen/tesela), no solo su URL."""
    from urllib.parse import urlencode
    resultado = {"metadatos": "sin comprobar", "imagen": "sin comprobar", "detalle": ""}
    try:
        if config.get("tipo") == "arcgis_tiles":
            base = config["url"].rstrip("/")
            req = urllib.request.Request(base + "?f=pjson", headers={"User-Agent": "SIGOber-Rural/1.0"})
            with urllib.request.urlopen(req, timeout=10) as respuesta:
                datos = json.loads(respuesta.read(1_500_000).decode("utf-8"))
            if datos.get("error"):
                raise RuntimeError(datos["error"].get("message", "Error REST ArcGIS"))
            resultado["metadatos"] = "OK"
            # Puerto Rico, Caquetá, aproximadamente zoom 10 / fila 507 / columna 298.
            req = urllib.request.Request(base + "/tile/10/507/298", headers={"User-Agent": "SIGOber-Rural/1.0"})
            with urllib.request.urlopen(req, timeout=10) as respuesta:
                tipo = respuesta.headers.get("Content-Type", "")
                contenido = respuesta.read(64)
            if not tipo.lower().startswith("image/"):
                raise RuntimeError("La tesela no devolvió una imagen; Content-Type=" + tipo)
            resultado["imagen"] = "OK (" + tipo + ")"
            resultado["detalle"] = "Tesela de prueba recibida (" + str(len(contenido)) + " bytes iniciales)."
        else:
            base = config["url"].rsplit("/WMSServer", 1)[0]
            rest = base.replace("/services/", "/rest/services/") + "?f=pjson"
            req = urllib.request.Request(rest, headers={"User-Agent": "SIGOber-Rural/1.0"})
            with urllib.request.urlopen(req, timeout=10) as respuesta:
                datos = json.loads(respuesta.read(1_500_000).decode("utf-8"))
            if datos.get("error"):
                raise RuntimeError(datos["error"].get("message", "Error REST ArcGIS"))
            resultado["metadatos"] = "OK"
            params = {
                "bbox": "-75.65,1.35,-74.75,2.35", "bboxSR": "4326", "imageSR": "4326",
                "size": "512,512", "format": "png32", "transparent": "true", "f": "image",
                "layers": "show:" + config["layers"].replace(",", ","),
            }
            url_imagen = base.rstrip("/") + "/export?" + urlencode(params)
            req = urllib.request.Request(url_imagen, headers={"User-Agent": "SIGOber-Rural/1.0"})
            with urllib.request.urlopen(req, timeout=15) as respuesta:
                tipo = respuesta.headers.get("Content-Type", "")
                contenido = respuesta.read(64)
            if not tipo.lower().startswith("image/"):
                raise RuntimeError("La petición de mapa no devolvió una imagen; Content-Type=" + tipo + "; respuesta=" + repr(contenido[:50]))
            resultado["imagen"] = "OK (" + tipo + ")"
            resultado["detalle"] = "Imagen de mapa generada por el servicio REST de IGAC."
    except Exception as exc:
        resultado["detalle"] = type(exc).__name__ + ": " + str(exc)
        if resultado["metadatos"] == "sin comprobar":
            resultado["metadatos"] = "FALLÓ"
        else:
            resultado["imagen"] = "FALLÓ"
    return resultado

def nombres_cartografia_local_disponible():
    """Solo ofrece en el selector las capas locales cuyos archivos existen."""
    carpeta = DATA_DIR / "cartografia_oficial" / "igac"
    return [
        nombre for nombre, (archivo, _, _) in CARTOGRAFIA_LOCAL.items()
        if (carpeta / archivo).is_file()
    ]


@st.cache_data(show_spinner=False)
def cargar_json(nombre):
    ruta=DATA_DIR/nombre
    if not ruta.exists(): return None
    with open(ruta,"r",encoding="utf-8") as f: return json.load(f)
@st.cache_data(show_spinner=False)
def cargar_pbot_capas():
    capas=[]
    for archivo,titulo,campos in PBOT_CAPAS:
        ruta=PBOT_DIR/archivo
        if not ruta.exists(): continue
        try:
            with open(ruta,"r",encoding="utf-8") as f: geo=json.load(f)
            if geo.get("type")=="FeatureCollection": capas.append((archivo,titulo,geo,campos))
        except Exception: continue
    return capas
@st.cache_data(show_spinner=False)
def cargar_eventos_locales():
    for nombre in ("SITUACIONES_TERRITORIALES_eventos.csv",):
        ruta=DATA_DIR/nombre
        if ruta.exists(): return pd.read_csv(ruta,dtype=str).fillna("")
    return pd.DataFrame()
@st.cache_data(show_spinner=False)
def cargar_veredas_topo():
    topo=cargar_json("veredas_puerto_rico.json")
    if not topo or topo.get("type")!="Topology" or "Veredas" not in topo.get("objects",{}): raise RuntimeError("No se encontró un TopoJSON válido con el objeto Veredas.")
    return topo
@st.cache_data(show_spinner=False)
def propiedades_veredas(topo): return pd.DataFrame([g.get("properties",{}) or {} for g in topo.get("objects",{}).get("Veredas",{}).get("geometries",[])]).fillna("")
@st.cache_data(show_spinner=False)
def resumenes_por_vereda(eventos):
    vacio=pd.DataFrame(columns=["codigo_ver_resuelto","SIGOber_situaciones","SIGOber_anios","SIGOber_tipos","SIGOber_confianza"])
    if eventos is None or eventos.empty or "codigo_ver_resuelto" not in eventos.columns: return vacio
    df=eventos.copy(); df["codigo_ver_resuelto"]=df["codigo_ver_resuelto"].astype(str).str.strip(); df=df[df["codigo_ver_resuelto"]!=""]
    if df.empty: return vacio
    def valores(col): return df[col].astype(str).str.strip() if col in df.columns else pd.Series("",index=df.index)
    df["_anio"],df["_tipo"],df["_conf"]=valores("anio"),valores("tipo_conflicto"),valores("confianza")
    def uniq(series): return ", ".join(sorted(x for x in series.unique() if x))
    return df.groupby("codigo_ver_resuelto",sort=False).agg(SIGOber_situaciones=("codigo_ver_resuelto","size"),SIGOber_anios=("_anio",uniq),SIGOber_tipos=("_tipo",uniq),SIGOber_confianza=("_conf",uniq)).reset_index()
def normalizar_conflictos(df):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy().fillna(""); out["lat_num"]=pd.to_numeric(out["lat"],errors="coerce") if "lat" in out.columns else pd.NA; out["lon_num"]=pd.to_numeric(out["lon"],errors="coerce") if "lon" in out.columns else pd.NA
    out["precision_coordenada"]="VALIDA"; out.loc[out[["lat_num","lon_num"]].isna().any(axis=1),"precision_coordenada"]="SIN_COORDENADA"
    inval=(out["lat_num"].abs()>90)|(out["lon_num"].abs()>180); out.loc[inval & out[["lat_num","lon_num"]].notna().all(axis=1),"precision_coordenada"]="REQUIERE_REVISION"; return out
def config_gsheets():
    try:
        c=st.secrets.get("connections",{}); x=c.get("gsheets",{}) if hasattr(c,"get") else {}; return dict(x) if hasattr(x,"items") else {}
    except Exception: return {}
def spreadsheet_id_desde_config(cfg):
    raw=str(cfg.get("spreadsheet","") or cfg.get("spreadsheet_url","")).strip(); m=re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)",raw); return m.group(1) if m else raw
@st.cache_data(ttl=300,max_entries=4,show_spinner=False)
def leer_google_hoja(nombre_hoja):
    from streamlit_gsheets import GSheetsConnection
    conn=st.connection("gsheets",type=GSheetsConnection); return conn.read(worksheet=nombre_hoja,ttl=300).fillna("")
def leer_google_sheets():
    resultado={}
    for hoja in ("Conflictos","Actores","SADCI","Relación Interinstitucional"):
        try: resultado[hoja]=leer_google_hoja(hoja)
        except Exception as e: resultado[hoja]=e
    return resultado
def popup_conflicto(row):
    v=lambda c: html.escape(str(row.get(c,"") or "")); return ("<div style='width:280px;font-family:Arial'><h4>Situación registrada</h4>" f"<b>ID:</b> {v('id_conflicto')}<br><b>Tipo:</b> {v('tipo_conflicto')}<br><b>Vereda:</b> {v('vereda')}<br><b>Descripción:</b> {v('descripcion')}<br><b>Registrado por:</b> {v('registrado_por')}<br><b>Estado coordenada:</b> {v('precision_coordenada')}<br><b>Lat/Lon fuente:</b> {v('lat')} / {v('lon')}</div>")
@st.cache_data(show_spinner=False,max_entries=32)
def preparar_topo_para_eventos(topo,resumen):
    copia=json.loads(json.dumps(topo)); tabla=resumen.set_index("codigo_ver_resuelto") if not resumen.empty else pd.DataFrame()
    for g in copia.get("objects",{}).get("Veredas",{}).get("geometries",[]):
        p=g.setdefault("properties",{}); codigo=str(p.get("CODIGO_VER","")).strip()
        if not tabla.empty and codigo in tabla.index:
            r=tabla.loc[codigo]; p["SIGOber_situaciones"]=int(r["SIGOber_situaciones"]); p["SIGOber_anios"]=str(r["SIGOber_anios"]); p["SIGOber_tipos"]=str(r["SIGOber_tipos"]); p["SIGOber_confianza"]=str(r["SIGOber_confianza"])
        else: p["SIGOber_situaciones"]=0; p["SIGOber_anios"]="Sin registros"; p["SIGOber_tipos"]="Sin registros"; p["SIGOber_confianza"]="Sin registros"
    return copia

def construir_mapa(topo,eventos_historicos,conflictos=None,codigo_seleccionado="",mostrar_conflictos=True,pbot_seleccionadas=(),perspectiva="Territorio",cartografia_oficial_seleccionada=(),cartografia_local_seleccionada=()):
    inicio=time.perf_counter(); resumen=resumenes_por_vereda(eventos_historicos); topo_mapa=preparar_topo_para_eventos(topo,resumen); conteo=resumen.set_index("codigo_ver_resuelto")["SIGOber_situaciones"].to_dict() if not resumen.empty else {}; perspectiva=perspectiva or "Territorio"
    m=folium.Map(location=[1.9123,-75.1842],zoom_start=10,tiles="OpenStreetMap",prefer_canvas=True)
    grupo_territorio=folium.FeatureGroup(name="Territorio — Veredas",show=True)
    folium.Marker([1.9123,-75.1842],tooltip="Puerto Rico, Caquetá").add_to(grupo_territorio)
    def estilo_territorio(feature):
        p=feature.get("properties",{}); codigo=str(p.get("CODIGO_VER","")).strip(); sel=bool(codigo) and codigo==str(codigo_seleccionado).strip()
        return {"fillColor":"#eeeeee","color":"#111111" if sel else "#555555","weight":2.8 if sel else .8,"fillOpacity":.22}
    folium.TopoJson(data=topo,object_path="objects.Veredas",name="Veredas",style_function=estilo_territorio,tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_VER","CODIGO_VER","AREA_HA","FUENTE"],aliases=["Vereda","Código","Área (ha)","Fuente cartográfica"],localize=True,sticky=True,labels=True,style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;"),show=True).add_to(grupo_territorio)
    grupo_territorio.add_to(m)
    grupo_situaciones=folium.FeatureGroup(name="Situaciones por vereda — capa temática",show=False)
    def estilo_situaciones(feature):
        p=feature.get("properties",{}); codigo=str(p.get("CODIGO_VER","")).strip(); n=int(conteo.get(codigo,0)); sel=bool(codigo) and codigo==str(codigo_seleccionado).strip()
        fill="#d73027" if n>=2 else ("#fc8d59" if n==1 else "#eeeeee"); opacity=.72 if n else .10
        return {"fillColor":fill,"color":"#111111" if sel else "#a94442","weight":2.8 if sel else (1.0 if n else .35),"fillOpacity":.78 if sel else opacity}
    folium.TopoJson(data=topo_mapa,object_path="objects.Veredas",name="Situaciones documentadas por vereda",style_function=estilo_situaciones,tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_VER","CODIGO_VER","SIGOber_situaciones","SIGOber_anios","SIGOber_tipos","SIGOber_confianza"],aliases=["Vereda","Código","Situaciones documentadas","Años","Tipos de situación","Confianza"],localize=True,sticky=True,labels=True,style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;"),show=True).add_to(grupo_situaciones)
    grupo_situaciones.add_to(m)
    if mostrar_conflictos and conflictos is not None and not conflictos.empty:
        validos=conflictos.loc[conflictos["precision_coordenada"].eq("VALIDA")]; grupo=folium.FeatureGroup(name="Conflictos — Google Sheets",show=True)
        for row in validos.itertuples(index=False):
            data=row._asdict(); folium.CircleMarker(location=[float(data["lat_num"]),float(data["lon_num"])],radius=7,weight=2,fill=True,fill_opacity=.85,tooltip=f"{data.get('tipo_conflicto','Situación')} — {data.get('vereda','')}",popup=folium.Popup(popup_conflicto(data),max_width=340)).add_to(grupo)
        grupo.add_to(m)
    aliases_pbot={"UGOT":"UGOT","Aptitud":"Aptitud","area_ha":"Área (ha)","Area_ha":"Área (ha)","Tipo":"Tipo","area_m2":"Área (m²)","Id":"ID","codigo":"Código","sector_cat":"Sector catastral","tipo_avalu":"Tipo avalúo","Reporte":"Reporte"}; disponibles={x[0]:x for x in cargar_pbot_capas()}
    for archivo in pbot_seleccionadas:
        capa=disponibles.get(archivo)
        if not capa: continue
        _,titulo,geo,campos_preferidos=capa; grupo_pbot=folium.FeatureGroup(name=f"{titulo} — PBOT 2015",show=True); features=geo.get("features",[]); props=(features[0].get("properties",{}) or {}) if features else {}; campos=[campo for campo in campos_preferidos if campo in props]; tooltip_pbot=folium.GeoJsonTooltip(fields=campos,aliases=[aliases_pbot.get(campo,campo) for campo in campos],localize=True,labels=True,sticky=True,style="background-color:white;color:#222;font-family:Arial;font-size:12px;padding:8px;") if campos else None; folium.GeoJson(geo,name=titulo,tooltip=tooltip_pbot).add_to(grupo_pbot); grupo_pbot.add_to(m)

    # Capas IGAC descargadas: el mapa puede seguir funcionando sin el servicio remoto.
    for nombre_capa in cartografia_local_seleccionada:
        config_local = CARTOGRAFIA_LOCAL.get(nombre_capa)
        if not config_local:
            continue
        archivo_local, color_local, grosor_local = config_local
        ruta_local = DATA_DIR / "cartografia_oficial" / "igac" / archivo_local
        if not ruta_local.exists():
            continue
        try:
            with open(ruta_local, "r", encoding="utf-8") as f:
                geo_local = json.load(f)
            if geo_local.get("type") != "FeatureCollection" or not geo_local.get("features"):
                continue
            grupo_local = folium.FeatureGroup(name=nombre_capa, show=True)
            folium.GeoJson(
                geo_local, name=nombre_capa,
                style_function=lambda feature, color=color_local, weight=grosor_local: {
                    "color": color, "weight": weight, "opacity": 0.9,
                    "fillColor": color, "fillOpacity": 0.18,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["_igac_layer_name"] if "_igac_layer_name" in (geo_local["features"][0].get("properties") or {}) else [],
                    aliases=["Capa IGAC"] if "_igac_layer_name" in (geo_local["features"][0].get("properties") or {}) else [],
                    sticky=True,
                ) if "_igac_layer_name" in (geo_local["features"][0].get("properties") or {}) else None,
            ).add_to(grupo_local)
            grupo_local.add_to(m)
        except (OSError, ValueError, TypeError):
            # Una capa local corrupta no debe impedir cargar el resto del mapa.
            continue

    for nombre_capa in cartografia_oficial_seleccionada:
        config = CARTOGRAFIA_OFICIAL.get(nombre_capa)
        if not config:
            continue
        if config.get("tipo") == "arcgis_tiles":
            # Teselas nativas de ArcGIS REST: orden {nivel}/{fila}/{columna}.
            folium.TileLayer(
                tiles=config["url"] + "/tile/{z}/{y}/{x}",
                name=nombre_capa, attr=config["attribution"],
                overlay=True, control=True, show=False,
                opacity=0.68, min_zoom=5, max_zoom=16,
            ).add_to(m)
        else:
            folium.raster_layers.WmsTileLayer(
                url=config["url"], name=nombre_capa, layers=config["layers"],
                fmt="image/png", transparent=True, overlay=True, control=True,
                version="1.1.1", attr=config["attribution"], show=False,
            ).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m); return m,time.perf_counter()-inicio

def resumen_sadci(sadci):
    if not isinstance(sadci,pd.DataFrame) or sadci.empty: return None
    out={}
    for c in ("presupuesto_anual_rural","num_personal_planta","num_personal_contratista","ejecucion_presupuestal_pct","cumplimiento_pdt_pct","calificacion_mepi"):
        if c in sadci.columns:
            vals=pd.to_numeric(sadci[c],errors="coerce").dropna()
            if not vals.empty: out[c]=float(vals.mean())
    return out

def indicador_pct(valor): return "—" if valor is None or pd.isna(valor) else f"{float(valor):.0f}%"

def mostrar_indicadores_sadci(sadci):
    r=resumen_sadci(sadci)
    st.markdown("<div class='sigo-section'>Indicadores SADCI</div>",unsafe_allow_html=True)
    if not r:
        st.caption("Sin datos SADCI disponibles para mostrar indicadores.")
        return
    a,b,c,d,e,f=st.columns(6)
    a.metric("Presupuesto rural",f"{r.get('presupuesto_anual_rural',0):,.0f}" if r.get("presupuesto_anual_rural") is not None else "—")
    b.metric("Personal planta",f"{r.get('num_personal_planta',0):.0f}" if r.get("num_personal_planta") is not None else "—")
    c.metric("Contratistas",f"{r.get('num_personal_contratista',0):.0f}" if r.get("num_personal_contratista") is not None else "—")
    d.metric("Ejecución",indicador_pct(r.get("ejecucion_presupuestal_pct")))
    e.metric("Cumplimiento PDT",indicador_pct(r.get("cumplimiento_pdt_pct")))
    f.metric("MEPI",f"{r.get('calificacion_mepi',0):.1f}" if r.get("calificacion_mepi") is not None else "—")

def mostrar_contexto_gobernabilidad(actores,sadci,relacion):
    st.markdown("<div class='sigo-section'>Gobernabilidad</div>",unsafe_allow_html=True)
    st.markdown("<div class='sigo-note'><b>Actores</b> + <b>Capacidades</b> → interpretación institucional → <b>Decisiones</b><br><span style='opacity:.72'>Estas dimensiones permanecen como contexto de gobernabilidad y no se convierten en capas geográficas hasta disponer de datos espaciales propios.</span></div>",unsafe_allow_html=True)
    a,b,c=st.columns(3); a.metric("Actores registrados",len(actores) if isinstance(actores,pd.DataFrame) else 0); r=resumen_sadci(sadci); b.metric("Ejecución",indicador_pct(r.get("ejecucion_presupuestal_pct")) if r else "—"); c.metric("Relaciones interinstitucionales",len(relacion) if isinstance(relacion,pd.DataFrame) else 0)

def contexto_interpretacion_ia(historicos,codigo_sel,dimension,pbot_seleccionadas,sadci):
    codigo=str(codigo_sel or "").strip()
    df=historicos.copy() if isinstance(historicos,pd.DataFrame) else pd.DataFrame()
    if codigo and "codigo_ver_resuelto" in df.columns:
        df=df[df["codigo_ver_resuelto"].astype(str).str.strip()==codigo]
    resumen={"dimension_seleccionada":dimension,"codigo_vereda":codigo or "Todas las veredas","situaciones":int(len(df)),"tipos":[],"anios":[],"fuente_situaciones":"SITUACIONES_TERRITORIALES_eventos.csv","pbot":[],"sadci":{}}
    for col,key in (("tipo_conflicto","tipos"),("anio","anios")):
        if col in df.columns: resumen[key]=sorted({str(x).strip() for x in df[col].tolist() if str(x).strip()})[:20]
    titulos={archivo:titulo for archivo,titulo,_,_ in cargar_pbot_capas()}
    resumen["pbot"]=[titulos.get(x,x) for x in pbot_seleccionadas]
    r=resumen_sadci(sadci)
    if r: resumen["sadci"]={k:round(v,2) for k,v in r.items()}
    return resumen

def interpretar_localmente(contexto):
    """Fallback determinista sin conexión ni API."""
    n=int(contexto.get("situaciones",0) or 0)
    vereda=str(contexto.get("codigo_vereda","Todas las veredas"))
    tipos=[str(x) for x in contexto.get("tipos",[]) if str(x).strip()]
    anios=[str(x) for x in contexto.get("anios",[]) if str(x).strip()]
    pbot=[str(x) for x in contexto.get("pbot",[]) if str(x).strip()]
    lineas=[f"Se registran {n} situaciones documentadas para {vereda}."]
    if tipos:
        lineas.append("Los tipos registrados incluyen: "+", ".join(tipos[:6])+".")
    if anios:
        lineas.append("La evidencia disponible comprende los años: "+", ".join(anios[:8])+".")
    if pbot:
        lineas.append("La lectura puede contrastarse con: "+", ".join(pbot[:4])+".")
    if contexto.get("sadci"):
        lineas.append("También hay indicadores institucionales SADCI disponibles como contexto de capacidad.")
    relaciones=[]
    if n and len(tipos)>1:
        relaciones.append("La coexistencia de distintos tipos de situación sugiere investigar si comparten factores territoriales, institucionales o temporales.")
    if n and len(anios)>1:
        relaciones.append("Los registros de varios años permiten investigar persistencias, cambios de concentración o secuencias temporales.")
    if n and pbot:
        relaciones.append("La superposición con el PBOT puede orientar una hipótesis sobre posibles relaciones entre situaciones y condiciones previstas por el ordenamiento; no demuestra causalidad.")
    if not relaciones:
        relaciones.append("La evidencia disponible no permite establecer causalidad; conviene ampliar o contrastar los datos antes de afirmar un patrón.")
    preguntas=[
        "¿La relación observada se mantiene al comparar otras veredas o periodos?",
        "¿Qué información adicional permitiría contrastar esta hipótesis?",
        "¿Qué fuente independiente podría confirmarla o refutarla?"
    ]
    texto=("### Síntesis territorial\n"+" ".join(lineas)+
           "\n\n### Relaciones e hipótesis para investigar\n"+
           "\n".join("- "+x for x in relaciones)+
           "\n\n### Preguntas para profundizar\n"+
           "\n".join("- "+x for x in preguntas)+
           "\n\n> **Interpretación local:** generada sin API y exclusivamente a partir de las evidencias estructuradas disponibles en SIGOber-Rural.")
    return texto,None

def interpretar_con_ia(contexto):
    cfg=st.secrets.get("openai",{}) if hasattr(st.secrets,"get") else {}
    api_key=str(cfg.get("api_key","") or st.secrets.get("OPENAI_API_KEY","")).strip()
    if not api_key:
        return interpretar_localmente(contexto)
    modelo=str(cfg.get("model","gpt-5.6-luna")).strip() or "gpt-5.6-luna"
    system=("Eres una capa de interpretación territorial de SIGOber-Rural. Usa EXCLUSIVAMENTE el JSON entregado. "
            "No inventes hechos, ubicaciones ni causalidades. Distingue evidencia, interpretación e hipótesis. "
            "Puedes proponer relaciones o hipótesis causales como líneas de investigación cuando surjan de patrones o coincidencias presentes en los datos, pero debes etiquetarlas claramente como hipótesis, no como hechos. "
            "Para cada hipótesis, explica brevemente qué evidencia del contexto la motiva y qué información adicional ayudaría a contrastarla. "
            "No conviertas correlación, coincidencia temporal o proximidad territorial en causalidad demostrada. "
            "No hagas recomendaciones de política pública ni tomes decisiones por la institución. "
            "Devuelve exactamente tres secciones breves en español: Síntesis territorial, Relaciones e hipótesis para investigar, Preguntas para profundizar. "
            "Las preguntas deben orientar investigación y verificación, no ordenar acciones. No uses información externa.")
    payload={"model":modelo,"input":[{"role":"system","content":system},{"role":"user","content":"Contexto controlado de SIGOber-Rural:\n"+json.dumps(contexto,ensure_ascii=False)}],"max_output_tokens":700}
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as response: data=json.loads(response.read().decode("utf-8"))
        texto=data.get("output_text","")
        if not texto:
            partes=[]
            for item in data.get("output",[]):
                for content in item.get("content",[]):
                    if content.get("type")=="output_text": partes.append(content.get("text",""))
            texto="\n".join(partes).strip()
        return texto or None,"La respuesta de IA no contenía texto utilizable."
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):
        return interpretar_localmente(contexto)

def panel_interpretacion_ia(historicos,codigo_sel,dimension,pbot_seleccionadas,sadci):
    st.markdown("### Interpretación asistida por IA")
    st.caption("La IA interpreta únicamente las evidencias que SIGOber-Rural le entrega; no agrega hechos externos.")
    if st.button("Interpretar con IA",key="interpretar_ia",use_container_width=True):
        contexto=contexto_interpretacion_ia(historicos,codigo_sel,dimension,pbot_seleccionadas,sadci)
        with st.spinner("Interpretando las evidencias seleccionadas…"):
            texto,error=interpretar_con_ia(contexto)
        if texto:
            st.session_state["ia_resultado"]={"texto":texto,"contexto":contexto}
        else:
            st.warning(error)
    resultado=st.session_state.get("ia_resultado")
    if resultado:
        st.markdown(resultado["texto"])
        st.caption("Fuentes utilizadas: situaciones territoriales locales, capas PBOT seleccionadas y/o indicadores SADCI disponibles. La interpretación no agrega hechos que no estén presentes en las fuentes.")

st.markdown("""<style>
.sigo-hero{padding:1.05rem 1.25rem 1.15rem;border:1px solid rgba(128,128,128,.22);border-radius:1.05rem;background:linear-gradient(118deg,rgba(31,91,75,.13),rgba(91,128,108,.025));margin:.2rem 0 1rem}
.sigo-kicker{font-size:.72rem;font-weight:760;letter-spacing:.14em;text-transform:uppercase;opacity:.65}
.sigo-title{font-size:2.45rem;font-weight:830;line-height:1.04;margin:.18rem 0 .4rem}
.sigo-subtitle{font-size:1rem;opacity:.78;max-width:920px}
.sigo-section{margin-top:.75rem;margin-bottom:.25rem;font-size:1.12rem;font-weight:760}
.sigo-note{padding:.8rem 1rem;border-radius:.8rem;border:1px solid rgba(128,128,128,.2);background:rgba(128,128,128,.045)}
.sigo-nav-card{padding:.8rem .9rem;border:1px solid rgba(128,128,128,.2);border-radius:.8rem;background:rgba(128,128,128,.025);min-height:94px}
.sigo-nav-title{font-weight:750;font-size:1rem;margin-bottom:.2rem}
.sigo-nav-desc{font-size:.82rem;opacity:.72}
.gigapp-card{padding:.35rem .5rem;border:1px solid rgba(128,128,128,.18);border-radius:.55rem;background:rgba(128,128,128,.025);margin-bottom:.3rem}
.gigapp-card h4{margin:0;font-size:.86rem}.gigapp-q{font-size:.72rem;opacity:.62}
.gigapp-card p{margin:.12rem 0 0;font-size:.74rem;opacity:.7}
.gigapp-caption{font-size:.82rem;opacity:.72;text-align:center;margin:.1rem auto .6rem;max-width:680px}
div[data-testid="stMetric"]{padding:.55rem .7rem;border:1px solid rgba(128,128,128,.17);border-radius:.72rem;background:rgba(128,128,128,.03)}
div[data-testid="stMetricLabel"]{font-size:.83rem}
</style>""",unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### SIGOber-Rural")
    modo_presentacion=st.toggle("Modo exploración 2026",value=False,help="Presentación narrativa alrededor del territorio.")
    st.divider()
    st.caption("Puerto Rico · Caquetá")
    st.caption("Rama de desarrollo: Develope")
st.markdown("<div class='sigo-hero'><div class='sigo-kicker'>Sistema de información territorial · versión en preparación</div><div class='sigo-title'>SIGOber-Rural</div><div class='sigo-subtitle'>Una lectura integrada de la gobernabilidad rural de Puerto Rico, Caquetá: territorio, situaciones documentadas, ordenamiento y capacidades institucionales.</div></div>",unsafe_allow_html=True)

st.markdown("### Explora los módulos")
nav1, nav2, nav3 = st.columns(3, gap="medium")
with nav1:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>🗺️ Ordenamiento territorial</div><div class='sigo-nav-desc'>Consulta capas de formulación del PBOT 2015, manteniendo su fecha y procedencia.</div></div>", unsafe_allow_html=True)
    st.page_link("pages/02_Ordenamiento_PBOT2015.py", label="Abrir PBOT 2015", icon="🧭")
with nav2:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>🧩 Cartografía social</div><div class='sigo-nav-desc'>Importa registros participativos y revisa su calidad técnica antes de validarlos.</div></div>", unsafe_allow_html=True)
    st.page_link("pages/03_Cartografia_Social.py", label="Abrir cartografía social", icon="📍")
with nav3:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>📊 Indicadores SADCI</div><div class='sigo-nav-desc'>Explora metas, resultados reproducidos, fichas metodológicas y disponibilidad veredal.</div></div>", unsafe_allow_html=True)
    st.page_link("pages/04_Indicadores_SADCI.py", label="Abrir indicadores SADCI", icon="📈")
st.caption("La vista principal está dedicada a la exploración territorial. Los datos se muestran según su fuente y disponibilidad; no se completan vacíos mediante estimaciones no documentadas.")

with st.expander("📡 Captura territorial offline", expanded=False):
    st.markdown("**Capture evidencia directamente en el territorio, incluso con conectividad limitada.**")
    st.caption("El formulario funciona desconectado, guarda los registros localmente en el dispositivo y permite sincronizarlos cuando se recupera la conexión.")
    formulario_path=BASE_DIR/"app"/"captura_offline.html"
    if formulario_path.exists():
        with open(formulario_path,"rb") as f:
            st.download_button("⬇️ Descargar formulario de captura offline",data=f.read(),file_name="captura_offline.html",mime="text/html",use_container_width=True)
    else:
        st.caption("Formulario de captura no disponible.")
try:
    topo=cargar_veredas_topo()
except (OSError, ValueError, RuntimeError, KeyError) as exc:
    st.error("No fue posible cargar la cartografía base de veredas.")
    st.caption("La exploración del mapa necesita un TopoJSON válido con el objeto Veredas.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()
historicos=cargar_eventos_locales()
if historicos is None:
    historicos=pd.DataFrame()
if "google_data" not in st.session_state:
    with st.spinner("Conectando con las fuentes territoriales…"): st.session_state["google_data"]=leer_google_sheets()
gd=st.session_state["google_data"]
if not modo_presentacion:
    num_veredas_situacion=historicos["codigo_ver_resuelto"].nunique() if not historicos.empty and "codigo_ver_resuelto" in historicos.columns else 0; num_conflictos=len(gd["Conflictos"]) if isinstance(gd.get("Conflictos"),pd.DataFrame) else 0; num_actores=len(gd["Actores"]) if isinstance(gd.get("Actores"),pd.DataFrame) else 0
    a,b,c,d=st.columns(4)
    a.metric("Situaciones históricas",len(historicos),help="Registros del archivo territorial local; no equivale necesariamente al total de hechos ocurridos.")
    b.metric("Veredas con registros",num_veredas_situacion,help="Veredas con al menos un registro asociado en la base territorial local.")
    c.metric("Conflictos en Sheets",num_conflictos if isinstance(gd.get("Conflictos"),pd.DataFrame) else "—",help="Guion significa que la hoja no pudo consultarse; no representa cero registros.")
    d.metric("Actores registrados",num_actores if isinstance(gd.get("Actores"),pd.DataFrame) else "—",help="Guion significa que la hoja no pudo consultarse; no representa cero actores.")
    mostrar_indicadores_sadci(gd.get("SADCI"))
    st.markdown("<div class='sigo-note'><b>Lectura de gobernabilidad:</b> SIGOber-Rural organiza el territorio alrededor de situaciones, ordenamiento y conocimiento comunitario, manteniendo actores y capacidades como información institucional separada.</div>",unsafe_allow_html=True)
    with st.expander("🔧 Diagnóstico de fuentes y rendimiento"):
        cfg=config_gsheets()
        sid=spreadsheet_id_desde_config(cfg)
        hojas=("Conflictos","Actores","SADCI","Relación Interinstitucional")
        hojas_ok=[nombre for nombre in hojas if isinstance(gd.get(nombre),pd.DataFrame)]
        st.write({
            "Cartografía base":"Disponible",
            "Eventos territoriales":f"{len(historicos)} registros",
            "Hojas institucionales disponibles":f"{len(hojas_ok)} de {len(hojas)}",
            "Identificador de hoja":(sid[:6]+"…"+sid[-4:]) if sid else "No configurado",
        })
        for nombre in hojas:
            valor=gd.get(nombre)
            if isinstance(valor,pd.DataFrame):
                st.success(f"{nombre}: disponible ({len(valor)} registros)")
            else:
                st.warning(f"{nombre}: no disponible en esta sesión")
                if isinstance(valor,Exception):
                    st.caption(f"Detalle: {type(valor).__name__}: {valor}")
        if st.button("Actualizar fuentes",key="actualizar_fuentes"):
            leer_google_hoja.clear()
            cargar_eventos_locales.clear()
            cargar_veredas_topo.clear()
            st.session_state["google_data"]=leer_google_sheets()
            st.rerun()
else:
    mostrar_indicadores_sadci(gd.get("SADCI"))
veredas_df=propiedades_veredas(topo); nombres=veredas_df[["CODIGO_VER","NOMBRE_VER"]].drop_duplicates().copy(); nombres["etiqueta"]=nombres["NOMBRE_VER"].astype(str)+" — "+nombres["CODIGO_VER"].astype(str); opciones=["Todas las veredas"]+sorted(nombres["etiqueta"].tolist())

@st.fragment
def render_mapa_interactivo():
    if modo_presentacion:
        if "gigapp_dimension" not in st.session_state or st.session_state["gigapp_dimension"] not in GIGAPP_DIMENSIONES: st.session_state["gigapp_dimension"]="Territorio"
        left,center,right=st.columns([1.0,4.8,1.8],gap="medium")
        with left:
            st.markdown("### Selección")
            st.caption("Partes y secciones")
            dimension=st.selectbox("Perspectiva",list(GIGAPP_DIMENSIONES.keys()),index=list(GIGAPP_DIMENSIONES.keys()).index(st.session_state["gigapp_dimension"]),label_visibility="collapsed")
            st.session_state["gigapp_dimension"]=dimension
            st.caption(GIGAPP_DIMENSIONES[dimension]["pregunta"])
            st.divider()
            st.markdown("**Vereda**")
            seleccion=st.selectbox("Vereda",opciones,label_visibility="collapsed")
            codigo_sel="" if seleccion=="Todas las veredas" else seleccion.split(" — ")[-1]
            st.divider()
            st.markdown("**Capas PBOT 2015**")
            cartografia_oficial_seleccionada=st.multiselect("Cartografía oficial remota",options=list(CARTOGRAFIA_OFICIAL.keys()),default=[],key="cartografia_oficial_presentacion",help="Servicios remotos IGAC/UPRA; requieren conectividad y WMS disponible.")
            cartografia_local_disponible=nombres_cartografia_local_disponible(); cartografia_local_seleccionada=st.multiselect("Cartografía IGAC descargada (local)",options=cartografia_local_disponible,default=[],key="cartografia_local_presentacion",help="Solo aparecen archivos GeoJSON locales que existen en data/cartografia_oficial/igac/.")
            if not cartografia_local_disponible: st.caption("Aún no hay capas IGAC locales. Consulta docs/descarga_cartografia_igac.md para descargarlas.")
            pbot_opciones={archivo:titulo for archivo,titulo,_,_ in cargar_pbot_capas()}
            pbot_seleccionadas=st.multiselect("Capas",options=list(pbot_opciones.keys()),format_func=lambda x:pbot_opciones[x],default=[],label_visibility="collapsed",help="Seleccione una o varias capas PBOT. Cada una queda disponible individualmente en el control del mapa.")
        with center:
            conflictos=normalizar_conflictos(gd["Conflictos"]) if isinstance(gd.get("Conflictos"),pd.DataFrame) else pd.DataFrame()
            mapa,segundos_mapa=construir_mapa(topo,historicos,conflictos,codigo_sel,True,tuple(pbot_seleccionadas),perspectiva="Territorio",cartografia_oficial_seleccionada=tuple(cartografia_oficial_seleccionada),cartografia_local_seleccionada=tuple(cartografia_local_seleccionada))
            st_folium(mapa,width="100%",height=720,returned_objects=["last_active_drawing"])
        with right:
            with st.container(height=500,border=True):
                panel_interpretacion_ia(historicos,codigo_sel,dimension,tuple(pbot_seleccionadas),gd.get("SADCI"))
    else:
        st.markdown("<div class='sigo-section'>Explorar territorio</div>",unsafe_allow_html=True); st.caption("Seleccione una vereda y, si lo necesita, filtre las situaciones documentadas. Las capas PBOT se mantienen opcionales para conservar fluidez."); seleccion=st.selectbox("Vereda",opciones,label_visibility="collapsed"); codigo_sel="" if seleccion=="Todas las veredas" else seleccion.split(" — ")[-1]; f1,f2,f3,f4=st.columns(4); eventos_f=historicos.copy()
        if not eventos_f.empty:
            anios=sorted([x for x in eventos_f.get("anio",pd.Series(dtype=str)).astype(str).unique() if x],reverse=True); ys=f1.multiselect("Año",anios,default=[]); tipos=sorted([x for x in eventos_f.get("tipo_conflicto",pd.Series(dtype=str)).astype(str).unique() if x]); ts=f2.multiselect("Tipo de situación",tipos,default=[]); confs=sorted([x for x in eventos_f.get("confianza",pd.Series(dtype=str)).astype(str).unique() if x]); cs=f3.multiselect("Confianza",confs,default=[])
            if ys: eventos_f=eventos_f[eventos_f["anio"].astype(str).isin(ys)]
            if ts: eventos_f=eventos_f[eventos_f["tipo_conflicto"].astype(str).isin(ts)]
            if cs: eventos_f=eventos_f[eventos_f["confianza"].astype(str).isin(cs)]
        mostrar=f4.checkbox("Mostrar conflictos de Sheets",value=True); pbot_opciones={archivo:titulo for archivo,titulo,_,_ in cargar_pbot_capas()}; pbot_seleccionadas=st.multiselect("Capas PBOT 2015 (opcional)",options=list(pbot_opciones.keys()),format_func=lambda x:pbot_opciones[x],default=[],help="Las capas PBOT no se cargan al navegador hasta que se seleccionan."); cartografia_oficial_seleccionada=st.multiselect("Cartografía oficial remota (opcional)",options=list(CARTOGRAFIA_OFICIAL.keys()),default=[],key="cartografia_oficial_exploracion",help="Servicios remotos IGAC/UPRA; requieren conectividad y WMS disponible."); cartografia_local_disponible=nombres_cartografia_local_disponible(); cartografia_local_seleccionada=st.multiselect("Cartografía IGAC descargada (local)",options=cartografia_local_disponible,default=[],key="cartografia_local_exploracion",help="Solo aparecen archivos GeoJSON locales que existen en data/cartografia_oficial/igac/.");
        if not cartografia_local_disponible: st.caption("Aún no hay capas IGAC locales. Consulta docs/descarga_cartografia_igac.md para descargarlas.")
        st.caption("Capa histórica: SITUACIONES_TERRITORIALES. Puntos: registros operativos de la hoja Conflictos. Las fuentes se mantienen separadas.")
        with st.expander("Diagnóstico de servicios cartográficos oficiales"):
            st.caption("Prueba metadatos y una imagen/tesela real desde el entorno donde se ejecuta SIGOber-Rural.")
            if st.button("Probar cada servicio cartográfico", key="comprobar_wms_oficial"):
                for nombre, config in CARTOGRAFIA_OFICIAL.items():
                    resultado = comprobar_servicio_cartografico(config)
                    st.markdown("**" + nombre + "**")
                    st.write({"metadatos": resultado["metadatos"], "imagen/tesela": resultado["imagen"], "detalle": resultado["detalle"]})

        st.caption("Ordenamiento Territorial — cartografía de formulación PBOT 2015. No implica actualización al PBOT 2023."); conflictos=normalizar_conflictos(gd["Conflictos"]) if isinstance(gd.get("Conflictos"),pd.DataFrame) else pd.DataFrame(); mapa,segundos_mapa=construir_mapa(topo,eventos_f,conflictos,codigo_sel,mostrar,tuple(pbot_seleccionadas),perspectiva="Territorio",cartografia_oficial_seleccionada=tuple(cartografia_oficial_seleccionada),cartografia_local_seleccionada=tuple(cartografia_local_seleccionada)); st.caption(f"Generación del mapa en servidor: {segundos_mapa:.2f} s"); st_folium(mapa,width="100%",height=650,returned_objects=["last_active_drawing"])
render_mapa_interactivo()
st.markdown("### Cómo leer el mapa")
leyenda1,leyenda2,leyenda3=st.columns(3)
with leyenda1:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>🗺️ Territorio</div><div class='sigo-nav-desc'>Límites y atributos de veredas según la cartografía base disponible.</div></div>",unsafe_allow_html=True)
with leyenda2:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>🟠🔴 Situaciones documentadas</div><div class='sigo-nav-desc'>En la capa temática: naranja = un registro; rojo = dos o más registros asociados a la vereda.</div></div>",unsafe_allow_html=True)
with leyenda3:
    st.markdown("<div class='sigo-nav-card'><div class='sigo-nav-title'>🧭 Capas de referencia</div><div class='sigo-nav-desc'>Las capas PBOT 2015 e IGAC/UPRA se activan por separado y conservan su procedencia.</div></div>",unsafe_allow_html=True)
st.info("Un polígono sin registros asociados solo indica que la base consultada no contiene registros enlazados a esa vereda. No demuestra que allí no ocurran situaciones. Las capas PBOT corresponden a cartografía de formulación de 2015; las capas oficiales remotas requieren conexión y disponibilidad del proveedor.")
st.caption("SIGOber-Rural · versión 1.0 en preparación · Puerto Rico, Caquetá")
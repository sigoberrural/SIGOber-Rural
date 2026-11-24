#!/usr/bin/env python3
"""Descarga cartografía IGAC de Puerto Rico (Caquetá) a GeoJSON local.

Uso:
  python scripts/descargar_cartografia_igac.py --grupo vias
  python scripts/descargar_cartografia_igac.py --grupo todos

Solo usa la biblioteca estándar de Python. Los archivos se escriben en
data/cartografia_oficial/igac/ y no alteran los datos de veredas ni el PBOT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://mapas2.igac.gov.co/server3/rest/services/carto/carto10000puertorico18592/MapServer"
SALIDA = Path(__file__).resolve().parents[1] / "data" / "cartografia_oficial" / "igac"
# Envolvente de trabajo amplia alrededor de Puerto Rico, Caquetá (EPSG:4326).
BBOX = (-75.65, 1.35, -74.75, 2.35)
TAMANO_PAGINA = 1000

GRUPOS = {
    "vias": {"archivo": "igac_vias.geojson", "capas": [6, 8, 9, 10]},
    "drenajes": {"archivo": "igac_drenajes.geojson", "capas": [13, 14, 17, 18]},
    "construcciones": {"archivo": "igac_construcciones.geojson", "capas": [0, 15, 16]},
    "curvas_piscinas": {"archivo": "igac_curvas_piscinas.geojson", "capas": [7, 19]},
    "bosque": {"archivo": "igac_bosque.geojson", "capas": [20]},
}
NOMBRES_CAPA = {
    0: "Construccion_P", 6: "Puente_L", 7: "Curva_Nivel", 8: "Via",
    9: "Vias", 10: "Limite_Via", 13: "Drenaje_L", 14: "Drenaje",
    15: "Construccion_R", 16: "Zona_Dura", 17: "Drenaje_R",
    18: "Deposito_Agua_R", 19: "Piscina", 20: "Bosque",
}


def solicitar_json(url: str, timeout: int = 40) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SIGOber-Rural/1.0 (descarga cartografia oficial)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as respuesta:
            cuerpo = respuesta.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo consultar IGAC: {exc}") from exc
    try:
        datos = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"IGAC no devolvió JSON válido para {url}") from exc
    if datos.get("error"):
        error = datos["error"]
        raise RuntimeError(f"IGAC REST {error.get('code')}: {error.get('message')}")
    return datos


def consultar_capa(layer_id: int) -> tuple[list[dict], dict]:
    url_capa = f"{BASE}/{layer_id}"
    meta = solicitar_json(url_capa + "?f=pjson")
    if meta.get("type") != "Feature Layer":
        raise RuntimeError(f"La capa {layer_id} no es una capa de entidades.")
    object_id = meta.get("objectIdField") or meta.get("objectIdFieldName") or "OBJECTID"
    acumuladas: list[dict] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "geometry": ",".join(map(str, BBOX)),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "resultOffset": str(offset),
            "resultRecordCount": str(TAMANO_PAGINA),
            "orderByFields": object_id,
        }
        url = url_capa + "/query?" + urllib.parse.urlencode(params)
        pagina = solicitar_json(url)
        features = pagina.get("features", [])
        if not isinstance(features, list):
            raise RuntimeError(f"Respuesta inesperada al consultar la capa {layer_id}.")
        for feature in features:
            properties = feature.setdefault("properties", {})
            properties["_igac_layer_id"] = layer_id
            properties["_igac_layer_name"] = NOMBRES_CAPA.get(layer_id, str(layer_id))
        acumuladas.extend(features)
        print(f"  Capa {layer_id} ({NOMBRES_CAPA.get(layer_id, 'sin nombre')}): {len(acumuladas)} entidades", flush=True)
        if not features or len(features) < TAMANO_PAGINA:
            break
        offset += len(features)
        time.sleep(0.15)
    return acumuladas, meta


def descargar(grupo: str) -> dict:
    config = GRUPOS[grupo]
    todas: list[dict] = []
    resumen_capas = []
    for layer_id in config["capas"]:
        features, meta = consultar_capa(layer_id)
        todas.extend(features)
        resumen_capas.append({
            "id": layer_id,
            "nombre": NOMBRES_CAPA.get(layer_id, str(layer_id)),
            "geometria": meta.get("geometryType"),
            "entidades": len(features),
        })
    geojson = {
        "type": "FeatureCollection",
        "name": grupo,
        "features": todas,
        "metadata": {
            "fuente": "Instituto Geográfico Agustín Codazzi (IGAC)",
            "servicio": BASE,
            "grupo": grupo,
            "bbox_epsg4326": list(BBOX),
            "descargado_utc": datetime.now(timezone.utc).isoformat(),
            "capas": resumen_capas,
            "nota": "Descarga filtrada por envolvente; verificar cobertura antes de análisis.",
        },
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / config["archivo"]
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_text(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporal.replace(destino)
    digest = hashlib.sha256(destino.read_bytes()).hexdigest()
    print(f"Guardado: {destino} ({len(todas)} entidades; SHA-256 {digest})")
    return {
        "grupo": grupo,
        "archivo": str(destino.relative_to(Path(__file__).resolve().parents[1])),
        "entidades": len(todas),
        "sha256": digest,
        "capas": resumen_capas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grupo", choices=[*GRUPOS, "todos"], default="todos")
    args = parser.parse_args()
    print(f"Servicio: {BASE}")
    servicio = solicitar_json(BASE + "?f=pjson")
    if servicio.get("error"):
        raise SystemExit(f"El servicio IGAC no está disponible: {servicio['error']}")
    print(f"Servicio disponible; versión ArcGIS {servicio.get('currentVersion')}")
    grupos = list(GRUPOS) if args.grupo == "todos" else [args.grupo]
    resultados = []
    for grupo in grupos:
        print(f"\nDescargando grupo: {grupo}")
        try:
            resultados.append(descargar(grupo))
        except Exception as exc:
            print(f"ERROR en {grupo}: {type(exc).__name__}: {exc}")
    manifiesto = {
        "fuente": BASE,
        "consultado_utc": datetime.now(timezone.utc).isoformat(),
        "bbox_epsg4326": list(BBOX),
        "resultados": resultados,
        "grupos_solicitados": grupos,
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "manifiesto_descarga.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if len(resultados) != len(grupos):
        raise SystemExit("La descarga terminó parcialmente; revisar errores y manifiesto.")
    print(f"\nDescarga terminada: {len(resultados)} grupo(s). Manifiesto actualizado.")


if __name__ == "__main__":
    main()

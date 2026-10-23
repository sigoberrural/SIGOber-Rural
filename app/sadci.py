"""Funciones reproducibles para calcular y validar indicadores SADCI."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "indicadores_sadci.json"

def cargar_catalogo(ruta: str | Path = CATALOG_PATH) -> list[dict[str, Any]]:
    with Path(ruta).open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("El catálogo SADCI debe ser una lista.")
    errores = validar_catalogo(datos)
    if errores:
        raise ValueError("Catálogo inválido: " + "; ".join(x["detalle"] for x in errores[:5]))
    return datos

def validar_catalogo(indicadores: list[dict[str, Any]]) -> list[dict[str, str]]:
    hallazgos, vistos = [], set()
    requeridos = {"codigo","nombre","dimension","formula","numerador","denominador","valor_numerador","valor_denominador","operador_meta","valor_meta","direccion","fuentes","responsable","periodicidad","escala"}
    for i, item in enumerate(indicadores, 1):
        codigo = str(item.get("codigo", "")).strip() or f"fila_{i}"
        for campo in sorted(requeridos - set(item)):
            hallazgos.append({"codigo":codigo,"tipo":"CAMPO_AUSENTE","detalle":f"Falta el campo obligatorio: {campo}."})
        if codigo in vistos:
            hallazgos.append({"codigo":codigo,"tipo":"CODIGO_DUPLICADO","detalle":"El código aparece más de una vez."})
        vistos.add(codigo)
        if item.get("direccion") not in {"mayor_es_mejor","menor_es_mejor"}:
            hallazgos.append({"codigo":codigo,"tipo":"DIRECCION_INVALIDA","detalle":"Dirección de mejora inválida."})
        if item.get("operador_meta") not in {">",">=","<","<="}:
            hallazgos.append({"codigo":codigo,"tipo":"OPERADOR_INVALIDO","detalle":"Operador de meta inválido."})
        try:
            n, d = float(item.get("valor_numerador")), float(item.get("valor_denominador"))
            if d <= 0:
                hallazgos.append({"codigo":codigo,"tipo":"DENOMINADOR_NO_POSITIVO","detalle":"El denominador debe ser mayor que cero."})
            if n < 0 or d < 0:
                hallazgos.append({"codigo":codigo,"tipo":"VALOR_NEGATIVO","detalle":"Revisar valores negativos."})
        except (TypeError, ValueError):
            hallazgos.append({"codigo":codigo,"tipo":"VALOR_NO_NUMERICO","detalle":"Numerador y denominador deben ser numéricos."})
    return hallazgos

def calcular_porcentaje(numerador: Any, denominador: Any) -> float | None:
    try:
        n, d = float(numerador), float(denominador)
    except (TypeError, ValueError):
        return None
    if d <= 0 or n < 0 or d < 0:
        return None
    return n / d * 100.0

def cumple_meta(valor: float | None, operador: str, umbral: float) -> bool | None:
    if valor is None:
        return None
    operaciones = {">":lambda a,b:a>b, ">=":lambda a,b:a>=b, "<":lambda a,b:a<b, "<=":lambda a,b:a<=b}
    if operador not in operaciones:
        raise ValueError(f"Operador de meta no admitido: {operador}")
    return bool(operaciones[operador](valor, float(umbral)))

def evaluar_indicador(indicador: dict[str, Any]) -> dict[str, Any]:
    resultado = dict(indicador)
    porcentaje = calcular_porcentaje(indicador.get("valor_numerador"), indicador.get("valor_denominador"))
    meta = cumple_meta(porcentaje, indicador.get("operador_meta", ""), indicador.get("valor_meta", 0))
    resultado["resultado_calculado_pct"] = porcentaje
    resultado["diferencia_fuente_pp"] = (float(indicador["resultado_fuente_pct"]) - porcentaje if porcentaje is not None and indicador.get("resultado_fuente_pct") not in (None, "") else None)
    resultado["meta_cumplida"] = meta
    resultado["estado_meta"] = "SIN DATOS" if meta is None else ("CUMPLE META" if meta else "NO CUMPLE META")
    original = str(indicador.get("semaforo_fuente", "")).strip().upper()
    resultado["semaforo_fuente_requiere_revision"] = original == "VERDE" and meta is False
    resultado["estado_dato"] = indicador.get("estado_dato", "PENDIENTE_VERIFICACION")
    return resultado

def evaluar_catalogo(indicadores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [evaluar_indicador(x) for x in indicadores]

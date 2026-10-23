"""Plantillas y validaciones para la ingesta estructurada de SIGOber-Rural."""
from __future__ import annotations

from io import BytesIO
import json
from typing import Any

import pandas as pd

CAMPOS_PROBLEMATICAS = [
    "id_registro", "codigo_ver", "vereda", "categoria", "subcategoria",
    "descripcion", "fecha", "latitud", "longitud", "fuente",
    "referencia_evidencia", "tipo_fuente", "organizacion_aportante",
    "estado_validacion", "observaciones",
]
CAMPOS_SADCI = [
    "codigo", "periodo", "valor_numerador", "valor_denominador",
    "fuentes", "responsable", "fecha_corte", "observaciones",
    "estado_dato",
]


def crear_excel_plantilla(tipo: str, catalogo: list[dict[str, Any]] | None = None) -> bytes:
    """Devuelve una plantilla XLSX con instrucciones y columnas estables."""
    if tipo == "problematicas":
        columnas = CAMPOS_PROBLEMATICAS
        ejemplo = {
            "id_registro": "PS-0001", "codigo_ver": "", "vereda": "",
            "categoria": "", "subcategoria": "", "descripcion": "",
            "fecha": "AAAA-MM-DD", "latitud": "", "longitud": "",
            "fuente": "", "referencia_evidencia": "", "tipo_fuente": "",
            "organizacion_aportante": "", "estado_validacion": "PENDIENTE",
            "observaciones": "",
        }
        instrucciones = [
            ["Plantilla de problemáticas sociales — SIGOber-Rural"],
            ["Una fila por registro. No invente códigos de vereda; use el catálogo territorial oficial."],
            ["La carga no certifica la veracidad. Mantenga la fuente y evidencia y deje estado_validacion en PENDIENTE."],
            ["Campos", "Descripción"],
            ["codigo_ver", "Código oficial de la vereda si está disponible."],
            ["categoria", "Categoría acordada por el equipo metodológico."],
            ["fecha", "Fecha del hecho o de observación, formato AAAA-MM-DD."],
            ["latitud / longitud", "Opcionales; coordenadas WGS84 si se conocen."],
        ]
    elif tipo == "sadci":
        columnas = CAMPOS_SADCI
        ejemplo = {
            "codigo": "TDN", "periodo": "2026", "valor_numerador": "",
            "valor_denominador": "", "fuentes": "", "responsable": "",
            "fecha_corte": "AAAA-MM-DD", "observaciones": "",
            "estado_dato": "PENDIENTE_VERIFICACION",
        }
        instrucciones = [
            ["Plantilla de actualización SADCI — SIGOber-Rural"],
            ["Una fila por indicador y periodo. El código debe existir en el catálogo SADCI."],
            ["Introduzca numerador y denominador; la aplicación calcula el porcentaje."],
            ["No cambie fórmulas, metas ni dirección del indicador desde esta plantilla."],
            ["Los registros importados quedan pendientes de verificación documental."],
        ]
        if catalogo:
            instrucciones += [["Códigos admitidos", ", ".join(str(x.get("codigo", "")) for x in catalogo)]]
    else:
        raise ValueError("Tipo de plantilla no admitido.")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([ejemplo], columns=columnas).to_excel(writer, sheet_name="Datos", index=False)
        pd.DataFrame(instrucciones).to_excel(writer, sheet_name="Instrucciones", index=False, header=False)
    return buffer.getvalue()


def leer_archivo_tabular(archivo: Any) -> pd.DataFrame:
    """Lee CSV o Excel sin mutar el archivo original."""
    nombre = str(getattr(archivo, "name", "")).lower()
    contenido = archivo.getvalue() if hasattr(archivo, "getvalue") else archivo
    if nombre.endswith(".csv"):
        return pd.read_csv(BytesIO(contenido), dtype=str, keep_default_na=False)
    if nombre.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(contenido), dtype=str).fillna("")
    raise ValueError("Formato no admitido: utiliza CSV o Excel (.xlsx).")


def validar_problematicas(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    errores = []
    for _, fila in resultado.iterrows():
        fila_errores = []
        for campo in ("id_registro", "vereda", "categoria", "descripcion", "fuente"):
            if campo not in resultado.columns or not str(fila.get(campo, "")).strip():
                fila_errores.append(f"Falta {campo}")
        if str(fila.get("fecha", "")).strip():
            try:
                pd.to_datetime(fila["fecha"], errors="raise")
            except (ValueError, TypeError):
                fila_errores.append("Fecha inválida")
        for campo, minimo, maximo in (("latitud", -90, 90), ("longitud", -180, 180)):
            valor = str(fila.get(campo, "")).strip()
            if valor:
                try:
                    numero = float(valor)
                    if not minimo <= numero <= maximo:
                        fila_errores.append(f"{campo} fuera de rango")
                except ValueError:
                    fila_errores.append(f"{campo} no numérico")
        errores.append("; ".join(fila_errores))
    resultado["errores_validacion"] = errores
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
    if "id_registro" in resultado.columns:
        duplicados = resultado["id_registro"].astype(str).duplicated(keep=False) & resultado["id_registro"].astype(str).ne("")
        resultado.loc[duplicados, "valido_revision_tecnica"] = False
        resultado.loc[duplicados, "errores_validacion"] = resultado.loc[duplicados, "errores_validacion"].map(
            lambda x: (x + "; " if x else "") + "ID duplicado"
        )
    return resultado


def validar_importacion_sadci(df: pd.DataFrame, catalogo: list[dict[str, Any]]) -> pd.DataFrame:
    """Valida filas de actualización sin escribir en el catálogo oficial."""
    resultado = df.copy()
    codigos = {str(item.get("codigo", "")).strip() for item in catalogo}
    errores = []
    for _, fila in resultado.iterrows():
        fila_errores = []
        codigo = str(fila.get("codigo", "")).strip()
        if not codigo:
            fila_errores.append("Falta codigo")
        elif codigo not in codigos:
            fila_errores.append("Código SADCI desconocido")
        if not str(fila.get("periodo", "")).strip():
            fila_errores.append("Falta periodo")
        for campo in ("valor_numerador", "valor_denominador"):
            valor = str(fila.get(campo, "")).strip()
            try:
                numero = float(valor)
                if numero < 0 or (campo == "valor_denominador" and numero <= 0):
                    fila_errores.append(f"{campo} fuera de rango")
            except ValueError:
                fila_errores.append(f"{campo} no numérico")
        errores.append("; ".join(fila_errores))
    resultado["errores_validacion"] = errores
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
    if "codigo" in resultado.columns:
        clave = resultado["codigo"].astype(str).str.strip() + "::" + resultado.get("periodo", pd.Series([""] * len(resultado), index=resultado.index)).astype(str).str.strip()
        duplicados = clave.duplicated(keep=False) & resultado["codigo"].astype(str).str.strip().ne("")
        resultado.loc[duplicados, "valido_revision_tecnica"] = False
        resultado.loc[duplicados, "errores_validacion"] = resultado.loc[duplicados, "errores_validacion"].map(
            lambda x: (x + "; " if x else "") + "Indicador y periodo duplicados"
        )
    return resultado


def aplicar_actualizacion_sadci(catalogo: list[dict[str, Any]], filas: pd.DataFrame, periodo: str | None = None) -> list[dict[str, Any]]:
    """Aplica datos de una importación validada solo a una copia en memoria."""
    salida = [dict(item) for item in catalogo]
    por_codigo = {str(item.get("codigo", "")): item for item in salida}
    for fila in filas.to_dict(orient="records"):
        codigo = str(fila.get("codigo", "")).strip()
        if codigo not in por_codigo:
            continue
        if periodo and str(fila.get("periodo", "")).strip() != periodo:
            continue
        destino = por_codigo[codigo]
        destino["valor_numerador"] = float(fila["valor_numerador"])
        destino["valor_denominador"] = float(fila["valor_denominador"])
        destino["fuentes"] = str(fila.get("fuentes", "")).strip() or destino.get("fuentes", "")
        destino["responsable"] = str(fila.get("responsable", "")).strip() or destino.get("responsable", "")
        destino["observaciones"] = str(fila.get("observaciones", "")).strip() or destino.get("observaciones", "")
        destino["estado_dato"] = "PENDIENTE_VERIFICACION"
        destino["periodo_importado"] = str(fila.get("periodo", "")).strip()
        destino["fecha_corte_importada"] = str(fila.get("fecha_corte", "")).strip()
    return salida

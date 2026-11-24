"""Plantillas y validaciones para la ingesta estructurada de SIGOber-Rural."""
from __future__ import annotations

from io import BytesIO
import json
from typing import Any

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

CAMPOS_PROBLEMATICAS = [
    "id_registro", "codigo_ver", "vereda", "categoria", "subcategoria",
    "descripcion", "fecha", "latitud", "longitud", "fuente",
    "referencia_evidencia", "tipo_fuente", "organizacion_aportante",
    "estado_validacion", "observaciones",
]

# Campos ajustados estrictamente a las variables de cálculo requeridas por el DCI
CAMPOS_SADCI = [
    "codigo_variable", "nombre_variable_o_indicador", "periodo", 
    "valor_ingresado", "unidad_medida", "fuente_informacion", 
    "responsable_reporte", "fecha_corte", "observaciones"
]


def crear_excel_plantilla(tipo: str, catalogo: list[dict[str, Any]] | None = None) -> bytes:
    """Devuelve una plantilla XLSX enfocada en las variables de entrada para el cálculo DCI."""
    wb = openpyxl.Workbook()
    
    font_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="26694E", end_color="26694E", fill_type="solid")

    if tipo == "problematicas":
        ws_inst = wb.active
        ws_inst.title = "Instrucciones"
        instrucciones_prob = [
            ["INSTRUCTIVO — PLANTILLA DE PROBLEMÁTICAS SOCIALES"],
            ["1. Una fila por registro. Use el catálogo territorial oficial para las veredas."],
            ["Campo", "Descripción"],
            ["codigo_ver", "Código oficial de la vereda."],
            ["categoria", "Categoría metodológica."],
            ["fecha", "Formato AAAA-MM-DD."]
        ]
        for row in instrucciones_prob:
            ws_inst.append(row)
            
        ws_datos = wb.create_sheet(title="Datos")
        ws_datos.append(CAMPOS_PROBLEMATICAS)
        for col_num in range(1, len(CAMPOS_PROBLEMATICAS) + 1):
            cell = ws_datos.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header

    elif tipo == "sadci":
        # 1. Pestaña de Instrucciones y Glosario conceptual (separado de los datos operativos)
        ws_inst = wb.active
        ws_inst.title = "Glosario y Guía"
        
        instrucciones_sadci = [
            ["GUÍA DE DILIGENCIAMIENTO — VARIABLES DE CÁLCULO DCI"],
            ["1. Ingrese únicamente los valores numéricos o porcentuales requeridos para cada variable."],
            ["2. No altere los códigos de las variables para garantizar el procesamiento automático."],
            [""],
            ["GLOSARIO DE REFERENCIA (QUÉ MIDE CADA COMPONENTE):"],
            ["Variable / Indicador", "Definición conceptual"],
            ["Presupuesto Anual Rural", "Recursos financieros asignados para la inversión y atención en la zona rural."],
            ["Personal de Planta (Rural)", "Talento humano vinculado de planta con funciones orientadas al sector rural."],
            ["Personal Contratista", "Apoyo técnico y operativo temporal contratado para proyectos rurales."],
            ["Ejecución Presupuestal (%)", "Porcentaje de gestión financiera ejecutada frente a la asignación."],
            ["Cumplimiento PDT (%)", "Grado de avance en las metas del Plan de Desarrollo Territorial rural."],
            ["Calificación MEPI", "Puntaje oficial de desempeño institucional y gestión fiscal."]
        ]
        for row in instrucciones_sadci:
            ws_inst.append(row)

        # 2. Pestaña de Datos Operativa (Estrictamente las variables de cálculo)
        ws_datos = wb.create_sheet(title="Variables de Cálculo")
        ws_datos.append(CAMPOS_SADCI)
        for col_num in range(1, len(CAMPOS_SADCI) + 1):
            cell = ws_datos.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Variables base preconfiguradas para el cálculo del DCI
        variables_base = [
            ("presupuesto_anual_rural", "Presupuesto Anual Rural", "COP ($)"),
            ("num_personal_planta", "Personal de Planta (Rural)", "Número de personas"),
            ("num_personal_contratista", "Personal Contratista", "Número de personas"),
            ("ejecucion_presupuestal_pct", "Ejecución Presupuestal", "Porcentaje (%)"),
            ("cumplimiento_pdt_pct", "Cumplimiento PDT", "Porcentaje (%)"),
            ("calificacion_mepi", "Calificación MEPI", "Puntaje (0 - 100)")
        ]

        for codigo_var, nombre_var, unidad in variables_base:
            fila = [
                codigo_var,
                nombre_var,
                "2026",          # Periodo por defecto
                "",              # Valor a diligenciar por el usuario
                unidad,          # Unidad de medida clara para el cálculo
                "",              # Fuente
                "",              # Responsable
                "2026-06-30",    # Fecha de corte estándar
                ""               # Observaciones
            ]
            ws_datos.append(fila)
            
    else:
        raise ValueError("Tipo de plantilla no admitido.")

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 16)

    buffer = BytesIO()
    wb.save(buffer)
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
    """Valida filas de actualización enfocadas en las variables de cálculo."""
    resultado = df.copy()
    errores = []
    for _, fila in resultado.iterrows():
        fila_errores = []
        codigo = str(fila.get("codigo_variable", "")).strip()
        if not codigo:
            fila_errores.append("Falta código de variable")
        if not str(fila.get("periodo", "")).strip():
            fila_errores.append("Falta periodo")
        valor = str(fila.get("valor_ingresado", "")).strip()
        if not valor:
            fila_errores.append("Falta valor ingresado")
        else:
            try:
                float(valor)
            except ValueError:
                fila_errores.append("El valor ingresado debe ser numérico")
        errores.append("; ".join(fila_errores))
    resultado["errores_validacion"] = errores
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
    return resultado


def aplicar_actualizacion_sadci(catalogo: list[dict[str, Any]], filas: pd.DataFrame, periodo: str | None = None) -> list[dict[str, Any]]:
    """Aplica los valores de las variables validadas a la estructura en memoria."""
    salida = [dict(item) for item in catalogo]
    # Mapeo de variables operativas hacia las métricas que consume el resumen SADCI
    for fila in filas.to_dict(orient="records"):
        codigo = str(fila.get("codigo_variable", "")).strip()
        valor_str = str(fila.get("valor_ingresado", "")).strip()
        try:
            val_num = float(valor_str)
        except ValueError:
            continue
        
        # Actualizamos directamente la propiedad correspondiente en el diccionario en memoria
        for item in salida:
            if str(item.get("codigo", "")).strip() == codigo or codigo in item:
                item[codigo] = val_num
    return salida

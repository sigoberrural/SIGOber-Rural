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
CAMPOS_SADCI = [
    "codigo", "periodo", "valor_numerador", "valor_denominador",
    "fuentes", "responsable", "fecha_corte", "observaciones",
    "estado_dato",
]


def crear_excel_plantilla(tipo: str, catalogo: list[dict[str, Any]] | None = None) -> bytes:
    """Devuelve una plantilla XLSX con diseño profesional, glosario DCI y estructura estable."""
    wb = openpyxl.Workbook()
    
    # Estilos comunes para openpyxl
    font_titulo = Font(name="Arial", size=12, bold=True, color="1F4E78")
    font_sub = Font(name="Arial", size=10, bold=True, color="26694E")
    font_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="26694E", end_color="26694E", fill_type="solid")
    border_celda = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    if tipo == "problematicas":
        # 1. Pestaña de Instrucciones y Glosario
        ws_inst = wb.active
        ws_inst.title = "Instrucciones"
        
        instrucciones_prob = [
            ["INSTRUCTIVO — PLANTILLA DE PROBLEMÁTICAS SOCIALES"],
            ["1. Una fila por registro. No invente códigos de vereda; use el catálogo territorial oficial."],
            ["2. La carga no certifica la veracidad. Mantenga la fuente y evidencia y deje estado_validacion en PENDIENTE."],
            [""],
            ["DESCRIPCIÓN DE CAMPOS CLAVE:"],
            ["Campo", "Descripción"],
            ["codigo_ver", "Código oficial de la vereda si está disponible."],
            ["categoria", "Categoría acordada por el equipo metodológico."],
            ["fecha", "Fecha del hecho o de observación, formato AAAA-MM-DD."],
            ["latitud / longitud", "Opcionales; coordenadas WGS84 si se conocen."]
        ]
        for row in instrucciones_prob:
            ws_inst.append(row)
            
        # 2. Pestaña de Datos
        ws_datos = wb.create_sheet(title="Datos")
        ws_datos.append(CAMPOS_PROBLEMATICAS)
        for col_num in range(1, len(CAMPOS_PROBLEMATICAS) + 1):
            cell = ws_datos.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        fila_ejemplo = [
            "PS-0001", "", "", "", "", "", "AAAA-MM-DD", "", "", 
            "", "", "", "", "PENDIENTE", ""
        ]
        ws_datos.append(fila_ejemplo)

    elif tipo == "sadci":
        # 1. Pestaña de Glosario e Instrucciones Detalladas
        ws_inst = wb.active
        ws_inst.title = "Glosario e Instrucciones"
        
        instrucciones_sadci = [
            ["INSTRUCTIVO Y GLOSARIO — ACTUALIZACIÓN SADCI (DCI)"],
            ["1. Una fila por indicador y periodo. El código del indicador no debe modificarse."],
            ["2. Introduzca los valores numéricos de Numerador y Denominador; los porcentajes y tasas se calculan automáticamente en el sistema."],
            ["3. Formato de fecha obligatorio para la fecha de corte: AAAA-MM-DD."],
            ["4. Los registros importados quedarán marcados como pendientes de verificación documental."],
            [""],
            ["GLOSARIO DE DIMENSIONES DE CAPACIDAD INSTITUCIONAL (DCI):"],
            ["Indicador / Dimensión", "Descripción detallada del indicador"],
            ["Presupuesto Anual Rural", "Mide la asignación de recursos financieros dirigidos específicamente a la atención e inversión en el sector rural del municipio."],
            ["Personal de Planta (Rural)", "Cuantifica el talento humano vinculado directamente a la administración pública con funciones orientadas a la gestión rural."],
            ["Personal Contratista", "Evalúa el apoyo operativo y técnico temporal contratado para la ejecución de proyectos, programas y atención en el campo."],
            ["Ejecución Presupuestal (%)", "Mide la capacidad de gestión financiera comparando el presupuesto ejecutado frente al presupuesto asignado para la ruralidad."],
            ["Cumplimiento PDT (%)", "Evalúa el grado de avance físico y de metas del Plan de Desarrollo Territorial relacionadas con el sector rural."],
            ["Calificación MEPI", "Puntaje que refleja el desempeño institucional y la gestión fiscal de acuerdo con las mediciones oficiales establecidas."]
        ]
        for row in instrucciones_sadci:
            ws_inst.append(row)

        if catalogo:
            ws_inst.append([""])
            ws_inst.append(["CÓDIGOS ADMITIDOS EN EL CATÁLOGO:"])
            codigos_str = ", ".join(str(x.get("codigo", "")) for x in catalogo)
            ws_inst.append([codigos_str])

        # 2. Pestaña de Datos Operativa
        ws_datos = wb.create_sheet(title="Datos")
        ws_datos.append(CAMPOS_SADCI)
        for col_num in range(1, len(CAMPOS_SADCI) + 1):
            cell = ws_datos.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        if catalogo:
            for indicador in catalogo:
                fila = [
                    str(indicador.get("codigo", "")).strip(),
                    "", # periodo
                    "", # valor_numerador
                    "", # valor_denominador
                    "", # fuentes
                    "", # responsable
                    "", # fecha_corte
                    "", # observaciones
                    "PENDIENTE_VERIFICACION"
                ]
                ws_datos.append(fila)
        else:
            ws_datos.append(["TDN", "", "", "", "", "", "", "", "PENDIENTE_VERIFICACION"])
            
    else:
        raise ValueError("Tipo de plantilla no admitido.")

    # Ajuste automático de ancho de columnas para ambas pestañas
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

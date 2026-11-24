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

# Estructura histórica de la plantilla DCI/SADCI funcional.
# Se conserva el contrato de datos utilizado por el módulo principal.
CAMPOS_SADCI = [
    "codigo_variable", "nombre_variable_o_indicador", "periodo",
    "valor_ingresado", "unidad_medida", "fuente_informacion",
    "responsable_reporte", "fecha_corte", "observaciones",
]

# Esquema independiente para el catálogo metodológico de diez indicadores.
CAMPOS_SADCI_INDICADORES = [
    "codigo", "periodo", "valor_numerador", "valor_denominador",
    "fuentes", "responsable", "fecha_corte", "observaciones",
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
        # Plantilla DCI/SADCI original: se conservan nombres, orden,
        # hojas, glosario y seis variables de entrada que ya eran funcionales.
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

        ws_datos = wb.create_sheet(title="Variables de Cálculo")
        ws_datos.append(CAMPOS_SADCI)
        for cell in ws_datos[1]:
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        variables_base = [
            ("presupuesto_anual_rural", "Presupuesto Anual Rural", "COP ($)"),
            ("num_personal_planta", "Personal de Planta (Rural)", "Número de personas"),
            ("num_personal_contratista", "Personal Contratista", "Número de personas"),
            ("ejecucion_presupuestal_pct", "Ejecución Presupuestal", "Porcentaje (%)"),
            ("cumplimiento_pdt_pct", "Cumplimiento PDT", "Porcentaje (%)"),
            ("calificacion_mepi", "Calificación MEPI", "Puntaje (0 - 100)")
        ]
        for codigo_var, nombre_var, unidad in variables_base:
            ws_datos.append([
                codigo_var, nombre_var, "2026", "", unidad, "", "", "2026-06-30", ""
            ])

    elif tipo == "sadci_indicadores":
        # Plantilla distinta para la matriz de diez indicadores del catálogo SADCI.
        ws_inst = wb.active
        ws_inst.title = "Instrucciones"
        instrucciones = [
            ["ACTUALIZACIÓN DE INDICADORES SADCI"],
            ["Una fila por indicador y periodo. No modifique los códigos ni las fórmulas del catálogo."],
            ["Complete numerador, denominador, periodo, fuente, responsable y fecha de corte."],
            ["Los datos cargados quedan pendientes de verificación documental."],
            ["Código", "Indicador", "Numerador", "Denominador"],
        ]
        for row in instrucciones:
            ws_inst.append(row)

        ws_datos = wb.create_sheet(title="Actualización SADCI")
        ws_datos.append(CAMPOS_SADCI_INDICADORES)
        for cell in ws_datos[1]:
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for indicador in (catalogo or []):
            ws_datos.append([
                str(indicador.get("codigo", "")).strip(), "", "", "", "", "", "", ""
            ])
            ws_inst.append([
                str(indicador.get("codigo", "")),
                str(indicador.get("nombre", "")),
                str(indicador.get("numerador", "")),
                str(indicador.get("denominador", "")),
            ])

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
    """Lee CSV o Excel apuntando a la hoja correcta de variables de cálculo."""
    nombre = str(getattr(archivo, "name", "")).lower()
    contenido = archivo.getvalue() if hasattr(archivo, "getvalue") else archivo
    if nombre.endswith(".csv"):
        return pd.read_csv(BytesIO(contenido), dtype=str, keep_default_na=False)
    if nombre.endswith((".xlsx", ".xls")):
        # Selecciona la hoja de datos, nunca la portada de instrucciones.
        xls = pd.ExcelFile(BytesIO(contenido))
        hojas_operativas = ("Actualización SADCI", "Variables de Cálculo", "Datos")
        hoja_objetivo = next(
            (nombre for nombre in hojas_operativas if nombre in xls.sheet_names),
            xls.sheet_names[0],
        )
        return pd.read_excel(xls, sheet_name=hoja_objetivo, dtype=str).fillna("")
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
    """Valida tanto la plantilla DCI histórica como la matriz de indicadores SADCI."""
    resultado = df.copy()

    # Esquema original DCI: seis variables con un valor directo por fila.
    # No se transforma a numerador/denominador ni se renombran sus columnas.
    if {"codigo_variable", "valor_ingresado"}.issubset(resultado.columns):
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
                    float(valor.replace(",", "."))
                except (TypeError, ValueError):
                    fila_errores.append("El valor ingresado debe ser numérico")
            errores.append("; ".join(fila_errores))

        resultado["errores_validacion"] = errores
        resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")
        return resultado

    # Esquema de diez indicadores: numerador y denominador.
    if "codigo" not in resultado.columns and "codigo_variable" in resultado.columns:
        resultado = resultado.rename(columns={"codigo_variable": "codigo"})

    codigos_validos = {
        str(item.get("codigo", "")).strip()
        for item in catalogo
        if str(item.get("codigo", "")).strip()
    }
    errores = []
    for _, fila in resultado.iterrows():
        fila_errores = []
        codigo = str(fila.get("codigo", "")).strip()
        periodo = str(fila.get("periodo", "")).strip()

        if not codigo:
            fila_errores.append("Falta código de indicador")
        elif codigo not in codigos_validos:
            fila_errores.append("Código de indicador no reconocido")

        if not periodo:
            fila_errores.append("Falta periodo")

        valores = {}
        for campo, etiqueta in (
            ("valor_numerador", "numerador"),
            ("valor_denominador", "denominador"),
        ):
            bruto = str(fila.get(campo, "")).strip()
            if not bruto:
                fila_errores.append(f"Falta {etiqueta}")
                continue
            try:
                numero = float(bruto.replace(",", "."))
                valores[campo] = numero
            except (TypeError, ValueError):
                fila_errores.append(f"El {etiqueta} debe ser numérico")

        if "valor_numerador" in valores and valores["valor_numerador"] < 0:
            fila_errores.append("El numerador no puede ser negativo")
        if "valor_denominador" in valores and valores["valor_denominador"] <= 0:
            fila_errores.append("El denominador debe ser mayor que cero")

        errores.append("; ".join(fila_errores))

    resultado["errores_validacion"] = errores
    resultado["valido_revision_tecnica"] = resultado["errores_validacion"].eq("")

    if {"codigo", "periodo"}.issubset(resultado.columns):
        codigos = resultado["codigo"].astype(str).str.strip()
        periodos = resultado["periodo"].astype(str).str.strip()
        duplicados = (
            pd.DataFrame({"codigo": codigos, "periodo": periodos})
            .duplicated(keep=False)
            & codigos.ne("")
            & periodos.ne("")
        )
        resultado.loc[duplicados, "valido_revision_tecnica"] = False
        resultado.loc[duplicados, "errores_validacion"] = resultado.loc[
            duplicados, "errores_validacion"
        ].map(lambda x: (x + "; " if x else "") + "Indicador y periodo duplicados")

    return resultado

def aplicar_actualizacion_sadci(
    catalogo: list[dict[str, Any]],
    filas: pd.DataFrame,
    periodo: str | None = None,
) -> list[dict[str, Any]]:
    """Aplica numeradores y denominadores a una copia del catálogo en memoria."""
    salida = [dict(item) for item in catalogo]
    por_codigo = {str(item.get("codigo", "")).strip(): item for item in salida}

    for fila in filas.to_dict(orient="records"):
        codigo = str(fila.get("codigo", fila.get("codigo_variable", ""))).strip()
        periodo_fila = str(fila.get("periodo", "")).strip()
        if periodo and periodo_fila != str(periodo).strip():
            continue
        indicador = por_codigo.get(codigo)
        if indicador is None:
            continue

        try:
            numerador = float(str(fila.get("valor_numerador", "")).strip().replace(",", "."))
            denominador = float(str(fila.get("valor_denominador", "")).strip().replace(",", "."))
        except (TypeError, ValueError):
            continue
        if numerador < 0 or denominador <= 0:
            continue

        indicador["valor_numerador"] = numerador
        indicador["valor_denominador"] = denominador
        indicador["estado_dato"] = "PENDIENTE_VERIFICACION"
        indicador["periodo_actualizacion"] = periodo_fila
        for campo_origen, campo_destino in (
            ("fuentes", "fuentes"),
            ("responsable", "responsable"),
            ("fecha_corte", "fecha_corte"),
            ("observaciones", "observaciones_actualizacion"),
        ):
            valor = str(fila.get(campo_origen, "")).strip()
            if valor:
                indicador[campo_destino] = valor

    return salida

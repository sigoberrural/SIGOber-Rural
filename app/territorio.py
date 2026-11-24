"""Validación conservadora de los eventos territoriales usados en el mapa.

No corrige filas incompletas ni infiere asignaciones espaciales. Solo habilita
la agregación por vereda cuando la fuente declara explícitamente una validación
a escala VEREDA y el código existe en la capa base.
"""
import csv
from pathlib import Path

import pandas as pd


COLUMNAS_REQUERIDAS = {
    "id", "anio", "codigo_ver_resuelto", "precision_espacial",
    "estado_territorial", "tipo_conflicto", "confianza",
}
COLUMNAS_RESUMEN = [
    "codigo_ver_resuelto", "SIGOber_situaciones", "SIGOber_anios",
    "SIGOber_tipos", "SIGOber_confianza",
]


def leer_eventos_territoriales(ruta):
    """Lee solo registros con el número exacto de columnas y devuelve auditoría."""
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.reader(archivo, strict=True)
        try:
            encabezado = next(lector)
        except StopIteration:
            return pd.DataFrame(), {"filas_incompletas": [], "filas_leidas": 0}

        faltantes = COLUMNAS_REQUERIDAS.difference(encabezado)
        if faltantes:
            raise ValueError(
                "El CSV de situaciones no contiene las columnas requeridas: "
                + ", ".join(sorted(faltantes))
            )

        registros = []
        incompletas = []
        for fila in lector:
            if len(fila) != len(encabezado):
                incompletas.append({
                    "linea": lector.line_num,
                    "id": fila[0].strip() if fila else "",
                    "columnas": len(fila),
                })
                continue
            registros.append(fila)

    datos = pd.DataFrame(registros, columns=encabezado).fillna("")
    auditoria = {
        "filas_leidas": len(registros) + len(incompletas),
        "filas_validas_estructura": len(registros),
        "filas_incompletas": incompletas,
    }
    return datos, auditoria


def resumir_eventos_por_vereda(eventos, codigos_veredas):
    """Agrega únicamente evidencia validada explícitamente a escala de vereda."""
    if eventos is None or eventos.empty:
        return pd.DataFrame(columns=COLUMNAS_RESUMEN)

    requeridas = {
        "id", "codigo_ver_resuelto", "estado_territorial", "precision_espacial",
        "anio", "tipo_conflicto", "confianza",
    }
    if not requeridas.issubset(eventos.columns):
        return pd.DataFrame(columns=COLUMNAS_RESUMEN)

    codigos = {str(codigo).strip() for codigo in codigos_veredas if str(codigo).strip()}
    df = eventos.copy()
    for columna in requeridas:
        df[columna] = df[columna].fillna("").astype(str).str.strip()

    df = df.loc[
        df["estado_territorial"].eq("VALIDADA_EN_CAPA")
        & df["precision_espacial"].eq("VEREDA")
        & df["codigo_ver_resuelto"].ne("")
        & df["codigo_ver_resuelto"].isin(codigos)
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_RESUMEN)

    def valores_unicos(serie):
        return ", ".join(sorted(valor for valor in serie.unique() if valor))

    return (
        df.groupby("codigo_ver_resuelto", sort=False)
        .agg(
            SIGOber_situaciones=("id", "size"),
            SIGOber_anios=("anio", valores_unicos),
            SIGOber_tipos=("tipo_conflicto", valores_unicos),
            SIGOber_confianza=("confianza", valores_unicos),
        )
        .reset_index()
    )

# -*- coding: utf-8 -*-
"""
============================================================================
 LECTURA DEL CRONOGRAMA (Last Planner System)
============================================================================

El Excel, en la hoja "01_MAESTRO", tiene una fila de FECHAS (fila 6) y, por
cada ACTIVIDAD (fila), el codigo de SECTOR ("1CS6", "2PS13"...) escrito justo
en la columna del dia que le toca. De ahi sale todo.

Si el Excel no estuviera disponible, se usa como respaldo el volcado
`data/plan_obra.json` (mismo contenido, ya procesado).
============================================================================
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime

HOJA = "01_MAESTRO"
FILA_FECHAS = 5          # indice 0 -> fila 6 del Excel
PRIMERA_FILA_DATOS = 6
COL_DESCRIPCION = 2      # columna C

# Codigo de sector: 1CS6, 2PS13, ...
SECTOR_RE = re.compile(r"^[12][A-Z]{2}\d+$", re.IGNORECASE)


def clasificar_tipo(descripcion: str) -> str:
    """Decide a que lista del dia va cada actividad, por su nombre."""
    d = (descripcion or "").upper()
    if "ACERO" in d or "ESTRIBO" in d:
        return "ACERO"
    if "ENCOFRADO" in d or "DESENCOFRADO" in d:
        return "ENCOFRADO"
    if "CONCRETO" in d or "MORTERO" in d or "TARRAJEO" in d or "CIELORASO" in d:
        return "CONCRETO"
    return "VARIOS"


def _leer_desde_excel(ruta_excel: str, fecha_objetivo: date) -> list:
    import pandas as pd

    df = pd.read_excel(ruta_excel, sheet_name=HOJA, header=None)

    fila_fechas = df.iloc[FILA_FECHAS]
    col_de_fecha = None
    for ci in range(len(fila_fechas)):
        v = fila_fechas[ci]
        if isinstance(v, (pd.Timestamp, datetime)) and v.date() == fecha_objetivo:
            col_de_fecha = ci
            break
    if col_de_fecha is None:
        return []       # fin de semana o fuera del plan

    tareas, vistos = [], set()
    for ri in range(PRIMERA_FILA_DATOS, len(df)):
        desc = df.iat[ri, COL_DESCRIPCION]
        if not isinstance(desc, str) or not desc.strip():
            continue
        desc = desc.strip()
        val = df.iat[ri, col_de_fecha]
        if isinstance(val, str) and SECTOR_RE.match(val.strip()):
            sector = val.strip().upper()
            if (sector, desc) in vistos:
                continue
            vistos.add((sector, desc))
            tareas.append({"sector": sector, "actividad": desc,
                           "tipo": clasificar_tipo(desc)})
    return tareas


def _leer_desde_json(ruta_json: str, fecha_objetivo: date) -> list:
    with open(ruta_json, encoding="utf-8") as f:
        plan = json.load(f)
    objetivo = fecha_objetivo.isoformat()
    tareas, vistos = [], set()
    for fila in plan:
        if fila.get("fecha") != objetivo:
            continue
        sector = (fila.get("sector") or "").strip().upper()
        desc = (fila.get("actividad") or "").strip()
        if not sector or not desc or (sector, desc) in vistos:
            continue
        vistos.add((sector, desc))
        tareas.append({"sector": sector, "actividad": desc,
                       "tipo": fila.get("tipo") or clasificar_tipo(desc)})
    return tareas


def leer_tareas_del_dia(ruta_excel: str, fecha_objetivo: date,
                        ruta_json: str = None) -> list:
    """Tareas programadas para esa fecha: [{sector, actividad, tipo}, ...].

    Usa el Excel; si no existe, cae al respaldo JSON.
    """
    if ruta_excel and os.path.exists(ruta_excel):
        return _leer_desde_excel(ruta_excel, fecha_objetivo)
    if ruta_json and os.path.exists(ruta_json):
        return _leer_desde_json(ruta_json, fecha_objetivo)
    raise SystemExit(
        f"ERROR: no encuentro el cronograma.\n"
        f"  - Excel esperado en: {ruta_excel}\n"
        f"  - Respaldo JSON en:  {ruta_json}\n"
        f"Sube el archivo al repositorio o ajusta RUTA_EXCEL."
    )

# -*- coding: utf-8 -*-
"""
============================================================================
 CRONOGRAMA — lee el plan de obra (Last Planner) y lo entiende.
============================================================================

FORMA QUE ESPERA DEL EXCEL
--------------------------
Una FILA con las fechas (una fecha por columna) y una COLUMNA con el nombre
de cada actividad. En el cruce, el codigo de SECTOR que le toca ese dia:

                 ...  |  26/08  |  27/08  |  28/08  |  <- fila_fechas
    ACERO EN ZAPATAS  |  1CS11  |  1CS12  |         |
    ENCOFRADO ...     |         |  1CS15  |  1CS16  |
    ^ columna_actividad

Donde esta cada cosa se configura en configuracion.json -> cronograma:
hoja, fila_fechas, primera_fila_datos, columna_actividad y patron_sector.
Asi, otro Excel con esta misma forma se lee cambiando dos numeros y una letra,
sin tocar el codigo.

RESPALDO
--------
`sincronizar` vuelca todo el plan a un JSON (data/plan_obra.json). Si algun
dia el Excel falta o esta corrupto, se lee ese JSON y la obra no se detiene.
============================================================================
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime

from . import ajustes


def _indice_columna(letra: str) -> int:
    """'A' -> 0, 'C' -> 2, 'AA' -> 26. Acepta tambien un numero."""
    letra = str(letra).strip().upper()
    if letra.isdigit():
        return int(letra) - 1
    n = 0
    for ch in letra:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Columna invalida: {letra!r}. Usa una letra como 'C'.")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def familia_de(actividad: str) -> str:
    """Familia de trabajo de una actividad, por sus palabras clave.

    Lo que no case con ninguna clave cae en la familia de descarte, para que
    ninguna tarjeta se quede sin destino ni se acumule donde no debe.
    """
    from .trello import normalizar

    texto = normalizar(actividad)          # sin acentos ni simbolos
    for nombre, familia in ajustes.FAMILIAS.items():
        for clave in familia.get("claves") or []:
            if normalizar(clave) in texto:
                return nombre
    return ajustes.familia_por_defecto()


def destino_de(actividad: str) -> tuple:
    """(familia, lista_destino) de una actividad.

    Manda lo que digas en mapeo.json; si ahi no hay nada, se deduce por
    palabras clave.
    """
    from .trello import normalizar

    mapeado = ajustes.destino_de_actividad(normalizar(actividad))
    familia = mapeado.get("familia") or familia_de(actividad)
    lista = mapeado.get("lista") or ajustes.lista_de_familia(familia)
    return familia, lista


# ---------------------------------------------------------------------------
# Lectura del Excel
# ---------------------------------------------------------------------------
def leer_excel_completo(ruta_excel: str = None) -> list:
    """Todo el plan: [{fecha, sector, actividad, familia}, ...] ordenado."""
    import pandas as pd

    ruta = ruta_excel or ajustes.RUTA_EXCEL
    df = pd.read_excel(ruta, sheet_name=ajustes.HOJA, header=None)

    fila_fechas = ajustes.FILA_FECHAS - 1            # el JSON cuenta como Excel
    primera_fila = ajustes.PRIMERA_FILA_DATOS - 1
    col_actividad = _indice_columna(ajustes.COLUMNA_ACTIVIDAD)
    patron = re.compile(ajustes.PATRON_SECTOR, re.IGNORECASE)

    if fila_fechas >= len(df):
        raise SystemExit(
            f"ERROR: la hoja '{ajustes.HOJA}' no tiene la fila {ajustes.FILA_FECHAS}.\n"
            f"Revisa configuracion.json -> cronograma.fila_fechas."
        )

    # Que columna corresponde a cada fecha
    fechas_por_columna = {}
    for ci, valor in enumerate(df.iloc[fila_fechas]):
        if isinstance(valor, (pd.Timestamp, datetime)):
            fechas_por_columna[ci] = valor.date()

    if not fechas_por_columna:
        raise SystemExit(
            f"ERROR: no encontre ninguna fecha en la fila {ajustes.FILA_FECHAS} "
            f"de la hoja '{ajustes.HOJA}'.\n"
            f"Revisa configuracion.json -> cronograma.fila_fechas / hoja."
        )

    plan, vistos = [], set()
    for ri in range(primera_fila, len(df)):
        actividad = df.iat[ri, col_actividad]
        if not isinstance(actividad, str) or not actividad.strip():
            continue
        actividad = actividad.strip()
        for ci, fecha in fechas_por_columna.items():
            valor = df.iat[ri, ci]
            if not isinstance(valor, str):
                continue
            sector = valor.strip().upper()
            if not patron.match(sector):
                continue
            clave = (fecha, sector, actividad)
            if clave in vistos:
                continue
            vistos.add(clave)
            plan.append({
                "fecha": fecha.isoformat(),
                "sector": sector,
                "actividad": actividad,
                "familia": familia_de(actividad),
            })

    plan.sort(key=lambda t: (t["fecha"], t["sector"], t["actividad"]))
    return plan


def guardar_respaldo(plan: list, ruta_json: str = None) -> str:
    ruta = ruta_json or ajustes.RUTA_PLAN_JSON
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    return ruta


def leer_respaldo(ruta_json: str = None) -> list:
    ruta = ruta_json or ajustes.RUTA_PLAN_JSON
    with open(ruta, encoding="utf-8") as f:
        plan = json.load(f)
    return plan if isinstance(plan, list) else []


def tareas_del_dia(fecha: date, ruta_excel: str = None, ruta_json: str = None) -> list:
    """Tareas programadas para una fecha: [{sector, actividad, familia, lista}, ...].

    Usa el Excel; si no esta disponible, cae al respaldo JSON.
    """
    ruta = ruta_excel or ajustes.RUTA_EXCEL
    if ruta and os.path.exists(ruta):
        plan = leer_excel_completo(ruta)
    else:
        respaldo = ruta_json or ajustes.RUTA_PLAN_JSON
        if not (respaldo and os.path.exists(respaldo)):
            raise SystemExit(
                f"ERROR: no encuentro el cronograma.\n"
                f"  - Excel esperado en: {ruta}\n"
                f"  - Respaldo JSON en:  {respaldo}\n"
                f"Sube el archivo o corrige configuracion.json -> cronograma.archivo."
            )
        print(f"AVISO: no esta el Excel; uso el respaldo {respaldo}.")
        plan = leer_respaldo(respaldo)

    objetivo = fecha.isoformat()
    tareas = []
    for fila in plan:
        if fila.get("fecha") != objetivo:
            continue
        actividad = (fila.get("actividad") or "").strip()
        sector = (fila.get("sector") or "").strip().upper()
        if not actividad or not sector:
            continue
        familia, lista = destino_de(actividad)
        tareas.append({
            "sector": sector,
            "actividad": actividad,
            "familia": familia,
            "lista": lista,
        })
    return tareas


def actividades_distintas(plan: list) -> list:
    """Catalogo de actividades del plan, con cuantas veces aparece cada una."""
    cuenta = {}
    for fila in plan:
        actividad = (fila.get("actividad") or "").strip()
        if actividad:
            cuenta[actividad] = cuenta.get(actividad, 0) + 1
    return sorted(cuenta.items(), key=lambda kv: (-kv[1], kv[0]))

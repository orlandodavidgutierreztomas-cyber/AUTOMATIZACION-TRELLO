#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 AUTOMATIZACIÓN TRELLO — CONSTRUCCIÓN DE AULAS
 Crea las tarjetas del día en Trello a partir del cronograma Excel (LPS).
============================================================================

QUÉ HACE
--------
Lee la hoja "01_MAESTRO" del Excel de planeamiento, detecta qué SECTOR hace
qué ACTIVIDAD en una FECHA dada, y crea en Trello una tarjeta por cada uno,
con el formato "[SECTOR] — [ACTIVIDAD]", fecha de vencimiento, y colocada en
la lista correcta según el tipo de trabajo (Acero / Encofrado / Concreto /
Varios).

Reproduce exactamente la lógica que hoy se hace a mano en el tablero.

CÓMO SE USA
-----------
    python crear_tarjetas.py --fecha 2026-08-26
    python crear_tarjetas.py --fecha hoy
    python crear_tarjetas.py --fecha 2026-08-26 --dry-run   (no crea, solo muestra)

CONFIGURACIÓN
-------------
Rellena las credenciales en config.py (o variables de entorno). NADA de
credenciales va escrito aquí.
============================================================================
"""

import argparse
import sys
import re
import json
import time
from datetime import date, datetime

import requests

import settings as config  # settings resuelve entorno (GitHub Secrets) o config.py local


# ---------------------------------------------------------------------------
# 1. CLASIFICADOR DE TIPO DE TRABAJO
#    Decide a qué lista del tablero va cada actividad, por su nombre.
# ---------------------------------------------------------------------------
def clasificar_tipo(descripcion: str) -> str:
    d = descripcion.upper()
    if "ACERO" in d or "ESTRIBO" in d:
        return "ACERO"
    if "ENCOFRADO" in d:
        return "ENCOFRADO"
    if "CONCRETO" in d or "MORTERO" in d or "TARRAJEO" in d or "CIELORASO" in d:
        return "CONCRETO"
    return "VARIOS"


# ---------------------------------------------------------------------------
# 2. LECTOR DEL EXCEL
#    Devuelve la lista de tareas de una fecha: [{sector, actividad, tipo}, ...]
# ---------------------------------------------------------------------------
SECTOR_RE = re.compile(r"^[12][A-Z]{2}\d+$", re.IGNORECASE)  # ej. 1CS6, 2PS13


def leer_tareas_del_dia(ruta_excel: str, fecha_objetivo: date) -> list:
    """Lee 01_MAESTRO y devuelve las tareas cuyo sector cae en fecha_objetivo."""
    import pandas as pd

    df = pd.read_excel(ruta_excel, sheet_name="01_MAESTRO", header=None)

    # Fila 6 (índice 5) contiene las fechas, una por columna.
    fila_fechas = df.iloc[5]
    col_de_fecha = None
    for ci in range(len(fila_fechas)):
        v = fila_fechas[ci]
        if isinstance(v, (pd.Timestamp, datetime)) and v.date() == fecha_objetivo:
            col_de_fecha = ci
            break

    if col_de_fecha is None:
        return []  # ese día no hay columna (fin de semana o fuera de plan)

    tareas = []
    vistos = set()
    for ri in range(6, len(df)):
        desc = df.iat[ri, 2]  # columna C = descripción de actividad
        if not isinstance(desc, str) or not desc.strip():
            continue
        desc = desc.strip()
        val = df.iat[ri, col_de_fecha]
        if isinstance(val, str) and SECTOR_RE.match(val.strip()):
            sector = val.strip()
            clave = (sector, desc)
            if clave in vistos:
                continue
            vistos.add(clave)
            tareas.append({
                "sector": sector,
                "actividad": desc,
                "tipo": clasificar_tipo(desc),
            })
    return tareas


# ---------------------------------------------------------------------------
# 3. CLIENTE TRELLO (API REST oficial)
# ---------------------------------------------------------------------------
class Trello:
    BASE = "https://api.trello.com/1"

    def __init__(self, key: str, token: str):
        self.auth = {"key": key, "token": token}

    def _get(self, path, params=None):
        p = dict(self.auth)
        if params:
            p.update(params)
        r = requests.get(f"{self.BASE}{path}", params=p, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path, params):
        p = dict(self.auth)
        p.update(params)
        r = requests.post(f"{self.BASE}{path}", params=p, timeout=30)
        r.raise_for_status()
        return r.json()

    def listas_del_tablero(self, board_id: str) -> dict:
        """Devuelve {nombre_lista: id_lista}."""
        data = self._get(f"/boards/{board_id}/lists")
        return {l["name"]: l["id"] for l in data}

    def tarjetas_del_tablero(self, board_id: str) -> set:
        """Devuelve el conjunto de nombres de tarjetas ya existentes (para no duplicar)."""
        data = self._get(f"/boards/{board_id}/cards", {"fields": "name"})
        return {c["name"] for c in data}

    def crear_tarjeta(self, list_id: str, nombre: str, due_iso: str = None, desc: str = ""):
        params = {"idList": list_id, "name": nombre, "desc": desc}
        if due_iso:
            params["due"] = due_iso
        return self._post("/cards", params)


# ---------------------------------------------------------------------------
# 4. LÓGICA PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Crea tarjetas del día en Trello desde el Excel LPS.")
    ap.add_argument("--fecha", required=True, help='Fecha "AAAA-MM-DD" o la palabra "hoy".')
    ap.add_argument("--dry-run", action="store_true", help="No crea nada; solo muestra qué haría.")
    args = ap.parse_args()

    # Resolver fecha
    if args.fecha.lower() == "hoy":
        fecha = date.today()
    else:
        fecha = datetime.strptime(args.fecha, "%Y-%m-%d").date()

    print(f"\n=== Tarjetas para el {fecha.strftime('%A %d/%m/%Y')} ===\n")

    # 1) Leer Excel
    tareas = leer_tareas_del_dia(config.RUTA_EXCEL, fecha)
    if not tareas:
        print("No hay tareas programadas para esa fecha (fin de semana o fuera de plan).")
        return
    print(f"Se encontraron {len(tareas)} tareas en el cronograma.\n")

    # 2) Vencimiento: fin de la jornada de ese día, en hora local Perú (UTC-5)
    #    17:00 Lima = 22:00 UTC
    due_iso = f"{fecha.isoformat()}T22:00:00.000Z"

    if args.dry_run:
        for t in tareas:
            print(f"  [{t['tipo']:9}] {t['sector']} — {t['actividad']}")
        print("\n(DRY-RUN: no se creó nada.)")
        return

    # 3) Conectar a Trello
    tr = Trello(config.TRELLO_KEY, config.TRELLO_TOKEN)
    listas = tr.listas_del_tablero(config.BOARD_ID)
    existentes = tr.tarjetas_del_tablero(config.BOARD_ID)

    # 4) Crear una tarjeta por tarea, en la lista según su tipo
    creadas, saltadas = 0, 0
    for t in tareas:
        nombre = f"{t['sector']} — {t['actividad']}"
        if nombre in existentes:
            saltadas += 1
            continue  # idempotencia: no duplicar

        lista_destino = config.LISTA_POR_TIPO[t["tipo"]]
        list_id = listas.get(lista_destino)
        if not list_id:
            print(f"  ⚠ No encuentro la lista '{lista_destino}' en el tablero. Salto: {nombre}")
            continue

        tr.crear_tarjeta(list_id, nombre, due_iso)
        creadas += 1
        print(f"  ✓ [{t['tipo']:9}] {nombre}")
        time.sleep(0.15)  # respetar límite de la API de Trello

    print(f"\n=== Listo: {creadas} creadas, {saltadas} ya existían (no duplicadas). ===")


if __name__ == "__main__":
    main()

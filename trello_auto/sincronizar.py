#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 SINCRONIZAR — relee el Excel y el tablero, y arma el mapeo.
============================================================================

Se aprieta el boton cuando cambias el Excel (una revision nueva del
cronograma) o cuando tocas el tablero (una plantilla nueva, una lista nueva).
Hace tres cosas de golpe:

  1. Lee el Excel entero y saca TODAS las actividades distintas.
  2. Vuelca el plan completo a data/plan_obra.json  (el RESPALDO: si algun
     dia el Excel falta, la obra sigue corriendo con este archivo).
  3. Lee el tablero en vivo -los nombres reales de tus listas y que
     actividades ya tienen plantilla- y escribe mapeo.json.

EL MAPEO
--------
mapeo.json lleva una fila por actividad diciendo a que familia pertenece y a
que lista del dia va. Llega PRE-RELLENADO con la mejor suposicion por
palabras clave, para que no tengas que mapear decenas de actividades a mano:
solo corriges las que esten mal. Lo que corrijas se RESPETA en las
sincronizaciones siguientes.

Tambien te deja a la vista los nombres reales de las listas del tablero,
para que elijas de lo que existe en vez de escribirlos de memoria.

USO
---
    python -m trello_auto.sincronizar
    python -m trello_auto.sincronizar --dry-run
============================================================================
"""

from __future__ import annotations

import argparse
import json
import sys

from . import ajustes
from .cronograma import actividades_distintas, familia_de, leer_excel_completo
from .trello import Trello, construir_indice_plantillas, normalizar


def cargar_mapeo_actual() -> dict:
    try:
        datos = json.loads(ajustes.ARCHIVO_MAPEO.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Relee el Excel y el tablero, y actualiza el mapeo y el respaldo.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No escribe archivos; solo muestra que haria.")
    args = ap.parse_args()

    print("=" * 74)
    print(f" SINCRONIZAR - {ajustes.NOMBRE_OBRA}")
    print("=" * 74)

    # --- 1. El cronograma -------------------------------------------------
    print(f"\n1) Leyendo {ajustes.RUTA_EXCEL}")
    print(f"   hoja '{ajustes.HOJA}' · fechas en la fila {ajustes.FILA_FECHAS} · "
          f"actividades en la columna {ajustes.COLUMNA_ACTIVIDAD}")
    plan = leer_excel_completo()
    catalogo = actividades_distintas(plan)
    fechas = sorted({f["fecha"] for f in plan})
    print(f"   {len(plan)} tareas · {len(catalogo)} actividades distintas · "
          f"{len(fechas)} dias con trabajo")
    if fechas:
        print(f"   del {fechas[0]} al {fechas[-1]}")

    # --- 2. El respaldo ---------------------------------------------------
    if args.dry_run:
        print(f"\n2) (DRY-RUN) no escribo {ajustes.RUTA_PLAN_JSON}")
    else:
        from .cronograma import guardar_respaldo
        ruta = guardar_respaldo(plan)
        print(f"\n2) Respaldo escrito: {ruta}")

    # --- 3. El tablero ----------------------------------------------------
    nombres_listas, plantillas = [], {}
    if ajustes.TRELLO_KEY and ajustes.TRELLO_TOKEN:
        tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
        listas = tr.listas(ajustes.BOARD_ID)
        cards = tr.tarjetas(ajustes.BOARD_ID)
        nombres_listas = [lst["name"] for lst in listas]
        plantillas = construir_indice_plantillas(cards, listas, ajustes.MARCA_PLANTILLA)
        print(f"\n3) Tablero: {len(nombres_listas)} listas, "
              f"{len(plantillas)} plantillas")
        for n in nombres_listas:
            print(f"     · {n}")
    else:
        print("\n3) Sin credenciales: no leo el tablero (el mapeo se arma igual).")

    # --- 4. El mapeo ------------------------------------------------------
    anterior = cargar_mapeo_actual()
    previas = (anterior.get("actividades") or {})

    actividades, nuevas, conservadas, con_plantilla = {}, 0, 0, 0
    for nombre, veces in catalogo:
        clave = normalizar(nombre)
        familia_auto = familia_de(nombre)
        anterior_fila = previas.get(clave) or {}

        # Lo que tu hayas corregido manda sobre la suposicion automatica
        familia = anterior_fila.get("familia") or familia_auto
        lista = anterior_fila.get("lista") or ajustes.lista_de_familia(familia)
        tiene = clave in plantillas

        if anterior_fila:
            conservadas += 1
        else:
            nuevas += 1
        if tiene:
            con_plantilla += 1

        actividades[clave] = {
            "actividad": nombre,
            "familia": familia,
            "lista": lista,
            "veces_en_el_plan": veces,
            "tiene_plantilla": tiene,
        }

    mapeo = {
        "_ayuda": (
            "Una fila por actividad del cronograma. 'familia' agrupa para el "
            "reporte y 'lista' dice a que lista del dia va la tarjeta. Llega "
            "pre-rellenado por palabras clave: corrige solo lo que este mal, y "
            "se respetara en las proximas sincronizaciones. 'tiene_plantilla' "
            "es informativo: dice si esa actividad ya tiene su tarjeta "
            "PLANTILLA en el tablero."
        ),
        "listas_del_tablero": nombres_listas,
        "familias_disponibles": [f for f in ajustes.FAMILIAS],
        "actividades": actividades,
    }

    print(f"\n4) Mapeo: {len(actividades)} actividades "
          f"({nuevas} nuevas, {conservadas} ya estaban)")
    print(f"   con plantilla en el tablero: {con_plantilla} de {len(actividades)}")

    sin_plantilla = [v["actividad"] for v in actividades.values()
                     if not v["tiene_plantilla"]]
    if sin_plantilla and plantillas:
        print(f"\n   Actividades SIN plantilla ({len(sin_plantilla)}):")
        for nombre in sin_plantilla[:12]:
            print(f"     · {nombre}")
        if len(sin_plantilla) > 12:
            print(f"     ... y {len(sin_plantilla) - 12} mas")

    if args.dry_run:
        print(f"\n   (DRY-RUN) no escribo {ajustes.ARCHIVO_MAPEO.name}")
    else:
        ajustes.ARCHIVO_MAPEO.write_text(
            json.dumps(mapeo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n   Escrito: {ajustes.ARCHIVO_MAPEO.name}")

    print("\n" + "=" * 74)
    print(" Sincronizado.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

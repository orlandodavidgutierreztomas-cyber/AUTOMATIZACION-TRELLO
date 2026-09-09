#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ARRANQUE — que parte de la obra ya estaba hecha antes de entrar el sistema.
============================================================================

EL PROBLEMA
-----------
El sistema casi nunca arranca el primer dia de obra. Se pone en marcha a
mitad de camino, y para entonces el cronograma ya tiene cientos de
actividades con fecha pasada. Muchas estan hechas -la obra avanzo- pero el
sistema no lo vio, porque no existia.

Si nadie se lo dice, el avance de obra sale mal: el dashboard mostraria un
0% cuando en realidad la obra lleva medio primer piso levantado, y todo el
cumplimiento del Last Planner quedaria falseado desde el primer dia.

LA SOLUCION
-----------
Se declara UNA VEZ, al empezar. Este robot cuenta las actividades del
cronograma anteriores a la fecha de arranque, pregunta cuantas de esas ya
estaban hechas, y lo anota como PUNTO DE PARTIDA en el historico.

A partir de ahi el sistema sigue solo: cada cierre suma lo culminado del
dia, y el avance de obra es el punto de partida mas lo que se lleve hecho.

COMO SE CONTESTA (--hechas)
  todas    Todo lo anterior al arranque ya esta hecho. Es lo normal cuando
           la obra viene al dia y el sistema entra hoy.
  ninguna  Nada estaba hecho. El plan empieza de cero.
  hasta    Estaba hecho lo anterior a una fecha (--hasta), y lo de entre esa
           fecha y el arranque quedo pendiente. Es el caso real cuando la
           obra viene con retraso.
  numero   La cifra exacta, si la sabes de tu propio control.

Se puede corregir cuantas veces haga falta: REEMPLAZA el punto de partida,
nunca lo suma dos veces.

USO
---
    python -m trello_auto.arranque --ver
    python -m trello_auto.arranque --hechas todas --dry-run
    python -m trello_auto.arranque --hechas hasta --hasta 2026-08-31
    python -m trello_auto.arranque --hechas 240
============================================================================
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date

from . import ajustes, horario
from .cronograma import leer_respaldo
from .historico import guardar_cierre, serie_culminadas

CLAVE_ARRANQUE = "ARRANQUE"


def fecha_de_arranque() -> date:
    """El dia en que el sistema toma el control de la obra.

    Si no se ha configurado, es hoy: lo anterior es historia que el sistema
    no vio.
    """
    valor = ajustes.dato("obra.arranque")
    if not valor:
        return horario.hoy_local()
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError as e:
        raise SystemExit(
            f"ERROR: obra.arranque no es una fecha: {valor!r}. "
            f"Escribela como 2026-09-08."
        ) from e


def anteriores_al_arranque(plan: list, arranque: date) -> list:
    """Las tareas del cronograma con fecha anterior al arranque."""
    corte = arranque.isoformat()
    return [t for t in plan if (t.get("fecha") or "") < corte]


def cuantas_hechas(previas: list, respuesta: str, hasta: date = None) -> int:
    """Traduce la respuesta a un numero de tareas ya hechas."""
    if respuesta == "todas":
        return len(previas)
    if respuesta == "ninguna":
        return 0
    if respuesta == "hasta":
        if not hasta:
            raise SystemExit("ERROR: con --hechas hasta hace falta --hasta AAAA-MM-DD.")
        tope = hasta.isoformat()
        return sum(1 for t in previas if (t.get("fecha") or "") < tope)
    try:
        n = int(respuesta)
    except ValueError:
        raise SystemExit(
            f"ERROR: no entiendo --hechas {respuesta!r}. Usa todas, ninguna, "
            f"hasta, o un numero."
        ) from None
    if not 0 <= n <= len(previas):
        raise SystemExit(
            f"ERROR: {n} no cabe: antes del arranque hay {len(previas)} tareas.")
    return n


def punto_de_partida() -> int:
    """Lo que ya estaba hecho al arrancar, si se declaro."""
    arranque = fecha_de_arranque()
    for dia, culminadas in serie_culminadas(0):
        if dia == arranque:
            return culminadas
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Declara que parte de la obra ya estaba hecha al arrancar.")
    ap.add_argument("--hechas", default=None,
                    help="todas | ninguna | hasta | un numero.")
    ap.add_argument("--hasta", default=None,
                    help="Con '--hechas hasta': estaba hecho lo anterior a esta fecha.")
    ap.add_argument("--ver", action="store_true",
                    help="Solo muestra el cronograma anterior al arranque.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No anota nada; solo muestra que anotaria.")
    args = ap.parse_args()

    arranque = fecha_de_arranque()
    plan = leer_respaldo()
    if not plan:
        raise SystemExit(
            "ERROR: no hay cronograma leido. Corre antes 'Sincronizar'.")

    previas = anteriores_al_arranque(plan, arranque)

    print("=" * 74)
    print(f" ARRANQUE - {ajustes.NOMBRE_OBRA}")
    print(f" El sistema toma el control el {horario.fecha_larga(arranque)}")
    print("=" * 74)
    print(f"\n Cronograma completo:        {len(plan):5} tareas")
    print(f" Anteriores al arranque:     {len(previas):5} tareas  <- de estas hablamos")
    print(f" Del arranque en adelante:   {len(plan) - len(previas):5} tareas"
          f"  <- estas las gestiona el sistema")

    if previas:
        por_mes = Counter((t.get("fecha") or "?")[:7] for t in previas)
        print("\n Lo anterior al arranque, por mes:")
        for mes in sorted(por_mes):
            print(f"   {mes}   {por_mes[mes]:4} tareas")

    ya = punto_de_partida()
    if ya:
        print(f"\n Punto de partida declarado: {ya} de {len(previas)} ya estaban hechas.")
    else:
        print("\n Todavia no se ha declarado nada: el avance cuenta desde cero.")

    if args.ver or not args.hechas:
        if not args.hechas:
            print("\n Para declararlo, vuelve a correr eligiendo --hechas:")
            print("   todas    todo lo anterior al arranque ya esta hecho")
            print("   ninguna  el plan empieza de cero")
            print("   hasta    estaba hecho lo anterior a --hasta AAAA-MM-DD")
            print("   <numero> la cifra exacta, si la sabes")
        print("=" * 74)
        return 0

    hasta = None
    if args.hasta:
        try:
            hasta = date.fromisoformat(args.hasta.strip())
        except ValueError as e:
            raise SystemExit(f"ERROR: --hasta no es una fecha: {args.hasta!r}") from e

    hechas = cuantas_hechas(previas, str(args.hechas).strip().lower(), hasta)
    faltan = len(previas) - hechas
    avance = hechas / len(plan) * 100 if plan else 0

    print("\n" + "-" * 74)
    print(f" Punto de partida: {hechas} de {len(previas)} tareas anteriores ya hechas.")
    print(f" Quedan {faltan} atrasadas de antes del arranque.")
    print(f" La obra arranca con un {avance:.1f}% del plan completo.")

    if args.dry_run:
        print("\n (DRY-RUN: no se anoto nada.)")
    else:
        ruta = guardar_cierre(arranque, hechas)
        print(f"\n Anotado en {ruta}, con fecha {arranque}.")
        print(" Corre 'Reporte' para que el dashboard lo recoja.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

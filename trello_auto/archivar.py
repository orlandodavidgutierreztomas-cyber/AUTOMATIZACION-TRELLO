#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 5 — ARCHIVAR: guarda lo culminado y deja el tablero limpio.
============================================================================

QUE HACE
--------
Al final del dia, archiva las tarjetas de la lista CULMINADO. Archivar en
Trello no borra nada: las tarjetas quedan guardadas y se pueden recuperar
desde el menu del tablero. Solo dejan de ocupar espacio a la vista.

SOLO archiva lo culminado. Lo que quedo abierto se queda en su lista de por
cerrar, a la vista: en Last Planner el trabajo que no termina no se guarda,
se REPROGRAMA, y para reprogramarlo hay que poder verlo.

  --antiguedad N           archiva solo lo que vencio hace N dias o mas
                           (util para dejar unos dias de margen antes de
                           guardar lo culminado)

Es IDEMPOTENTE: solo ve tarjetas abiertas, asi que lo ya archivado se ignora.

USO
---
    python -m trello_auto.archivar
    python -m trello_auto.archivar --dry-run
    python -m trello_auto.archivar --antiguedad 7
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes, horario
from .trello import Trello, buscar_lista, nombre_de_lista


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Archiva las tarjetas culminadas para dejar el tablero limpio.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No archiva nada; solo muestra que haria.")
    ap.add_argument("--antiguedad", type=int, default=0,
                    help="Archiva solo lo vencido hace N dias o mas (por defecto 0: todo).")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)

    # Solo lo culminado. Lo que quedo abierto NO se archiva: se reprograma,
    # y para eso tiene que seguir a la vista en su lista de por cerrar.
    objetivo = [ajustes.LISTA_CULMINADO]

    hoy = horario.hoy_local()
    print("=" * 74)
    print(f" ARCHIVAR - {horario.fecha_larga(hoy)} ({ajustes.TZ_OBRA})")
    if args.antiguedad:
        print(f" Solo lo vencido hace {args.antiguedad} dias o mas")
    print("=" * 74)

    archivadas = conservadas = 0
    for clave in objetivo:
        lid = buscar_lista(listas, clave)
        if not lid:
            print(f"\n--- '{clave}': no existe en el tablero, se omite.")
            continue
        tarjetas = tr.tarjetas_de_lista(lid)
        print(f"\n--- {nombre_de_lista(listas, lid)}: {len(tarjetas)} tarjetas")

        for card in tarjetas:
            vence = horario.utc_a_local(card.get("due"))
            dias = (hoy - vence.date()).days if vence else 0
            if args.antiguedad and dias < args.antiguedad:
                print(f"  - conservo ({dias}d): {card['name']}")
                conservadas += 1
                continue
            print(f"  archivo ({dias}d): {card['name']}")
            if not args.dry_run:
                tr.archivar(card["id"])
            archivadas += 1

    modo = "  (DRY-RUN: no se archivo nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    print(f" Archivadas: {archivadas}.{modo}")
    if conservadas:
        print(f" Conservadas por ser recientes: {conservadas}.")
    print(" Nada se borro: en Trello lo archivado se recupera desde el menu "
          "del tablero.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

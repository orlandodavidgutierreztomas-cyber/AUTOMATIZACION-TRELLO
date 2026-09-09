#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 REUBICAR — vacia una lista repartiendo sus tarjetas por familia.
============================================================================

Sirve para retirar una columna del tablero SIN PERDER TRABAJO. Cada tarjeta
se lee, se identifica su actividad y su familia, y se manda a la lista que le
corresponde segun la configuracion actual. Al final, si se pide, la lista
vacia se archiva.

De aqui salio el retiro de la vieja lista de "no cumplidas": ese trabajo no
estaba terminado, asi que no se podia archivar; habia que devolverlo a la
lista de por cerrar de su familia para poder reprogramarlo.

NADA SE BORRA. Mover una tarjeta conserva su nombre, su descripcion, sus
checklists, sus etiquetas, sus comentarios y su historial. Archivar una lista
en Trello tampoco borra: se puede recuperar desde el menu del tablero.

Es IDEMPOTENTE: la tarjeta que ya esta en su destino no se toca, asi que
repetir la corrida no hace nada.

USO
---
    python -m trello_auto.reubicar --desde "NO CUMPLIDAS" --dry-run
    python -m trello_auto.reubicar --desde "NO CUMPLIDAS"
    python -m trello_auto.reubicar --desde "NO CUMPLIDAS" --archivar-lista
    python -m trello_auto.reubicar --desde "X" --a-lista "T. DEL DIA VARIOS"
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes, horario
from .cronograma import destino_de
from .distribuir import partes_del_nombre
from .trello import Trello, buscar_lista, nombre_de_lista


def destino_de_tarjeta(nombre_tarjeta: str) -> tuple:
    """(familia, clave_de_lista) a la que pertenece esta tarjeta."""
    actividad = partes_del_nombre(nombre_tarjeta).get("actividad") or nombre_tarjeta
    familia, _lista = destino_de(actividad)
    return familia, ajustes.lista_cierre_de_familia(familia)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Vacia una lista repartiendo sus tarjetas por familia.")
    ap.add_argument("--desde", required=True,
                    help="Palabra clave de la lista que se quiere vaciar.")
    ap.add_argument("--a-lista", default=None,
                    help="Mandarlo TODO a esta lista, en vez de repartir por familia.")
    ap.add_argument("--archivar-lista", action="store_true",
                    help="Archiva la lista de origen cuando quede vacia.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No mueve ni archiva nada; solo muestra que haria.")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)

    origen = buscar_lista(listas, args.desde)
    if not origen:
        raise SystemExit(f"ERROR: no encuentro ninguna lista que case con "
                         f"'{args.desde}' en el tablero.")

    print("=" * 74)
    print(f" REUBICAR - {horario.fecha_larga(horario.hoy_local())} ({ajustes.TZ_OBRA})")
    print(f" Vaciando: {nombre_de_lista(listas, origen)}")
    if args.a_lista:
        print(f" Todo va a: {args.a_lista}")
    else:
        print(" Cada tarjeta va a la lista de por cerrar de SU familia.")
    print("=" * 74)

    tarjetas = tr.tarjetas_de_lista(origen)
    print(f"\n {len(tarjetas)} tarjetas por reubicar\n")

    cache, movidas, quietas, sin_destino = {}, 0, 0, 0
    for card in tarjetas:
        if args.a_lista:
            familia, clave = "-", args.a_lista
        else:
            familia, clave = destino_de_tarjeta(card["name"])
        if clave not in cache:
            cache[clave] = buscar_lista(listas, clave)
        destino = cache[clave]

        if not destino:
            print(f"  ! sin destino ('{clave}'): {card['name'][:52]}")
            sin_destino += 1
            continue
        if card.get("idList") == destino:
            quietas += 1
            continue
        print(f"  -> {familia:12} {clave:34} {card['name'][:44]}")
        if not args.dry_run:
            tr.mover(card["id"], destino)
        movidas += 1

    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    print(f" {movidas} movidas · {quietas} ya estaban en su sitio · "
          f"{sin_destino} sin destino{modo}")

    if sin_destino:
        print(" La lista NO se archiva: quedan tarjetas sin sitio a donde ir.")
    elif args.archivar_lista:
        if args.dry_run:
            print(" (DRY-RUN: aqui se archivaria la lista de origen.)")
        else:
            tr.archivar_lista(origen)
            print(" Lista de origen archivada. Se puede recuperar desde el")
            print(" menu del tablero: Mas -> Listas archivadas.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

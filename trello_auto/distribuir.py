#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 2 — DISTRIBUIR: vacia ESPERA repartiendo a las listas del dia.
============================================================================

QUE HACE
--------
Al amanecer, coge las tarjetas que PREPARAR dejo anoche en la lista ESPERA
y manda cada una a su lista del dia, segun la familia de su actividad
(Acero, Encofrado, Concreto...). La lista de espera queda vacia y el tablero
amanece listo para la jornada.

COMO SABE A DONDE VA CADA UNA
-----------------------------
Del nombre de la tarjeta saca la actividad ("1CS11 - ACERO ... - 28/08/2026")
y la busca en el mapeo (mapeo.json). Si ahi no esta, la deduce por palabras
clave. Lo que no case con nada cae en la familia de descarte, nunca se queda
sin destino.

CONTROL DE FECHA
----------------
Avisa si en ESPERA quedo alguna tarjeta de otro dia (senal de que un dia no
se distribuyo). Por defecto las reparte igual; con --solo-hoy las deja.

Es IDEMPOTENTE: si ESPERA ya esta vacia, no hace nada.

USO
---
    python -m trello_auto.distribuir
    python -m trello_auto.distribuir --dry-run
    python -m trello_auto.distribuir --solo-hoy
============================================================================
"""

from __future__ import annotations

import argparse
import re
import sys

from . import ajustes, horario
from .cronograma import destino_de
from .trello import Trello, buscar_lista

# "1CS11 - ACERO DE VIGA DE CIMENTACION - 28/08/2026"
NOMBRE_RE = re.compile(r"^\s*(?P<sector>\S+)\s+-\s+(?P<actividad>.+?)\s+-\s+"
                       r"(?P<fecha>\d{2}/\d{2}/\d{4})\s*$")


def partes_del_nombre(nombre: str) -> dict:
    """Saca sector, actividad y fecha del nombre de una tarjeta del dia."""
    m = NOMBRE_RE.match(nombre or "")
    if not m:
        return {}
    return m.groupdict()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reparte las tarjetas de ESPERA a sus listas del dia.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No mueve nada; solo muestra que haria.")
    ap.add_argument("--solo-hoy", action="store_true",
                    help="Reparte solo las tarjetas fechadas hoy; deja el resto en ESPERA.")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)

    id_espera = buscar_lista(listas, ajustes.LISTA_ESPERA)
    if not id_espera:
        raise SystemExit(
            f"ERROR: no encuentro la lista de espera '{ajustes.LISTA_ESPERA}'.\n"
            f"Revisa configuracion.json -> listas.espera."
        )

    hoy = horario.hoy_local()
    hoy_txt = f"{hoy:%d/%m/%Y}"

    print("=" * 74)
    print(f" DISTRIBUIR - {horario.fecha_larga(hoy)} ({ajustes.TZ_OBRA})")
    print(f" Origen: lista '{ajustes.LISTA_ESPERA}'")
    print("=" * 74)

    en_espera = tr.tarjetas_de_lista(id_espera)
    if not en_espera:
        print("\nLa lista de espera ya esta vacia. Nada que repartir.")
        return 0
    print(f"\n{len(en_espera)} tarjetas en espera.")

    # Cache de listas destino ya resueltas, para no buscarlas una y otra vez
    destinos = {}
    movidas = saltadas = sin_lista = de_otro_dia = 0

    for card in en_espera:
        partes = partes_del_nombre(card["name"])
        actividad = partes.get("actividad", "")
        fecha_txt = partes.get("fecha", "")

        if not actividad:
            print(f"  ? No entiendo el nombre, la dejo en espera: {card['name']}")
            saltadas += 1
            continue

        if fecha_txt and fecha_txt != hoy_txt:
            de_otro_dia += 1
            if args.solo_hoy:
                print(f"  - De otro dia ({fecha_txt}), la dejo: {card['name']}")
                saltadas += 1
                continue

        familia, nombre_lista = destino_de(actividad)
        if nombre_lista not in destinos:
            destinos[nombre_lista] = buscar_lista(listas, nombre_lista)
        id_destino = destinos[nombre_lista]

        if not id_destino:
            print(f"  ! No encuentro la lista '{nombre_lista}' para {familia}. "
                  f"La dejo en espera: {card['name']}")
            sin_lista += 1
            continue

        print(f"  -> [{familia:11}] {card['name']}")
        if not args.dry_run:
            tr.mover(card["id"], id_destino)
        movidas += 1

    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    print(f" Repartidas: {movidas}.{modo}")
    if de_otro_dia:
        print(f" AVISO: {de_otro_dia} tarjetas no eran de hoy "
              f"(quedo trabajo sin distribuir algun dia).")
    if sin_lista:
        print(f" AVISO: {sin_lista} sin lista destino; siguen en espera.")
    if saltadas:
        print(f" Sin tocar: {saltadas}.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

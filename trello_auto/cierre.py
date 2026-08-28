#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 3 — CIERRE: mueve cada tarjeta segun su control de calidad.
============================================================================

QUE HACE
--------
Al cierre de la jornada recorre las listas del dia (y la de "por cerrar") y
manda cada tarjeta a donde le toca:

  - Checklist 100% marcado   ->  CULMINADO
  - Le falta algun item      ->  T. NO CUMPLIDAS

Manda el control de calidad, no la marca de "completa" de Trello: no basta
con tildar la tarjeta, hay que haber marcado cada item.

CRITERIO (configuracion.json -> cierre.criterio)
  "checklist" -> POR DEFECTO. Todos los items marcados.
  "auto"      -> checklist completo O tarjeta marcada como completa.
  "marcada"   -> solo la marca de completa de Trello.

Es IDEMPOTENTE: al terminar, las listas del dia quedan vacias; una segunda
corrida no encuentra nada que mover.

USO
---
    python -m trello_auto.cierre
    python -m trello_auto.cierre --dry-run
    python -m trello_auto.cierre --criterio auto
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes, horario
from .trello import Trello, buscar_lista, checklist_completo, contar_checks

CRITERIOS = ("checklist", "auto", "marcada")


def esta_terminada(card: dict, criterio: str) -> bool:
    marcada = bool(card.get("dueComplete"))
    completo = checklist_completo(card)
    if criterio == "marcada":
        return marcada
    if criterio == "auto":
        return marcada or completo
    return completo


def listas_a_cerrar() -> list:
    """Las listas del dia de cada familia, mas la de 'por cerrar' si existe."""
    claves = []
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        if lista and lista not in claves:
            claves.append(lista)
    if ajustes.LISTA_POR_CERRAR and ajustes.LISTA_POR_CERRAR not in claves:
        claves.append(ajustes.LISTA_POR_CERRAR)
    return claves


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mueve las tarjetas del dia segun su control de calidad.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No mueve nada; solo muestra que haria.")
    ap.add_argument("--criterio", default=None, choices=list(CRITERIOS),
                    help="Criterio de 'terminada' (por defecto, el configurado).")
    args = ap.parse_args()

    criterio = (args.criterio or ajustes.CRITERIO_CIERRE).lower()
    if criterio not in CRITERIOS:
        raise SystemExit(f"ERROR: criterio invalido {criterio!r}. Usa {CRITERIOS}.")

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)

    id_culminado = buscar_lista(listas, ajustes.LISTA_CULMINADO)
    id_no_cumplidas = buscar_lista(listas, ajustes.LISTA_NO_CUMPLIDAS)
    if not id_culminado or not id_no_cumplidas:
        estado_c = "ok" if id_culminado else "NO ENCONTRADA"
        estado_n = "ok" if id_no_cumplidas else "NO ENCONTRADA"
        raise SystemExit(
            "ERROR: no encuentro las listas de destino en el tablero.\n"
            f"  - '{ajustes.LISTA_CULMINADO}' -> {estado_c}\n"
            f"  - '{ajustes.LISTA_NO_CUMPLIDAS}' -> {estado_n}\n"
            "Revisa configuracion.json -> listas."
        )

    print("=" * 74)
    print(f" CIERRE - {horario.fecha_larga(horario.hoy_local())} ({ajustes.TZ_OBRA})")
    print(f" Criterio: {criterio}")
    print("=" * 74)

    a_culminado = a_no_cumplidas = 0
    for clave in listas_a_cerrar():
        lid = buscar_lista(listas, clave)
        if not lid:
            print(f"\n--- '{clave}': no existe en el tablero, se omite.")
            continue
        tarjetas = tr.tarjetas_de_lista(lid)
        print(f"\n--- '{clave}': {len(tarjetas)} tarjetas")
        for card in tarjetas:
            terminada = esta_terminada(card, criterio)
            cuenta = contar_checks(card, ajustes.RESPONSABLES)
            destino = id_culminado if terminada else id_no_cumplidas
            etiqueta = "CULMINADA" if terminada else "NO CUMPLIDA"
            detalle = f"{cuenta['pendientes']}/{cuenta['total']} pendientes"
            print(f"  -> [{etiqueta:11}] {detalle:18} {card['name']}")
            if not args.dry_run:
                tr.mover(card["id"], destino)
            if terminada:
                a_culminado += 1
            else:
                a_no_cumplidas += 1

    total = a_culminado + a_no_cumplidas
    ppc = (a_culminado / total * 100) if total else 0
    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    print(f" Cierre: {a_culminado} culminadas, {a_no_cumplidas} no cumplidas.{modo}")
    if total:
        print(f" PPC del dia (cumplimiento del plan): {ppc:.0f}%")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

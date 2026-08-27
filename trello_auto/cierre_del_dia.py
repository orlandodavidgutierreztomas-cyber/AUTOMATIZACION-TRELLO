#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 CIERRE DEL DIA - mueve las tarjetas segun su estado.
============================================================================

QUE HACE
--------
Recorre las listas "T. DEL DIA" (Acero, Encofrado, Concreto, Varios) y la
lista "EN EJECUCION", y al cierre de la jornada:

  - Las tarjetas TERMINADAS      ->  CULMINADO
  - Las demas                    ->  T. NO CUMPLIDAS

Asi, al dia siguiente, las listas del dia quedan limpias para las tarjetas
nuevas, y queda registro de que se cumplio y que no.

CUANDO SE CONSIDERA TERMINADA  (settings.CRITERIO_CIERRE)
---------------------------------------------------------
  "checklist" -> POR DEFECTO. Solo si TODOS los items de sus checklists estan
                 marcados: manda el control de calidad, no basta con tildar la
                 tarjeta. Si le falta un item (o no tiene checklist), va a
                 NO CUMPLIDAS.
  "auto"      -> marcada como completa en Trello  O  checklist 100% marcado
  "marcada"   -> solo si la tarjeta esta marcada como completa

Los nombres de lista se resuelven por PALABRA CLAVE: funcionan aunque las
listas tengan emojis, acentos o espacios de mas.

USO
---
    python -m trello_auto.cierre_del_dia
    python -m trello_auto.cierre_del_dia --dry-run
    python -m trello_auto.cierre_del_dia --criterio checklist
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import horario
from . import settings as config
from .trello import Trello, buscar_lista


def checklist_completo(card: dict) -> bool:
    """True si la tarjeta tiene al menos un item y TODOS estan marcados."""
    items = [ci for cl in (card.get("checklists") or [])
             for ci in cl.get("checkItems", [])]
    if not items:
        return False
    return all(ci.get("state") == "complete" for ci in items)


def esta_terminada(card: dict, criterio: str) -> bool:
    marcada = bool(card.get("dueComplete"))
    completo = checklist_completo(card)
    if criterio == "marcada":
        return marcada
    if criterio == "checklist":
        return completo
    return marcada or completo          # "auto"


def main() -> int:
    ap = argparse.ArgumentParser(description="Mueve las tarjetas del dia segun su estado.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No mueve nada; solo muestra que haria.")
    ap.add_argument("--criterio", default=None,
                    choices=["auto", "checklist", "marcada"],
                    help="Criterio de 'terminada' (por defecto, el configurado).")
    args = ap.parse_args()

    criterio = (args.criterio or config.CRITERIO_CIERRE).lower()
    if criterio not in ("auto", "checklist", "marcada"):
        raise SystemExit(f"ERROR: criterio invalido {criterio!r}.")

    config.exigir_credenciales()
    tr = Trello(config.TRELLO_KEY, config.TRELLO_TOKEN)
    listas = tr.listas(config.BOARD_ID)

    id_culminado = buscar_lista(listas, config.LISTA_CULMINADO)
    id_no_cumplidas = buscar_lista(listas, config.LISTA_NO_CUMPLIDAS)
    if not id_culminado or not id_no_cumplidas:
        estado_c = "ok" if id_culminado else "NO ENCONTRADA"
        estado_n = "ok" if id_no_cumplidas else "NO ENCONTRADA"
        raise SystemExit(
            "ERROR: no encuentro las listas de destino en el tablero.\n"
            f"  - Busco '{config.LISTA_CULMINADO}' -> {estado_c}\n"
            f"  - Busco '{config.LISTA_NO_CUMPLIDAS}' -> {estado_n}\n"
            "Revisa los nombres en settings.py (se buscan por palabra clave)."
        )

    print("=" * 74)
    print(f" Cierre del dia {horario.hoy_local():%d/%m/%Y} ({config.TZ_OBRA}) "
          f"- criterio: {criterio}")
    print("=" * 74)

    claves = list(config.LISTA_DIA_POR_TIPO.values()) + [config.LISTA_EN_EJECUCION]

    a_culminado = a_no_cumplidas = 0
    for clave in claves:
        lid = buscar_lista(listas, clave)
        if not lid:
            print(f"\n--- '{clave}': lista no encontrada en el tablero, se omite.")
            continue
        tarjetas = tr.tarjetas_de_lista(lid)
        print(f"\n--- '{clave}': {len(tarjetas)} tarjetas")
        for card in tarjetas:
            terminada = esta_terminada(card, criterio)
            destino = id_culminado if terminada else id_no_cumplidas
            etiqueta = "CULMINADA" if terminada else "NO CUMPLIDA"
            print(f"  -> [{etiqueta:11}] {card['name']}")
            if not args.dry_run:
                tr.mover(card["id"], destino)
            if terminada:
                a_culminado += 1
            else:
                a_no_cumplidas += 1

    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    print(f" Cierre: {a_culminado} -> CULMINADO, {a_no_cumplidas} -> NO CUMPLIDAS.{modo}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

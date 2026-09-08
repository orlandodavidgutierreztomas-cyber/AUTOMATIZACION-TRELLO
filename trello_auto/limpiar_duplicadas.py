#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 LIMPIAR DUPLICADAS — quita las copias vacias, nunca el trabajo hecho.
============================================================================

POR QUE HACE FALTA
------------------
La obra avanza mas rapido que el plan y el encargado adelanta tarjetas a
mano. Entre eso y las corridas manuales, acaban existiendo dos o tres
tarjetas con el mismo nombre. Duplican el conteo del reporte y ensucian el
tablero.

QUE HACE
--------
Agrupa las tarjetas abiertas por nombre (sin acentos ni mayusculas) y, donde
hay mas de una, CONSERVA LA QUE TIENE TRABAJO y archiva las copias vacias.

REGLAS DE SEGURIDAD — solo se archiva una copia si cumple TODAS:
  · Tiene otra tarjeta con el mismo nombre que se queda.
  · NO tiene ni un solo item de checklist marcado.
  · NO tiene comentarios.
  · NO tiene adjuntos.
Si una copia tiene cualquier rastro de trabajo, se queda y se avisa: prefiere
dejar un duplicado a borrar el trabajo de alguien.

Cual se conserva: la de mas items marcados. A igualdad, la que tenga
adjuntos o comentarios. A igualdad, la mas antigua.

ARCHIVA, NO BORRA. En Trello lo archivado se recupera desde el menu del
tablero. No se usa el borrado permanente a proposito.

USO
---
    python -m trello_auto.limpiar_duplicadas --dry-run     (empieza aqui)
    python -m trello_auto.limpiar_duplicadas
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes
from .trello import Trello, nombre_de_lista, normalizar


def _creada_en(card: dict) -> int:
    """Momento de creacion, que Trello codifica en los 8 primeros digitos del id."""
    try:
        return int(str(card.get("id", ""))[:8], 16)
    except ValueError:
        return 0


def _trabajo(card: dict) -> dict:
    """Rastros de trabajo humano en una tarjeta."""
    b = card.get("badges") or {}
    return {
        "marcados": int(b.get("checkItemsChecked") or 0),
        "items": int(b.get("checkItems") or 0),
        "comentarios": int(b.get("comments") or 0),
        "adjuntos": int(b.get("attachments") or 0),
    }


def esta_vacia(card: dict) -> bool:
    """True si no hay ni un rastro de trabajo humano: se puede archivar."""
    t = _trabajo(card)
    return (t["marcados"] == 0 and t["comentarios"] == 0 and t["adjuntos"] == 0)


def elegir_superviviente(grupo: list) -> dict:
    """De un grupo de duplicadas, la que se queda: la que mas trabajo tiene."""
    def puntaje(card):
        t = _trabajo(card)
        return (t["marcados"], t["adjuntos"] + t["comentarios"], -_creada_en(card))
    return max(grupo, key=puntaje)


def agrupar_duplicadas(cards: list) -> dict:
    """{nombre_normalizado: [tarjetas]} solo con los nombres repetidos."""
    grupos = {}
    for c in cards:
        clave = normalizar(c.get("name", ""))
        if clave:
            grupos.setdefault(clave, []).append(c)
    return {k: v for k, v in grupos.items() if len(v) > 1}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Archiva las tarjetas duplicadas que no tengan trabajo hecho.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No archiva nada; solo muestra que haria.")
    ap.add_argument("--incluir-plantillas", action="store_true",
                    help="Tambien revisa las tarjetas PLANTILLA (por defecto no).")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)
    cards = tr._req("GET", f"/boards/{ajustes.BOARD_ID}/cards",
                    {"fields": "name,idList,badges", "filter": "open"})

    if not args.incluir_plantillas:
        from .trello import es_plantilla
        cards = [c for c in cards if not es_plantilla(c.get("name", ""))]

    print("=" * 74)
    print(f" LIMPIAR DUPLICADAS - {ajustes.NOMBRE_OBRA}")
    print(f" {len(cards)} tarjetas abiertas en el tablero")
    print(" Duplicada = MISMO NOMBRE COMPLETO (sector, actividad y fecha).")
    print(" 'ACERO DE ZAPATA' y 'ACERO DE COLUMNA' NUNCA se agrupan; tampoco")
    print(" dos sectores distintos ni dos dias distintos.")
    print(" Solo se archiva una copia si NO tiene checks marcados, ni")
    print(" comentarios, ni adjuntos. Archivar no borra: se recupera desde")
    print(" el menu del tablero.")
    if args.dry_run:
        print(" (DRY-RUN: no se archiva nada)")
    print("=" * 74)

    grupos = agrupar_duplicadas(cards)
    if not grupos:
        print("\nNo hay ninguna tarjeta repetida. El tablero esta limpio.")
        return 0

    print(f"\n{len(grupos)} nombres aparecen mas de una vez.")

    archivadas = protegidas = 0
    for clave in sorted(grupos):
        grupo = grupos[clave]
        superviviente = elegir_superviviente(grupo)
        t = _trabajo(superviviente)

        print(f"\n--- {grupo[0]['name']}  ({len(grupo)} copias)")
        print(f"  CONSERVO  {t['marcados']}/{t['items']} marcados · "
              f"{nombre_de_lista(listas, superviviente.get('idList'))}")

        for card in grupo:
            if card["id"] == superviviente["id"]:
                continue
            tc = _trabajo(card)
            donde = nombre_de_lista(listas, card.get("idList"))
            if not esta_vacia(card):
                print(f"  PROTEGIDA {card['name']}")
                print(f"            {tc['marcados']}/{tc['items']} marcados, "
                      f"{tc['comentarios']} comentarios, {tc['adjuntos']} adjuntos "
                      f"· {donde}")
                print("            tiene trabajo hecho: NO la toco.")
                protegidas += 1
                continue
            print(f"  archivo   {card['name']}")
            print(f"            vacia · {donde}")
            if not args.dry_run:
                tr.archivar(card["id"])
            archivadas += 1

    print("\n" + "=" * 74)
    if args.dry_run:
        print(f" DRY-RUN: se archivarian {archivadas} copias vacias.")
    else:
        print(f" Archivadas {archivadas} copias vacias.")
    if protegidas:
        print(f" {protegidas} duplicadas NO se tocaron porque tenian trabajo")
        print(" hecho. Revisalas a mano y decide cual vale.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

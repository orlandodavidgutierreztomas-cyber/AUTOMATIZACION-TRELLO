#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 MONTAR TABLERO — deja un tablero vacio listo para trabajar, desde el Excel.
============================================================================

Es el arranque de una obra nueva. Con un tablero en blanco y el cronograma
subido, este robot construye todo lo que hace falta:

  1. LAS COLUMNAS. Crea las listas que el sistema necesita y que todavia no
     existan: la de espera, una por familia de trabajo, la de gracia, la de
     culminado y la de no cumplidas. En el orden en que fluye el trabajo.

  2. LAS PLANTILLAS. Una tarjeta PLANTILLA por cada actividad del cronograma
     que no tenga la suya, con un checklist por responsable ya montado. Los
     items son genericos: el objetivo NO es acertar el protocolo de cada
     actividad -eso lo sabe la obra, no el programa- sino dejar el esqueleto
     puesto para que solo haya que rellenarlo.

Asi, en vez de crear 75 tarjetas a mano con su estructura, se editan 75
tarjetas que ya existen y ya tienen la forma correcta.

ES IDEMPOTENTE Y NO DESTRUYE NADA: solo crea lo que falta. Si una lista o una
plantilla ya existe, la deja intacta -no la toca, no la renombra, no le borra
los items que hayas escrito-. Se puede correr las veces que haga falta, por
ejemplo cuando el cronograma incorpore actividades nuevas.

USO
---
    python -m trello_auto.montar_tablero --dry-run      (ver que haria)
    python -m trello_auto.montar_tablero
    python -m trello_auto.montar_tablero --solo-listas
    python -m trello_auto.montar_tablero --solo-plantillas
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes
from .cronograma import actividades_distintas, destino_de, leer_excel_completo
from .trello import Trello, buscar_lista, construir_indice_plantillas, normalizar

# Lista de plantillas donde nacen las tarjetas nuevas
LISTA_PLANTILLAS = "PLANTILLAS"

# Items genericos por responsable. Son un ESQUELETO a rellenar, no un
# protocolo: cada obra sabe que hay que verificar en cada actividad.
ITEMS_GENERICOS = {
    "CAMP": [
        "Frente disponible, accesible y liberado para ejecutar",
        "Materiales, equipos y cuadrilla en sitio",
    ],
    "BIM": [
        "Informacion vigente y compatibilizada publicada para la ejecucion",
    ],
    "EST": [
        "Criterio tecnico validado segun la informacion vigente",
        "Observaciones o puntos singulares resueltos, si corresponde",
    ],
    "CAL": [
        "Requisitos previos liberados antes de iniciar",
        "Verificacion en campo realizada y registrada en el protocolo",
        "Conformidad emitida y frente liberado para la actividad siguiente",
    ],
    "SSOMA": [
        "Charla de seguridad dictada y permisos vigentes",
        "Zona senalizada, ordenada y limpia al terminar",
    ],
    "AMB": [
        "Residuos segregados y dispuestos donde corresponde",
    ],
}

DESCRIPCION = """**PLANTILLA GENERICA — falta completarla.**

Esta tarjeta la creo la automatizacion a partir del cronograma. Su checklist
es un esqueleto: tiene una lista por responsable, pero los items son
genericos.

QUE HACER CON ELLA
1. Reescribe los items con el control de calidad real de esta actividad.
2. Anade la descripcion, las etiquetas y los adjuntos que quieras.
3. Borra los responsables que no intervengan aqui.

Cada tarjeta del dia de **{actividad}** se creara copiando esta: se llevara
su descripcion, sus checklists y sus etiquetas tal como esten en ese momento.
Lo que edites aqui rige desde el dia siguiente, sin tocar el codigo.

_Familia: {familia}. Aparece {veces} veces en el cronograma._
"""


def listas_necesarias() -> list:
    """[(nombre, para_que)] en el orden en que fluye el trabajo."""
    necesarias = [(ajustes.LISTA_ESPERA, "donde nacen las tarjetas de manana")]
    vistas = set()
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        if lista and lista not in vistas:
            vistas.add(lista)
            necesarias.append((lista, f"trabajo del dia · {familia}"))
    if ajustes.LISTA_POR_CERRAR:
        necesarias.append((ajustes.LISTA_POR_CERRAR, "margen de gracia del cierre"))
    necesarias.append((ajustes.LISTA_CULMINADO, "lo que cumplio"))
    necesarias.append((ajustes.LISTA_NO_CUMPLIDAS, "lo que no cumplio"))
    necesarias.append((LISTA_PLANTILLAS, "las plantillas de cada actividad"))
    return necesarias


def montar_listas(tr: Trello, listas: list, dry_run: bool) -> tuple:
    """Crea las listas que falten. Devuelve (listas_actualizadas, creadas)."""
    creadas = 0
    print("\n--- COLUMNAS DEL TABLERO ---")
    for nombre, para_que in listas_necesarias():
        if buscar_lista(listas, nombre):
            print(f"  ya existe   {nombre}")
            continue
        print(f"  CREAR       {nombre:34} ({para_que})")
        if not dry_run:
            nueva = tr.crear_lista(ajustes.BOARD_ID, nombre)
            listas.append({"id": nueva["id"], "name": nueva["name"]})
        creadas += 1
    return listas, creadas


def montar_plantillas(tr: Trello, listas: list, cards: list, dry_run: bool) -> tuple:
    """Crea una plantilla generica por actividad que no tenga la suya."""
    plan = leer_excel_completo()
    catalogo = actividades_distintas(plan)
    existentes = construir_indice_plantillas(cards, listas, ajustes.MARCA_PLANTILLA)

    id_plantillas = buscar_lista(listas, LISTA_PLANTILLAS)
    if not id_plantillas and not dry_run:
        raise SystemExit(
            f"ERROR: no encuentro la lista '{LISTA_PLANTILLAS}'. "
            f"Corre antes la parte de columnas."
        )

    faltan = [(n, v) for n, v in catalogo if normalizar(n) not in existentes]
    print("\n--- PLANTILLAS ---")
    print(f"  {len(catalogo)} actividades en el cronograma · "
          f"{len(catalogo) - len(faltan)} ya tienen plantilla")
    if not faltan:
        print("  No falta ninguna. Nada que crear.")
        return 0, 0

    creadas = items_puestos = 0
    for nombre, veces in faltan:
        familia, _lista = destino_de(nombre)
        print(f"  CREAR  [{familia:11}] PLANTILLA - {nombre}")
        if dry_run:
            creadas += 1
            continue

        card = tr.crear_tarjeta({
            "idList": id_plantillas,
            "name": f"PLANTILLA - {nombre}",
            "desc": DESCRIPCION.format(actividad=nombre, familia=familia, veces=veces),
            "pos": "bottom",
        })
        creadas += 1

        # Un checklist por responsable, en el orden de la configuracion
        for codigo in ajustes.CODIGOS_RESPONSABLE:
            items = ITEMS_GENERICOS.get(codigo)
            if not items:
                continue
            titulo = ajustes.RESPONSABLES[codigo].get("nombre", codigo).upper()
            checklist_id = tr.crear_checklist(card["id"], f"{titulo} - POR COMPLETAR")
            for item in items:
                tr.agregar_item(checklist_id, item)
                items_puestos += 1

    return creadas, items_puestos


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Monta las columnas y las plantillas de un tablero desde el Excel.")
    ap.add_argument("--dry-run", action="store_true",
                    help="No crea nada; solo muestra que haria.")
    ap.add_argument("--solo-listas", action="store_true",
                    help="Solo crea las columnas que falten.")
    ap.add_argument("--solo-plantillas", action="store_true",
                    help="Solo crea las plantillas que falten.")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)
    cards = tr.tarjetas(ajustes.BOARD_ID)

    print("=" * 74)
    print(f" MONTAR TABLERO - {ajustes.NOMBRE_OBRA}")
    print(f" Tablero {ajustes.BOARD_ID}: {len(listas)} listas, {len(cards)} tarjetas")
    print(" Solo se crea lo que falta. Nada existente se toca ni se borra.")
    if args.dry_run:
        print(" (DRY-RUN: no se crea nada)")
    print("=" * 74)

    listas_creadas = plantillas_creadas = items = 0

    if not args.solo_plantillas:
        listas, listas_creadas = montar_listas(tr, listas, args.dry_run)

    if not args.solo_listas:
        plantillas_creadas, items = montar_plantillas(tr, listas, cards, args.dry_run)

    print("\n" + "=" * 74)
    if args.dry_run:
        print(f" DRY-RUN: se crearian {listas_creadas} columnas y "
              f"{plantillas_creadas} plantillas.")
    else:
        print(f" Listo: {listas_creadas} columnas y {plantillas_creadas} plantillas "
              f"creadas ({items} items de checklist).")
        if plantillas_creadas:
            print(f"\n Las plantillas nuevas estan en la lista '{LISTA_PLANTILLAS}'")
            print(" con items GENERICOS. Reescribelos con el control de calidad")
            print(" real de cada actividad: eso es lo que copiara cada tarjeta")
            print(" del dia. Puedes hacerlo poco a poco, empezando por las")
            print(" actividades de la fase que viene.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

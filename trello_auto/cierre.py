#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 3 — CIERRE: mueve cada tarjeta segun su control de calidad.
============================================================================

EL CIERRE VA EN DOS FASES, con un margen de gracia en medio. La razon es
practica: cuando termina la jornada los especialistas siguen ocupados, y
dar por perdida una tarjeta a la que solo le faltaba marcarse seria
injusto y ensuciaria la estadistica.

  FASE 1 — "gracia"  (a la hora de fin de jornada)
    Recorre las listas del dia:
      checklist completo  ->  CULMINADO
      le falta algo       ->  T. POR CERRAR      <- el margen
    Las listas del dia quedan limpias, y lo pendiente queda a la vista, en un
    solo sitio, para quien todavia tenga que marcar.

  FASE 2 — "final"  (unas horas despues, cierre definitivo del dia)
    Recorre la lista de gracia (y las del dia, por si algo llego tarde):
      checklist completo  ->  CULMINADO         <- alcanzo a marcar
      le falta algo       ->  se queda donde esta

NO HAY LISTA DE "NO CUMPLIDAS", y es a proposito. En Last Planner el trabajo
que no se termino no se archiva: se REPROGRAMA. Mandarlo a un saco aparte
obligaria a sacarlo de ahi a mano, tarjeta por tarjeta, para volver a
meterlo en la programacion. Asi que lo que no cierra se queda en la lista de
por cerrar de su familia, a la vista, hasta que se termine o se reprograme.

Una tarjeta cuenta como terminada por su control de calidad O por la marca de
"cumplida" de Trello, lo que llegue primero (criterio "auto"). Quien quiera
exigir el checklist completo sin excepciones tiene el criterio "checklist".

CRITERIO (configuracion.json -> cierre.criterio)
  "auto"      -> POR DEFECTO. Vale cualquiera de las dos formas de cerrar:
                 el checklist completo O la tarjeta marcada como cumplida.
                 Es lo razonable en obra: hay actividades que no necesitan
                 todos los checks, y si el responsable la da por cumplida,
                 esta cumplida.
  "checklist" -> exige TODOS los items marcados, sin excepcion.
  "marcada"   -> solo la marca de Trello, ignora los checklists.

Ambas fases son IDEMPOTENTES: al terminar, las listas de origen quedan
vacias; una segunda corrida no encuentra nada que mover.

USO
---
    python -m trello_auto.cierre                    (fase de gracia)
    python -m trello_auto.cierre --fase final       (cierre definitivo)
    python -m trello_auto.cierre --dry-run
    python -m trello_auto.cierre --criterio auto
============================================================================
"""

from __future__ import annotations

import argparse
import sys

from . import ajustes, horario
from .cronograma import destino_de
from .distribuir import partes_del_nombre
from .trello import Trello, buscar_lista, checklist_completo, contar_checks, nombre_de_lista

CRITERIOS = ("checklist", "auto", "marcada")
FASES = ("gracia", "final")


def esta_terminada(card: dict, criterio: str) -> bool:
    marcada = bool(card.get("dueComplete"))
    completo = checklist_completo(card)
    if criterio == "marcada":
        return marcada
    if criterio == "auto":
        return marcada or completo
    return completo


def listas_del_dia() -> list:
    """Las listas del dia de cada familia, sin repetir."""
    claves = []
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        if lista and lista not in claves:
            claves.append(lista)
    return claves


def origenes_de_la_fase(fase: str) -> list:
    """De donde saca tarjetas cada fase."""
    if fase == "gracia":
        return listas_del_dia()
    # En el cierre definitivo se barre la lista de gracia y, por si acaso,
    # tambien las del dia: si la fase 1 no llego a correr, nada se queda atras.
    return ajustes.listas_de_cierre() + listas_del_dia()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mueve las tarjetas del dia segun su control de calidad.")
    ap.add_argument("--fase", default="gracia", choices=list(FASES),
                    help="'gracia' (fin de jornada) o 'final' (cierre definitivo).")
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
    if not id_culminado:
        raise SystemExit(
            f"ERROR: no encuentro la lista '{ajustes.LISTA_CULMINADO}'.\n"
            f"Revisa configuracion.json -> listas.culminado."
        )

    # A donde va lo que NO esta terminado: a la lista de por cerrar de su
    # FAMILIA, para que el tablero no mezcle acero con concreto. Es el mismo
    # destino en las dos fases; en la definitiva, la que ya estaba ahi
    # simplemente se queda, lista para reprogramarse.
    rotulo_pendiente = "A GRACIA" if args.fase == "gracia" else "SIGUE ABIERTA"

    faltan = [c for c in ajustes.listas_de_cierre() if not buscar_lista(listas, c)]
    if faltan:
        raise SystemExit(
            "ERROR: faltan listas de por cerrar en el tablero:\n"
            + "\n".join(f"  - {c}" for c in faltan)
            + "\nCrealas en Trello (o con 'Montar tablero'), o corrige "
              "configuracion.json -> familias.<X>.lista_cierre."
        )

    cache_gracia = {}

    def destino_pendiente(nombre_tarjeta):
        """(id_destino, nombre_legible) de donde va esta tarjeta si no cerro."""
        actividad = partes_del_nombre(nombre_tarjeta).get("actividad") or nombre_tarjeta
        familia, _lista = destino_de(actividad)
        clave = ajustes.lista_cierre_de_familia(familia)
        if clave not in cache_gracia:
            cache_gracia[clave] = buscar_lista(listas, clave)
        return cache_gracia[clave], clave

    print("=" * 74)
    print(f" CIERRE ({args.fase.upper()}) - {horario.fecha_larga(horario.hoy_local())} "
          f"({ajustes.TZ_OBRA})")
    print(f" Criterio: {criterio}")
    if args.fase == "gracia":
        print(f" Lo terminado va a '{ajustes.LISTA_CULMINADO}'.")
        print(" Lo pendiente espera en la lista de cierre DE SU FAMILIA:")
        for familia in ajustes.FAMILIAS:
            print(f"   {familia:12} -> {ajustes.lista_cierre_de_familia(familia)}")
        print(f" hasta el cierre definitivo de las {ajustes.hora_de('cierre_final')}.")
    else:
        print(" Cierre definitivo: se rescata lo que alcanzaron a marcar tarde.")
        print(" Lo que siga sin marcar SE QUEDA en su lista de por cerrar,")
        print(" para reprogramarlo. Nada se archiva como 'no cumplido'.")
    print("=" * 74)

    a_culminado = a_pendiente = 0
    for clave in origenes_de_la_fase(args.fase):
        lid = buscar_lista(listas, clave)
        if not lid:
            print(f"\n--- '{clave}': no existe en el tablero, se omite.")
            continue
        tarjetas = tr.tarjetas_de_lista(lid)
        print(f"\n--- {nombre_de_lista(listas, lid)}: {len(tarjetas)} tarjetas")
        for card in tarjetas:
            terminada = esta_terminada(card, criterio)
            cuenta = contar_checks(card, ajustes.RESPONSABLES)
            if terminada:
                destino, adonde = id_culminado, ajustes.LISTA_CULMINADO
            else:
                destino, adonde = destino_pendiente(card["name"])
            etiqueta = "CULMINADA" if terminada else rotulo_pendiente
            detalle = f"{cuenta['pendientes']}/{cuenta['total']} pendientes"
            print(f"  -> [{etiqueta:13}] {detalle:18} {card['name']}")
            if not destino:
                print(f"     ! sin lista destino ('{adonde}'), la dejo donde esta")
                continue
            if card.get("idList") == destino:
                # Ya esta donde le toca: no la toco y no la cuento dos veces
                continue
            if not args.dry_run:
                tr.mover(card["id"], destino)
            if terminada:
                a_culminado += 1
            else:
                a_pendiente += 1

    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    if args.fase == "gracia":
        print(f" Fin de jornada: {a_culminado} culminadas, "
              f"{a_pendiente} en margen de gracia.{modo}")
        if a_pendiente:
            print(f" Esas {a_pendiente} todavia se pueden salvar marcando su checklist "
                  f"antes de las {ajustes.hora_de('cierre_final')}.")
    else:
        print(f" Cierre definitivo: {a_culminado} rescatadas al final.{modo}")
        print(" El resto sigue en su lista de por cerrar, para reprogramarse.")
        # Lo culminado del dia si se anota: de esa serie sale el avance de
        # obra. Se cuenta lo que HAY en CULMINADO, no lo que movio esta
        # corrida, para que repetir el cierre no sume dos veces. Vale porque
        # 'archivar' vacia esa lista cada noche, despues de este paso.
        if not args.dry_run:
            from .historico import guardar_cierre
            culminadas_hoy = len(tr.tarjetas_de_lista(id_culminado))
            ruta = guardar_cierre(horario.hoy_local(), culminadas_hoy)
            print(f" {culminadas_hoy} culminadas hoy. Anotado en {ruta}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

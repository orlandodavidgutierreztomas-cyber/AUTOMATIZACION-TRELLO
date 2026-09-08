#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 3 — CIERRE: mueve cada tarjeta segun su control de calidad.
============================================================================

EL CIERRE VA EN DOS FASES, con un margen de gracia en medio. La razon es
practica: cuando termina la jornada los especialistas siguen ocupados, y
mandar al saco de "no cumplidas" una tarjeta que solo faltaba marcar seria
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
      le falta algo       ->  T. NO CUMPLIDAS   <- ahora si, no se cumplio

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

    # A donde va lo que NO esta terminado.
    # En la fase de gracia depende de la FAMILIA de cada tarjeta: cada una
    # espera en su propia lista de cierre, para que el tablero no mezcle acero
    # con concreto. En la definitiva, todo va al mismo sitio: no cumplidas.
    rotulo_pendiente = "A GRACIA" if args.fase == "gracia" else "NO CUMPLIDA"

    id_no_cumplidas = buscar_lista(listas, ajustes.LISTA_NO_CUMPLIDAS)
    if args.fase == "final" and not id_no_cumplidas:
        raise SystemExit(
            f"ERROR: no encuentro la lista '{ajustes.LISTA_NO_CUMPLIDAS}'.\n"
            f"Revisa configuracion.json -> listas.no_cumplidas."
        )

    if args.fase == "gracia":
        faltan = [c for c in ajustes.listas_de_cierre() if not buscar_lista(listas, c)]
        if faltan:
            raise SystemExit(
                "ERROR: faltan listas de gracia en el tablero:\n"
                + "\n".join(f"  - {c}" for c in faltan)
                + "\nCrealas en Trello (o con 'Montar tablero'), o corrige "
                  "configuracion.json -> familias.<X>.lista_cierre."
            )

    cache_gracia = {}

    def destino_pendiente(nombre_tarjeta):
        """(id_destino, nombre_legible) de donde va esta tarjeta si no cerro."""
        if args.fase == "final":
            return id_no_cumplidas, ajustes.LISTA_NO_CUMPLIDAS
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
        print(f" Cierre definitivo: lo que siga sin marcar pasa a "
              f"'{ajustes.LISTA_NO_CUMPLIDAS}'.")
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
            print(f"  -> [{etiqueta:11}] {detalle:18} {card['name']}")
            if not destino:
                print(f"     ! sin lista destino ('{adonde}'), la dejo donde esta")
                continue
            if not args.dry_run:
                tr.mover(card["id"], destino)
            if terminada:
                a_culminado += 1
            else:
                a_pendiente += 1

    total = a_culminado + a_pendiente
    modo = "  (DRY-RUN: no se movio nada)" if args.dry_run else ""
    print("\n" + "=" * 74)
    if args.fase == "gracia":
        print(f" Fin de jornada: {a_culminado} culminadas, "
              f"{a_pendiente} en margen de gracia.{modo}")
        if a_pendiente:
            print(f" Esas {a_pendiente} todavia se pueden salvar marcando su checklist "
                  f"antes de las {ajustes.hora_de('cierre_final')}.")
    else:
        ppc = (a_culminado / total * 100) if total else 0
        print(f" Cierre definitivo: {a_culminado} culminadas, "
              f"{a_pendiente} no cumplidas.{modo}")
        if total:
            print(f" PPC del dia (cumplimiento del plan): {ppc:.0f}%")
        # El PPC solo sirve si se guarda: un numero suelto no dice nada, la
        # serie de dias si. De aqui salen las graficas de tendencia.
        if not args.dry_run and total:
            from .historico import guardar_ppc
            ruta = guardar_ppc(horario.hoy_local(), a_culminado, a_pendiente)
            print(f" Anotado en {ruta}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

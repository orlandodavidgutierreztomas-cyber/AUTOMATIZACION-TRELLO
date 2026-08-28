#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 1 — PREPARAR: crea las tarjetas del dia siguiente en la lista ESPERA.
============================================================================

QUE HACE
--------
La tarde del dia 27 crea las tarjetas del dia 28 y las deja en la lista
ESPERA. Al amanecer del 28, el robot DISTRIBUIR las reparte a sus listas del
dia. Asi el tablero de hoy no se ensucia con lo de manana, y si el
cronograma trae una sorpresa hay toda la tarde para verla venir.

Cada tarjeta:
  - Se llama  "[SECTOR] - [ACTIVIDAD] - DD/MM/AAAA".
  - COPIA de su tarjeta PLANTILLA (la que lleva PLANTILLA en el nombre) su
    descripcion, sus checklists con todos los items, y sus etiquetas.
  - Lleva hora de INICIO y de FIN de la jornada de ese dia.
  - Nace en la lista ESPERA.

Si una actividad todavia no tiene plantilla, la tarjeta se crea igual, con
una descripcion generada, para no dejarla fuera del plan.

Es IDEMPOTENTE: si ya existe una tarjeta con ese nombre, no la duplica.

USO
---
    python -m trello_auto.preparar                      (las de manana)
    python -m trello_auto.preparar --fecha hoy
    python -m trello_auto.preparar --fecha 2026-09-01 --dry-run
    python -m trello_auto.preparar --fecha 2026-09-01 --fecha-fin 2026-09-04
============================================================================
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta

from . import ajustes, horario
from .cronograma import tareas_del_dia
from .trello import Trello, buscar_lista, construir_indice_plantillas, normalizar


def parse_fecha(texto: str) -> date:
    """'hoy', 'manana' o 'AAAA-MM-DD' -> date, en la hora de la obra."""
    texto = (texto or "").strip().lower()
    if texto in ("manana", "mañana", "tomorrow", ""):
        return horario.hoy_local() + timedelta(days=1)
    if texto in ("hoy", "today"):
        return horario.hoy_local()
    if texto in ("ayer", "yesterday"):
        return horario.hoy_local() - timedelta(days=1)
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(
            f"ERROR: fecha invalida {texto!r}. Usa AAAA-MM-DD, 'hoy' o 'manana'."
        ) from None


def descripcion_generada(tarea: dict, fecha_txt: str) -> str:
    return (f"**Sector:** {tarea['sector']}\n"
            f"**Actividad:** {tarea['actividad']}\n"
            f"**Familia:** {tarea['familia']}\n"
            f"**Programado para:** {fecha_txt}\n\n"
            f"_Aun no existe una tarjeta PLANTILLA para esta actividad en el "
            f"tablero. Crea una que se llame «PLANTILLA - {tarea['actividad']}» "
            f"y las proximas tarjetas copiaran su descripcion, sus checklists "
            f"y sus etiquetas automaticamente._")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crea en ESPERA las tarjetas de un dia, copiando las "
                    "plantillas del propio tablero.")
    ap.add_argument("--fecha", default="manana",
                    help='Fecha "AAAA-MM-DD", "hoy" o "manana" (por defecto: manana).')
    ap.add_argument("--fecha-fin", default=None,
                    help='Fecha final del rango (opcional).')
    ap.add_argument("--dry-run", action="store_true",
                    help="No crea nada; solo muestra que haria.")
    args = ap.parse_args()

    horario.parse_hhmm(ajustes.HORA_INICIO)
    horario.parse_hhmm(ajustes.HORA_FIN)

    inicio = parse_fecha(args.fecha)
    fin = parse_fecha(args.fecha_fin) if args.fecha_fin else inicio
    if fin < inicio:
        raise SystemExit("ERROR: --fecha-fin no puede ser anterior a --fecha.")
    fechas = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]

    print("=" * 74)
    print(f" PREPARAR - {ajustes.NOMBRE_OBRA}")
    if len(fechas) > 1:
        print(f" Tarjetas del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y} ({len(fechas)} dias)")
    else:
        print(f" Tarjetas para el {horario.fecha_larga(inicio)}")
    print(f" Jornada: {ajustes.HORA_INICIO} a {ajustes.HORA_FIN} ({ajustes.TZ_OBRA})")
    print(f" Destino: lista '{ajustes.LISTA_ESPERA}'")
    print("=" * 74)

    tr = listas = plantillas = None
    existentes = set()
    id_espera = None

    if not args.dry_run:
        ajustes.exigir_credenciales()

    if ajustes.TRELLO_KEY and ajustes.TRELLO_TOKEN:
        tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
        listas = tr.listas(ajustes.BOARD_ID)
        cards = tr.tarjetas(ajustes.BOARD_ID)
        existentes = {c["name"] for c in cards}
        plantillas = construir_indice_plantillas(cards, listas, ajustes.MARCA_PLANTILLA)
        id_espera = buscar_lista(listas, ajustes.LISTA_ESPERA)
        print(f"Tablero: {len(listas)} listas, {len(cards)} tarjetas, "
              f"{len(plantillas)} plantillas.")
        if not id_espera and not args.dry_run:
            raise SystemExit(
                f"ERROR: no encuentro la lista de espera '{ajustes.LISTA_ESPERA}'.\n"
                f"Revisa configuracion.json -> listas.espera."
            )
    else:
        print("(Sin credenciales: solo se lee el cronograma, no el tablero.)")
    if args.dry_run:
        print("(DRY-RUN: no se crea ni se modifica nada en Trello.)")

    creadas = saltadas = con_plantilla = sin_plantilla = 0

    for fecha in fechas:
        tareas = tareas_del_dia(fecha)
        print(f"\n--- {horario.fecha_larga(fecha)} ---")
        if not tareas:
            print("  (sin tareas programadas)")
            continue
        print(f"  {len(tareas)} tareas en el cronograma.")

        inicio_iso = horario.local_a_iso_utc(fecha, ajustes.HORA_INICIO)
        fin_iso = horario.local_a_iso_utc(fecha, ajustes.HORA_FIN)
        fecha_txt = f"{fecha:%d/%m/%Y}"

        for t in tareas:
            nombre = f"{t['sector']} - {t['actividad']} - {fecha_txt}"
            if nombre in existentes:
                saltadas += 1
                continue

            pl = plantillas.get(normalizar(t["actividad"])) if plantillas is not None else None
            etiqueta = "PLANTILLA" if pl else ("SIN LEER " if plantillas is None else "SIMPLE   ")

            if args.dry_run:
                print(f"  [{t['familia']:11}][{etiqueta}] {nombre}")
                con_plantilla += 1 if pl else 0
                sin_plantilla += 0 if pl else 1
                continue

            params = {
                "idList": id_espera,
                "name": nombre,
                "start": inicio_iso,
                "due": fin_iso,
                "pos": "bottom",
            }
            if pl:
                params["idCardSource"] = pl["id"]
                params["keepFromSource"] = ajustes.COPIAR_DE_PLANTILLA
                params["desc"] = pl["desc"]
                con_plantilla += 1
            else:
                params["desc"] = descripcion_generada(t, fecha_txt)
                sin_plantilla += 1

            tr.crear_tarjeta(params)
            existentes.add(nombre)
            creadas += 1
            print(f"  OK [{t['familia']:11}][{etiqueta}] {nombre}")

    print("\n" + "=" * 74)
    if args.dry_run:
        print(f" DRY-RUN: se habrian creado {con_plantilla + sin_plantilla} tarjetas "
              f"({con_plantilla} con plantilla, {sin_plantilla} sin ella).")
    else:
        print(f" Listo: {creadas} creadas en ESPERA "
              f"({con_plantilla} con plantilla, {sin_plantilla} sin ella), "
              f"{saltadas} ya existian.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 AUTOMATIZACION TRELLO - CONSTRUCCION DE AULAS
 Crea las tarjetas del dia en Trello a partir del cronograma Excel (LPS),
 COPIANDO la tarjeta PLANTILLA de cada actividad desde el propio tablero.
============================================================================

QUE HACE
--------
Lee la hoja "01_MAESTRO" del Excel, detecta que SECTOR hace que ACTIVIDAD en
una FECHA dada y, por cada uno, crea en Trello una tarjeta que:

  - Se llama  "[SECTOR] - [ACTIVIDAD] - DD/MM/AAAA".
  - COPIA de la tarjeta PLANTILLA del tablero (las que viven en las listas
    "PLANTILLA_..."):  su DESCRIPCION  y  todos sus CHECKLISTS con sus items.
  - Lleva HORA DE INICIO y HORA DE FIN (rango de fechas de Trello), tomadas
    de la configuracion (HORA_INICIO / HORA_FIN, hora local de la obra).
  - Se coloca en la lista del dia correcta segun el tipo de trabajo
    (Acero / Encofrado / Concreto / Varios).

El emparejamiento actividad -> plantilla se hace LEYENDO EL TABLERO EN VIVO:
no hay IDs escritos en el codigo. Si manana agregas una plantilla nueva al
tablero, el script la usa automaticamente.

Si una actividad TODAVIA no tiene plantilla, la tarjeta se crea igual, con una
descripcion generada y el checklist de respaldo de su tipo de trabajo
(settings.CHECKLIST_POR_TIPO), para no dejarla sin control de calidad.

Es IDEMPOTENTE: si una tarjeta con ese nombre ya existe, no la duplica.

COMO SE USA
-----------
    python -m trello_auto.crear_tarjetas --fecha hoy
    python -m trello_auto.crear_tarjetas --fecha 2026-08-26
    python -m trello_auto.crear_tarjetas --fecha 2026-08-26 --dry-run

    # Rango de fechas (crea las tarjetas de cada dia del rango, inclusive):
    python -m trello_auto.crear_tarjetas --fecha 2026-08-26 --fecha-fin 2026-08-29

    # Solo un tipo de trabajo (ACERO / ENCOFRADO / CONCRETO / VARIOS):
    python -m trello_auto.crear_tarjetas --fecha hoy --tipo CONCRETO

    # Cambiar el horario de la jornada solo para esta corrida:
    python -m trello_auto.crear_tarjetas --fecha hoy --hora-inicio 08:00 --hora-fin 18:00

CONFIGURACION
-------------
Credenciales y opciones en settings.py (variables de entorno / GitHub Secrets
/ horario.json). NADA de credenciales va escrito aqui.
============================================================================
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta

from . import horario
from . import settings as config
from .excel import leer_tareas_del_dia
from .trello import Trello, buscar_lista, construir_indice_plantillas, normalizar


# ---------------------------------------------------------------------------
# Utilidades de fechas
# ---------------------------------------------------------------------------
def parse_fecha(texto: str) -> date:
    """"hoy" o "AAAA-MM-DD" -> date. "hoy" usa la zona horaria de la obra."""
    texto = (texto or "").strip()
    if texto.lower() in ("hoy", "today", ""):
        return horario.hoy_local()
    if texto.lower() in ("manana", "mañana", "tomorrow"):
        return horario.hoy_local() + timedelta(days=1)
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(
            f"ERROR: fecha invalida {texto!r}. Usa AAAA-MM-DD o 'hoy'."
        ) from None


def rango_de_fechas(inicio: date, fin: date) -> list:
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


DIAS_ES = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


def fecha_larga(d: date) -> str:
    """'jueves 27/08/2026' (sin depender del idioma del sistema)."""
    return f"{DIAS_ES[d.weekday()]} {d:%d/%m/%Y}"


# ---------------------------------------------------------------------------
# Creacion de una tarjeta
# ---------------------------------------------------------------------------
def descripcion_generada(tarea: dict, fecha_txt: str) -> str:
    return (f"**Sector:** {tarea['sector']}\n"
            f"**Actividad:** {tarea['actividad']}\n"
            f"**Tipo de trabajo:** {tarea['tipo']}\n"
            f"**Programado para:** {fecha_txt} (plan maestro 01_MAESTRO).\n\n"
            f"_Aun no existe una tarjeta PLANTILLA para esta actividad en el "
            f"tablero; se uso el checklist de respaldo. En cuanto crees la "
            f"plantilla, las proximas tarjetas la copiaran automaticamente._")


def agregar_checklist_respaldo(tr: Trello, card_id: str, tipo: str) -> bool:
    """Checklist generico para las actividades que aun no tienen plantilla."""
    items = config.CHECKLIST_POR_TIPO.get(tipo)
    if not items:
        return False
    checklist_id = tr.crear_checklist(card_id, "Control de Calidad")
    for item in items:
        tr.agregar_item(checklist_id, item)
    return True


# ---------------------------------------------------------------------------
# Logica principal
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crea las tarjetas del dia en Trello desde el cronograma LPS, "
                    "copiando las plantillas del propio tablero.")
    ap.add_argument("--fecha", default="hoy",
                    help='Fecha inicial "AAAA-MM-DD" o la palabra "hoy" (por defecto: hoy).')
    ap.add_argument("--fecha-fin", default=None,
                    help='Fecha final "AAAA-MM-DD" (opcional). Corre cada dia del rango.')
    ap.add_argument("--tipo", default="TODOS",
                    choices=("TODOS",) + config.TIPOS,
                    help="Crea solo tarjetas de ese tipo de trabajo (por defecto TODOS).")
    ap.add_argument("--hora-inicio", default=None,
                    help="Hora de inicio de la jornada HH:MM (por defecto, la configurada).")
    ap.add_argument("--hora-fin", default=None,
                    help="Hora de fin / vencimiento HH:MM (por defecto, la configurada).")
    ap.add_argument("--dry-run", action="store_true",
                    help="No crea nada; solo muestra que haria.")
    args = ap.parse_args()

    hora_inicio = args.hora_inicio or config.HORA_INICIO
    hora_fin = args.hora_fin or config.HORA_FIN
    horario.parse_hhmm(hora_inicio)     # valida temprano, con mensaje claro
    horario.parse_hhmm(hora_fin)

    fecha_inicio = parse_fecha(args.fecha)
    fecha_fin = parse_fecha(args.fecha_fin) if args.fecha_fin else fecha_inicio
    if fecha_fin < fecha_inicio:
        raise SystemExit("ERROR: --fecha-fin no puede ser anterior a --fecha.")
    fechas = rango_de_fechas(fecha_inicio, fecha_fin)

    print("=" * 74)
    if len(fechas) > 1:
        print(f" Tarjetas del {fecha_inicio:%d/%m/%Y} al {fecha_fin:%d/%m/%Y} "
              f"({len(fechas)} dias) - tipo: {args.tipo}")
    else:
        print(f" Tarjetas para el {fecha_inicio:%d/%m/%Y} - tipo: {args.tipo}")
    print(f" Jornada: {hora_inicio} a {hora_fin} ({config.TZ_OBRA})")
    print("=" * 74)

    # --- Conectar y leer el tablero UNA sola vez para todo el rango --------
    # En dry-run tambien se LEE el tablero (solo lectura) para poder decir si
    # cada actividad tiene plantilla y si la tarjeta ya existe. Si no hay
    # credenciales, el dry-run sigue funcionando solo con el cronograma.
    tr = listas = plantillas = None
    existentes = set()
    if not args.dry_run:
        config.exigir_credenciales()

    if config.TRELLO_KEY and config.TRELLO_TOKEN:
        tr = Trello(config.TRELLO_KEY, config.TRELLO_TOKEN)
        listas = tr.listas(config.BOARD_ID)
        cards = tr.tarjetas(config.BOARD_ID)
        existentes = {c["name"] for c in cards}
        plantillas = construir_indice_plantillas(listas, cards, config.CLAVE_PLANTILLAS)
        print(f"Tablero leido: {len(listas)} listas, {len(cards)} tarjetas, "
              f"{len(plantillas)} plantillas detectadas.")
    else:
        print("(Sin credenciales: solo se lee el cronograma, no el tablero.)")
    if args.dry_run:
        print("(DRY-RUN: no se crea ni se modifica nada en Trello.)")

    creadas = saltadas = con_plantilla = sin_plantilla = sin_lista = 0

    for fecha in fechas:
        tareas = leer_tareas_del_dia(config.RUTA_EXCEL, fecha, config.RUTA_PLAN_JSON)
        if args.tipo != "TODOS":
            tareas = [t for t in tareas if t["tipo"] == args.tipo]

        print(f"\n--- {fecha_larga(fecha)} ---")
        if not tareas:
            print("  (sin tareas programadas para esa fecha/tipo)")
            continue
        print(f"  {len(tareas)} tareas en el cronograma.")

        inicio_iso = horario.local_a_iso_utc(fecha, hora_inicio)
        fin_iso = horario.local_a_iso_utc(fecha, hora_fin)
        fecha_txt = f"{fecha:%d/%m/%Y}"

        for t in tareas:
            nombre = f"{t['sector']} - {t['actividad']} - {fecha_txt}"

            if nombre in existentes:
                saltadas += 1
                continue                              # idempotencia

            pl = plantillas.get(normalizar(t["actividad"])) if plantillas is not None else None

            if args.dry_run:
                if plantillas is None:
                    etiqueta = "SIN LEER  "     # no se pudo consultar el tablero
                else:
                    etiqueta = "PLANTILLA " if pl else "RESPALDO  "
                print(f"  [{t['tipo']:9}][{etiqueta}] {nombre}")
                if pl:
                    con_plantilla += 1
                else:
                    sin_plantilla += 1
                continue

            list_id = buscar_lista(listas, config.LISTA_DIA_POR_TIPO[t["tipo"]])
            if not list_id:
                print(f"  ! No encuentro la lista del dia de '{t['tipo']}' "
                      f"(busco '{config.LISTA_DIA_POR_TIPO[t['tipo']]}'). Salto: {nombre}")
                sin_lista += 1
                continue

            params = {
                "idList": list_id,
                "name": nombre,
                "start": inicio_iso,
                "due": fin_iso,
                "pos": "bottom",
            }
            if pl:
                # Copia descripcion y TODOS los checklists desde la plantilla.
                params["idCardSource"] = pl["id"]
                params["keepFromSource"] = "checklists"
                params["desc"] = pl["desc"]
            else:
                params["desc"] = descripcion_generada(t, fecha_txt)

            card = tr.crear_tarjeta(params)
            existentes.add(nombre)
            creadas += 1

            if pl:
                con_plantilla += 1
                etiqueta = "PLANTILLA "
            else:
                agregar_checklist_respaldo(tr, card["id"], t["tipo"])
                sin_plantilla += 1
                etiqueta = "RESPALDO  "
            print(f"  OK [{t['tipo']:9}][{etiqueta}] {nombre}")

    print("\n" + "=" * 74)
    if args.dry_run:
        print(f" DRY-RUN: no se creo nada. Se habrian creado {con_plantilla + sin_plantilla} "
              f"tarjetas.")
    else:
        print(f" Listo: {creadas} creadas ({con_plantilla} con plantilla, "
              f"{sin_plantilla} con checklist de respaldo), "
              f"{saltadas} ya existian.")
        if sin_lista:
            print(f" Atencion: {sin_lista} tarjetas no se crearon por no encontrar su lista.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

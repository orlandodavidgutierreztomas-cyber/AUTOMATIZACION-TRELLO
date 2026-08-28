#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 ROBOT 4 — REPORTE: saca una foto del tablero y la deja lista para el Excel.
============================================================================

QUE HACE
--------
Recorre las tarjetas, cuenta los items de checklist que faltan por marcar,
los reparte por responsable (Estructuras, Calidad, Campo, Ambiental, BIM,
Seguridad) y escribe un CSV con una fila por tarjeta.

Cada corrida es un CORTE con su fecha y hora. Puedes hacer los que quieras
al dia -a mediodia, a las tres, antes del cierre-: SOLO LEE, nunca escribe
en Trello. Los cortes se van acumulando en el historico, asi que del CSV
sale tanto la foto de ahora como la pelicula de como evoluciona el pendiente.

ALCANCE (--alcance)
  dia           Las listas del dia + "por cerrar"  (lo que esta en juego hoy)
  no-cumplidas  La lista de no cumplidas           (la deuda acumulada)
  todo          Las dos cosas

SALIDA
  reportes/ultimo.csv   solo este corte (el que lee tu dashboard)
  reportes/cortes.csv   historico acumulado de todos los cortes

Repetir un corte en el mismo minuto lo REEMPLAZA en el historico, no lo
duplica: el CSV nunca cuenta dos veces lo mismo.

USO
---
    python -m trello_auto.reporte
    python -m trello_auto.reporte --alcance no-cumplidas
    python -m trello_auto.reporte --alcance todo
============================================================================
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime

from . import ajustes, horario
from .cronograma import destino_de
from .distribuir import partes_del_nombre
from .trello import Trello, buscar_lista, contar_checks

ALCANCES = ("dia", "no-cumplidas", "todo")


def columnas() -> list:
    """Cabecera del CSV. Reproduce la hoja DATOS del dashboard."""
    return (["CORTE", "SECTOR / ZONA", "ACTIVIDAD", "FAMILIA", "VENCE"]
            + list(ajustes.CODIGOS_RESPONSABLE)
            + ["OTROS", "CHECKS PENDIENTES", "TOTAL CHECKS", "ANTIGUEDAD (dias)",
               "CLAVE ORDEN", "LISTA TRELLO", "DIA DEL CORTE", "ESTADO",
               "LINK TRELLO"])


def dia_del_corte(vence, hoy) -> str:
    """Etiqueta que usa el dashboard para separar lo de hoy de lo arrastrado."""
    if vence is None:
        return "SIN FECHA"
    if vence.date() >= hoy:
        return "HOY"
    return "AYER Y ANTES"


def fila_de_tarjeta(card: dict, nombre_lista: str, estado: str,
                    corte: datetime, orden: int) -> dict:
    hoy = corte.date()
    partes = partes_del_nombre(card.get("name", ""))
    actividad = partes.get("actividad") or card.get("name", "")
    sector = partes.get("sector") or ""
    familia, _ = destino_de(actividad)

    vence = horario.utc_a_local(card.get("due"))
    antiguedad = max(0, (hoy - vence.date()).days) if vence else 0

    cuenta = contar_checks(card, ajustes.RESPONSABLES)

    fila = {
        "CORTE": corte.strftime("%Y-%m-%d %H:%M"),
        "SECTOR / ZONA": sector,
        "ACTIVIDAD": actividad,
        "FAMILIA": familia,
        "VENCE": vence.strftime("%Y-%m-%d %H:%M") if vence else "",
        "OTROS": cuenta["sin_responsable"],
        "CHECKS PENDIENTES": cuenta["pendientes"],
        "TOTAL CHECKS": cuenta["total"],
        "ANTIGUEDAD (dias)": antiguedad,
        # Ordena por urgencia: mas pendientes primero, sin empates
        "CLAVE ORDEN": round(cuenta["pendientes"] + orden / 10000, 4),
        "LISTA TRELLO": nombre_lista,
        "DIA DEL CORTE": dia_del_corte(vence, hoy),
        "ESTADO": estado,
        "LINK TRELLO": card.get("shortUrl", ""),
    }
    for codigo in ajustes.CODIGOS_RESPONSABLE:
        fila[codigo] = cuenta["por_responsable"].get(codigo, 0)
    return fila


def listas_del_alcance(alcance: str) -> list:
    """[(clave_de_lista, estado)] segun el alcance pedido."""
    objetivo = []
    if alcance in ("dia", "todo"):
        for familia in ajustes.FAMILIAS:
            lista = ajustes.lista_de_familia(familia)
            if lista and all(lista != c for c, _ in objetivo):
                objetivo.append((lista, "EN JUEGO"))
        if ajustes.LISTA_POR_CERRAR:
            objetivo.append((ajustes.LISTA_POR_CERRAR, "POR CERRAR"))
    if alcance in ("no-cumplidas", "todo"):
        objetivo.append((ajustes.LISTA_NO_CUMPLIDAS, "NO CUMPLIDA"))
    return objetivo


def escribir_csv(ruta, filas: list, cabecera: list):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cabecera, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def acumular_historico(ruta, filas: list, cabecera: list, corte_txt: str):
    """Anade el corte al historico, reemplazandolo si ya estaba."""
    previas = []
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            previas = [r for r in csv.DictReader(f) if r.get("CORTE") != corte_txt]
    escribir_csv(ruta, previas + filas, cabecera)
    return len(previas)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Genera el corte de control y lo deja en CSV para el dashboard.")
    ap.add_argument("--alcance", default="dia", choices=list(ALCANCES),
                    help="Que tarjetas entran en el corte (por defecto: dia).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Muestra el corte por pantalla sin escribir los CSV.")
    args = ap.parse_args()

    ajustes.exigir_credenciales()
    tr = Trello(ajustes.TRELLO_KEY, ajustes.TRELLO_TOKEN)
    listas = tr.listas(ajustes.BOARD_ID)

    corte = horario.ahora_local()
    corte_txt = corte.strftime("%Y-%m-%d %H:%M")

    print("=" * 74)
    print(f" REPORTE - {ajustes.NOMBRE_OBRA}")
    print(f" Corte: {corte_txt} ({ajustes.TZ_OBRA}) · alcance: {args.alcance}")
    print("=" * 74)

    filas, orden = [], 0
    for clave, estado in listas_del_alcance(args.alcance):
        lid = buscar_lista(listas, clave)
        if not lid:
            print(f"\n--- '{clave}': no existe en el tablero, se omite.")
            continue
        tarjetas = tr.tarjetas_de_lista(lid)
        from .trello import nombre_de_lista
        nombre_real = nombre_de_lista(listas, lid)
        print(f"\n--- {nombre_real}: {len(tarjetas)} tarjetas")
        for card in tarjetas:
            orden += 1
            fila = fila_de_tarjeta(card, nombre_real, estado, corte, orden)
            filas.append(fila)
            print(f"  {fila['SECTOR / ZONA']:7} {fila['CHECKS PENDIENTES']:>3}/"
                  f"{fila['TOTAL CHECKS']:<3} pend · {fila['ANTIGUEDAD (dias)']}d · "
                  f"{fila['ACTIVIDAD'][:44]}")

    cabecera = columnas()
    total_pend = sum(f["CHECKS PENDIENTES"] for f in filas)
    total_checks = sum(f["TOTAL CHECKS"] for f in filas)
    avance = (1 - total_pend / total_checks) * 100 if total_checks else 0

    print("\n" + "=" * 74)
    print(f" {len(filas)} tarjetas · {total_pend} checks pendientes de "
          f"{total_checks} ({avance:.0f}% avanzado)")

    if filas:
        print("\n Pendientes por responsable:")
        for codigo in ajustes.CODIGOS_RESPONSABLE:
            n = sum(f[codigo] for f in filas)
            if n:
                nombre = ajustes.RESPONSABLES[codigo].get("nombre", codigo)
                print(f"   {codigo:6} {nombre:14} {n:4}")

    if args.dry_run:
        print("\n (DRY-RUN: no se escribio ningun archivo.)")
    else:
        escribir_csv(ajustes.ARCHIVO_ULTIMO, filas, cabecera)
        previas = acumular_historico(ajustes.ARCHIVO_HISTORICO, filas, cabecera, corte_txt)
        print(f"\n Escrito: {ajustes.ARCHIVO_ULTIMO.name} ({len(filas)} filas)")
        print(f" Historico: {ajustes.ARCHIVO_HISTORICO.name} "
              f"({previas + len(filas)} filas en total)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

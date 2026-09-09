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
en Trello, y cada corte REEMPLAZA al anterior.

No se guarda la foto de cada corte. Del pasado lo que importa es el avance y
el cumplimiento, y eso lo lleva el cierre en reportes/culminadas.csv.

ALCANCE (--alcance)
  dia   Las listas del dia            (lo programado y lo que se adelanto)
  todo  Ademas, las de "por cerrar"   (lo que quedo abierto y se reprograma)

SALIDA
  reportes/ultimo.csv   el corte de ahora (el que lee tu dashboard)

USO
---
    python -m trello_auto.reporte
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

ALCANCES = ("dia", "todo")


def columnas() -> list:
    """Cabecera del CSV. Reproduce la hoja DATOS del dashboard."""
    return (["CORTE", "SECTOR / ZONA", "ACTIVIDAD", "FAMILIA", "VENCE"]
            + list(ajustes.CODIGOS_RESPONSABLE)
            + ["OTROS", "CHECKS PENDIENTES", "TOTAL CHECKS", "ANTIGUEDAD (dias)",
               "MARCADA", "CLAVE ORDEN", "LISTA TRELLO", "DIA DEL CORTE",
               "ESTADO", "LINK TRELLO"])


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
        # La marca de "cumplida" de Trello. Importa porque, con el criterio
        # por defecto, cierra la tarjeta aunque el checklist no este completo.
        "MARCADA": "si" if card.get("dueComplete") else "",
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
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        if lista and all(lista != c for c, _ in objetivo):
            objetivo.append((lista, "EN JUEGO"))
    if alcance == "todo":
        # Las listas de por cerrar, sean una o varias: ahi queda lo que no
        # cerro al fin de jornada, esperando a terminarse o reprogramarse.
        for lista in ajustes.listas_de_cierre():
            if all(lista != c for c, _ in objetivo):
                objetivo.append((lista, "POR CERRAR"))
    return objetivo


def escribir_csv(ruta, filas: list, cabecera: list):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cabecera, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Genera el corte de control y lo deja en CSV para el dashboard.")
    ap.add_argument("--alcance", default="todo", choices=list(ALCANCES),
                    help="Que listas entran en el corte (por defecto: todo).")
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
        print(f"\n Escrito: {ajustes.ARCHIVO_ULTIMO.name} ({len(filas)} filas)")

        # El dashboard web, que es lo que publica GitHub Pages
        from .tablero import generar
        print(f" Dashboard: {generar(filas, corte, args.alcance)}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

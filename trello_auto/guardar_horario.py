#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 GUARDAR HORARIO - escribe horario.json validando lo que se pidio.
============================================================================

Lo usa el workflow "3. Cambiar horario": toma lo que escribiste en el
formulario del boton "Run workflow" (llega como variables de entorno), valida
que las horas tengan sentido y actualiza `horario.json` en la raiz del repo.

Los campos vacios NO se tocan: se conserva lo que ya estaba.

Tambien sirve desde tu PC:

    HORA_CREAR=07:00 python -m trello_auto.guardar_horario
    python -m trello_auto.guardar_horario --hora-crear 07:00 --hora-fin 18:00
    python -m trello_auto.guardar_horario --ver
============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import horario
from . import settings as config

# Campo -> como se valida
CAMPOS_HORA = ("HORA_CREAR", "HORA_CIERRE", "HORA_INICIO", "HORA_FIN")
CAMPOS_OTROS = ("DIAS_HABILES", "TZ_OBRA")
CAMPOS = CAMPOS_HORA + CAMPOS_OTROS


def normalizar_hora(texto: str) -> str:
    """Valida y deja la hora en formato HH:MM ('7:5' -> '07:05')."""
    h, m = horario.parse_hhmm(texto)
    return f"{h:02d}:{m:02d}"


def validar_tz(nombre: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(nombre)
    except Exception as e:
        raise ValueError(
            f"Zona horaria desconocida: {nombre!r}. Usa un nombre valido, "
            f"por ejemplo 'America/Lima'."
        ) from e
    return nombre


def leer_actual() -> dict:
    try:
        datos = json.loads(config.ARCHIVO_HORARIO.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def recopilar_cambios(args) -> dict:
    """Junta lo pedido por linea de comandos y por variables de entorno."""
    pedido = {}
    for campo in CAMPOS:
        por_cli = getattr(args, campo.lower(), None)
        valor = por_cli if por_cli not in (None, "") else os.environ.get(campo, "")
        valor = (valor or "").strip()
        if valor:
            pedido[campo] = valor

    cambios = {}
    for campo, valor in pedido.items():
        if campo in CAMPOS_HORA:
            cambios[campo] = normalizar_hora(valor)
        elif campo == "DIAS_HABILES":
            horario.parse_dias(valor)          # valida
            cambios[campo] = valor
        elif campo == "TZ_OBRA":
            cambios[campo] = validar_tz(valor)
    return cambios


def main() -> int:
    ap = argparse.ArgumentParser(description="Actualiza horario.json (horas de la automatizacion).")
    for campo in CAMPOS:
        ap.add_argument(f"--{campo.lower().replace('_', '-')}", dest=campo.lower(),
                        default=None, help=f"Nuevo valor de {campo}.")
    ap.add_argument("--ver", action="store_true", help="Solo muestra el horario vigente.")
    args = ap.parse_args()

    actual = leer_actual()

    if args.ver:
        print(json.dumps(actual, indent=2, ensure_ascii=False))
        print("\nEfectivo ahora mismo:", config.resumen_horario())
        return 0

    try:
        cambios = recopilar_cambios(args)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not cambios:
        print("No se pidio ningun cambio (todos los campos venian vacios).")
        resumen = "sin cambios"
    else:
        nuevo = dict(actual)
        nuevo.update(cambios)
        # Orden estable para que el diff del commit se lea facil.
        ordenado = {c: nuevo[c] for c in CAMPOS if c in nuevo}
        ordenado.update({k: v for k, v in nuevo.items() if k not in ordenado})
        config.ARCHIVO_HORARIO.write_text(
            json.dumps(ordenado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        resumen = ", ".join(f"{k}={v}" for k, v in cambios.items())
        print("Horario actualizado:")
        for k, v in cambios.items():
            anterior = actual.get(k, "(por defecto)")
            print(f"  {k}: {anterior}  ->  {v}")
        print(f"\nArchivo: {config.ARCHIVO_HORARIO}")

    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"resumen={resumen}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

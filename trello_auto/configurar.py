#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 CONFIGURAR — cambia configuracion.json validando lo que se pide.
============================================================================

Lo usa el workflow "Configurar" de GitHub: tomas el boton "Run workflow",
escribes lo que quieras cambiar, y este programa valida, guarda y hace el
commit. NUNCA hay que entrar al codigo.

Los campos que dejes vacios NO se tocan.

QUE SE PUEDE CAMBIAR
--------------------
  Horas de la jornada   --jornada-inicio 07:00   --jornada-fin 18:30
    (se escriben DENTRO de cada tarjeta de Trello)

  Horas de los robots   --hora-preparar 18:00    --hora-cierre 19:00
                        --hora-distribuir 05:00  --hora-reporte 15:00
                        --hora-archivar 21:00
    (despiertan a cada automatizacion; no salen en ninguna tarjeta)

  Dias habiles          --dias 1-5
  Zona horaria          --tz America/Lima
  Forma del Excel       --hoja 01_MAESTRO  --fila-fechas 6
                        --columna-actividad C  --primera-fila-datos 7
  Criterio del cierre   --criterio checklist

Tambien sirve desde tu PC:
    python -m trello_auto.configurar --ver
    python -m trello_auto.configurar --hora-cierre 19:00 --jornada-fin 18:30
============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import ajustes, horario

# Cada opcion: (argumento, variable de entorno, ruta dentro del JSON, tipo)
CAMPOS = [
    ("jornada_inicio", "JORNADA_INICIO", "jornada.inicio", "hora"),
    ("jornada_fin", "JORNADA_FIN", "jornada.fin", "hora"),
    ("hora_preparar", "HORA_PREPARAR", "relojes.preparar.hora", "hora"),
    ("hora_distribuir", "HORA_DISTRIBUIR", "relojes.distribuir.hora", "hora"),
    ("hora_cierre", "HORA_CIERRE", "relojes.cierre.hora", "hora"),
    ("hora_reporte", "HORA_REPORTE", "relojes.reporte.hora", "hora"),
    ("hora_archivar", "HORA_ARCHIVAR", "relojes.archivar.hora", "hora"),
    ("dias", "DIAS_HABILES", "relojes.*.dias", "dias"),
    ("tz", "TZ_OBRA", "obra.zona_horaria", "tz"),
    ("tablero", "BOARD_ID", "obra.tablero", "texto"),
    ("hoja", "HOJA", "cronograma.hoja", "texto"),
    ("fila_fechas", "FILA_FECHAS", "cronograma.fila_fechas", "entero"),
    ("primera_fila_datos", "PRIMERA_FILA_DATOS", "cronograma.primera_fila_datos", "entero"),
    ("columna_actividad", "COLUMNA_ACTIVIDAD", "cronograma.columna_actividad", "columna"),
    ("criterio", "CRITERIO_CIERRE", "cierre.criterio", "criterio"),
    ("ventana", "VENTANA_MIN", "ventana_minutos", "entero"),
]


def validar(valor: str, tipo: str):
    valor = str(valor).strip()
    if tipo == "hora":
        h, m = horario.parse_hhmm(valor)
        return f"{h:02d}:{m:02d}"
    if tipo == "dias":
        horario.parse_dias(valor)
        return valor
    if tipo == "tz":
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(valor)
        except Exception as e:
            raise ValueError(
                f"Zona horaria desconocida: {valor!r}. Usa por ejemplo 'America/Lima'."
            ) from e
        return valor
    if tipo == "entero":
        n = int(valor)
        if n <= 0:
            raise ValueError(f"Debe ser un numero mayor que cero: {valor!r}")
        return n
    if tipo == "columna":
        v = valor.upper()
        if not v.isalpha():
            raise ValueError(f"Columna invalida: {valor!r}. Usa una letra como 'C'.")
        return v
    if tipo == "criterio":
        v = valor.lower()
        if v not in ("checklist", "auto", "marcada"):
            raise ValueError(
                f"Criterio invalido: {valor!r}. Usa checklist, auto o marcada.")
        return v
    return valor


def poner(cfg: dict, ruta: str, valor):
    """Escribe un valor en el JSON siguiendo la notacion de puntos."""
    if ".*." in ruta:            # relojes.*.dias -> a todos los relojes
        antes, despues = ruta.split(".*.")
        for tarea in (cfg.get(antes) or {}):
            if isinstance(cfg[antes][tarea], dict):
                cfg[antes][tarea][despues] = valor
        return
    partes = ruta.split(".")
    actual = cfg
    for p in partes[:-1]:
        actual = actual.setdefault(p, {})
    actual[partes[-1]] = valor


def leer(cfg: dict, ruta: str):
    if ".*." in ruta:
        antes, despues = ruta.split(".*.")
        valores = {v.get(despues) for k, v in (cfg.get(antes) or {}).items()
                   if isinstance(v, dict)}
        return ", ".join(sorted(str(v) for v in valores if v))
    actual = cfg
    for p in ruta.split("."):
        if not isinstance(actual, dict) or p not in actual:
            return None
        actual = actual[p]
    return actual


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cambia la configuracion de la obra sin tocar el codigo.")
    for arg, _env, _ruta, _tipo in CAMPOS:
        ap.add_argument(f"--{arg.replace('_', '-')}", dest=arg, default=None)
    ap.add_argument("--ver", action="store_true",
                    help="Solo muestra la configuracion vigente.")
    args = ap.parse_args()

    cfg = json.loads(ajustes.ARCHIVO_CONFIG.read_text(encoding="utf-8"))

    if args.ver:
        print(ajustes.resumen())
        return 0

    cambios, errores = {}, []
    for arg, env, ruta, tipo in CAMPOS:
        crudo = getattr(args, arg, None)
        if crudo in (None, ""):
            crudo = os.environ.get(env, "")
        crudo = str(crudo or "").strip()
        if not crudo:
            continue
        try:
            cambios[ruta] = (validar(crudo, tipo), leer(cfg, ruta))
        except ValueError as e:
            errores.append(f"  --{arg.replace('_', '-')}: {e}")

    if errores:
        print("ERROR: hay valores invalidos, no se guardo nada:\n" + "\n".join(errores),
              file=sys.stderr)
        return 1

    if not cambios:
        print("No se pidio ningun cambio (todos los campos venian vacios).")
        resumen_txt = "sin cambios"
    else:
        print("Configuracion actualizada:")
        for ruta, (nuevo, viejo) in cambios.items():
            poner(cfg, ruta, nuevo)
            print(f"  {ruta}: {viejo}  ->  {nuevo}")
        ajustes.ARCHIVO_CONFIG.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        resumen_txt = ", ".join(f"{r.split('.')[-1]}={n}" for r, (n, _) in cambios.items())
        print(f"\nArchivo: {ajustes.ARCHIVO_CONFIG}")

    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"resumen={resumen_txt}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 PORTERO HORARIO — decide si esta corrida programada es la que toca.
============================================================================

EL PROBLEMA
-----------
GitHub Actions solo acepta un `cron:` FIJO escrito dentro del archivo del
workflow. Si la hora estuviera ahi, cada cambio de horario obligaria a entrar
al codigo, editarlo y hacer commit.

LA SOLUCION
-----------
El workflow se despierta cada media hora dentro de una franja amplia, y este
portero solo deja pasar las citas que caen en la ventana que abre a la hora
configurada (`HORA_CREAR` / `HORA_CIERRE`); el resto del dia se apaga solo.

Esa hora vive en `horario.json` (o en una Variable del repositorio), y se
cambia desde el navegador con el workflow "Cambiar horario" -> Run workflow.
NUNCA hay que tocar el codigo.

Ademas la hora se evalua en la zona horaria de la obra (TZ_OBRA), asi que un
eventual cambio de horario de verano se ajusta solo.

USO
---
    python -m trello_auto.portero --tarea crear
    python -m trello_auto.portero --tarea cierre

Escribe `ejecutar=true|false` en $GITHUB_OUTPUT para que el workflow decida.
============================================================================
"""

from __future__ import annotations

import argparse
import os
import sys

from . import horario
from . import settings as config


def main() -> int:
    ap = argparse.ArgumentParser(description="Decide si toca ejecutar la tarea ahora.")
    ap.add_argument("--tarea", required=True, choices=["crear", "cierre"],
                    help="Que tarea se esta evaluando.")
    ap.add_argument("--hora", default=None,
                    help="Hora objetivo HH:MM (por defecto, la configurada).")
    ap.add_argument("--dias", default=None,
                    help="Dias habiles, ej. '1-5' (por defecto, los configurados).")
    ap.add_argument("--ventana", type=int, default=None,
                    help="Tolerancia en minutos (por defecto, VENTANA_MIN).")
    args = ap.parse_args()

    hora = args.hora or (config.HORA_CREAR if args.tarea == "crear" else config.HORA_CIERRE)
    dias = args.dias or config.DIAS_HABILES

    ejecutar, motivo = horario.toca_ejecutar(hora, dias, ventana_min=args.ventana)

    ahora = horario.ahora_local()
    print(f"Ahora: {ahora:%Y-%m-%d %H:%M} ({config.TZ_OBRA})")
    print(f"Tarea '{args.tarea}' programada a las {hora}, dias {dias}.")
    print(("SI toca ejecutar: " if ejecutar else "NO toca ejecutar: ") + motivo)

    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"ejecutar={'true' if ejecutar else 'false'}\n")
            f.write(f"hora={hora}\n")
            f.write(f"motivo={motivo}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

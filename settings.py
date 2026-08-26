# -*- coding: utf-8 -*-
"""
Resuelve la configuración desde:
  1) Variables de entorno (GitHub Secrets, Google Cloud, etc.)  ← prioridad
  2) El archivo config.py local (solo para pruebas en tu PC)    ← respaldo

Así el MISMO código funciona tanto en tu computadora como en GitHub Actions
sin cambiar nada. Las credenciales nunca están escritas en el código.
"""

import os

# Intenta cargar config.py (existe solo en tu PC; en GitHub no está)
try:
    import config as _local
except ImportError:
    _local = None


def _get(nombre, defecto=None):
    # Primero el entorno (GitHub Secrets); si no, config.py; si no, el defecto.
    if nombre in os.environ:
        return os.environ[nombre]
    if _local and hasattr(_local, nombre):
        return getattr(_local, nombre)
    return defecto


TRELLO_KEY   = _get("TRELLO_KEY")
TRELLO_TOKEN = _get("TRELLO_TOKEN")
BOARD_ID     = _get("BOARD_ID", "gzoZo6ip")
RUTA_EXCEL   = _get("RUTA_EXCEL", "5__LPS_PLANNING_REV_9.xlsx")

LISTA_POR_TIPO = {
    "ACERO":     "🟦 ACERO — DÍA",
    "ENCOFRADO": "🟧 ENCOFRADO — DÍA",
    "CONCRETO":  "🟩 CONCRETO Y MORTERO — DÍA",
    "VARIOS":    "⬛ VARIOS — DÍA (trazo · excavación · relleno)",
}

# Validación temprana con mensaje claro
if not TRELLO_KEY or not TRELLO_TOKEN:
    raise SystemExit(
        "ERROR: faltan credenciales de Trello.\n"
        "  • En tu PC: crea config.py (copia de config.example.py) con tus datos.\n"
        "  • En GitHub Actions: crea los Secrets TRELLO_KEY y TRELLO_TOKEN."
    )

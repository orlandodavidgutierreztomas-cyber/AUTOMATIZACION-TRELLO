# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN — copia este archivo a "config.py" y complétalo.
NUNCA subas config.py a un repositorio público (está en .gitignore).
"""

import os

# ---------------------------------------------------------------------------
# CREDENCIALES DE TRELLO
# Se obtienen gratis en: https://trello.com/power-ups/admin  (API Key + Token)
# Para producción, es más seguro leerlas de variables de entorno (os.environ).
# ---------------------------------------------------------------------------
TRELLO_KEY   = os.environ.get("TRELLO_KEY",   "PEGA_AQUI_TU_API_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN", "PEGA_AQUI_TU_TOKEN")

# ---------------------------------------------------------------------------
# TABLERO DESTINO
# El ID corto del tablero (lo que va después de /b/ en la URL).
# Tablero "AULAS — CONTROL DIARIO (MEJORADO)":
# ---------------------------------------------------------------------------
BOARD_ID = "gzoZo6ip"

# ---------------------------------------------------------------------------
# RUTA DEL EXCEL DE PLANEAMIENTO
# ---------------------------------------------------------------------------
RUTA_EXCEL = os.environ.get("RUTA_EXCEL", "5__LPS_PLANNING_REV_9.xlsx")

# ---------------------------------------------------------------------------
# MAPEO: tipo de trabajo  ->  nombre EXACTO de la lista en el tablero.
# Si renombras una lista en Trello, actualiza aquí el nombre.
# ---------------------------------------------------------------------------
LISTA_POR_TIPO = {
    "ACERO":     "🟦 ACERO — DÍA",
    "ENCOFRADO": "🟧 ENCOFRADO — DÍA",
    "CONCRETO":  "🟩 CONCRETO Y MORTERO — DÍA",
    "VARIOS":    "⬛ VARIOS — DÍA (trazo · excavación · relleno)",
}

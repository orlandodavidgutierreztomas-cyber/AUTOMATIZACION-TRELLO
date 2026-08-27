# -*- coding: utf-8 -*-
"""
CONFIGURACION LOCAL - copia este archivo a "config.py" y complétalo.

Solo hace falta en TU PC, para pruebas. En GitHub Actions no se usa: allá las
credenciales viajan como Secrets. NUNCA subas config.py (lo bloquea .gitignore).

Las HORAS viven en horario.json y se cambian desde el botón "Run workflow"
del workflow "3. Cambiar horario". Aquí solo van tus credenciales.
"""

# ---------------------------------------------------------------------------
# CREDENCIALES DE TRELLO  (gratis: https://trello.com/power-ups/admin)
#   1) Crea un Power-Up (o usa uno) y copia tu API Key.
#   2) Genera un Token con el enlace "Token" de esa misma página.
# ---------------------------------------------------------------------------
TRELLO_KEY = "PEGA_AQUI_TU_API_KEY"
TRELLO_TOKEN = "PEGA_AQUI_TU_TOKEN"

# ---------------------------------------------------------------------------
# TABLERO DESTINO — el ID corto, lo que va después de /b/ en la URL.
# "AULAS — CONTROL DIARIO":  https://trello.com/b/gzoZo6ip
# ---------------------------------------------------------------------------
BOARD_ID = "gzoZo6ip"

# ---------------------------------------------------------------------------
# OPCIONAL — solo si quieres sobrescribir algo en tu PC.
# Si lo dejas comentado, manda horario.json / el valor por defecto.
# ---------------------------------------------------------------------------
# RUTA_EXCEL = r"C:\ruta\a\5__LPS_PLANNING_REV_9.xlsx"
# HORA_INICIO = "07:00"
# HORA_FIN = "17:00"
# CRITERIO_CIERRE = "auto"      # auto | checklist | marcada

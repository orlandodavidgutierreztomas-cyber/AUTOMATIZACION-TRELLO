# -*- coding: utf-8 -*-
"""
CONFIGURACION LOCAL — copia este archivo a "config.py" y complétalo.

Solo hace falta en TU PC, para pruebas. En GitHub Actions no se usa: allá las
credenciales viajan como Secrets. NUNCA subas config.py (lo bloquea .gitignore).

Todo lo demás —horas, listas, familias, forma del Excel— vive en
configuracion.json y se edita desde Actions → "Configurar".
"""

# ---------------------------------------------------------------------------
# CREDENCIALES DE TRELLO  (gratis: https://trello.com/power-ups/admin)
#   1) Crea un Power-Up (o usa uno) y copia tu API Key.
#   2) Genera un Token con el enlace "Token" de esa misma página.
# ---------------------------------------------------------------------------
TRELLO_KEY = "PEGA_AQUI_TU_API_KEY"
TRELLO_TOKEN = "PEGA_AQUI_TU_TOKEN"

# ---------------------------------------------------------------------------
# OPCIONAL — solo para sobrescribir algo en tu PC.
# Si lo dejas comentado, manda configuracion.json.
# ---------------------------------------------------------------------------
# BOARD_ID = "gzoZo6ip"
# RUTA_EXCEL = "data/mi_cronograma.xlsx"

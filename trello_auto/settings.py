# -*- coding: utf-8 -*-
"""
============================================================================
 CONFIGURACIÓN EFECTIVA
============================================================================

Resuelve cada valor por ORDEN DE PRIORIDAD:

  1) Variable de entorno            ← GitHub Secrets / Variables / dispatch
  2) horario.json (raíz del repo)   ← lo escribe el workflow "Cambiar horario"
  3) config.py local                ← solo para pruebas en tu PC
  4) Valor por defecto de este archivo

Gracias a esto, el MISMO código corre en tu computadora y en GitHub Actions
sin cambiar una sola línea, y las HORAS se pueden cambiar desde el navegador
(botón "Run workflow") sin tocar el código.

Las credenciales NUNCA se escriben aquí.
============================================================================
"""

import json
import os
from pathlib import Path

# Raíz del repositorio (este archivo vive en trello_auto/)
RAIZ = Path(__file__).resolve().parent.parent

# Archivo de horario editable desde GitHub (workflow "Cambiar horario").
ARCHIVO_HORARIO = RAIZ / "horario.json"

# config.py existe solo en tu PC; en GitHub no está (lo bloquea .gitignore).
try:
    import config as _local
except ImportError:
    _local = None


def _cargar_horario() -> dict:
    try:
        datos = json.loads(ARCHIVO_HORARIO.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


_HORARIO = _cargar_horario()


def _get(nombre, defecto=None):
    """Devuelve el valor de `nombre` según el orden de prioridad del módulo."""
    valor = os.environ.get(nombre)
    if valor not in (None, ""):
        return valor
    if nombre in _HORARIO and str(_HORARIO[nombre]).strip():
        return str(_HORARIO[nombre]).strip()
    if _local is not None and hasattr(_local, nombre):
        return getattr(_local, nombre)
    return defecto


# ---------------------------------------------------------------------------
# CREDENCIALES Y DESTINO
# ---------------------------------------------------------------------------
TRELLO_KEY   = _get("TRELLO_KEY")
TRELLO_TOKEN = _get("TRELLO_TOKEN")
BOARD_ID     = _get("BOARD_ID", "gzoZo6ip")          # tablero "AULAS — CONTROL DIARIO"
RUTA_EXCEL   = _get("RUTA_EXCEL", str(RAIZ / "data" / "5__LPS_PLANNING_REV_9.xlsx"))
RUTA_PLAN_JSON = _get("RUTA_PLAN_JSON", str(RAIZ / "data" / "plan_obra.json"))

# ---------------------------------------------------------------------------
# HORARIO  (todo esto se cambia SIN tocar el código: ver README → "Cambiar la hora")
# ---------------------------------------------------------------------------
TZ_OBRA      = _get("TZ_OBRA", "America/Lima")  # zona horaria de la obra

HORA_INICIO  = _get("HORA_INICIO", "07:00")     # hora de INICIO de cada tarjeta
HORA_FIN     = _get("HORA_FIN",    "17:00")     # hora de FIN / vencimiento

HORA_CREAR   = _get("HORA_CREAR",  "06:30")     # a qué hora se crean las tarjetas
HORA_CIERRE  = _get("HORA_CIERRE", "20:00")     # a qué hora corre el cierre del día

DIAS_HABILES = _get("DIAS_HABILES", "1-5")      # 1=lunes … 7=domingo ("1-5", "1,3,5")

# Tolerancia del "portero" horario, en minutos: la corrida sigue siendo válida
# dentro de esta ventana después de la hora configurada.
#
# Es ancha a propósito. GitHub retrasa —y a veces descarta— las tareas
# programadas cuando tiene carga, así que una ventana corta puede dejarte un día
# sin tarjetas. Y no hay riesgo en que pasen varias corridas: crear tarjetas no
# duplica ninguna, y el cierre no encuentra nada que mover la segunda vez.
VENTANA_MIN  = int(_get("VENTANA_MIN", "90"))

# ---------------------------------------------------------------------------
# LISTAS DEL TABLERO — se buscan por PALABRA CLAVE
# El script encuentra la lista real aunque tenga emojis, acentos o espacios
# de más (p. ej. "T. DEL DÍA ACERO- 🟦🟦🟦🟦🟦" se encuentra con "T. DEL DIA ACERO").
# ---------------------------------------------------------------------------
LISTA_DIA_POR_TIPO = {
    "ACERO":     _get("LISTA_DIA_ACERO",     "T. DEL DIA ACERO"),
    "ENCOFRADO": _get("LISTA_DIA_ENCOFRADO", "T. DEL DIA ENCOFRADO"),
    "CONCRETO":  _get("LISTA_DIA_CONCRETO",  "T. DEL DIA CONCRETO"),
    "VARIOS":    _get("LISTA_DIA_VARIOS",    "T. DEL DIA VARIOS"),
}

LISTA_EN_EJECUCION  = _get("LISTA_EN_EJECUCION",  "EN EJECUCION")
LISTA_CULMINADO     = _get("LISTA_CULMINADO",     "CULMINADO")
LISTA_NO_CUMPLIDAS  = _get("LISTA_NO_CUMPLIDAS",  "NO CUMPLIDAS")
CLAVE_PLANTILLAS    = _get("CLAVE_PLANTILLAS",    "PLANTILL")  # listas "PLANTILLA_…"

TIPOS = ("ACERO", "ENCOFRADO", "CONCRETO", "VARIOS")

# ---------------------------------------------------------------------------
# CRITERIO DE CIERRE — cuándo se considera TERMINADA una tarjeta:
#   "checklist" → solo si TODOS los ítems de sus checklists están marcados
#                 (POR DEFECTO: manda el control de calidad, no basta con
#                  tildar la tarjeta; sin checklist marcado -> NO CUMPLIDA)
#   "auto"      → marcada como completa  O  checklist 100% marcado
#   "marcada"   → solo si la tarjeta está marcada como completa en Trello
# ---------------------------------------------------------------------------
CRITERIO_CIERRE = _get("CRITERIO_CIERRE", "checklist").lower()

# ---------------------------------------------------------------------------
# QUÉ SE COPIA DE LA TARJETA PLANTILLA
# La API de Trello obliga a decir qué partes traer al duplicar una tarjeta:
# lo que no se pide, no se copia. Valores válidos, separados por coma:
#   checklists · labels · members · attachments · comments · stickers
#   customFields  (o "all" para traer absolutamente todo)
#
# OJO: no incluyas "due" ni "start" — las fechas las pone el script con el
# horario del día (HORA_INICIO / HORA_FIN), no las de la plantilla.
#
# La descripción se copia siempre, aparte (no es parte de esta lista).
# ---------------------------------------------------------------------------
COPIAR_DE_PLANTILLA = _get("COPIAR_DE_PLANTILLA", "checklists,labels")

# ---------------------------------------------------------------------------
# CHECKLIST DE RESPALDO, por tipo de trabajo.
# Solo se usa cuando la actividad TODAVÍA NO tiene tarjeta PLANTILLA en el
# tablero. Si la plantilla existe, se copian sus checklists reales tal cual.
#
# ⚠ PROVISIONAL: ítems genéricos para no dejar tarjetas sin control de calidad.
# Reemplázalos por tu plantilla real cuando la tengas.
# ---------------------------------------------------------------------------
CHECKLIST_POR_TIPO = {
    "ACERO": [
        "Diámetro y cantidad de varilla según plano",
        "Longitud de anclaje y empalmes correctos",
        "Recubrimiento libre verificado",
        "Amarre firme, sin varillas sueltas",
        "Limpieza (sin óxido suelto, aceite o tierra)",
    ],
    "ENCOFRADO": [
        "Alineación y verticalidad verificadas",
        "Dimensiones según plano",
        "Apuntalamiento y arriostre correctos",
        "Hermeticidad (sin fugas de lechada)",
        "Desmoldante aplicado y superficie limpia",
    ],
    "CONCRETO": [
        "Diseño de mezcla verificado",
        "Liberación de acero y encofrado firmada",
        "Vibrado correcto, sin cangrejeras",
        "Curado programado",
    ],
    "VARIOS": [
        "Niveles y ejes verificados según plano",
        "Zona limpia y señalizada",
    ],
}


def exigir_credenciales():
    """Falla temprano y con un mensaje claro si faltan las credenciales.

    Se llama desde los scripts (no al importar) para que los tests y el
    'portero' horario puedan usar este módulo sin necesitar credenciales.
    """
    if not TRELLO_KEY or not TRELLO_TOKEN:
        raise SystemExit(
            "ERROR: faltan credenciales de Trello.\n"
            "  • En tu PC: copia config.example.py a config.py y complétalo.\n"
            "  • En GitHub Actions: crea los Secrets TRELLO_KEY y TRELLO_TOKEN."
        )


def resumen_horario() -> str:
    return (f"TZ={TZ_OBRA} · jornada {HORA_INICIO}-{HORA_FIN} · "
            f"crear {HORA_CREAR} · cierre {HORA_CIERRE} · días {DIAS_HABILES}")

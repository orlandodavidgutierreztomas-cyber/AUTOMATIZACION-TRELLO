# -*- coding: utf-8 -*-
"""
============================================================================
 AJUSTES — la configuración efectiva de la obra.
============================================================================

Un solo lugar del que todo el resto del programa lee. Junta tres fuentes,
por ORDEN DE PRIORIDAD:

  1) Variables de entorno       ← GitHub Secrets / Variables / Run workflow
  2) configuracion.json         ← lo propio de esta obra (editable con botón)
  3) config.py local            ← solo para pruebas en tu PC

Las credenciales NUNCA se escriben en un archivo del repositorio: viajan
como Secrets y llegan por variable de entorno.

El código Python de este proyecto es GENÉRICO: nada de esta obra en concreto
está escrito en él. Para llevarlo a otra obra basta con editar
`configuracion.json` y `mapeo.json`.
============================================================================
"""

from __future__ import annotations

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CONFIG = RAIZ / "configuracion.json"
ARCHIVO_MAPEO = RAIZ / "mapeo.json"

# config.py existe solo en tu PC; en GitHub no está (lo bloquea .gitignore).
try:
    import config as _local
except ImportError:
    _local = None


def _leer_json(ruta: Path) -> dict:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _sin_ayuda(d):
    """Quita las claves '_ayuda', que son comentarios para quien edita el JSON."""
    if isinstance(d, dict):
        return {k: _sin_ayuda(v) for k, v in d.items() if k != "_ayuda"}
    return d


CONFIG = _sin_ayuda(_leer_json(ARCHIVO_CONFIG))
MAPEO = _sin_ayuda(_leer_json(ARCHIVO_MAPEO))


def _env(nombre, defecto=None):
    """Variable de entorno, o config.py, o el valor por defecto."""
    valor = os.environ.get(nombre)
    if valor not in (None, ""):
        return valor
    if _local is not None and hasattr(_local, nombre):
        return getattr(_local, nombre)
    return defecto


def dato(ruta: str, defecto=None):
    """Lee un valor del JSON con notación de puntos: dato('jornada.inicio')."""
    actual = CONFIG
    for parte in ruta.split("."):
        if not isinstance(actual, dict) or parte not in actual:
            return defecto
        actual = actual[parte]
    return actual if actual not in (None, "") else defecto


# ---------------------------------------------------------------------------
# CREDENCIALES  (solo por entorno / config.py — nunca en el repositorio)
# ---------------------------------------------------------------------------
TRELLO_KEY = _env("TRELLO_KEY")
TRELLO_TOKEN = _env("TRELLO_TOKEN")

# ---------------------------------------------------------------------------
# OBRA
# ---------------------------------------------------------------------------
NOMBRE_OBRA = _env("NOMBRE_OBRA", dato("obra.nombre", "OBRA"))
BOARD_ID = _env("BOARD_ID", dato("obra.tablero"))
TZ_OBRA = _env("TZ_OBRA", dato("obra.zona_horaria", "America/Lima"))

# ---------------------------------------------------------------------------
# CRONOGRAMA  (la forma de TU Excel)
# ---------------------------------------------------------------------------
RUTA_EXCEL = _env("RUTA_EXCEL", str(RAIZ / dato("cronograma.archivo", "data/plan.xlsx")))
RUTA_PLAN_JSON = _env("RUTA_PLAN_JSON",
                      str(RAIZ / dato("cronograma.respaldo_json", "data/plan_obra.json")))
HOJA = _env("HOJA", dato("cronograma.hoja", "01_MAESTRO"))
FILA_FECHAS = int(_env("FILA_FECHAS", dato("cronograma.fila_fechas", 6)))
PRIMERA_FILA_DATOS = int(_env("PRIMERA_FILA_DATOS", dato("cronograma.primera_fila_datos", 7)))
COLUMNA_ACTIVIDAD = str(_env("COLUMNA_ACTIVIDAD", dato("cronograma.columna_actividad", "C")))
PATRON_SECTOR = _env("PATRON_SECTOR", dato("cronograma.patron_sector", r"^[12][A-Z]{2}\d+$"))

# ---------------------------------------------------------------------------
# JORNADA — se escribe DENTRO de cada tarjeta
# ---------------------------------------------------------------------------
HORA_INICIO = _env("HORA_INICIO", dato("jornada.inicio", "07:00"))
HORA_FIN = _env("HORA_FIN", dato("jornada.fin", "17:00"))

# ---------------------------------------------------------------------------
# RELOJES — despiertan a cada robot
# ---------------------------------------------------------------------------
TAREAS = ("preparar", "distribuir", "cierre", "reporte", "archivar")


def hora_de(tarea: str) -> str:
    """Hora configurada para un robot. La variable de entorno manda."""
    return _env(f"HORA_{tarea.upper()}", dato(f"relojes.{tarea}.hora", "06:00"))


def dias_de(tarea: str) -> str:
    """Días hábiles de un robot ('1-5', '1,3,5'). La variable de entorno manda."""
    return _env(f"DIAS_{tarea.upper()}",
                _env("DIAS_HABILES", dato(f"relojes.{tarea}.dias", "1-5")))


VENTANA_MIN = int(_env("VENTANA_MIN", dato("ventana_minutos", 90)))

# ---------------------------------------------------------------------------
# LISTAS DEL TABLERO — se buscan por palabra clave
# ---------------------------------------------------------------------------
LISTA_ESPERA = _env("LISTA_ESPERA", dato("listas.espera", "ESPERA"))
LISTA_POR_CERRAR = _env("LISTA_POR_CERRAR", dato("listas.por_cerrar", ""))
LISTA_CULMINADO = _env("LISTA_CULMINADO", dato("listas.culminado", "CULMINADO"))
LISTA_NO_CUMPLIDAS = _env("LISTA_NO_CUMPLIDAS", dato("listas.no_cumplidas", "NO CUMPLIDAS"))

# ---------------------------------------------------------------------------
# FAMILIAS DE TRABAJO — agrupan actividades y deciden la lista del día
# ---------------------------------------------------------------------------
FAMILIAS = dato("familias", {}) or {}


def familia_por_defecto() -> str:
    """La familia de descarte: recoge lo que no case con ninguna palabra clave."""
    for nombre, f in FAMILIAS.items():
        if f.get("por_defecto"):
            return nombre
    return next(iter(FAMILIAS), "Varios")


def lista_de_familia(familia: str) -> str:
    f = FAMILIAS.get(familia) or FAMILIAS.get(familia_por_defecto(), {})
    return f.get("lista", "")


# ---------------------------------------------------------------------------
# RESPONSABLES — un checklist por responsable dentro de cada tarjeta
# ---------------------------------------------------------------------------
RESPONSABLES = dato("responsables", {}) or {}
CODIGOS_RESPONSABLE = [c for c in RESPONSABLES]

# ---------------------------------------------------------------------------
# PLANTILLAS Y CIERRE
# ---------------------------------------------------------------------------
MARCA_PLANTILLA = _env("MARCA_PLANTILLA", dato("plantillas.marca", "PLANTIL"))
COPIAR_DE_PLANTILLA = _env("COPIAR_DE_PLANTILLA", dato("plantillas.copiar", "checklists,labels"))
CRITERIO_CIERRE = str(_env("CRITERIO_CIERRE", dato("cierre.criterio", "checklist"))).lower()

# ---------------------------------------------------------------------------
# REPORTES
# ---------------------------------------------------------------------------
CARPETA_REPORTES = RAIZ / dato("reportes.carpeta", "reportes")
ARCHIVO_HISTORICO = RAIZ / dato("reportes.historico", "reportes/cortes.csv")
ARCHIVO_ULTIMO = RAIZ / dato("reportes.ultimo", "reportes/ultimo.csv")


# ---------------------------------------------------------------------------
# MAPEO actividad -> familia / lista  (mapeo.json, generado por "Sincronizar")
# ---------------------------------------------------------------------------
def destino_de_actividad(actividad_normalizada: str) -> dict:
    """Devuelve {'familia':..., 'lista':...} para una actividad, o {} si no está."""
    return (MAPEO.get("actividades") or {}).get(actividad_normalizada, {})


def exigir_credenciales():
    """Falla temprano y claro si faltan las credenciales de Trello."""
    if not TRELLO_KEY or not TRELLO_TOKEN:
        raise SystemExit(
            "ERROR: faltan credenciales de Trello.\n"
            "  - En tu PC: copia config.example.py a config.py y complétalo.\n"
            "  - En GitHub: crea los Secrets TRELLO_KEY y TRELLO_TOKEN."
        )
    if not BOARD_ID:
        raise SystemExit(
            "ERROR: falta el tablero. Ponlo en configuracion.json -> obra.tablero."
        )


def resumen() -> str:
    relojes = " · ".join(f"{t} {hora_de(t)}" for t in TAREAS)
    return (f"{NOMBRE_OBRA} · tablero {BOARD_ID} · {TZ_OBRA}\n"
            f"  jornada {HORA_INICIO}-{HORA_FIN}\n"
            f"  relojes: {relojes}\n"
            f"  familias: {', '.join(k for k in FAMILIAS)}\n"
            f"  responsables: {', '.join(CODIGOS_RESPONSABLE)}")

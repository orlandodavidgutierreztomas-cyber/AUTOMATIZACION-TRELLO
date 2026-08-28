# -*- coding: utf-8 -*-
"""
============================================================================
 HORARIO — zona horaria, horas de la jornada y "portero" de ejecucion.
============================================================================

Todo lo que tiene que ver con el reloj vive aqui:

  - La zona horaria de la obra (ajustes.TZ_OBRA). Si alguna vez hubiera
    cambio de horario, se ajusta solo: nunca se suma "-5" a mano.
  - La conversion "HH:MM hora local del dia X" -> ISO-8601 UTC, que es el
    formato que exige la API de Trello.
  - El portero (`toca_ejecutar`), que decide si una corrida programada de
    GitHub corresponde a la hora configurada. Gracias a el, la hora se
    cambia desde el navegador y NO desde el codigo.

HAY DOS CLASES DE HORA, y conviene no confundirlas:
  - JORNADA (inicio / fin): se ESCRIBE DENTRO de cada tarjeta de Trello.
  - RELOJES (preparar, distribuir, cierre, reporte, archivar): DESPIERTAN a
    cada robot. No aparecen en ninguna tarjeta.
============================================================================
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:                # respaldo muy improbable
    ZoneInfo = None

from . import ajustes


def zona() -> timezone:
    """Zona horaria de la obra. Si el sistema no la tiene, cae a UTC-5 fijo."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo(ajustes.TZ_OBRA)
        except Exception:
            pass
    return timezone(timedelta(hours=-5))


def ahora_local() -> datetime:
    """Fecha y hora actuales en la zona horaria de la obra."""
    return datetime.now(zona())


def hoy_local() -> date:
    return ahora_local().date()


def parse_hhmm(texto: str) -> tuple:
    """'7:5' o '07:05' -> (7, 5). Valida el rango; lanza ValueError si no vale."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*[:.]\s*(\d{1,2})\s*", str(texto))
    if not m:
        raise ValueError(f"Hora invalida: {texto!r}. Usa el formato HH:MM (ej. 06:30).")
    h, mi = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError(f"Hora fuera de rango: {texto!r}.")
    return h, mi


def local_a_iso_utc(dia: date, hhmm: str) -> str:
    """'HH:MM' hora local del dia dado -> ISO-8601 UTC, como lo pide Trello."""
    h, mi = parse_hhmm(hhmm)
    dt_local = datetime(dia.year, dia.month, dia.day, h, mi, tzinfo=zona())
    return dt_local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def utc_a_local(texto_iso: str) -> datetime:
    """ISO-8601 UTC de Trello -> datetime en la hora de la obra."""
    if not texto_iso:
        return None
    limpio = texto_iso.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(limpio).astimezone(zona())
    except ValueError:
        return None


def parse_dias(texto: str) -> set:
    """'1-5' o '1,3,5' o '1-5,7' -> {1,2,3,4,5}. 1=lunes ... 7=domingo."""
    dias = set()
    for parte in str(texto).split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = (int(x) for x in parte.split("-", 1))
            dias.update(range(min(a, b), max(a, b) + 1))
        else:
            dias.add(int(parte))
    validos = {d for d in dias if 1 <= d <= 7}
    if not validos:
        raise ValueError(f"Dias habiles invalidos: {texto!r}. Usa por ejemplo '1-5'.")
    return validos


def toca_ejecutar(hora_objetivo: str, dias: str, ahora: datetime = None,
                  ventana_min: int = None) -> tuple:
    """Esta corrida programada, ¿es la que corresponde?

    GitHub Actions solo acepta un cron FIJO escrito en el archivo del workflow.
    Por eso el workflow se despierta cada media hora y este portero deja pasar
    solo las citas que caen en la ventana que abre a la hora configurada. Asi
    la hora real se cambia desde el navegador, sin tocar el codigo.

    La ventana es ancha (ajustes.VENTANA_MIN) porque GitHub retrasa o descarta
    citas cuando tiene carga. Que pasen dos corridas no hace dano: todos los
    robots son idempotentes.

    Devuelve (True/False, motivo_legible).
    """
    ahora = ahora or ahora_local()
    ventana = ajustes.VENTANA_MIN if ventana_min is None else ventana_min

    dia_semana = ahora.isoweekday()
    habiles = parse_dias(dias)
    if dia_semana not in habiles:
        return False, (f"hoy es dia {dia_semana} y los dias configurados son "
                       f"{sorted(habiles)}")

    h, mi = parse_hhmm(hora_objetivo)
    objetivo = ahora.replace(hour=h, minute=mi, second=0, microsecond=0)
    diferencia = (ahora - objetivo).total_seconds() / 60.0

    if 0 <= diferencia < ventana:
        return True, (f"son las {ahora:%H:%M} ({ajustes.TZ_OBRA}) y la hora "
                      f"configurada es {hora_objetivo}")
    return False, (f"son las {ahora:%H:%M} ({ajustes.TZ_OBRA}); la corrida es a "
                   f"las {hora_objetivo} (ventana de {ventana} min)")


DIAS_ES = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


def fecha_larga(d: date) -> str:
    """'jueves 27/08/2026' (sin depender del idioma del sistema)."""
    return f"{DIAS_ES[d.weekday()]} {d:%d/%m/%Y}"

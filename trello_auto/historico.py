# -*- coding: utf-8 -*-
"""
============================================================================
 HISTORICO — la memoria de la obra: lo que permite ver la pelicula.
============================================================================

Un corte suelto es una FOTO: cuantos checks faltan ahora. El valor real del
Last Planner esta en la TENDENCIA: si el pendiente sube o baja, si el
cumplimiento mejora semana a semana, si el avance sigue el plan.

Para eso hay que guardar lo que pasa cada dia. Aqui viven los dos registros:

  reportes/culminadas.csv  Una fila por dia de cierre: cuantas tarjetas se
                       culminaron. De ahi sale el avance de obra.

                       No se anota lo "no cumplido": el trabajo que no
                       termina no se archiva, se reprograma, y sigue vivo en
                       su lista de por cerrar hasta que se haga.

Se REEMPLAZA por fecha, nunca se duplica: repetir el cierre de un dia
corrige la cifra en vez de sumarla dos veces.

No se guarda la foto entera del tablero en cada corte. Lo que hay que ver es
el AVANCE y el CUMPLIMIENTO, y para eso basta con lo culminado: lo que esta
abierto ahora mismo ya se ve en el tablero y en el dashboard del dia.
============================================================================
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime

from . import ajustes

COLUMNAS_DIA = ["FECHA", "CULMINADAS"]


def _ruta_dia():
    return ajustes.ARCHIVO_CULMINADAS


def _leer_csv(ruta) -> list:
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _escribir_csv(ruta, filas, columnas):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


# ---------------------------------------------------------------------------
# Culminadas por dia — de aqui sale el avance de obra
# ---------------------------------------------------------------------------
def guardar_cierre(dia: date, culminadas: int) -> str:
    """Anota cuantas tarjetas se culminaron ese dia. Reemplaza si ya estaba."""
    fila = {"FECHA": dia.isoformat(), "CULMINADAS": culminadas}
    ruta = _ruta_dia()
    previas = [f for f in _leer_csv(ruta) if f.get("FECHA") != fila["FECHA"]]
    previas.append(fila)
    previas.sort(key=lambda f: f.get("FECHA", ""))
    _escribir_csv(ruta, previas, COLUMNAS_DIA)
    return str(ruta)


def serie_culminadas(dias: int = 30) -> list:
    """[(fecha, culminadas)] de los ultimos dias con cierre."""
    serie = []
    for f in _leer_csv(_ruta_dia()):
        try:
            serie.append((date.fromisoformat(f["FECHA"]),
                          int(f.get("CULMINADAS") or 0)))
        except (ValueError, KeyError):
            continue
    serie.sort(key=lambda x: x[0])
    return serie[-dias:] if dias else serie


def avance_de_obra() -> dict:
    """Cuanto del plan completo lleva culminado la obra.

    Compara lo culminado (acumulado del PPC) contra el total de tareas del
    cronograma, y contra lo que el plan decia que deberia estar hecho a estas
    alturas. La diferencia entre esas dos cosas es el adelanto o el retraso.
    """
    from .cronograma import leer_respaldo

    try:
        plan = leer_respaldo()
    except (OSError, ValueError):
        return {}
    if not plan:
        return {}

    total_plan = len(plan)
    hoy = datetime.now().date()
    try:
        from . import horario
        hoy = horario.hoy_local()
    except Exception:
        pass

    programadas_a_hoy = sum(1 for t in plan if (t.get("fecha") or "") <= hoy.isoformat())
    culminadas = sum(c for _f, c in serie_culminadas(0))

    # Lo que ya estaba hecho antes de que el sistema entrara. Se declara una
    # vez con el robot 'arranque' y va dentro de las culminadas, pero se
    # informa aparte: no lo hicieron los robots, y quien lea el dashboard
    # tiene que poder distinguirlo.
    from .arranque import punto_de_partida
    partida = punto_de_partida()

    return {
        "total_plan": total_plan,
        "programadas_a_hoy": programadas_a_hoy,
        "culminadas": culminadas,
        "punto_de_partida": partida,
        "culminadas_con_el_sistema": culminadas - partida,
        "avance_real": round(culminadas / total_plan * 100, 1) if total_plan else 0,
        "avance_previsto": round(programadas_a_hoy / total_plan * 100, 1) if total_plan else 0,
        "desvio": culminadas - programadas_a_hoy,
    }

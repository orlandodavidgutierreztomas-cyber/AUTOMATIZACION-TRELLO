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

  reportes/cortes.csv  Todos los cortes del reporte, con una fila por tarjeta.
                       De ahi sale la evolucion del pendiente dentro del dia.

Los dos se REEMPLAZAN por clave, nunca se duplican: repetir un cierre o un
corte del mismo momento sobreescribe esa fila en vez de anadir otra.
============================================================================
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime

from . import ajustes

COLUMNAS_DIA = ["FECHA", "CULMINADAS"]


def _ruta_dia():
    return ajustes.CARPETA_REPORTES / "culminadas.csv"


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

    return {
        "total_plan": total_plan,
        "programadas_a_hoy": programadas_a_hoy,
        "culminadas": culminadas,
        "avance_real": round(culminadas / total_plan * 100, 1) if total_plan else 0,
        "avance_previsto": round(programadas_a_hoy / total_plan * 100, 1) if total_plan else 0,
        "desvio": culminadas - programadas_a_hoy,
    }


# ---------------------------------------------------------------------------
# Cortes — la evolucion del pendiente
# ---------------------------------------------------------------------------
def serie_pendientes(cortes: int = 20) -> list:
    """[(etiqueta_corte, checks_pendientes, tarjetas)] de los ultimos cortes."""
    filas = _leer_csv(ajustes.ARCHIVO_HISTORICO)
    grupos = {}
    for f in filas:
        corte = f.get("CORTE")
        if not corte:
            continue
        acumulado = grupos.setdefault(corte, {"pend": 0, "n": 0})
        try:
            acumulado["pend"] += int(f.get("CHECKS PENDIENTES") or 0)
        except ValueError:
            pass
        acumulado["n"] += 1

    salida = []
    for corte in sorted(grupos):
        etiqueta = corte[5:16].replace("-", "/") if len(corte) >= 16 else corte
        salida.append((etiqueta, grupos[corte]["pend"], grupos[corte]["n"]))
    return salida[-cortes:] if cortes else salida

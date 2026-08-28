# -*- coding: utf-8 -*-
"""Pruebas del cronograma (el Excel real) y de los relojes."""

from datetime import date, datetime, timedelta, timezone

import pytest

from trello_auto import ajustes, horario
from trello_auto.cronograma import (
    _indice_columna,
    actividades_distintas,
    destino_de,
    familia_de,
    leer_excel_completo,
    tareas_del_dia,
)


# --- lectura del Excel ------------------------------------------------------
def test_indice_columna():
    assert _indice_columna("A") == 0
    assert _indice_columna("C") == 2
    assert _indice_columna("Z") == 25
    assert _indice_columna("AA") == 26
    assert _indice_columna("3") == 2          # tambien acepta numero
    with pytest.raises(ValueError):
        _indice_columna("C3")


def test_lee_el_cronograma_real_completo():
    plan = leer_excel_completo()
    assert len(plan) > 1000, "el plan real tiene mas de mil tareas"
    for fila in plan[:50]:
        assert fila["fecha"] and fila["sector"] and fila["actividad"]
        assert fila["familia"] in ajustes.FAMILIAS
    # Viene ordenado por fecha
    fechas = [f["fecha"] for f in plan]
    assert fechas == sorted(fechas)


def test_catalogo_de_actividades():
    plan = leer_excel_completo()
    catalogo = actividades_distintas(plan)
    assert len(catalogo) > 50
    # Ordenado de mas frecuente a menos
    veces = [v for _, v in catalogo]
    assert veces == sorted(veces, reverse=True)


def test_un_dia_con_trabajo_y_un_fin_de_semana():
    assert tareas_del_dia(date(2026, 8, 28)), "el 28/08/2026 es viernes y tiene trabajo"
    assert tareas_del_dia(date(2026, 8, 16)) == [], "el 16/08/2026 es domingo"


def test_cada_tarea_sale_con_familia_y_lista():
    for t in tareas_del_dia(date(2026, 8, 28)):
        assert t["familia"] in ajustes.FAMILIAS
        assert t["lista"], f"{t['actividad']} se quedo sin lista destino"


# --- clasificacion por familia ---------------------------------------------
@pytest.mark.parametrize("actividad, esperada", [
    ("ACERO INFERIOR EN ZAPATAS", "Acero"),
    ("COMPLETADO DE ESTRIBOS EN COLUMNAS Y PLACAS", "Acero"),
    ("ENCOFRADO DE FALSA ZAPATA", "Encofrado"),
    ("CONCRETO EN FALSA ZAPATA", "Concreto"),
    # Con tilde: la comparacion no debe depender de los acentos
    ("EXCAVACIÓN DE CIMENTACIONES", "Excavacion"),
    # "trazo PARA excavacion" es Trazo, no Excavacion: gana la mas especifica
    ("TRAZO Y REPLANTEO PARA EXCAVACIÓN DE CIMENTACIONES", "Trazo"),
    ("RELLENO CON AFIRMADO COMPACTADO HASTA NIVEL DE ZAPATA", "Relleno"),
])
def test_familia_de(actividad, esperada):
    assert familia_de(actividad) == esperada


def test_lo_desconocido_cae_en_la_familia_de_descarte():
    """Nada se queda sin destino: lo que no case va a la familia por defecto."""
    familia = familia_de("LADRILLO DE SEGUNDO PISO")
    assert familia == ajustes.familia_por_defecto()
    _, lista = destino_de("LADRILLO DE SEGUNDO PISO")
    assert lista, "hasta lo desconocido tiene lista destino"


# --- horas ------------------------------------------------------------------
def test_parse_hhmm():
    assert horario.parse_hhmm("07:00") == (7, 0)
    assert horario.parse_hhmm("7:5") == (7, 5)
    for malo in ("25:00", "07:99", "siete", "", "0700"):
        with pytest.raises(ValueError):
            horario.parse_hhmm(malo)


def test_local_a_iso_utc():
    # Peru es UTC-5 todo el año: 07:00 local = 12:00 UTC.
    assert horario.local_a_iso_utc(date(2026, 8, 28), "07:00") == "2026-08-28T12:00:00.000Z"
    # Despues de las 19:00 local, la fecha UTC ya es la del dia siguiente.
    assert horario.local_a_iso_utc(date(2026, 8, 28), "20:00") == "2026-08-29T01:00:00.000Z"


def test_utc_a_local():
    d = horario.utc_a_local("2026-08-28T22:00:00.000Z")
    assert (d.hour, d.minute) == (17, 0)      # 22:00 UTC = 17:00 en Lima
    assert horario.utc_a_local("") is None
    assert horario.utc_a_local("no es una fecha") is None


def test_parse_dias():
    assert horario.parse_dias("1-5") == {1, 2, 3, 4, 5}
    assert horario.parse_dias("1,3,5") == {1, 3, 5}
    with pytest.raises(ValueError):
        horario.parse_dias("")


# --- el portero -------------------------------------------------------------
def _lima(anio, mes, dia, h, m):
    return datetime(anio, mes, dia, h, m, tzinfo=timezone(timedelta(hours=-5)))


def test_el_portero_abre_la_ventana_a_la_hora_configurada():
    # Viernes 28/08/2026, hora configurada 18:00, ventana de 90 min.
    assert horario.toca_ejecutar("18:00", "1-5", _lima(2026, 8, 28, 18, 7), 90)[0] is True
    assert horario.toca_ejecutar("18:00", "1-5", _lima(2026, 8, 28, 19, 7), 90)[0] is True
    # A las 19:37 ya pasaron los 90 minutos.
    assert horario.toca_ejecutar("18:00", "1-5", _lima(2026, 8, 28, 19, 37), 90)[0] is False
    # Antes de la hora, nunca.
    assert horario.toca_ejecutar("18:00", "1-5", _lima(2026, 8, 28, 17, 37), 90)[0] is False


def test_el_portero_respeta_los_dias():
    # Domingo 30/08/2026 a la hora exacta: no corre.
    ok, motivo = horario.toca_ejecutar("18:00", "1-5", _lima(2026, 8, 30, 18, 7), 90)
    assert ok is False and "dia" in motivo
    assert horario.toca_ejecutar("18:00", "1-7", _lima(2026, 8, 30, 18, 7), 90)[0] is True


def test_cada_robot_tiene_hora_y_dias_configurados():
    for tarea in ajustes.TAREAS:
        horario.parse_hhmm(ajustes.hora_de(tarea))
        horario.parse_dias(ajustes.dias_de(tarea))


def test_la_ventana_cubre_al_menos_dos_citas_del_cron():
    """El cron despierta cada 30 min; la ventana debe tolerar que se pierda una."""
    assert ajustes.VENTANA_MIN >= 60

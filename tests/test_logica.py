# -*- coding: utf-8 -*-
"""Pruebas de la lógica que no toca la red: clasificación, horas y plantillas."""

from datetime import date, datetime, timedelta, timezone

import pytest

from trello_auto import horario
from trello_auto.excel import clasificar_tipo
from trello_auto.trello import (
    actividad_de_plantilla,
    buscar_lista,
    construir_indice_plantillas,
    es_plantilla,
    normalizar,
)


# --- clasificación de actividades ------------------------------------------
@pytest.mark.parametrize("actividad, esperado", [
    ("ACERO EN ZAPATAS", "ACERO"),
    ("HABILITACION DE ESTRIBOS", "ACERO"),
    ("ENCOFRADO DE FALSA ZAPATA", "ENCOFRADO"),
    ("DESENCOFRADO DE COLUMNAS", "ENCOFRADO"),
    ("CONCRETO EN FALSA ZAPATA", "CONCRETO"),
    ("TARRAJEO DE MUROS", "CONCRETO"),
    ("MORTERO DE NIVELACION", "CONCRETO"),
    ("EXCAVACION DE CIMENTACIONES", "VARIOS"),
    ("TRAZO Y REPLANTEO", "VARIOS"),
    ("", "VARIOS"),
])
def test_clasificar_tipo(actividad, esperado):
    assert clasificar_tipo(actividad) == esperado


# --- normalización y búsqueda de listas ------------------------------------
def test_normalizar_quita_emojis_y_acentos():
    assert normalizar("T. DEL DÍA ACERO- 🟦🟦🟦") == "T DEL DIA ACERO"


def test_buscar_lista_por_palabra_clave():
    listas = [
        {"id": "1", "name": "T. DEL DÍA ACERO- 🟦🟦🟦🟦🟦"},
        {"id": "2", "name": "CULMINADO 🎯"},
        {"id": "3", "name": "T. NO CUMPLIDAS 🆘"},
    ]
    assert buscar_lista(listas, "T. DEL DIA ACERO") == "1"
    assert buscar_lista(listas, "CULMINADO") == "2"
    assert buscar_lista(listas, "NO CUMPLIDAS") == "3"
    assert buscar_lista(listas, "T. DEL DIA CONCRETO") is None


# --- índice de plantillas ---------------------------------------------------
def test_una_tarjeta_es_plantilla_por_su_nombre():
    assert es_plantilla("📐 PLANTILLA — TRAZO Y REPLANTEO") is True
    assert es_plantilla("PLANTILA - ACERO INFERIOR EN ZAPATAS") is True   # una sola L
    assert es_plantilla("PLANTILLAS: CONCRETO EN FALSA ZAPATA") is True   # plural
    # Una tarjeta del día NUNCA debe confundirse con una plantilla.
    assert es_plantilla("1CS1 — ACERO INFERIOR EN ZAPATAS — 27/08/2026") is False


def test_la_clave_es_la_actividad_sin_la_marca():
    clave = actividad_de_plantilla("📐 PLANTILLA — TRAZO Y REPLANTEO DE SOBRECIMIENTOS")
    assert clave == "TRAZO Y REPLANTEO DE SOBRECIMIENTOS"
    clave = actividad_de_plantilla("PLANTILA - ACERO INFERIOR EN ZAPATAS")
    assert clave == "ACERO INFERIOR EN ZAPATAS"


def test_indice_no_depende_del_nombre_de_la_lista():
    """Caso real del tablero: el encabezado dice PLANTILA (una L) pero las
    tarjetas dicen PLANTILLA. Antes se perdía la lista entera."""
    listas = [
        {"id": "L1", "name": "📐 PLANTILA. TRAZO Y REPLANTEO"},   # errata real
        {"id": "L2", "name": "T. DEL DÍA VARIOS-⬛⬛⬛"},
    ]
    cards = [
        {"id": "C1", "idList": "L1", "desc": "protocolo",
         "name": "📐 PLANTILLA — TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"},
        {"id": "C2", "idList": "L2", "desc": "",
         "name": "1PS2 — TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS — 27/08/2026"},
    ]
    indice = construir_indice_plantillas(cards, listas, "PLANTIL")
    assert list(indice) == ["TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"]
    assert indice["TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"]["id"] == "C1"


def test_la_lista_marcada_sigue_valiendo_como_apoyo():
    """Una tarjeta sin la marca en su nombre, pero dentro de una lista de
    plantillas, se sigue indexando."""
    listas = [{"id": "L1", "name": "PLANTILLA_CONCRETO"}]
    cards = [{"id": "C1", "idList": "L1", "name": "CONCRETO EN FALSA ZAPATA", "desc": ""}]
    indice = construir_indice_plantillas(cards, listas, "PLANTIL")
    assert list(indice) == ["CONCRETO EN FALSA ZAPATA"]


def test_sin_listas_solo_manda_el_nombre_de_la_tarjeta():
    cards = [
        {"id": "C1", "idList": "X", "name": "PLANTILLA — ACERO EN ZAPATAS", "desc": ""},
        {"id": "C2", "idList": "X", "name": "1CS1 — ACERO EN ZAPATAS — 26/08/2026", "desc": ""},
    ]
    assert list(construir_indice_plantillas(cards)) == ["ACERO EN ZAPATAS"]


# --- horas ------------------------------------------------------------------
def test_parse_hhmm():
    assert horario.parse_hhmm("07:00") == (7, 0)
    assert horario.parse_hhmm("7:5") == (7, 5)
    for malo in ("25:00", "07:99", "siete", "", "0700"):
        with pytest.raises(ValueError):
            horario.parse_hhmm(malo)


def test_local_a_iso_utc_convierte_desde_lima():
    # Perú es UTC-5 todo el año: 07:00 local = 12:00 UTC.
    assert horario.local_a_iso_utc(date(2026, 8, 26), "07:00") == "2026-08-26T12:00:00.000Z"
    assert horario.local_a_iso_utc(date(2026, 8, 26), "17:00") == "2026-08-26T22:00:00.000Z"
    # Después de las 19:00 local, la fecha UTC ya es la del día siguiente.
    assert horario.local_a_iso_utc(date(2026, 8, 26), "20:00") == "2026-08-27T01:00:00.000Z"


def test_parse_dias():
    assert horario.parse_dias("1-5") == {1, 2, 3, 4, 5}
    assert horario.parse_dias("1,3,5") == {1, 3, 5}
    assert horario.parse_dias("1-5,7") == {1, 2, 3, 4, 5, 7}
    with pytest.raises(ValueError):
        horario.parse_dias("")


# --- el portero horario -----------------------------------------------------
def _lima(anio, mes, dia, h, m):
    return datetime(anio, mes, dia, h, m, tzinfo=timezone(timedelta(hours=-5)))


def test_portero_deja_pasar_una_sola_corrida():
    # Miércoles 26/08/2026, hora configurada 06:30, ventana de 35 min.
    ok, _ = horario.toca_ejecutar("06:30", "1-5", _lima(2026, 8, 26, 6, 30), 35)
    assert ok is True
    # La corrida de las 07:00 cae dentro de la ventana (tolera retrasos).
    ok, _ = horario.toca_ejecutar("06:30", "1-5", _lima(2026, 8, 26, 7, 0), 35)
    assert ok is True
    # La de las 07:30 ya no.
    ok, motivo = horario.toca_ejecutar("06:30", "1-5", _lima(2026, 8, 26, 7, 30), 35)
    assert ok is False and "06:30" in motivo
    # Tampoco una anterior a la hora.
    ok, _ = horario.toca_ejecutar("06:30", "1-5", _lima(2026, 8, 26, 6, 0), 35)
    assert ok is False


def test_portero_respeta_los_dias_habiles():
    # Domingo 30/08/2026 a la hora exacta: no corre.
    ok, motivo = horario.toca_ejecutar("06:30", "1-5", _lima(2026, 8, 30, 6, 30), 35)
    assert ok is False and "día" in motivo
    # Si se configuran los 7 días, sí corre.
    ok, _ = horario.toca_ejecutar("06:30", "1-7", _lima(2026, 8, 30, 6, 30), 35)
    assert ok is True


def test_portero_con_ventana_estrecha_solo_acepta_una_media_hora():
    ok, _ = horario.toca_ejecutar("20:00", "1-5", _lima(2026, 8, 26, 20, 29), 30)
    assert ok is True
    ok, _ = horario.toca_ejecutar("20:00", "1-5", _lima(2026, 8, 26, 20, 30), 30)
    assert ok is False

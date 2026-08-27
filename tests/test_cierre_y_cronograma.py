# -*- coding: utf-8 -*-
"""Pruebas del criterio de cierre y de la lectura del cronograma."""

from datetime import date

from trello_auto import settings as config
from trello_auto.cierre_del_dia import checklist_completo, esta_terminada
from trello_auto.excel import leer_tareas_del_dia


def _card(marcada=False, items=None):
    checklists = []
    if items is not None:
        checklists = [{"name": "Control de Calidad",
                       "checkItems": [{"state": e} for e in items]}]
    return {"id": "C", "name": "tarjeta", "dueComplete": marcada,
            "checklists": checklists}


def test_checklist_completo():
    assert checklist_completo(_card(items=["complete", "complete"])) is True
    assert checklist_completo(_card(items=["complete", "incomplete"])) is False
    assert checklist_completo(_card(items=[])) is False       # sin ítems
    assert checklist_completo(_card()) is False               # sin checklist


def test_criterio_auto_acepta_cualquiera_de_las_dos_formas():
    assert esta_terminada(_card(marcada=True), "auto") is True
    assert esta_terminada(_card(items=["complete"]), "auto") is True
    assert esta_terminada(_card(items=["incomplete"]), "auto") is False
    assert esta_terminada(_card(), "auto") is False


def test_criterio_checklist_exige_control_de_calidad():
    # Marcada pero con el checklist a medias: NO cuenta como terminada.
    assert esta_terminada(_card(marcada=True, items=["incomplete"]), "checklist") is False
    assert esta_terminada(_card(marcada=True), "checklist") is False
    assert esta_terminada(_card(items=["complete"]), "checklist") is True


def test_criterio_marcada_ignora_el_checklist():
    assert esta_terminada(_card(marcada=True, items=["incomplete"]), "marcada") is True
    assert esta_terminada(_card(items=["complete"]), "marcada") is False


# --- cronograma -------------------------------------------------------------
def test_lee_el_cronograma_real_y_clasifica():
    tareas = leer_tareas_del_dia(config.RUTA_EXCEL, date(2026, 8, 13),
                                 config.RUTA_PLAN_JSON)
    assert tareas, "el 13/08/2026 debe tener tareas programadas"
    for t in tareas:
        assert t["sector"] and t["actividad"]
        assert t["tipo"] in config.TIPOS


def test_fin_de_semana_sin_tareas():
    # 16/08/2026 es domingo.
    assert leer_tareas_del_dia(config.RUTA_EXCEL, date(2026, 8, 16),
                               config.RUTA_PLAN_JSON) == []


def test_respaldo_json_equivale_al_excel(tmp_path):
    dia = date(2026, 8, 13)
    del_excel = leer_tareas_del_dia(config.RUTA_EXCEL, dia, None)
    del_json = leer_tareas_del_dia(str(tmp_path / "no-existe.xlsx"), dia,
                                   config.RUTA_PLAN_JSON)
    assert {(t["sector"], t["actividad"]) for t in del_excel} == \
           {(t["sector"], t["actividad"]) for t in del_json}


def test_el_criterio_por_defecto_es_el_checklist():
    """El cierre lo manda el control de calidad, no la marca de la tarjeta."""
    assert config.CRITERIO_CIERRE == "checklist"


def test_de_la_plantilla_se_copian_checklists_y_etiquetas():
    """Las etiquetas de la plantilla deben viajar a la tarjeta del dia."""
    partes = [p.strip() for p in config.COPIAR_DE_PLANTILLA.split(",")]
    assert "checklists" in partes
    assert "labels" in partes
    # Las fechas las pone el script, nunca la plantilla.
    assert "due" not in partes and "start" not in partes

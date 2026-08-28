# -*- coding: utf-8 -*-
"""Pruebas de lo que tiene que ver con Trello: nombres, plantillas, checklists.

Ninguna toca la red: todas trabajan sobre datos de ejemplo copiados del
tablero real.
"""

import pytest

from trello_auto import ajustes
from trello_auto.cierre import esta_terminada
from trello_auto.distribuir import partes_del_nombre
from trello_auto.trello import (
    actividad_de_plantilla,
    buscar_lista,
    checklist_completo,
    construir_indice_plantillas,
    contar_checks,
    es_plantilla,
    normalizar,
    responsable_de_checklist,
)

# Las listas tal cual estan en el tablero real, con sus emojis y su errata.
LISTAS = [
    {"id": "L0", "name": "🕖ESPERA"},
    {"id": "L1", "name": "T. DEL DÍA ACERO-                    🟦🟦🟦🟦🟦"},
    {"id": "L2", "name": "T. DEL DÍA ENCOFRADO-🟧🟧🟧🟧"},
    {"id": "L3", "name": "T. DEL DÍA CONCRETO Y MORTERO- 🟩🟩🟩"},
    {"id": "L4", "name": "T. DEL DÍA VARIOS-⬛⬛⬛⬛⬛"},
    {"id": "L5", "name": "T.  POR CERRAR 🆘🆘🆘"},
    {"id": "L6", "name": "CULMINADO    🎯🎯🎯"},
    {"id": "L7", "name": "T.  NO CUMPLIDAS 🆘🆘🆘"},
    {"id": "L8", "name": "📐 PLANTILA. TRAZO Y REPLANTEO"},   # errata real: una sola L
    {"id": "L9", "name": "PLANTILLA_CONCRETO"},
]


# --- nombres de lista -------------------------------------------------------
def test_normalizar_quita_emojis_y_acentos():
    assert normalizar("T. DEL DÍA ACERO- 🟦🟦🟦") == "T DEL DIA ACERO"


@pytest.mark.parametrize("clave, esperado", [
    ("ESPERA", "L0"),
    ("T. DEL DIA ACERO", "L1"),
    ("T. DEL DIA CONCRETO", "L3"),
    ("T. POR CERRAR", "L5"),
    ("CULMINADO", "L6"),
    ("NO CUMPLIDAS", "L7"),
    ("LISTA QUE NO EXISTE", None),
])
def test_buscar_lista_por_palabra_clave(clave, esperado):
    assert buscar_lista(LISTAS, clave) == esperado


def test_todas_las_listas_configuradas_existen_en_el_tablero():
    """Si alguien renombra una lista, esta prueba lo delata."""
    for clave in (ajustes.LISTA_ESPERA, ajustes.LISTA_CULMINADO,
                  ajustes.LISTA_NO_CUMPLIDAS, ajustes.LISTA_POR_CERRAR):
        assert buscar_lista(LISTAS, clave), f"no encuentro '{clave}'"
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        assert buscar_lista(LISTAS, lista), f"familia {familia}: falta '{lista}'"


# --- plantillas -------------------------------------------------------------
def test_una_tarjeta_es_plantilla_por_su_nombre():
    assert es_plantilla("📐 PLANTILLA — TRAZO Y REPLANTEO") is True
    assert es_plantilla("PLANTILA - ACERO INFERIOR EN ZAPATAS") is True
    assert es_plantilla("PLANTILLAS: CONCRETO EN FALSA ZAPATA") is True
    assert es_plantilla("1CS1 - ACERO INFERIOR EN ZAPATAS - 27/08/2026") is False


def test_la_clave_es_la_actividad_sin_la_marca():
    assert actividad_de_plantilla("📐 PLANTILLA — TRAZO Y REPLANTEO DE SOBRECIMIENTOS") \
        == "TRAZO Y REPLANTEO DE SOBRECIMIENTOS"


def test_el_indice_no_depende_del_nombre_de_la_lista():
    """Caso real: el encabezado dice PLANTILA pero las tarjetas dicen PLANTILLA."""
    cards = [
        {"id": "C1", "idList": "L8", "desc": "protocolo",
         "name": "📐 PLANTILLA — TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"},
        {"id": "C2", "idList": "L4", "desc": "",
         "name": "1PS2 — TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS — 27/08/2026"},
    ]
    indice = construir_indice_plantillas(cards, LISTAS, ajustes.MARCA_PLANTILLA)
    assert list(indice) == ["TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"]
    assert indice["TRAZO Y REPLANTEO DE COLUMNAS Y PLACAS"]["id"] == "C1"


def test_la_lista_marcada_vale_como_apoyo():
    cards = [{"id": "C1", "idList": "L9", "name": "CONCRETO EN FALSA ZAPATA", "desc": ""}]
    indice = construir_indice_plantillas(cards, LISTAS, ajustes.MARCA_PLANTILLA)
    assert list(indice) == ["CONCRETO EN FALSA ZAPATA"]


# --- nombre de las tarjetas del dia -----------------------------------------
def test_partes_del_nombre():
    p = partes_del_nombre("1CS11 - ACERO DE VIGA DE CIMENTACIÓN - 28/08/2026")
    assert p["sector"] == "1CS11"
    assert p["actividad"] == "ACERO DE VIGA DE CIMENTACIÓN"
    assert p["fecha"] == "28/08/2026"


def test_partes_del_nombre_no_revienta_con_basura():
    assert partes_del_nombre("una tarjeta cualquiera") == {}
    assert partes_del_nombre("") == {}


# --- checklists por responsable ---------------------------------------------
CHECKLISTS_REALES = [
    {"name": "🧱 CAMPO — LIBERACIÓN DEL FRENTE",
     "checkItems": [{"state": "incomplete"}]},
    {"name": "🧩 BIM — COMPATIBILIZACIÓN E INFORMACIÓN",
     "checkItems": [{"state": "complete"}, {"state": "incomplete"},
                    {"state": "incomplete"}]},
    {"name": "🧠 ESTRUCTURAS — CRITERIO DE REPLANTEO",
     "checkItems": [{"state": "complete"}, {"state": "complete"},
                    {"state": "incomplete"}]},
    {"name": "🧪 CALIDAD — SUPERVISIÓN Y LIBERACIÓN",
     "checkItems": [{"state": "incomplete"}] * 6},
]


def test_responsable_de_checklist():
    assert responsable_de_checklist("🧠 ESTRUCTURAS — CRITERIO", ajustes.RESPONSABLES) == "EST"
    assert responsable_de_checklist("🧪 CALIDAD — LIBERACIÓN", ajustes.RESPONSABLES) == "CAL"
    assert responsable_de_checklist("🧱 CAMPO — FRENTE", ajustes.RESPONSABLES) == "CAMP"
    assert responsable_de_checklist("🧩 BIM — INFO", ajustes.RESPONSABLES) == "BIM"
    assert responsable_de_checklist("Control de Calidad general", ajustes.RESPONSABLES) == "CAL"
    assert responsable_de_checklist("otra cosa", ajustes.RESPONSABLES) is None


def test_contar_checks_reparte_por_responsable():
    card = {"checklists": CHECKLISTS_REALES}
    c = contar_checks(card, ajustes.RESPONSABLES)
    assert c["total"] == 13
    assert c["pendientes"] == 10          # 1 CAMPO + 2 BIM + 1 EST + 6 CAL
    assert c["por_responsable"]["CAMP"] == 1
    assert c["por_responsable"]["BIM"] == 2
    assert c["por_responsable"]["EST"] == 1
    assert c["por_responsable"]["CAL"] == 6
    assert c["sin_responsable"] == 0
    # Los pendientes por responsable suman el total de pendientes
    assert sum(c["por_responsable"].values()) + c["sin_responsable"] == c["pendientes"]


def test_checks_sin_dueno_se_cuentan_aparte():
    card = {"checklists": [{"name": "Lista suelta",
                            "checkItems": [{"state": "incomplete"}]}]}
    c = contar_checks(card, ajustes.RESPONSABLES)
    assert c["sin_responsable"] == 1
    assert sum(c["por_responsable"].values()) == 0


# --- criterio de cierre -----------------------------------------------------
def _card(marcada=False, items=None):
    checklists = ([{"name": "Control de Calidad",
                    "checkItems": [{"state": e} for e in items]}]
                  if items is not None else [])
    return {"id": "C", "name": "t", "dueComplete": marcada, "checklists": checklists}


def test_checklist_completo():
    assert checklist_completo(_card(items=["complete", "complete"])) is True
    assert checklist_completo(_card(items=["complete", "incomplete"])) is False
    assert checklist_completo(_card(items=[])) is False
    assert checklist_completo(_card()) is False


def test_criterio_checklist_es_el_que_manda_por_defecto():
    assert ajustes.CRITERIO_CIERRE == "checklist"
    # Marcada pero con el checklist a medias: NO cuenta como terminada.
    assert esta_terminada(_card(marcada=True, items=["incomplete"]), "checklist") is False
    assert esta_terminada(_card(items=["complete"]), "checklist") is True


def test_criterio_auto_acepta_cualquiera_de_las_dos_formas():
    assert esta_terminada(_card(marcada=True), "auto") is True
    assert esta_terminada(_card(items=["complete"]), "auto") is True
    assert esta_terminada(_card(items=["incomplete"]), "auto") is False


def test_criterio_marcada_ignora_el_checklist():
    assert esta_terminada(_card(marcada=True, items=["incomplete"]), "marcada") is True
    assert esta_terminada(_card(items=["complete"]), "marcada") is False


def test_de_la_plantilla_se_copian_checklists_y_etiquetas():
    partes = [p.strip() for p in ajustes.COPIAR_DE_PLANTILLA.split(",")]
    assert "checklists" in partes and "labels" in partes
    # Las fechas las pone el robot con el horario del dia, nunca la plantilla.
    assert "due" not in partes and "start" not in partes

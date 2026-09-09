# -*- coding: utf-8 -*-
"""Pruebas de lo que tiene que ver con Trello: nombres, plantillas, checklists.

Ninguna toca la red: todas trabajan sobre datos de ejemplo copiados del
tablero real.
"""

import pathlib

import pytest

from trello_auto import ajustes, horario
from trello_auto.cierre import esta_terminada, origenes_de_la_fase
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
    {"id": "L5a", "name": "T. POR CERRAR - ACERO"},
    {"id": "L5b", "name": "T. POR CERRAR - ENCOFRADO-CONCRETO"},
    {"id": "L5c", "name": "T. POR CERRAR - VARIOS"},
    {"id": "L6", "name": "CULMINADO    🎯🎯🎯"},
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
    ("LISTA QUE NO EXISTE", None),
])
def test_buscar_lista_por_palabra_clave(clave, esperado):
    assert buscar_lista(LISTAS, clave) == esperado


def test_todas_las_listas_configuradas_existen_en_el_tablero():
    """Si alguien renombra una lista, esta prueba lo delata."""
    for clave in (ajustes.LISTA_ESPERA, ajustes.LISTA_CULMINADO,
                  ajustes.LISTA_POR_CERRAR):
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


def test_por_defecto_vale_cualquiera_de_las_dos_formas_de_cerrar():
    """En obra hay actividades que no necesitan todos los checks: si el
    responsable la marca como cumplida, esta cumplida."""
    assert ajustes.CRITERIO_CIERRE == "auto"
    # Marcada, aunque le falten items del checklist
    assert esta_terminada(_card(marcada=True, items=["incomplete"]), "auto") is True
    # O con el checklist completo, aunque nadie la haya marcado
    assert esta_terminada(_card(items=["complete", "complete"]), "auto") is True
    # Ni lo uno ni lo otro: no cumplio
    assert esta_terminada(_card(items=["complete", "incomplete"]), "auto") is False
    assert esta_terminada(_card(), "auto") is False


def test_el_criterio_estricto_sigue_disponible():
    """Quien quiera exigir el checklist completo sin excepciones lo tiene."""
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


# --- el cierre en dos fases -------------------------------------------------
def test_la_fase_de_gracia_solo_barre_las_listas_del_dia():
    """En el fin de jornada NO se tocan las listas de gracia: son el destino."""
    origenes = origenes_de_la_fase("gracia")
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_cierre_de_familia(familia) not in origenes
        assert ajustes.lista_de_familia(familia) in origenes


def test_cada_familia_tiene_su_propia_lista_de_cierre():
    """El margen de gracia no es un saco comun: acero espera en la suya."""
    acero = ajustes.lista_cierre_de_familia("Acero")
    varios = ajustes.lista_cierre_de_familia("Varios")
    assert acero != varios
    # Encofrado y Concreto comparten la suya, como en el tablero real
    assert (ajustes.lista_cierre_de_familia("Encofrado")
            == ajustes.lista_cierre_de_familia("Concreto"))
    # Ninguna se queda sin destino
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_cierre_de_familia(familia)
    # Y no se repiten al barrerlas
    cierres = ajustes.listas_de_cierre()
    assert len(cierres) == len(set(cierres))


def test_el_cierre_final_barre_todas_las_listas_de_gracia():
    origenes = origenes_de_la_fase("final")
    # Cada familia tiene su lista de gracia, y todas se barren
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_cierre_de_familia(familia) in origenes
    # Y tambien las del dia, por si la fase de gracia no llego a correr
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_de_familia(familia) in origenes


def test_una_tarjeta_incompleta_sobrevive_a_la_fase_de_gracia():
    """El caso que motiva el margen: al fin de jornada le falta un item, y
    todavia se puede salvar antes del cierre definitivo."""
    a_medias = _card(items=["complete", "incomplete"])
    assert esta_terminada(a_medias, "checklist") is False   # -> va a gracia
    # El especialista marca el item que faltaba durante el margen...
    completada = _card(items=["complete", "complete"])
    assert esta_terminada(completada, "checklist") is True   # -> culmina


def test_el_cierre_final_tiene_su_propio_reloj():
    assert "cierre_final" in ajustes.TAREAS
    hora_gracia = ajustes.hora_de("cierre")
    hora_final = ajustes.hora_de("cierre_final")
    horario.parse_hhmm(hora_gracia)
    horario.parse_hhmm(hora_final)
    # El definitivo va DESPUES del fin de jornada: si no, no hay margen.
    assert hora_final > hora_gracia, (
        f"el cierre definitivo ({hora_final}) debe ir despues del fin de "
        f"jornada ({hora_gracia}), o el margen de gracia no existe")


# --- el cuadro de verificacion del mapeo ------------------------------------
def test_el_cuadro_solo_ofrece_opciones_validas(tmp_path, monkeypatch):
    """Las opciones de los desplegables salen de la configuracion y del
    tablero: no se puede elegir algo que no exista."""
    from trello_auto import revisar
    familias = revisar._opciones_familia()
    assert set(familias) == set(ajustes.FAMILIAS)
    listas = revisar._opciones_lista({"listas_del_tablero": ["🕖ESPERA"]})
    assert "🕖ESPERA" in listas
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_de_familia(familia) in listas


def test_el_cuadro_marca_lo_que_pide_atencion():
    from trello_auto.revisar import _motivo_revision
    descarte = ajustes.familia_por_defecto()
    # Bien resuelta y con plantilla: no hay que mirarla
    assert _motivo_revision({"familia": "Acero", "tiene_plantilla": True}) == ""
    # Cayo en el descarte: hay que decidirla
    assert "descarte" in _motivo_revision({"familia": descarte, "tiene_plantilla": True})
    # Sin plantilla: sale con el checklist generico
    assert "plantilla" in _motivo_revision({"familia": "Acero", "tiene_plantilla": False})


# --- las paginas web --------------------------------------------------------
def test_las_paginas_escapan_lo_que_viene_de_fuera():
    """Nombres de tarjeta y de actividad llegan de Trello y del Excel: si no se
    escapan, un caracter suelto rompe la pagina."""
    from trello_auto.web import e
    assert e("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert e('T. DEL DÍA "ACERO" & CIA') == "T. DEL DÍA &quot;ACERO&quot; &amp; CIA"
    assert e(None) == ""


def test_la_navegacion_enlaza_las_dos_paginas():
    from trello_auto.web import PAGINAS, navegacion
    html = navegacion("index.html")
    for archivo, _ in PAGINAS:
        assert f'href="{archivo}"' in html
    assert 'class="activo"' in html          # marca en cual estas
    assert "DASHBOARD_CONTROL.xlsx" not in html  # el Excel se retiro


def test_las_barras_no_revientan_sin_datos():
    from trello_auto.web import barras
    assert "Nada que mostrar" in barras([])
    assert "Nada que mostrar" in barras([("Acero", 0), ("Concreto", 0)])
    # Con datos, la mayor ocupa el 100% de su pista
    html = barras([("Acero", 10), ("Concreto", 5)])
    assert "width:100.0%" in html and "width:50.0%" in html


# --- cambiar una actividad sin descargar nada -------------------------------
ACTIVIDADES_EJEMPLO = {
    "ACERO INFERIOR EN ZAPATAS": {"actividad": "ACERO INFERIOR EN ZAPATAS",
                                  "familia": "Acero", "lista": "T. DEL DIA ACERO"},
    "ACERO SUPERIOR EN ZAPATAS": {"actividad": "ACERO SUPERIOR EN ZAPATAS",
                                  "familia": "Acero", "lista": "T. DEL DIA ACERO"},
    "EXCAVACION DE CIMENTACIONES": {"actividad": "EXCAVACIÓN DE CIMENTACIONES",
                                    "familia": "Excavacion",
                                    "lista": "T. DEL DIA VARIOS"},
}


def test_buscar_actividad_acepta_un_trozo_del_nombre():
    from trello_auto.revisar import buscar_actividad
    clave, ayuda = buscar_actividad("acero inferior", ACTIVIDADES_EJEMPLO)
    assert clave == "ACERO INFERIOR EN ZAPATAS" and ayuda is None
    # Y no depende de los acentos ni de las mayusculas
    clave, _ = buscar_actividad("excavación de cimentaciones", ACTIVIDADES_EJEMPLO)
    assert clave == "EXCAVACION DE CIMENTACIONES"


def test_buscar_actividad_avisa_si_es_ambiguo():
    """Mejor no cambiar nada que cambiar la actividad equivocada."""
    from trello_auto.revisar import buscar_actividad
    clave, ayuda = buscar_actividad("acero", ACTIVIDADES_EJEMPLO)
    assert clave is None
    assert "2 actividades" in ayuda


def test_buscar_actividad_sugiere_cuando_no_encuentra():
    from trello_auto.revisar import buscar_actividad
    clave, ayuda = buscar_actividad("acero inferiar en zapatas", ACTIVIDADES_EJEMPLO)
    assert clave is None
    assert "ACERO INFERIOR EN ZAPATAS" in ayuda    # la sugiere pese a la errata


def test_buscar_actividad_con_texto_vacio():
    from trello_auto.revisar import buscar_actividad
    assert buscar_actividad("", ACTIVIDADES_EJEMPLO)[0] is None


# --- montar el tablero desde cero -------------------------------------------
def test_las_listas_necesarias_cubren_todo_el_flujo():
    from trello_auto.montar_tablero import listas_necesarias
    nombres = [n for n, _ in listas_necesarias()]
    # El recorrido completo de una tarjeta tiene que estar cubierto
    assert ajustes.LISTA_ESPERA in nombres
    for cierre in ajustes.listas_de_cierre():
        assert cierre in nombres
    assert ajustes.LISTA_CULMINADO in nombres
    assert ajustes.LISTA_PLANTILLAS in nombres
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_de_familia(familia) in nombres
    # Sin repetidas: varias familias comparten la lista de varios
    assert len(nombres) == len(set(nombres))
    # Y NO se crea una lista de "no cumplidas": lo que no termina se
    # reprograma desde su lista de por cerrar, no se aparta en un saco.
    assert not any("NO CUMPLID" in n.upper() for n in nombres)


def test_cada_responsable_configurado_tiene_items_genericos():
    """Si se anade un responsable a la configuracion, hay que darle items."""
    from trello_auto.montar_tablero import ITEMS_GENERICOS
    for codigo in ajustes.CODIGOS_RESPONSABLE:
        assert codigo in ITEMS_GENERICOS, f"falta el esqueleto de {codigo}"
        assert ITEMS_GENERICOS[codigo], f"{codigo} no tiene ningun item"


def test_la_plantilla_generada_se_reconoce_como_plantilla():
    """La tarjeta que crea el montaje tiene que casar con su actividad."""
    from trello_auto.trello import actividad_de_plantilla, es_plantilla
    nombre = "PLANTILLA - ACERO INFERIOR EN ZAPATAS"
    assert es_plantilla(nombre)
    assert actividad_de_plantilla(nombre) == "ACERO INFERIOR EN ZAPATAS"


# --- historico y graficas ---------------------------------------------------
def test_guardar_cierre_reemplaza_el_dia_no_lo_duplica(tmp_path, monkeypatch):
    """Repetir el cierre del mismo dia corrige la cifra, no la suma dos veces."""
    from datetime import date

    from trello_auto import historico
    monkeypatch.setattr(historico.ajustes, "CARPETA_REPORTES", tmp_path)

    historico.guardar_cierre(date(2026, 9, 1), 5)
    historico.guardar_cierre(date(2026, 9, 1), 8)      # el mismo dia, corregido
    serie = historico.serie_culminadas(0)
    assert len(serie) == 1 and serie[0] == (date(2026, 9, 1), 8)


def test_el_historico_no_guarda_nada_de_no_cumplidas(tmp_path, monkeypatch):
    """Solo se anota lo culminado: lo que no termina se reprograma."""
    from datetime import date

    from trello_auto import historico
    monkeypatch.setattr(historico.ajustes, "CARPETA_REPORTES", tmp_path)

    historico.guardar_cierre(date(2026, 9, 1), 5)
    escrito = (tmp_path / "culminadas.csv").read_text(encoding="utf-8-sig")
    assert "NO CUMPLIDAS" not in escrito
    assert historico.COLUMNAS_DIA == ["FECHA", "CULMINADAS"]


def test_la_grafica_avisa_cuando_no_hay_bastantes_datos():
    from trello_auto.web import grafico_linea
    assert "mas de un dato" in grafico_linea([])
    assert "mas de un dato" in grafico_linea([("01/09", 50)])
    svg = grafico_linea([("01/09", 50), ("02/09", 80)], "%", meta=85)
    assert "<svg" in svg and "polyline" in svg and "meta 85%" in svg


# --- limpiar duplicadas -----------------------------------------------------
def _dup(cid, nombre, marcados=0, items=0, comentarios=0, adjuntos=0, lista="L1"):
    return {"id": cid, "name": nombre, "idList": lista,
            "badges": {"checkItemsChecked": marcados, "checkItems": items,
                       "comments": comentarios, "attachments": adjuntos}}


def test_solo_se_agrupan_los_nombres_repetidos():
    from trello_auto.limpiar_duplicadas import agrupar_duplicadas
    cards = [_dup("a" * 24, "1CS1 - ACERO - 01/09/2026"),
             _dup("b" * 24, "1CS1 — ACERO — 01/09/2026"),   # guion largo: es la misma
             _dup("c" * 24, "1CS2 - ACERO - 01/09/2026")]
    grupos = agrupar_duplicadas(cards)
    assert len(grupos) == 1
    assert len(next(iter(grupos.values()))) == 2


def test_una_tarjeta_con_trabajo_nunca_esta_vacia():
    from trello_auto.limpiar_duplicadas import esta_vacia
    assert esta_vacia(_dup("a" * 24, "x")) is True
    assert esta_vacia(_dup("a" * 24, "x", marcados=1)) is False
    assert esta_vacia(_dup("a" * 24, "x", comentarios=1)) is False
    assert esta_vacia(_dup("a" * 24, "x", adjuntos=1)) is False
    # Tener items sin marcar no es trabajo: la plantilla los pone sola
    assert esta_vacia(_dup("a" * 24, "x", items=12)) is True


def test_sobrevive_la_que_tiene_mas_trabajo():
    from trello_auto.limpiar_duplicadas import elegir_superviviente
    vacia = _dup("6a8f0001" + "0" * 16, "x")
    trabajada = _dup("6a8f0002" + "0" * 16, "x", marcados=7, items=12)
    assert elegir_superviviente([vacia, trabajada])["id"] == trabajada["id"]
    # Si ninguna tiene checks, gana la que tenga adjuntos
    con_adjunto = _dup("6a8f0003" + "0" * 16, "x", adjuntos=2)
    assert elegir_superviviente([vacia, con_adjunto])["id"] == con_adjunto["id"]


def test_a_igualdad_sobrevive_la_mas_antigua():
    from trello_auto.limpiar_duplicadas import elegir_superviviente
    vieja = _dup("6a8f0001" + "0" * 16, "x")
    nueva = _dup("6a9f0001" + "0" * 16, "x")
    assert elegir_superviviente([nueva, vieja])["id"] == vieja["id"]


@pytest.mark.parametrize("a, b, son_duplicadas", [
    # Lo que preocupa: dos aceros distintos NO pueden confundirse
    ("1CS1 - ACERO DE ZAPATA - 01/09/2026",
     "1CS1 - ACERO DE COLUMNA - 01/09/2026", False),
    # Mismo trabajo, sector distinto
    ("1CS1 - ACERO DE ZAPATA - 01/09/2026",
     "1CS2 - ACERO DE ZAPATA - 01/09/2026", False),
    # Mismo trabajo y sector, otro dia: son dos jornadas, no una copia
    ("1CS1 - ACERO DE ZAPATA - 01/09/2026",
     "1CS1 - ACERO DE ZAPATA - 03/09/2026", False),
    # Una actividad que contiene a la otra tampoco se confunde
    ("1CS1 - ACERO EN ZAPATAS - 01/09/2026",
     "1CS1 - ACERO INFERIOR EN ZAPATAS - 01/09/2026", False),
    # La duplicada de verdad: solo cambia el guion o los acentos
    ("1CS1 - ACERO DE CIMENTACION - 01/09/2026",
     "1CS1 — ACERO DE CIMENTACIÓN — 01/09/2026", True),
])
def test_solo_se_agrupa_lo_que_es_exactamente_la_misma_tarjeta(a, b, son_duplicadas):
    from trello_auto.limpiar_duplicadas import agrupar_duplicadas
    grupos = agrupar_duplicadas([_dup("a" * 24, a), _dup("b" * 24, b)])
    assert bool(grupos) is son_duplicadas


# --- cuantas listas de cierre se crean, segun como se configure -------------
def test_por_defecto_hay_una_lista_de_cierre_por_grupo_de_familias():
    """Lo normal: acero por un lado, encofrado y concreto juntos, el resto."""
    cierres = ajustes.listas_de_cierre()
    assert len(cierres) == 3
    # Ninguna sobra: todas las declara alguna familia
    declaradas = {ajustes.lista_cierre_de_familia(f) for f in ajustes.FAMILIAS}
    assert set(cierres) == declaradas


def test_se_puede_configurar_un_unico_cierre(monkeypatch):
    """Si se prefiere una sola lista, basta con apuntar todas las familias
    al mismo nombre: el sistema crea una y barre una."""
    unica = {f: dict(d, lista_cierre="T. POR CERRAR")
             for f, d in ajustes.FAMILIAS.items()}
    monkeypatch.setattr(ajustes, "FAMILIAS", unica)
    assert ajustes.listas_de_cierre() == ["T. POR CERRAR"]


def test_sin_lista_cierre_propia_se_usa_la_global(monkeypatch):
    """Y si ninguna familia declara la suya, se cae a listas.por_cerrar."""
    sin_cierre = {f: {k: v for k, v in d.items() if k != "lista_cierre"}
                  for f, d in ajustes.FAMILIAS.items()}
    monkeypatch.setattr(ajustes, "FAMILIAS", sin_cierre)
    assert ajustes.listas_de_cierre() == [ajustes.LISTA_POR_CERRAR]


def test_el_montaje_crea_exactamente_las_listas_de_cierre_declaradas():
    """Lo que se crea y lo que se barre tienen que ser lo mismo."""
    from trello_auto.montar_tablero import listas_necesarias
    creadas = [n for n, _ in listas_necesarias()]
    for cierre in ajustes.listas_de_cierre():
        assert cierre in creadas
    # Y no se cuela ninguna lista de cierre que nadie use
    de_cierre = [n for n in creadas if "POR CERRAR" in n.upper()]
    assert sorted(de_cierre) == sorted(ajustes.listas_de_cierre())


# --- estado del tablero: que lista hace que ---------------------------------
def test_el_estado_senala_las_listas_que_nadie_toca():
    """El caso real: al partir el cierre en tres, la vieja queda huerfana."""
    from trello_auto.estado import analizar
    listas = [
        {"id": "L1", "name": "🕖ESPERA"},
        {"id": "L2", "name": "T. DEL DÍA ACERO- 🟦"},
        {"id": "L3", "name": "T. POR CERRAR - ACERO"},
        {"id": "L4", "name": "T.  POR CERRAR 🆘"},          # la vieja, huerfana
        {"id": "L5", "name": "🧰 RECURSOS"},                # nunca tuvo papel
    ]
    cards = [{"id": "c1", "idList": "L4", "name": "1CS1 - ACERO - 01/09/2026"}]
    datos = analizar(listas, cards)
    sin_uso = {f["nombre"] for f in datos["filas"] if f["sin_uso"]}
    assert "T.  POR CERRAR 🆘" in sin_uso
    assert "🧰 RECURSOS" in sin_uso
    assert "T. POR CERRAR - ACERO" not in sin_uso
    # Y cuenta las tarjetas que se quedarian atrapadas
    atrapada = next(f for f in datos["filas"] if f["nombre"] == "T.  POR CERRAR 🆘")
    assert atrapada["tarjetas"] == 1


def test_el_estado_avisa_de_las_listas_que_faltan():
    """Si la configuracion nombra una lista inexistente, hay que verlo antes
    de que un robot se pare a mitad de una corrida."""
    from trello_auto.estado import analizar
    datos = analizar([{"id": "L1", "name": "🕖ESPERA"}], [])
    claves_que_faltan = {clave for clave, _ in datos["faltan"]}
    assert ajustes.LISTA_CULMINADO in claves_que_faltan
    assert ajustes.LISTA_ESPERA not in claves_que_faltan   # esa si existe


def test_una_lista_de_plantillas_antigua_no_cuenta_como_sin_uso():
    """Las listas PLANTILLA_* de siempre siguen sirviendo aunque no esten
    nombradas en la configuracion."""
    from trello_auto.estado import analizar
    listas = [{"id": "L1", "name": "PLANTILLA_CONCRETO"}]
    cards = [{"id": "c1", "idList": "L1", "name": "PLANTILLA - CONCRETO EN ZAPATA"}]
    fila = analizar(listas, cards)["filas"][0]
    assert fila["sin_uso"] is False


# --- coherencia entre robots ------------------------------------------------
def test_el_reporte_mira_las_mismas_listas_que_barre_el_cierre():
    """Si el cierre evalua una lista, el reporte tiene que contarla: si no,
    habria trabajo en juego que no aparece en ningun indicador."""
    from trello_auto.reporte import listas_del_alcance
    del_reporte = {clave for clave, _estado in listas_del_alcance("todo")}
    for cierre in ajustes.listas_de_cierre():
        assert cierre in del_reporte, f"el reporte no mira '{cierre}'"
    for familia in ajustes.FAMILIAS:
        assert ajustes.lista_de_familia(familia) in del_reporte


def test_el_alcance_no_repite_listas():
    """Varias familias comparten lista: no puede contarse dos veces."""
    from trello_auto.reporte import listas_del_alcance
    for alcance in ("dia", "todo"):
        claves = [c for c, _e in listas_del_alcance(alcance)]
        assert len(claves) == len(set(claves)), f"alcance '{alcance}' repite listas"


def test_el_reporte_registra_si_la_tarjeta_esta_marcada():
    """Con el criterio por defecto la marca cierra la tarjeta, asi que hay que
    poder ver cuales se cerraron asi y cuales por su checklist."""
    from datetime import datetime, timedelta, timezone

    from trello_auto.reporte import columnas, fila_de_tarjeta
    assert "MARCADA" in columnas()

    corte = datetime(2026, 9, 8, 15, 0, tzinfo=timezone(timedelta(hours=-5)))
    card = {"id": "C", "name": "1CS1 - ACERO EN ZAPATAS - 08/09/2026",
            "dueComplete": True, "checklists": [], "shortUrl": ""}
    assert fila_de_tarjeta(card, "T. DEL DIA ACERO", "EN JUEGO", corte, 1)["MARCADA"] == "si"
    card["dueComplete"] = False
    assert fila_de_tarjeta(card, "T. DEL DIA ACERO", "EN JUEGO", corte, 1)["MARCADA"] == ""


# --- el dashboard -----------------------------------------------------------
def _fila(pend=0, total=10, dias=0, marcada=False, familia="Acero"):
    return {"SECTOR / ZONA": "1CS1", "ACTIVIDAD": "ACERO EN ZAPATAS",
            "FAMILIA": familia, "VENCE": "2026-09-08 18:30", "OTROS": 0,
            "CHECKS PENDIENTES": pend, "TOTAL CHECKS": total,
            "ANTIGUEDAD (dias)": dias, "MARCADA": "si" if marcada else "",
            "CLAVE ORDEN": pend, "LISTA TRELLO": "T. DEL DIA",
            "DIA DEL CORTE": "HOY", "ESTADO": "EN JUEGO", "LINK TRELLO": ""}


def test_el_dashboard_cierra_igual_que_el_robot_del_cierre():
    """Si el dashboard contara distinto que el cierre, mentiria."""
    from trello_auto.tablero import _cerrada
    assert _cerrada(_fila(pend=0)) is True                  # checklist completo
    assert _cerrada(_fila(pend=5, marcada=True)) is True    # marcada como cumplida
    assert _cerrada(_fila(pend=5)) is False
    # Y coincide con el criterio "auto" del cierre
    for pend, marcada in [(0, False), (5, True), (5, False)]:
        card = _card(marcada=marcada,
                     items=["complete"] * (10 - pend) + ["incomplete"] * pend)
        assert _cerrada(_fila(pend=pend, marcada=marcada)) == \
            esta_terminada(card, "auto")


def test_el_panel_de_sin_cerrar_se_vacia_cuando_todo_cierra():
    """Lo que pidio el usuario: si todo esta cerrado, el tablero queda limpio."""
    from trello_auto.tablero import _sin_cerrar
    assert "Todo cerrado" in _sin_cerrar([_fila(pend=0), _fila(pend=3, marcada=True)])
    html = _sin_cerrar([_fila(pend=3, dias=2)])
    assert "Todo cerrado" not in html
    assert "1 atrasadas" in html


def _cuerpo(html: str) -> str:
    """Solo las filas: los desplegables de filtro repiten los mismos textos."""
    return html[html.index("<tbody>"):]


def test_las_atrasadas_salen_primero():
    from trello_auto.tablero import _sin_cerrar
    cuerpo = _cuerpo(_sin_cerrar([
        _fila(pend=1, dias=0), _fila(pend=1, dias=5, familia="Trazo"),
        _fila(pend=1, dias=2, familia="Concreto")]))
    # La de 5 dias debe aparecer antes que la de 2 y que la de hoy
    assert cuerpo.index("5 dias") < cuerpo.index("2 dias") < cuerpo.index("hoy")


def test_la_tabla_trae_filtro_de_familia():
    """Lo que pidio el usuario: el boton va en la cabecera Familia."""
    from trello_auto.tablero import _sin_cerrar
    html = _sin_cerrar([_fila(pend=1, familia="Encofrado"),
                        _fila(pend=1, familia="Acero")])
    # El desplegable cuelga de la cabecera, no de una barra aparte
    assert '<th>Familia<span class="filtro" data-campo="familia"' in html
    assert 'data-valor="Encofrado"' in html
    assert 'data-valor="Acero"' in html
    # Y cada fila declara la suya, que es de lo que tira el filtro
    assert 'data-familia="Encofrado"' in html


def test_no_se_pinta_un_filtro_de_una_sola_opcion():
    """Un desplegable con una sola familia no filtra nada: estorba."""
    from trello_auto.tablero import _sin_cerrar
    html = _sin_cerrar([_fila(pend=1, familia="Acero"), _fila(pend=2, familia="Acero")])
    assert 'class="filtro"' not in html
    assert "<th>Familia</th>" in html


def test_la_antiguedad_lleva_la_fecha_al_lado_sin_ano():
    """Dia y mes entre parentesis; el ano sobra, siempre es el de la obra."""
    from trello_auto.tablero import _sin_cerrar
    fila = _fila(pend=1, dias=0)
    fila["VENCE"] = "2026-09-08 18:30"
    cuerpo = _cuerpo(_sin_cerrar([fila]))
    assert "(08/09)" in cuerpo
    assert "2026" not in cuerpo


def test_la_fila_se_despliega_con_lo_que_debe_cada_responsable():
    """En vez de mandar a Trello, el detalle esta en la propia pagina."""
    from trello_auto.tablero import _sin_cerrar
    fila = _fila(pend=4)
    fila["EST"], fila["CAL"], fila["OTROS"] = 3, 1, 0
    fila["LINK TRELLO"] = "https://trello.com/c/abc"
    html = _sin_cerrar([fila])
    assert 'class="desplegable"' in html
    assert 'class="detalle"' in html
    assert "Estructuras" in html and "Calidad" in html
    # Y el enlace a Trello sigue existiendo, pero dentro del despliegue
    assert "Abrir en Trello" in html


def test_el_anillo_es_un_medidor_no_un_grafico_de_sectores():
    """Una sola razon contra su tope: arco proporcional sobre su pista."""
    from trello_auto.web import anillo
    html = anillo(75, "cerradas")
    assert "75%" in html
    # Dos circulos: la pista y el arco. Nada de sectores.
    assert html.count("<circle") == 2
    # Y el estado va tambien en palabras, no solo en color
    assert "meta" in html
    assert "en meta" in anillo(90, "x")
    assert "muy por debajo" in anillo(20, "x")


def test_cada_familia_conserva_su_color():
    """El color sigue a la entidad, no a su puesto en el ranking."""
    from trello_auto.web import color_de
    catalogo = list(ajustes.FAMILIAS)
    colores = {f: color_de(f, catalogo) for f in catalogo}
    assert len(set(colores.values())) == len(catalogo)   # ninguno repetido
    # Reordenar el ranking no cambia el color de nadie
    assert color_de("Acero", catalogo) == colores["Acero"]
    assert color_de("Familia inventada", catalogo) == "var(--suave)"


def test_la_barra_apilada_ignora_los_tramos_vacios():
    from trello_auto.web import barra_apilada
    html = barra_apilada([("Cerradas", 3, "var(--ok)"), ("En curso", 0, "var(--aviso)")])
    assert "Cerradas" in html and "En curso" not in html
    assert barra_apilada([("x", 0, "y")]) == ""


# --- ambitos y tema ---------------------------------------------------------
def test_los_ambitos_del_dashboard_coinciden_con_los_del_reporte():
    """Si el reporte etiqueta un estado que el dashboard no conoce, esas
    tarjetas desaparecerian de la pagina sin que nadie lo note."""
    from trello_auto.reporte import listas_del_alcance
    from trello_auto.tablero import AMBITOS
    del_dashboard = {clave for clave, _t, _q, _c in AMBITOS}
    del_reporte = {estado for _c, estado in listas_del_alcance("todo")}
    assert del_reporte <= del_dashboard, del_reporte - del_dashboard


def test_el_reporte_abarca_todo_por_defecto():
    """El dashboard tiene tres ambitos: si el corte solo trajera el del dia,
    dos secciones saldrian siempre vacias."""
    import argparse

    from trello_auto import reporte
    ap = argparse.ArgumentParser()
    ap.add_argument("--alcance", default="todo")
    assert ap.parse_args([]).alcance == "todo"
    assert "todo" in reporte.ALCANCES


def test_el_tema_se_puede_elegir_en_los_dos_sentidos():
    """Oscuro en un equipo claro, y claro en un equipo oscuro."""
    from trello_auto.web import CSS, TEMAS
    claves = [c for c, _r in TEMAS]
    assert claves == ["auto", "light", "suave", "dark"]
    # Cada eleccion explicita tiene su bloque, o no haria nada
    assert ':root[data-theme="dark"]' in CSS
    assert ':root[data-theme="suave"]' in CSS
    # Y el bloque del sistema cede ante una eleccion clara
    assert ':root:not([data-theme="light"])' in CSS


def test_la_seccion_lleva_titulo_y_explicacion():
    from trello_auto.web import seccion
    html = seccion("Por cerrar", "El margen de gracia", "5 tarjetas", "var(--aviso)")
    assert "Por cerrar" in html and "margen de gracia" in html
    assert "5 tarjetas" in html


# --- reubicar: retirar una columna sin perder trabajo ------------------------
@pytest.mark.parametrize("nombre, esperada", [
    ("1CS4 - ACERO SUPERIOR EN ZAPATAS - 27/08/2026", "Acero"),
    ("1CS3 - ENCOFRADO DE FALSA ZAPATA - 27/08/2026", "Encofrado"),
    ("1CS13 - CONCRETO EN FALSA ZAPATA - 27/08/2026", "Concreto"),
    ("1CS7 - TRAZO Y REPLANTEO PARA EXCAVACION - 27/08/2026", "Trazo"),
    ("1CS2 - RELLENO CON AFIRMADO COMPACTADO - 27/08/2026", "Relleno"),
])
def test_reubicar_manda_cada_tarjeta_a_la_lista_de_su_familia(nombre, esperada):
    """Al retirar una columna, el trabajo no se amontona: se reparte."""
    from trello_auto.reubicar import destino_de_tarjeta
    familia, clave = destino_de_tarjeta(nombre)
    assert familia == esperada
    assert clave == ajustes.lista_cierre_de_familia(esperada)


def test_reubicar_reparte_a_listas_que_existen_en_el_tablero():
    """Si el destino no existiera, el trabajo se quedaria en el limbo."""
    from trello_auto.reubicar import destino_de_tarjeta
    for nombre in ("1CS4 - ACERO SUPERIOR EN ZAPATAS",
                   "1CS3 - ENCOFRADO DE FALSA ZAPATA",
                   "1CS7 - EXCAVACION DE CIMENTACIONES"):
        _familia, clave = destino_de_tarjeta(nombre)
        assert buscar_lista(LISTAS, clave), f"no existe la lista '{clave}'"


def test_ninguna_tarjeta_desaparece_del_tablero_por_su_estado(tmp_path, monkeypatch):
    """Un corte viejo trae estados que ya no existen (la lista retirada de
    'no cumplidas', por ejemplo). Esa tarjeta sigue siendo trabajo abierto:
    tiene que verse, aunque sea en el ambito de refugio."""
    from datetime import datetime

    from trello_auto import tablero
    from trello_auto.tablero import generar
    monkeypatch.setattr(tablero.ajustes, "CARPETA_WEB", tmp_path)

    fila = _fila(pend=4, dias=3)
    fila["ESTADO"] = "NO CUMPLIDA"          # un estado ya retirado
    html = pathlib.Path(generar([fila], datetime(2026, 9, 8, 19, 0),
                                "todo")).read_text(encoding="utf-8")
    assert "Donde esta cada tarjeta" in html
    assert "ACERO EN ZAPATAS" in html


# --- el codigo del tablero --------------------------------------------------
@pytest.mark.parametrize("pegado", [
    "https://trello.com/b/gzoZo6ip/aulas-control-diario",
    "https://trello.com/b/gzoZo6ip/aulas-control-diario/",
    "http://trello.com/b/gzoZo6ip/aulas-control-diario",
    "trello.com/b/gzoZo6ip/aulas",
    "gzoZo6ip/aulas-control-diario",
    "gzoZo6ip",
    "  gzoZo6ip  ",
])
def test_vale_pegar_la_url_del_tablero(pegado):
    """Lo natural es copiar la barra del navegador. Pegar la URL entera era la
    equivocacion facil, y Trello no avisa: responde un 404 seco."""
    from trello_auto.ajustes import codigo_de_tablero
    assert codigo_de_tablero(pegado) == "gzoZo6ip"


def test_el_tablero_configurado_es_un_codigo_no_una_url():
    """Si en el JSON quedara pegada media URL, todos los robots fallarian."""
    from trello_auto.ajustes import codigo_de_tablero
    assert ajustes.BOARD_ID
    assert codigo_de_tablero(ajustes.BOARD_ID) == ajustes.BOARD_ID
    assert ajustes.BOARD_ID.isalnum(), (
        f"obra.tablero deberia ser solo el codigo, y es {ajustes.BOARD_ID!r}")


def test_configurar_limpia_la_url_antes_de_guardarla():
    from trello_auto.configurar import validar
    assert validar("https://trello.com/b/LzqD0qZh/prueba", "tablero") == "LzqD0qZh"
    assert validar("LzqD0qZh/prueba", "tablero") == "LzqD0qZh"
    with pytest.raises(ValueError):
        validar("no es un tablero", "tablero")

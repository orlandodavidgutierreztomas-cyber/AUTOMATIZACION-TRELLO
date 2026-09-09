# -*- coding: utf-8 -*-
"""Pruebas del cliente de Trello. Ninguna toca la red: se sustituye _req.

Nacieron de dos fallos reales al montar un tablero nuevo:
  - se pego media URL en obra.tablero, y Trello devolvio un 404 seco;
  - se mandaba el id CORTO del tablero como parametro 'idBoard', y crear la
    primera columna fallaba con un 400 sin explicacion.
"""

import pytest

from trello_auto.trello import ErrorTrello, Trello

LARGO = "6a8c6f4a44ab017c3add34b9"    # 24 caracteres: el id interno
CORTO = "LzqD0qZh"                    # el de la URL


class _Falso(Trello):
    """Un cliente que anota las llamadas en vez de hacerlas."""

    def __init__(self):
        super().__init__("k", "t")
        self.llamadas = []

    def _req(self, metodo, path, params=None):
        self.llamadas.append((metodo, path, params or {}))
        if metodo == "GET" and path.startswith("/boards/"):
            return {"id": LARGO}
        return {"id": "nueva", "name": (params or {}).get("name")}


def test_crear_lista_manda_el_id_largo_del_tablero():
    """Con el id corto, Trello responde 400: 'invalid value for idBoard'."""
    tr = _Falso()
    tr.crear_lista(CORTO, "T. DEL DIA ACERO")
    post = [c for c in tr.llamadas if c[0] == "POST"]
    assert post and post[0][1] == "/lists"
    assert post[0][2]["idBoard"] == LARGO


def test_el_id_largo_se_pide_una_sola_vez():
    """Montar un tablero crea varias columnas: no se pregunta en cada una."""
    tr = _Falso()
    for nombre in ("A", "B", "C"):
        tr.crear_lista(CORTO, nombre)
    consultas = [c for c in tr.llamadas if c[0] == "GET"]
    assert len(consultas) == 1


def test_un_id_que_ya_es_largo_no_se_consulta():
    tr = _Falso()
    tr.crear_lista(LARGO, "A")
    assert not [c for c in tr.llamadas if c[0] == "GET"]


class _Respuesta:
    def __init__(self, codigo, texto=""):
        self.status_code = codigo
        self.text = texto
        self.headers = {}


class _Sesion:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.intentos = 0

    def request(self, *_a, **_k):
        self.intentos += 1
        return self.respuesta


def test_un_error_nuestro_no_se_reintenta_y_dice_el_motivo():
    """Reintentar un 400 no arregla nada, y el motivo lo da Trello en el
    cuerpo. Esconderlo fue lo que dejo el fallo sin diagnosticar."""
    tr = Trello("k", "t")
    tr.sesion = _Sesion(_Respuesta(400, "invalid value for idBoard"))
    with pytest.raises(ErrorTrello, match="idBoard"):
        tr._req("POST", "/lists", {"idBoard": CORTO})
    assert tr.sesion.intentos == 1

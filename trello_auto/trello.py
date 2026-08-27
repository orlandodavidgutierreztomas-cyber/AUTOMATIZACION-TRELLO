# -*- coding: utf-8 -*-
"""
============================================================================
 CLIENTE DE LA API DE TRELLO  (compartido por los dos scripts)
============================================================================
Un solo lugar con las llamadas a Trello: reintentos ante cortes de red o
limite de peticiones (429), y utilidades para encontrar listas por palabra
clave aunque tengan emojis, acentos o espacios de mas.
============================================================================
"""

from __future__ import annotations

import re
import time
import unicodedata

import requests

TIEMPO_ESPERA = 30          # segundos por peticion
REINTENTOS = 4
PAUSA_ESCRITURA = 0.2       # segundos entre escrituras (limite de la API)


def normalizar(texto: str) -> str:
    """Para comparar nombres: sin acentos ni simbolos, MAYUSCULAS, 1 espacio.

    "T. DEL DIA ACERO- (emojis)"  ->  "T DEL DIA ACERO"
    """
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip().upper()


class ErrorTrello(RuntimeError):
    pass


class Trello:
    BASE = "https://api.trello.com/1"

    def __init__(self, key: str, token: str):
        self.auth = {"key": key, "token": token}
        self.sesion = requests.Session()

    # -- motor -------------------------------------------------------------
    def _req(self, metodo: str, path: str, params: dict = None):
        p = dict(self.auth)
        if params:
            p.update(params)
        ultimo_error = None
        for intento in range(REINTENTOS):
            try:
                r = self.sesion.request(metodo, f"{self.BASE}{path}",
                                        params=p, timeout=TIEMPO_ESPERA)
                if r.status_code == 429:                 # limite de peticiones
                    espera = float(r.headers.get("Retry-After", 2 ** intento))
                    time.sleep(min(espera, 30))
                    continue
                if r.status_code >= 500:                 # error temporal de Trello
                    time.sleep(2 ** intento)
                    continue
                r.raise_for_status()
                return r.json() if r.text else None
            except requests.RequestException as e:
                ultimo_error = e
                time.sleep(2 ** intento)
        raise ErrorTrello(
            f"Trello no respondio a {metodo} {path} tras {REINTENTOS} intentos: {ultimo_error}"
        )

    # -- lectura -----------------------------------------------------------
    def listas(self, board_id: str) -> list:
        """[{id, name}] de las listas abiertas del tablero."""
        return self._req("GET", f"/boards/{board_id}/lists",
                         {"fields": "name", "filter": "open"})

    def tarjetas(self, board_id: str) -> list:
        """[{id, name, idList, desc}] de las tarjetas abiertas del tablero."""
        return self._req("GET", f"/boards/{board_id}/cards",
                         {"fields": "name,idList,desc", "filter": "open"})

    def tarjetas_de_lista(self, list_id: str) -> list:
        """Tarjetas de una lista, con sus checklists embebidos (1 sola llamada)."""
        return self._req("GET", f"/lists/{list_id}/cards", {
            "fields": "name,due,dueComplete",
            "checklists": "all",
            "checklist_fields": "name",
        })

    # -- escritura ---------------------------------------------------------
    def crear_tarjeta(self, params: dict) -> dict:
        card = self._req("POST", "/cards", params)
        time.sleep(PAUSA_ESCRITURA)
        return card

    def crear_checklist(self, card_id: str, nombre: str) -> str:
        data = self._req("POST", "/checklists", {"idCard": card_id, "name": nombre})
        time.sleep(PAUSA_ESCRITURA)
        return data["id"]

    def agregar_item(self, checklist_id: str, texto: str):
        self._req("POST", f"/checklists/{checklist_id}/checkItems", {"name": texto})
        time.sleep(PAUSA_ESCRITURA)

    def mover(self, card_id: str, list_id: str):
        r = self._req("PUT", f"/cards/{card_id}", {"idList": list_id})
        time.sleep(PAUSA_ESCRITURA)
        return r


# ---------------------------------------------------------------------------
# Utilidades sobre las listas del tablero
# ---------------------------------------------------------------------------
def buscar_lista(listas: list, clave: str) -> str:
    """Id de la primera lista cuyo nombre CONTENGA la palabra clave (normalizada)."""
    k = normalizar(clave)
    for l in listas:
        if k and k in normalizar(l["name"]):
            return l["id"]
    return None


def nombre_de_lista(listas: list, list_id: str) -> str:
    for l in listas:
        if l["id"] == list_id:
            return l["name"]
    return "(desconocida)"


def construir_indice_plantillas(listas: list, cards: list, clave_plantillas: str) -> dict:
    """{actividad_normalizada: {'id':..., 'desc':..., 'nombre':...}}

    Recorre las tarjetas que viven en listas cuyo nombre contiene la palabra
    clave de plantillas (p. ej. "PLANTILLA_ACERO") y las indexa por el nombre
    de la actividad, quitando la palabra "PLANTILLA", emojis y guiones.

    El emparejamiento se hace LEYENDO EL TABLERO EN VIVO: no hay ningun id
    escrito en el codigo, asi que al agregar una plantilla nueva al tablero
    el script la usa automaticamente en la siguiente corrida.
    """
    clave = normalizar(clave_plantillas)
    ids_plantilla = {l["id"] for l in listas if clave in normalizar(l["name"])}
    indice = {}
    for c in cards:
        if c.get("idList") not in ids_plantilla:
            continue
        actividad = normalizar(re.sub(r"PLANTILLA", " ", c["name"], flags=re.I))
        if actividad:
            indice[actividad] = {
                "id": c["id"],
                "desc": c.get("desc") or "",
                "nombre": c["name"],
            }
    return indice

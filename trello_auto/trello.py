# -*- coding: utf-8 -*-
"""
============================================================================
 CLIENTE DE LA API DE TRELLO  (compartido por todos los robots)
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
        """Tarjetas de una lista, con sus checklists embebidos (1 sola llamada).

        Trae el estado de cada item, que es lo que usan el cierre y el reporte.
        """
        return self._req("GET", f"/lists/{list_id}/cards", {
            "fields": "name,due,dueComplete,shortUrl,labels,idList",
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

    def archivar(self, card_id: str):
        """Archiva la tarjeta (en Trello, 'closed'). No la borra."""
        r = self._req("PUT", f"/cards/{card_id}", {"closed": "true"})
        time.sleep(PAUSA_ESCRITURA)
        return r


# ---------------------------------------------------------------------------
# Utilidades sobre las listas del tablero
# ---------------------------------------------------------------------------
def buscar_lista(listas: list, clave: str) -> str:
    """Id de la primera lista cuyo nombre CONTENGA la palabra clave (normalizada)."""
    k = normalizar(clave)
    for lst in listas:
        if k and k in normalizar(lst["name"]):
            return lst["id"]
    return None


def nombre_de_lista(listas: list, list_id: str) -> str:
    for lst in listas:
        if lst["id"] == list_id:
            return lst["name"]
    return "(desconocida)"


# ---------------------------------------------------------------------------
# Plantillas
# ---------------------------------------------------------------------------
# Marca que declara plantilla a una tarjeta. Tolera "PLANTILLA", "PLANTILA"
# (con una sola L) y sus plurales, ya normalizados a MAYUSCULAS sin simbolos.
MARCA_PLANTILLA = re.compile(r"\bPLANTIL[A-Z]*\b")


def es_plantilla(nombre: str) -> bool:
    """True si el NOMBRE de la tarjeta la declara plantilla."""
    return bool(MARCA_PLANTILLA.search(normalizar(nombre)))


def actividad_de_plantilla(nombre: str) -> str:
    """Nombre de la actividad que representa una plantilla, sin la marca.

    "PLANTILLA - ACERO INFERIOR EN ZAPATAS"  ->  "ACERO INFERIOR EN ZAPATAS"
    """
    limpio = MARCA_PLANTILLA.sub(" ", normalizar(nombre))
    return re.sub(r"\s+", " ", limpio).strip()


def construir_indice_plantillas(cards: list, listas: list = None,
                                clave_plantillas: str = None) -> dict:
    """{actividad_normalizada: {'id':..., 'desc':..., 'nombre':...}}

    Una tarjeta cuenta como PLANTILLA si SU PROPIO NOMBRE lo dice. No depende
    del nombre de la lista donde viva: asi una errata en el encabezado de una
    columna no deja fuera a las plantillas que contiene.

    Como apoyo, si se pasan `listas` y `clave_plantillas`, tambien se indexan
    las tarjetas que vivan en una lista marcada aunque su nombre no lo diga.
    """
    ids_lista_plantilla = set()
    if listas and clave_plantillas:
        clave = normalizar(clave_plantillas)
        ids_lista_plantilla = {lst["id"] for lst in listas
                               if clave and clave in normalizar(lst["name"])}

    indice = {}
    for c in cards:
        por_nombre = es_plantilla(c["name"])
        por_lista = c.get("idList") in ids_lista_plantilla
        if not (por_nombre or por_lista):
            continue
        actividad = actividad_de_plantilla(c["name"])
        if actividad:
            indice[actividad] = {
                "id": c["id"],
                "desc": c.get("desc") or "",
                "nombre": c["name"],
            }
    return indice


# ---------------------------------------------------------------------------
# Checklists: pendientes por responsable
# ---------------------------------------------------------------------------
def responsable_de_checklist(nombre_checklist: str, responsables: dict) -> str:
    """Codigo del responsable dueno de un checklist, por su nombre.

    Los checklists de cada plantilla se llaman "ESTRUCTURAS - ...",
    "CALIDAD - ...", "CAMPO - ...". Devuelve 'EST', 'CAL', 'CAMP'... o None.
    """
    texto = normalizar(nombre_checklist)
    for codigo, datos in responsables.items():
        for clave in datos.get("claves") or []:
            if normalizar(clave) in texto:
                return codigo
    return None


def contar_checks(card: dict, responsables: dict) -> dict:
    """Cuenta los items de checklist de una tarjeta.

    Devuelve {'total':n, 'pendientes':n, 'por_responsable': {codigo: pendientes},
    'sin_responsable': n}
    """
    total = pendientes = 0
    por_responsable = {c: 0 for c in responsables}
    sin_dueno = 0

    for cl in card.get("checklists") or []:
        codigo = responsable_de_checklist(cl.get("name", ""), responsables)
        for item in cl.get("checkItems") or []:
            total += 1
            if str(item.get("state", "")).lower() != "complete":
                pendientes += 1
                if codigo:
                    por_responsable[codigo] += 1
                else:
                    sin_dueno += 1

    return {"total": total, "pendientes": pendientes,
            "por_responsable": por_responsable, "sin_responsable": sin_dueno}


def checklist_completo(card: dict) -> bool:
    """True si la tarjeta tiene al menos un item y TODOS estan marcados."""
    items = [i for cl in (card.get("checklists") or [])
             for i in cl.get("checkItems") or []]
    if not items:
        return False
    return all(str(i.get("state", "")).lower() == "complete" for i in items)

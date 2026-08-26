#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 CIERRE DEL DÍA — mueve tarjetas por su estado.
============================================================================

QUÉ HACE
--------
Recorre las listas "del día" (Acero, Encofrado, Concreto, Varios) y En
Ejecución, y al cierre de la jornada:
  • Las tarjetas marcadas como COMPLETAS  -> 🎯 T. TERMINADAS
  • Las tarjetas NO completadas           -> 🆘 T. NO CUMPLIDAS

Así, al día siguiente, las listas del día quedan limpias para las tarjetas
nuevas, y queda registro de qué se cumplió y qué no.

NOTA IMPORTANTE
---------------
Esta misma regla también puede hacerse SIN código con Butler (la
automatización nativa y gratuita de Trello), que se dispara sola cada noche.
Ver el README, sección "Butler". Este script es la alternativa por código
por si prefieres controlarlo tú desde Google Cloud junto al de creación.

USO
---
    python cierre_del_dia.py
    python cierre_del_dia.py --dry-run
============================================================================
"""

import argparse
import sys
import time

import requests

import settings as config  # settings resuelve entorno (GitHub Secrets) o config.py local


class Trello:
    BASE = "https://api.trello.com/1"

    def __init__(self, key, token):
        self.auth = {"key": key, "token": token}

    def _get(self, path, params=None):
        p = dict(self.auth)
        if params:
            p.update(params)
        r = requests.get(f"{self.BASE}{path}", params=p, timeout=30)
        r.raise_for_status()
        return r.json()

    def _put(self, path, params):
        p = dict(self.auth)
        p.update(params)
        r = requests.put(f"{self.BASE}{path}", params=p, timeout=30)
        r.raise_for_status()
        return r.json()

    def listas(self, board_id):
        return {l["name"]: l["id"] for l in self._get(f"/boards/{board_id}/lists")}

    def tarjetas_de_lista(self, list_id):
        return self._get(f"/lists/{list_id}/cards",
                         {"fields": "name,dueComplete"})

    def mover(self, card_id, list_id):
        return self._put(f"/cards/{card_id}", {"idList": list_id})


# Listas "del día" que se vacían al cierre
LISTAS_DEL_DIA = [
    "🟦 ACERO — DÍA",
    "🟧 ENCOFRADO — DÍA",
    "🟩 CONCRETO Y MORTERO — DÍA",
    "⬛ VARIOS — DÍA (trazo · excavación · relleno)",
    "🔄 EN EJECUCIÓN",
]
LISTA_TERMINADAS = "🎯 T. TERMINADAS"
LISTA_NO_CUMPLIDAS = "🆘 T. NO CUMPLIDAS"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tr = Trello(config.TRELLO_KEY, config.TRELLO_TOKEN)
    listas = tr.listas(config.BOARD_ID)

    id_terminadas = listas[LISTA_TERMINADAS]
    id_no_cumplidas = listas[LISTA_NO_CUMPLIDAS]

    a_terminadas, a_no_cumplidas = 0, 0
    for nombre_lista in LISTAS_DEL_DIA:
        lid = listas.get(nombre_lista)
        if not lid:
            continue
        for card in tr.tarjetas_de_lista(lid):
            destino = id_terminadas if card.get("dueComplete") else id_no_cumplidas
            etiqueta = "TERMINADA" if card.get("dueComplete") else "NO CUMPLIDA"
            print(f"  → [{etiqueta:11}] {card['name']}")
            if not args.dry_run:
                tr.mover(card["id"], destino)
                time.sleep(0.15)
            if card.get("dueComplete"):
                a_terminadas += 1
            else:
                a_no_cumplidas += 1

    modo = " (DRY-RUN, no se movió nada)" if args.dry_run else ""
    print(f"\n=== Cierre: {a_terminadas} → Terminadas, "
          f"{a_no_cumplidas} → No cumplidas.{modo} ===")


if __name__ == "__main__":
    main()

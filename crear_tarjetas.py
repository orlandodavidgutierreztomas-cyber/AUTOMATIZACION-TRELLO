#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atajo: permite escribir `python crear_tarjetas.py ...` como antes.

La logica vive en trello_auto/crear_tarjetas.py.
"""
import sys

from trello_auto.crear_tarjetas import main

if __name__ == "__main__":
    sys.exit(main())

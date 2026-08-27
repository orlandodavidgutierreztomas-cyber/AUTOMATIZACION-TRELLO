#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atajo: permite escribir `python cierre_del_dia.py ...` como antes.

La logica vive en trello_auto/cierre_del_dia.py.
"""
import sys

from trello_auto.cierre_del_dia import main

if __name__ == "__main__":
    sys.exit(main())

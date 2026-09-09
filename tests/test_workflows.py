# -*- coding: utf-8 -*-
"""Pruebas de los botones de GitHub Actions.

No corren nada en GitHub: leen los .yml y comprueban que esten bien armados.
Nacieron de un fallo real: el boton de "Reubicar" corria el script sin haber
instalado las dependencias, y reventaba en el import de requests.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.yml"))

# Modulos que necesitan una libreria de fuera (requests, pandas, openpyxl).
# Lo que solo usa la libreria estandar puede correr sin instalar nada.
EXTERNAS = ("requests", "pandas", "openpyxl")


def _modulos_de(texto: str) -> set:
    return set(re.findall(r"python -m trello_auto\.(\w+)", texto))


def _necesita_libreria_externa(modulo: str, vistos=None) -> bool:
    """True si el modulo, o algo de lo que importa, usa una libreria de fuera."""
    vistos = vistos if vistos is not None else set()
    if modulo in vistos:
        return False
    vistos.add(modulo)

    ruta = RAIZ / "trello_auto" / f"{modulo}.py"
    if not ruta.exists():
        return False
    codigo = ruta.read_text(encoding="utf-8")
    if any(re.search(rf"^\s*import {lib}\b|^\s*from {lib}\b", codigo, re.M)
           for lib in EXTERNAS):
        return True
    # Los import del propio paquete: "from .x import" y "from . import a, b"
    propios = set(re.findall(r"^\s*from \.(\w+) import", codigo, re.M))
    for grupo in re.findall(r"^\s*from \. import (.+)$", codigo, re.M):
        propios.update(p.strip() for p in grupo.split(","))
    return any(_necesita_libreria_externa(m, vistos) for m in propios)


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_el_workflow_instala_lo_que_su_script_necesita(wf):
    texto = wf.read_text(encoding="utf-8")
    modulos = {m for m in _modulos_de(texto) if _necesita_libreria_externa(m)}
    if not modulos:
        return
    assert "pip install -r requirements.txt" in texto, (
        f"{wf.name} corre {sorted(modulos)}, que necesita una libreria de "
        f"fuera, pero nunca instala requirements.txt")


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_el_workflow_hace_checkout_antes_de_correr_python(wf):
    texto = wf.read_text(encoding="utf-8")
    if not _modulos_de(texto):
        return
    assert "actions/checkout" in texto, f"{wf.name} corre python sin checkout"


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_el_workflow_llama_a_modulos_que_existen(wf):
    for modulo in _modulos_de(wf.read_text(encoding="utf-8")):
        assert (RAIZ / "trello_auto" / f"{modulo}.py").exists(), (
            f"{wf.name} llama a trello_auto.{modulo}, que no existe")


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_el_workflow_que_toca_trello_recibe_las_credenciales(wf):
    if wf.name == "ci.yml":
        return  # el CI solo se revisa a si mismo, en seco y sin red
    texto = wf.read_text(encoding="utf-8")
    modulos = _modulos_de(texto)
    # revisar y configurar no hablan con Trello: solo leen o escriben archivos
    if not modulos - {"revisar", "configurar"}:
        return
    for secreto in ("secrets.TRELLO_KEY", "secrets.TRELLO_TOKEN"):
        assert secreto in texto, f"{wf.name} no recibe {secreto}"

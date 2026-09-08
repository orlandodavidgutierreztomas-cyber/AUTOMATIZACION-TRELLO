# -*- coding: utf-8 -*-
"""
============================================================================
 ESTADO DEL TABLERO — que hace cada lista, y cuales no hace nada.
============================================================================

Lee el tablero ENTERO y dice, lista por lista, que papel juega en la
automatizacion y cuantas tarjetas tiene.

Para que sirve: cuando se reorganiza el tablero -se parte el cierre en tres,
se renombra una columna, se prueba algo- es facil quedarse con listas que ya
no toca nadie. Sus tarjetas se quedan ahi para siempre, sin que ningun robot
las evalue, y nada lo delata. Esta pagina las senala.

Tambien avisa al reves: si la configuracion nombra una lista que no existe en
el tablero, aparece como FALTA, antes de que un robot se pare a mitad de una
corrida.
============================================================================
"""

from __future__ import annotations

from . import ajustes
from .trello import buscar_lista, es_plantilla, normalizar


def papeles_configurados() -> list:
    """[(clave_de_lista, papel)] de todo lo que la automatizacion usa."""
    papeles = [(ajustes.LISTA_ESPERA, "Espera · donde nacen las tarjetas de manana")]
    vistas = set()
    for familia in ajustes.FAMILIAS:
        lista = ajustes.lista_de_familia(familia)
        if lista and lista not in vistas:
            vistas.add(lista)
            familias = [f for f in ajustes.FAMILIAS
                        if ajustes.lista_de_familia(f) == lista]
            papeles.append((lista, "Trabajo del dia · " + ", ".join(familias)))
    for lista in ajustes.listas_de_cierre():
        familias = [f for f in ajustes.FAMILIAS
                    if ajustes.lista_cierre_de_familia(f) == lista]
        detalle = ", ".join(familias) if familias else "todas"
        papeles.append((lista, "Margen de gracia · " + detalle))
    papeles.append((ajustes.LISTA_CULMINADO, "Culminado · lo que cumplio"))
    papeles.append((ajustes.LISTA_NO_CUMPLIDAS, "No cumplidas · lo que no cumplio"))
    papeles.append((ajustes.LISTA_PLANTILLAS, "Plantillas · el molde de cada actividad"))
    return papeles


def analizar(listas: list, cards: list) -> dict:
    """Cruza el tablero real con la configuracion.

    Devuelve {'filas': [...], 'faltan': [...]}. Cada fila lleva el nombre real
    de la lista, cuantas tarjetas tiene y que papel juega (o ninguno).
    """
    por_lista = {}
    for c in cards:
        por_lista[c.get("idList")] = por_lista.get(c.get("idList"), 0) + 1

    # Que lista real cubre cada papel configurado
    papel_de = {}
    faltan = []
    for clave, papel in papeles_configurados():
        lid = buscar_lista(listas, clave)
        if lid:
            papel_de.setdefault(lid, []).append(papel)
        else:
            faltan.append((clave, papel))

    filas = []
    for lst in listas:
        papeles = papel_de.get(lst["id"], [])
        n = por_lista.get(lst["id"], 0)
        # Las listas de plantillas viejas se reconocen por su contenido
        if not papeles:
            tiene_plantillas = any(
                c.get("idList") == lst["id"] and es_plantilla(c.get("name", ""))
                for c in cards)
            if tiene_plantillas or "PLANTIL" in normalizar(lst["name"]):
                papeles = ["Plantillas · (lista antigua, sigue sirviendo)"]
        filas.append({
            "nombre": lst["name"],
            "tarjetas": n,
            "papeles": papeles,
            "sin_uso": not papeles,
        })
    return {"filas": filas, "faltan": faltan}


def generar_vista(listas: list, cards: list) -> str:
    """Escribe docs/tablero.html con el estado del tablero."""
    from .web import e, escribir, kpi, pagina

    datos = analizar(listas, cards)
    filas = datos["filas"]
    faltan = datos["faltan"]

    sin_uso = [f for f in filas if f["sin_uso"]]
    atrapadas = sum(f["tarjetas"] for f in sin_uso)

    kpis = (
        kpi(len(filas), "Listas en el tablero", f"{len(cards)} tarjetas abiertas")
        + kpi(len(filas) - len(sin_uso), "Con papel en la automatizacion",
              "alguna robot las toca")
        + kpi(len(sin_uso), "Sin uso", "ningun robot las mira",
              "aviso" if sin_uso else "ok")
        + kpi(atrapadas, "Tarjetas atrapadas", "en listas sin uso",
              "alerta" if atrapadas else "ok")
    )

    avisos = []
    if faltan:
        detalle = "".join(
            f"<li><b>{e(clave)}</b> — {e(papel)}</li>" for clave, papel in faltan)
        avisos.append(
            '<div class="nota"><b>Faltan listas en el tablero.</b> La '
            'configuracion las nombra pero no existen, asi que el robot que '
            f'las necesite se detendra:<ul>{detalle}</ul>'
            'Crealas en Trello, o corrige <code>configuracion.json</code>.</div>')
    if atrapadas:
        avisos.append(
            f'<div class="nota"><b>Hay {atrapadas} tarjetas en listas que nadie '
            'mira.</b> Ningun robot las va a evaluar ni mover nunca. Sacalas a '
            'una lista con papel, o archiva esa columna en Trello.</div>')

    cuerpo_filas = []
    for f in filas:
        clase = ' class="revisar"' if f["sin_uso"] else ""
        papel = ("<br>".join(e(p) for p in f["papeles"]) if f["papeles"]
                 else '<b>SIN USO</b> — ningun robot la toca')
        cuerpo_filas.append(
            f'<tr{clase}><td class="act">{e(f["nombre"])}</td>'
            f'<td class="n">{f["tarjetas"]}</td><td>{papel}</td></tr>')

    cuerpo = (
        "".join(avisos)
        + f'<div class="rejilla">{kpis}</div>'
        + '<h2>Todas las listas del tablero</h2>'
        + '<div class="tabla-caja"><table><thead><tr>'
        + '<th>Lista</th><th>Tarjetas</th><th>Papel en la automatizacion</th>'
        + f'</tr></thead><tbody>{"".join(cuerpo_filas)}</tbody></table></div>'
    )

    html = pagina(
        "tablero.html",
        f"{ajustes.NOMBRE_OBRA} · estado del tablero",
        "Que hace cada lista, cuantas tarjetas tiene, y cuales no toca nadie",
        cuerpo,
        "Se regenera en cada sincronizacion. Las filas en ambar son listas que "
        "ningun robot mira.",
    )
    ruta = escribir("tablero.html", html)
    print(f"Estado del tablero: {ruta}")
    print(f"  {len(filas)} listas · {len(sin_uso)} sin uso · "
          f"{atrapadas} tarjetas atrapadas")
    for f in sin_uso:
        print(f"     SIN USO: {f['nombre']}  ({f['tarjetas']} tarjetas)")
    for clave, _papel in faltan:
        print(f"     FALTA:   {clave}")
    return ruta

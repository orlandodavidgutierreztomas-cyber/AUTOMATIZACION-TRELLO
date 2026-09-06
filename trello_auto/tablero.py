# -*- coding: utf-8 -*-
"""
============================================================================
 TABLERO — el dashboard web del corte de control.
============================================================================

Escribe `docs/index.html`, la pagina que publica GitHub Pages. Se regenera
en cada corrida del reporte, asi que la URL siempre muestra el ultimo corte
sin que nadie descargue ni suba nada.

Comparte aspecto con la vista del mapeo (ver web.py).
============================================================================
"""

from __future__ import annotations

from datetime import datetime

from . import ajustes
from .web import barras, e, escribir, kpi, pagina


def _tabla(filas: list) -> str:
    if not filas:
        return ('<div class="tabla-caja"><div class="vacio">'
                'No hay tarjetas en este corte.</div></div>')

    codigos = list(ajustes.CODIGOS_RESPONSABLE)
    cabecera = (["Sector", "Actividad", "Familia", "Vence"] + codigos
                + ["Pend.", "Total", "Dias", "Lista", "Estado", ""])
    th = "".join(f"<th>{e(c)}</th>" for c in cabecera)

    cuerpo = []
    for f in sorted(filas, key=lambda x: -x["CLAVE ORDEN"]):
        dias = f["ANTIGUEDAD (dias)"]
        clase_dias = ' class="n vieja"' if dias >= 1 else ' class="n"'
        celdas = [
            f'<td>{e(f["SECTOR / ZONA"])}</td>',
            f'<td class="act">{e(f["ACTIVIDAD"])}</td>',
            f'<td><span class="pill">{e(f["FAMILIA"])}</span></td>',
            f'<td>{e(f["VENCE"])}</td>',
        ]
        celdas += [f'<td class="n">{e(f.get(c)) if f.get(c) else "·"}</td>'
                   for c in codigos]
        celdas += [
            f'<td class="n">{e(f["CHECKS PENDIENTES"])}</td>',
            f'<td class="n">{e(f["TOTAL CHECKS"])}</td>',
            f'<td{clase_dias}>{e(dias)}</td>',
            f'<td>{e(f["LISTA TRELLO"])}</td>',
            f'<td><span class="pill">{e(f["ESTADO"])}</span></td>',
        ]
        enlace = f["LINK TRELLO"]
        celdas.append(
            f'<td><a href="{e(enlace)}" target="_blank" rel="noopener">abrir</a></td>'
            if enlace else "<td></td>")
        cuerpo.append("<tr>" + "".join(celdas) + "</tr>")

    return (f'<div class="tabla-caja"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(cuerpo)}</tbody></table></div>')


def generar(filas: list, corte: datetime, alcance: str) -> str:
    """Escribe el dashboard y devuelve la ruta."""
    n = len(filas)
    pendientes = sum(f["CHECKS PENDIENTES"] for f in filas)
    total = sum(f["TOTAL CHECKS"] for f in filas)
    avance = (1 - pendientes / total) * 100 if total else 0
    completas = sum(1 for f in filas if f["CHECKS PENDIENTES"] == 0)
    atrasadas = sum(1 for f in filas if f["ANTIGUEDAD (dias)"] >= 1)

    kpis = (
        kpi(n, "Tarjetas en el corte", f"{completas} con el checklist completo")
        + kpi(pendientes, "Checks pendientes", f"de {total} en total",
              "alerta" if pendientes else "ok")
        + kpi(f"{avance:.0f}%", "Avance del control", "items de calidad marcados",
              "ok" if avance >= 70 else "aviso")
        + kpi(atrasadas, "Tarjetas atrasadas", "vencieron antes de hoy",
              "alerta" if atrasadas else "ok")
    )

    por_resp = []
    for codigo in ajustes.CODIGOS_RESPONSABLE:
        nombre = ajustes.RESPONSABLES[codigo].get("nombre", codigo)
        por_resp.append((nombre, sum(f.get(codigo, 0) for f in filas)))
    por_resp.sort(key=lambda x: -x[1])

    familias = {}
    for f in filas:
        familias[f["FAMILIA"]] = familias.get(f["FAMILIA"], 0) + f["CHECKS PENDIENTES"]

    rangos = {"Vence hoy": 0, "Vencida 1 dia": 0, "Vencida mas de 1 dia": 0}
    for f in filas:
        d = f["ANTIGUEDAD (dias)"]
        rangos["Vence hoy" if d == 0 else
               "Vencida 1 dia" if d == 1 else "Vencida mas de 1 dia"] += 1

    cuerpo = (
        f'<div class="rejilla">{kpis}</div>'
        '<div class="paneles">'
        f'<div class="tarjeta"><h2>Checks pendientes por responsable</h2>'
        f'{barras(por_resp)}</div>'
        f'<div class="tarjeta"><h2>Checks pendientes por familia</h2>'
        f'{barras(sorted(familias.items(), key=lambda x: -x[1]))}</div>'
        '</div>'
        f'<div class="tarjeta" style="margin-bottom:22px">'
        f'<h2>Antiguedad de las tarjetas</h2>{barras(list(rangos.items()))}</div>'
        f'<h2>Detalle de tarjetas</h2>{_tabla(filas)}'
    )

    html = pagina(
        "index.html",
        f"{ajustes.NOMBRE_OBRA} · control del dia",
        f"Corte del {e(corte.strftime('%d/%m/%Y %H:%M'))} · hora de obra "
        f"({e(ajustes.TZ_OBRA)}) · alcance: {e(alcance)}",
        cuerpo,
        "Se regenera en cada corrida del reporte. Los checks pendientes salen "
        "de los items sin marcar de cada checklist de Trello.",
    )
    return escribir("index.html", html)

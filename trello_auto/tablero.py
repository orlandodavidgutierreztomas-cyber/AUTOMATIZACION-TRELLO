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
from .web import barra_progreso, barras, e, escribir, grafico_linea, kpi, pagina


def _tabla(filas: list) -> str:
    if not filas:
        return ('<div class="tabla-caja"><div class="vacio">'
                'No hay tarjetas en este corte.</div></div>')

    codigos = list(ajustes.CODIGOS_RESPONSABLE)
    cabecera = (["Sector", "Actividad", "Familia", "Vence"] + codigos
                + ["Pend.", "Total", "Dias", "Marcada", "Lista", "Estado", ""])
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
            f'<td class="n">{"✓" if f.get("MARCADA") else "·"}</td>',
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


def _avance_de_obra() -> str:
    """Cuanto lleva la obra frente a lo que el plan decia a estas alturas."""
    from .historico import avance_de_obra

    a = avance_de_obra()
    if not a or not a.get("total_plan"):
        return ""

    desvio = a["desvio"]
    if desvio > 0:
        estado, clase = f"{desvio} tareas por delante del plan", "ok"
    elif desvio < 0:
        estado, clase = f"{abs(desvio)} tareas por detras del plan", "alerta"
    else:
        estado, clase = "al dia con el plan", "ok"

    return (
        '<div class="tarjeta" style="margin-bottom:22px">'
        '<h2>Avance general de obra</h2>'
        + barra_progreso(a["avance_real"],
                         f'Ejecutado · {a["culminadas"]} de {a["total_plan"]} tareas',
                         clase)
        + barra_progreso(a["avance_previsto"],
                         f'Previsto por el plan a dia de hoy · '
                         f'{a["programadas_a_hoy"]} tareas', "")
        + f'<div class="sub" style="margin-top:10px">{e(estado)}</div>'
        + '</div>')


def _tendencias() -> str:
    """Las graficas que solo tienen sentido con varios dias acumulados."""
    from .historico import serie_pendientes, serie_ppc, serie_ppc_semanal

    paneles = []

    diario = serie_ppc(30)
    if diario:
        puntos = [(f"{d:%d/%m}", p) for d, p, _c, _t in diario]
        ultimo = diario[-1]
        paneles.append(
            '<div class="tarjeta"><h2>PPC diario · cumplimiento del plan</h2>'
            + grafico_linea(puntos, "%", meta=85)
            + f'<div class="sub" style="margin-top:8px">Ultimo cierre: '
            f'{ultimo[2]} de {ultimo[3]} tarjetas culminadas '
            f'({ultimo[1]:.0f}%).</div></div>')

    semanal = serie_ppc_semanal(12)
    if len(semanal) >= 2:
        paneles.append(
            '<div class="tarjeta"><h2>PPC semanal</h2>'
            + grafico_linea([(et, p) for et, p, _c, _t in semanal], "%", meta=85)
            + '<div class="sub" style="margin-top:8px">Acumulado de cada semana, '
            'no el promedio de los dias: un dia con 2 tarjetas no puede pesar '
            'lo mismo que uno con 20.</div></div>')

    pendientes = serie_pendientes(20)
    if len(pendientes) >= 2:
        paneles.append(
            '<div class="tarjeta"><h2>Checks pendientes en el tiempo</h2>'
            + grafico_linea([(et, v) for et, v, _n in pendientes])
            + '<div class="sub" style="margin-top:8px">Cada punto es un corte '
            'del reporte. Si la linea baja, el control se esta poniendo al '
            'dia.</div></div>')

    if not paneles:
        return ('<div class="nota">Las graficas de tendencia apareceran solas '
                'en cuanto haya varios dias de datos: el <b>PPC</b> se anota en '
                'cada cierre definitivo, y los <b>checks pendientes</b> en cada '
                'corrida del reporte.</div>')

    return f'<div class="paneles">{"".join(paneles)}</div>'


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
        + _avance_de_obra()
        + _tendencias()
        + '<div class="paneles">'
        + '<div class="tarjeta"><h2>Checks pendientes por responsable</h2>'
        + f'{barras(por_resp)}</div>'
        + '<div class="tarjeta"><h2>Checks pendientes por familia</h2>'
        + f'{barras(sorted(familias.items(), key=lambda x: -x[1]))}</div>'
        + '</div>'
        + '<div class="tarjeta" style="margin-bottom:22px">'
        + f'<h2>Antiguedad de las tarjetas</h2>{barras(list(rangos.items()))}</div>'
        + f'<h2>Detalle de tarjetas</h2>{_tabla(filas)}'
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

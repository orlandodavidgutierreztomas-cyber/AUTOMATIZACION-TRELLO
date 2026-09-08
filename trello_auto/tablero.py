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
from .web import (
    anillo,
    barra_apilada,
    barra_progreso,
    barras,
    color_de,
    e,
    escribir,
    grafico_linea,
    kpi,
    pagina,
)


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


def _cerrada(f: dict) -> bool:
    """Una tarjeta cuenta como cerrada igual que en el cierre: checklist
    completo O marcada como cumplida."""
    return f["CHECKS PENDIENTES"] == 0 or bool(f.get("MARCADA"))


def _estado_del_dia(filas: list) -> str:
    """El anillo de avance mas la composicion del dia, lado a lado."""
    if not filas:
        return ""

    cerradas = [f for f in filas if _cerrada(f)]
    atrasadas = [f for f in filas if not _cerrada(f) and f["ANTIGUEDAD (dias)"] >= 1]
    en_curso = [f for f in filas
                if not _cerrada(f) and f["ANTIGUEDAD (dias)"] < 1]
    ratio = len(cerradas) / len(filas) * 100

    pie = (f"<b>{len(cerradas)}</b> de <b>{len(filas)}</b> tarjetas del corte "
           f"ya estan cerradas, por checklist completo o porque el responsable "
           f"las marco como cumplidas.")

    composicion = barra_apilada([
        ("Cerradas", len(cerradas), "var(--ok)"),
        ("En curso", len(en_curso), "var(--aviso)"),
        ("Atrasadas", len(atrasadas), "var(--alerta)"),
    ])

    return (
        '<div class="paneles">'
        f'<div class="tarjeta"><h2>Avance del dia</h2>'
        f'{anillo(ratio, "cerradas", pie)}</div>'
        f'<div class="tarjeta"><h2>Composicion del corte</h2>{composicion}'
        f'<div class="sub" style="margin-top:14px">Atrasada = vencio antes de '
        f'hoy y sigue sin cerrar.</div></div>'
        '</div>')


def _sin_cerrar(filas: list) -> str:
    """Las que no se han cerrado, que son las que piden accion hoy."""
    pendientes = [f for f in filas if not _cerrada(f)]
    if not pendientes:
        return ('<div class="tarjeta" style="margin-bottom:22px"><div class="limpio">'
                '<div class="marca">✓</div>'
                '<div><b>Todo cerrado.</b></div>'
                '<div class="sub" style="margin-top:6px">No queda ninguna tarjeta '
                'sin cerrar en este corte.</div></div></div>')

    # Las mas atrasadas primero; a igualdad, las que mas checks deben
    pendientes.sort(key=lambda f: (-f["ANTIGUEDAD (dias)"], -f["CHECKS PENDIENTES"]))
    atrasadas = sum(1 for f in pendientes if f["ANTIGUEDAD (dias)"] >= 1)

    filas_html = []
    for f in pendientes[:25]:
        dias = f["ANTIGUEDAD (dias)"]
        if dias >= 2:
            color, texto = "var(--alerta)", f"{dias} dias"
        elif dias == 1:
            color, texto = "var(--serio)", "1 dia"
        else:
            color, texto = "var(--aviso)", "hoy"
        quien = [ajustes.RESPONSABLES[c].get("nombre", c)
                 for c in ajustes.CODIGOS_RESPONSABLE if f.get(c)]
        enlace = f["LINK TRELLO"]
        filas_html.append(
            f'<tr><td>{e(f["SECTOR / ZONA"])}</td>'
            f'<td class="act">{e(f["ACTIVIDAD"])}</td>'
            f'<td><span class="pill" style="border-color:'
            f'{color_de(f["FAMILIA"], list(ajustes.FAMILIAS))}">'
            f'{e(f["FAMILIA"])}</span></td>'
            f'<td><span class="estado" style="color:{color};margin:0">'
            f'<span class="pto" style="background:{color}"></span>{texto}</span></td>'
            f'<td class="n">{e(f["CHECKS PENDIENTES"])}/{e(f["TOTAL CHECKS"])}</td>'
            f'<td>{e(", ".join(quien)) or "—"}</td>'
            + (f'<td><a href="{e(enlace)}" target="_blank" rel="noopener">abrir</a></td>'
               if enlace else "<td></td>")
            + '</tr>')

    resto = ("" if len(pendientes) <= 25 else
             f'<div class="sub" style="margin-top:10px">… y {len(pendientes) - 25} '
             f'mas en la tabla de abajo.</div>')

    return (
        f'<h2>Sin cerrar · {len(pendientes)} tarjetas'
        + (f' · {atrasadas} atrasadas' if atrasadas else '')
        + '</h2>'
        + '<div class="tabla-caja"><table><thead><tr>'
        + '<th>Sector</th><th>Actividad</th><th>Familia</th><th>Antiguedad</th>'
        + '<th>Pend.</th><th>Quien debe marcar</th><th></th>'
        + f'</tr></thead><tbody>{"".join(filas_html)}</tbody></table></div>{resto}'
        + '<div style="height:22px"></div>')


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
            + grafico_linea(puntos, "%", meta=85, color="var(--s1)")
            + f'<div class="sub" style="margin-top:8px">Ultimo cierre: '
            f'{ultimo[2]} de {ultimo[3]} tarjetas culminadas '
            f'({ultimo[1]:.0f}%).</div></div>')

    semanal = serie_ppc_semanal(12)
    if len(semanal) >= 2:
        paneles.append(
            '<div class="tarjeta"><h2>PPC semanal</h2>'
            + grafico_linea([(et, p) for et, p, _c, _t in semanal], "%", meta=85,
                            color="var(--s7)")
            + '<div class="sub" style="margin-top:8px">Acumulado de cada semana, '
            'no el promedio de los dias: un dia con 2 tarjetas no puede pesar '
            'lo mismo que uno con 20.</div></div>')

    pendientes = serie_pendientes(20)
    if len(pendientes) >= 2:
        paneles.append(
            '<div class="tarjeta"><h2>Checks pendientes en el tiempo</h2>'
            + grafico_linea([(et, v) for et, v, _n in pendientes], color="var(--s2)")
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
    atrasadas = sum(1 for f in filas if f["ANTIGUEDAD (dias)"] >= 1)

    kpis = (
        kpi(n, "Tarjetas en el corte",
            f"{sum(1 for f in filas if _cerrada(f))} ya cerradas")
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
        + _estado_del_dia(filas)
        + _avance_de_obra()
        + _tendencias()
        + '<div class="paneles">'
        + '<div class="tarjeta"><h2>Checks pendientes por responsable</h2>'
        + barras(por_resp, {n: color_de(c, list(ajustes.CODIGOS_RESPONSABLE))
                            for c, n in [(c, ajustes.RESPONSABLES[c].get("nombre", c))
                                         for c in ajustes.CODIGOS_RESPONSABLE]})
        + '</div>'
        + '<div class="tarjeta"><h2>Checks pendientes por familia</h2>'
        + barras(sorted(familias.items(), key=lambda x: -x[1]),
                 {f: color_de(f, list(ajustes.FAMILIAS)) for f in familias})
        + '</div>'
        + '</div>'
        + '<div class="tarjeta" style="margin-bottom:22px">'
        + '<h2>Antiguedad de las tarjetas</h2>'
        + barras(list(rangos.items()), {"Vence hoy": "var(--ok)",
                                        "Vencida 1 dia": "var(--serio)",
                                        "Vencida mas de 1 dia": "var(--alerta)"})
        + '</div>'
        + _sin_cerrar(filas)
        + f'<h2>Detalle de todas las tarjetas</h2>{_tabla(filas)}'
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

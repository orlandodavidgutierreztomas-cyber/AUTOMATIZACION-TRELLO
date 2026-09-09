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
    filtro_columna,
    grafico_linea,
    kpi,
    pagina,
    seccion,
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


AMBITOS = [
    ("EN JUEGO", "Control del dia",
     "Lo que esta ahora en las listas del dia: lo programado para hoy mas lo "
     "que el encargado haya adelantado o repetido, sea de la fecha que sea.",
     "var(--s1)"),
    ("POR CERRAR", "Por cerrar",
     "Lo que no cerro al fin de la jornada. Se queda aqui, a la vista, hasta "
     "que se termine o se reprograme: no se archiva como incumplida.",
     "var(--aviso)"),
]


def _resumen_ambito(filas: list, titulo: str) -> str:
    """El anillo y la composicion de un ambito concreto."""
    if not filas:
        return ""
    cerradas = [f for f in filas if _cerrada(f)]
    atrasadas = [f for f in filas if not _cerrada(f) and f["ANTIGUEDAD (dias)"] >= 1]
    en_curso = [f for f in filas
                if not _cerrada(f) and f["ANTIGUEDAD (dias)"] < 1]
    ratio = len(cerradas) / len(filas) * 100

    pie = (f"<b>{len(cerradas)}</b> de <b>{len(filas)}</b> cerradas, por "
           f"checklist completo o porque el responsable las marco como "
           f"cumplidas.")
    composicion = barra_apilada([
        ("Cerradas", len(cerradas), "var(--ok)"),
        ("En curso", len(en_curso), "var(--aviso)"),
        ("Atrasadas", len(atrasadas), "var(--alerta)"),
    ])
    return (
        '<div class="paneles">'
        f'<div class="tarjeta"><h2>Avance · {e(titulo)}</h2>'
        f'{anillo(ratio, "cerradas", pie)}</div>'
        f'<div class="tarjeta"><h2>Composicion</h2>{composicion}'
        '<div class="sub" style="margin-top:14px">Atrasada = vencio antes de '
        'hoy y sigue sin cerrar.</div></div>'
        '</div>')


def _edad(dias: int) -> tuple:
    """(color, texto) de la antiguedad. Rojo para lo que lleva dias parado."""
    if dias >= 2:
        return "var(--alerta)", f"{dias} dias"
    if dias == 1:
        return "var(--serio)", "1 dia"
    return "var(--aviso)", "hoy"


def _dia_mes(vence: str) -> str:
    """'2026-09-08 18:30' -> '08/09'. El año sobra: siempre es el de la obra."""
    try:
        aaaa, mm, dd = vence.split(" ")[0].split("-")
        return f"{dd}/{mm}"
    except (ValueError, AttributeError):
        return ""


def _desglose(f: dict) -> str:
    """Cuantos checks debe cada responsable en esta tarjeta.

    Es lo que se ve al desplegar la fila: en vez de mandar a Trello para
    averiguarlo, el dato esta aqui mismo.
    """
    codigos = list(ajustes.CODIGOS_RESPONSABLE)
    lineas = []
    for codigo in codigos:
        faltan = f.get(codigo) or 0
        if not faltan:
            continue
        nombre = ajustes.RESPONSABLES[codigo].get("nombre", codigo)
        color = color_de(codigo, codigos)
        lineas.append(
            f'<span class="pto" style="background:{color}"></span>'
            f'<span>{e(nombre)}</span><b>{faltan}</b>')
    otros = f.get("OTROS") or 0
    if otros:
        lineas.append('<span class="pto" style="background:var(--suave)"></span>'
                      f'<span>Sin responsable asignado</span><b>{otros}</b>')

    if lineas:
        cuerpo = (f'<div class="quien">{"".join(lineas)}</div>'
                  f'<div class="sub">De {e(f["TOTAL CHECKS"])} items de control, '
                  f'faltan <b>{e(f["CHECKS PENDIENTES"])}</b>. Vence el '
                  f'{e(_dia_mes(f["VENCE"]))}.</div>')
    else:
        cuerpo = ('<div class="listo">Sin checks pendientes: la tarjeta esta '
                  'a la espera de que alguien la marque como cumplida.</div>')

    enlace = f.get("LINK TRELLO")
    boton = (f'<div><a href="{e(enlace)}" target="_blank" rel="noopener">'
             f'Abrir en Trello →</a></div>' if enlace else "")
    return f'<div class="desglose">{cuerpo}{boton}</div>'


def _quienes(nombres: list) -> str:
    """Nombres en la celda, pero sin que la fila se haga kilometrica."""
    if not nombres:
        return "—"
    if len(nombres) <= 2:
        return e(", ".join(nombres))
    return f'{e(", ".join(nombres[:2]))} <span class="sub">+{len(nombres) - 2}</span>'


def _sin_cerrar(filas: list, rotulo: str = "Sin cerrar") -> str:
    """Las que no se han cerrado: la lista de lo que hay que empujar.

    Cada fila se despliega para ver cuantos checks debe cada responsable, y
    la tabla trae filtros por familia, antiguedad y responsable.
    """
    pendientes = [f for f in filas if not _cerrada(f)]
    if not pendientes:
        return ('<div class="tarjeta" style="margin-bottom:22px"><div class="limpio">'
                '<div class="marca">✓</div>'
                '<div><b>Todo cerrado.</b></div>'
                '<div class="sub" style="margin-top:6px">No queda ninguna tarjeta '
                'sin cerrar aqui.</div></div></div>')

    # Las mas atrasadas primero; a igualdad, las que mas checks deben
    pendientes.sort(key=lambda f: (-f["ANTIGUEDAD (dias)"], -f["CHECKS PENDIENTES"]))
    atrasadas = sum(1 for f in pendientes if f["ANTIGUEDAD (dias)"] >= 1)
    codigos = list(ajustes.CODIGOS_RESPONSABLE)

    cuerpo = []
    for f in pendientes:
        dias = f["ANTIGUEDAD (dias)"]
        color, texto = _edad(dias)
        fecha = _dia_mes(f["VENCE"])
        deben = [ajustes.RESPONSABLES[c].get("nombre", c)
                 for c in codigos if f.get(c)]

        cuerpo.append(
            f'<tr class="desplegable" aria-expanded="false" '
            f'data-familia="{e(f["FAMILIA"])}" data-edad="{e(texto)}" '
            f'data-resp="{e("|".join(deben))}">'
            f'<td><span class="flecha">›</span> {e(f["SECTOR / ZONA"])}</td>'
            f'<td class="act">{e(f["ACTIVIDAD"])}</td>'
            f'<td><span class="pill" style="border-color:'
            f'{color_de(f["FAMILIA"], list(ajustes.FAMILIAS))}">'
            f'{e(f["FAMILIA"])}</span></td>'
            f'<td><span class="estado" style="color:{color};margin:0">'
            f'<span class="pto" style="background:{color}"></span>{texto}'
            + (f' <span style="opacity:.75">({e(fecha)})</span>' if fecha else "")
            + '</span></td>'
            f'<td class="n">{e(f["CHECKS PENDIENTES"])}/{e(f["TOTAL CHECKS"])}</td>'
            f'<td>{_quienes(deben)}</td>'
            '</tr>'
            f'<tr class="detalle" hidden><td colspan="6">{_desglose(f)}</td></tr>')

    caja = f"tabla-{abs(hash(rotulo)) % 100000}"
    filtro = filtro_columna("familia", sorted({f["FAMILIA"] for f in pendientes}))

    return (
        f'<h2>{e(rotulo)} · {len(pendientes)} tarjetas'
        + (f' · {atrasadas} atrasadas' if atrasadas else '')
        + '</h2>'
        + f'<div class="bloque-tabla" id="{caja}">'
        + '<div class="tabla-caja"><table><thead><tr>'
        + '<th>Sector</th><th>Actividad</th>'
        + f'<th>Familia{filtro}</th>'
        + '<th>Antiguedad</th><th>Pend.</th><th>Quien debe marcar</th>'
        + f'</tr></thead><tbody>{"".join(cuerpo)}</tbody></table></div>'
        + f'<div class="cuenta">{len(pendientes)} tarjetas</div></div>'
        + '<div class="sub" style="margin-top:6px">Toca una fila para ver '
          'cuantos checks debe cada responsable.</div>'
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
    from .historico import serie_culminadas, serie_pendientes

    paneles = []

    culminadas = serie_culminadas(30)
    if len(culminadas) >= 2:
        paneles.append(
            '<div class="tarjeta"><h2>Tarjetas culminadas por dia</h2>'
            + grafico_linea([(f"{d:%d/%m}", c) for d, c in culminadas],
                            color="var(--s1)")
            + f'<div class="sub" style="margin-top:8px">Ultimo cierre: '
            f'{culminadas[-1][1]} tarjetas culminadas. Acumulado de '
            f'{sum(c for _d, c in culminadas)} en los ultimos '
            f'{len(culminadas)} dias de cierre.</div></div>')

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
                'en cuanto haya varios dias de datos: las <b>culminadas</b> se '
                'anotan en cada cierre definitivo, y los <b>checks '
                'pendientes</b> en cada corrida del reporte.</div>')

    return f'<div class="paneles">{"".join(paneles)}</div>'


def generar(filas: list, corte: datetime, alcance: str) -> str:
    """Escribe el dashboard y devuelve la ruta.

    El orden de la pagina va de lo general a lo concreto, y luego por ambito:
      1. Los cuatro numeros de cabecera, en orden de lectura natural.
      2. Reparto entre ambitos.
      3. CONTROL DEL DIA — lo que esta en juego ahora.
      4. POR CERRAR — lo que quedo abierto y hay que reprogramar.
      5. CONTROL GENERAL — avance de obra, tendencias y desgloses.
    """
    n = len(filas)
    cerradas = [f for f in filas if _cerrada(f)]
    sin_cerrar = [f for f in filas if not _cerrada(f)]
    atrasadas = [f for f in sin_cerrar if f["ANTIGUEDAD (dias)"] >= 1]
    pendientes = sum(f["CHECKS PENDIENTES"] for f in filas)
    total = sum(f["TOTAL CHECKS"] for f in filas)

    # 1. Cabecera: cuantas hay -> cuantas cerradas -> cuantas faltan -> cuantas
    #    van tarde. Se lee de izquierda a derecha como una frase.
    kpis = (
        kpi(n, "Tarjetas abiertas", "en todo el corte")
        + kpi(len(cerradas), "Cerradas",
              f"{len(cerradas) / n * 100:.0f}% del corte" if n else "",
              "ok" if n and len(cerradas) == n else "")
        + kpi(len(sin_cerrar), "Sin cerrar",
              f"{pendientes} checks pendientes de {total}",
              "aviso" if sin_cerrar else "ok")
        + kpi(len(atrasadas), "Atrasadas", "vencieron antes de hoy",
              "alerta" if atrasadas else "ok")
    )

    # 2. Como se reparten entre los tres ambitos
    por_ambito = {clave: [f for f in filas if f.get("ESTADO") == clave]
                  for clave, _t, _q, _c in AMBITOS}
    reparto = barra_apilada([
        (titulo, len(por_ambito[clave]), color)
        for clave, titulo, _q, color in AMBITOS])

    cuerpo = [f'<div class="rejilla">{kpis}</div>']
    if reparto:
        cuerpo.append(
            '<div class="tarjeta" style="margin-bottom:22px">'
            '<h2>Donde esta cada tarjeta</h2>' + reparto + '</div>')

    # 3, 4 y 5. Un bloque por ambito, solo si tiene tarjetas
    for clave, titulo, que_es, color in AMBITOS:
        del_ambito = por_ambito[clave]
        if not del_ambito:
            continue
        cuerpo.append(seccion(titulo, que_es, f"{len(del_ambito)} tarjetas", color))
        cuerpo.append(_resumen_ambito(del_ambito, titulo))
        cuerpo.append(_sin_cerrar(del_ambito, f"Sin cerrar · {titulo}"))

    # 6. Lo general
    cuerpo.append(seccion(
        "Control general",
        "El acumulado de la obra y la evolucion en el tiempo, sin separar por "
        "ambito."))
    cuerpo.append(_avance_de_obra())
    cuerpo.append(_tendencias())

    por_resp = []
    for codigo in ajustes.CODIGOS_RESPONSABLE:
        nombre = ajustes.RESPONSABLES[codigo].get("nombre", codigo)
        por_resp.append((nombre, sum(f.get(codigo, 0) for f in filas)))
    por_resp.sort(key=lambda x: -x[1])
    colores_resp = {ajustes.RESPONSABLES[c].get("nombre", c):
                    color_de(c, list(ajustes.CODIGOS_RESPONSABLE))
                    for c in ajustes.CODIGOS_RESPONSABLE}

    familias = {}
    sectores = {}
    for f in filas:
        familias[f["FAMILIA"]] = familias.get(f["FAMILIA"], 0) + f["CHECKS PENDIENTES"]
        s = f["SECTOR / ZONA"] or "?"
        sectores[s] = sectores.get(s, 0) + f["CHECKS PENDIENTES"]
    top_sectores = sorted(sectores.items(), key=lambda x: -x[1])[:10]

    rangos = {"Vence hoy": 0, "Vencida 1 dia": 0, "Vencida mas de 1 dia": 0}
    for f in filas:
        d = f["ANTIGUEDAD (dias)"]
        rangos["Vence hoy" if d == 0 else
               "Vencida 1 dia" if d == 1 else "Vencida mas de 1 dia"] += 1

    cuerpo.append(
        '<div class="paneles">'
        + '<div class="tarjeta"><h2>Checks pendientes por responsable</h2>'
        + barras(por_resp, colores_resp)
        + '<div class="sub" style="margin-top:10px">Quien concentra el trabajo '
          'de control que falta.</div></div>'
        + '<div class="tarjeta"><h2>Checks pendientes por familia</h2>'
        + barras(sorted(familias.items(), key=lambda x: -x[1]),
                 {f: color_de(f, list(ajustes.FAMILIAS)) for f in familias})
        + '</div>'
        + '<div class="tarjeta"><h2>Sectores con mas pendiente</h2>'
        + barras(top_sectores)
        + '<div class="sub" style="margin-top:10px">Los diez frentes donde se '
          'acumula el control sin cerrar.</div></div>'
        + '<div class="tarjeta"><h2>Antiguedad de las tarjetas</h2>'
        + barras(list(rangos.items()), {"Vence hoy": "var(--ok)",
                                        "Vencida 1 dia": "var(--serio)",
                                        "Vencida mas de 1 dia": "var(--alerta)"})
        + '</div>'
        + '</div>')

    cuerpo.append(f'<h2>Detalle de todas las tarjetas</h2>{_tabla(filas)}')

    html = pagina(
        "index.html",
        f"{ajustes.NOMBRE_OBRA} · control del dia",
        f"Corte del {e(corte.strftime('%d/%m/%Y %H:%M'))} · hora de obra "
        f"({e(ajustes.TZ_OBRA)}) · alcance: {e(alcance)}",
        "".join(cuerpo),
        "Se regenera en cada corrida del reporte. Una tarjeta cuenta como "
        "cerrada igual que en el cierre: checklist completo o marcada como "
        "cumplida.",
    )
    return escribir("index.html", html)

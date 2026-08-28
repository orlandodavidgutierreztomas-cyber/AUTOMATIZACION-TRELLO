# -*- coding: utf-8 -*-
"""
============================================================================
 TABLERO — genera el dashboard web a partir del corte de control.
============================================================================

Escribe `dashboard/index.html`: una pagina AUTOCONTENIDA (los datos van
dentro del propio archivo, no pide nada por internet) con los indicadores
del corte.

Por que autocontenida:
  - Se puede publicar en GitHub Pages y verla desde el celular.
  - Se puede descargar y abrir sin conexion; funciona igual.
  - Se puede pasar a otra persona por correo y la ve tal cual.
  - Si el repositorio pasa a privado, el archivo descargado sigue sirviendo.

No sustituye al Excel: el Excel es para analizar y cruzar; esta pagina es
para mirar de un vistazo como va el dia.
============================================================================
"""

from __future__ import annotations

import html
import os
from datetime import datetime

from . import ajustes

PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
  :root {{
    --fondo:#f5f6f8; --panel:#ffffff; --borde:#e3e6ea; --texto:#1b2733;
    --suave:#65727f; --acento:#1f4e79; --ok:#1e7a4b; --alerta:#b3261e;
    --aviso:#b06a00; --barra:#dfe4ea;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --fondo:#12161b; --panel:#1a2027; --borde:#2b333d; --texto:#e7ecf2;
      --suave:#9aa7b4; --acento:#7fb3e8; --ok:#5cc98d; --alerta:#ff8a80;
      --aviso:#f0b45e; --barra:#2b333d;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; padding:24px; background:var(--fondo); color:var(--texto);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  }}
  .envoltura {{ max-width:1200px; margin:0 auto; }}
  header {{ margin-bottom:22px; }}
  h1 {{ font-size:22px; margin:0 0 4px; letter-spacing:-.01em; }}
  .sub {{ color:var(--suave); font-size:13.5px; }}
  .rejilla {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); margin-bottom:22px; }}
  .tarjeta {{ background:var(--panel); border:1px solid var(--borde); border-radius:10px; padding:16px 18px; }}
  .kpi .n {{ font-size:30px; font-weight:650; letter-spacing:-.02em; }}
  .kpi .r {{ color:var(--suave); font-size:12.5px; text-transform:uppercase; letter-spacing:.05em; margin-top:2px; }}
  .kpi .pie {{ font-size:12.5px; color:var(--suave); margin-top:6px; }}
  .alerta .n {{ color:var(--alerta); }} .ok .n {{ color:var(--ok); }} .aviso .n {{ color:var(--aviso); }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.06em; color:var(--suave);
       margin:0 0 14px; font-weight:600; }}
  .paneles {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); margin-bottom:22px; }}
  .fila {{ display:grid; grid-template-columns:104px 1fr 46px; align-items:center; gap:10px; margin-bottom:9px; font-size:13.5px; }}
  .pista {{ background:var(--barra); border-radius:4px; height:9px; overflow:hidden; }}
  .relleno {{ height:100%; border-radius:4px; background:var(--acento); }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; color:var(--suave); }}
  .tabla-caja {{ background:var(--panel); border:1px solid var(--borde); border-radius:10px; overflow-x:auto; }}
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
  th,td {{ padding:9px 12px; text-align:left; border-bottom:1px solid var(--borde); white-space:nowrap; }}
  th {{ color:var(--suave); font-weight:600; font-size:12px; text-transform:uppercase;
        letter-spacing:.04em; position:sticky; top:0; background:var(--panel); }}
  tr:last-child td {{ border-bottom:none; }}
  td.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .act {{ white-space:normal; min-width:260px; }}
  .pill {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:11.5px;
           border:1px solid var(--borde); color:var(--suave); }}
  .vieja {{ color:var(--alerta); font-weight:600; }}
  a {{ color:var(--acento); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  footer {{ margin-top:22px; color:var(--suave); font-size:12.5px; }}
  .vacio {{ padding:40px; text-align:center; color:var(--suave); }}
</style>
</head>
<body>
<div class="envoltura">
<header>
  <h1>{obra}</h1>
  <div class="sub">Corte del {corte} · hora de obra ({tz}) · alcance: {alcance}</div>
</header>

<div class="rejilla">{kpis}</div>

<div class="paneles">
  <div class="tarjeta">
    <h2>Checks pendientes por responsable</h2>
    {por_responsable}
  </div>
  <div class="tarjeta">
    <h2>Checks pendientes por familia</h2>
    {por_familia}
  </div>
</div>

<div class="tarjeta" style="margin-bottom:22px">
  <h2>Antiguedad de las tarjetas</h2>
  {antiguedad}
</div>

<h2>Detalle de tarjetas</h2>
<div class="tabla-caja">{tabla}</div>

<footer>
  Generado automaticamente el {generado}. Los checks pendientes salen de los
  items sin marcar de cada checklist de Trello.
</footer>
</div>
</body>
</html>
"""


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _kpi(valor, rotulo, pie="", clase="") -> str:
    pie_html = f'<div class="pie">{_e(pie)}</div>' if pie else ""
    return (f'<div class="tarjeta kpi {clase}"><div class="n">{_e(valor)}</div>'
            f'<div class="r">{_e(rotulo)}</div>{pie_html}</div>')


def _barras(pares: list) -> str:
    """pares: [(rotulo, valor)] ya ordenado. Devuelve barras horizontales."""
    pares = [(r, v) for r, v in pares if v]
    if not pares:
        return '<div class="sub">Sin pendientes.</div>'
    tope = max(v for _, v in pares)
    filas = []
    for rotulo, valor in pares:
        ancho = round(valor / tope * 100, 1) if tope else 0
        filas.append(
            f'<div class="fila"><span>{_e(rotulo)}</span>'
            f'<span class="pista"><span class="relleno" style="width:{ancho}%"></span></span>'
            f'<span class="num">{valor}</span></div>')
    return "".join(filas)


def _tabla(filas: list) -> str:
    if not filas:
        return '<div class="vacio">No hay tarjetas en este corte.</div>'

    codigos = list(ajustes.CODIGOS_RESPONSABLE)
    cabecera = (["Sector", "Actividad", "Familia", "Vence"] + codigos
                + ["Pend.", "Total", "Dias", "Lista", "Estado"])
    th = "".join(f"<th>{_e(c)}</th>" for c in cabecera) + "<th></th>"

    cuerpo = []
    for f in sorted(filas, key=lambda x: -x["CLAVE ORDEN"]):
        dias = f["ANTIGUEDAD (dias)"]
        clase_dias = ' class="n vieja"' if dias >= 1 else ' class="n"'
        celdas = [
            f'<td>{_e(f["SECTOR / ZONA"])}</td>',
            f'<td class="act">{_e(f["ACTIVIDAD"])}</td>',
            f'<td><span class="pill">{_e(f["FAMILIA"])}</span></td>',
            f'<td>{_e(f["VENCE"])}</td>',
        ]
        celdas += [f'<td class="n">{_e(f.get(c, 0)) if f.get(c) else "·"}</td>'
                   for c in codigos]
        celdas += [
            f'<td class="n">{_e(f["CHECKS PENDIENTES"])}</td>',
            f'<td class="n">{_e(f["TOTAL CHECKS"])}</td>',
            f'<td{clase_dias}>{_e(dias)}</td>',
            f'<td>{_e(f["LISTA TRELLO"])}</td>',
            f'<td><span class="pill">{_e(f["ESTADO"])}</span></td>',
        ]
        enlace = f['LINK TRELLO']
        celdas.append(f'<td><a href="{_e(enlace)}" target="_blank" rel="noopener">abrir</a></td>'
                      if enlace else "<td></td>")
        cuerpo.append("<tr>" + "".join(celdas) + "</tr>")

    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(cuerpo)}</tbody></table>"


def generar(filas: list, corte: datetime, alcance: str, ruta_salida) -> str:
    """Escribe el dashboard HTML y devuelve la ruta."""
    n = len(filas)
    pendientes = sum(f["CHECKS PENDIENTES"] for f in filas)
    total = sum(f["TOTAL CHECKS"] for f in filas)
    avance = (1 - pendientes / total) * 100 if total else 0
    listas_ok = sum(1 for f in filas if f["CHECKS PENDIENTES"] == 0)
    atrasadas = sum(1 for f in filas if f["ANTIGUEDAD (dias)"] >= 1)

    kpis = (
        _kpi(n, "Tarjetas en el corte",
             f"{listas_ok} con el checklist completo")
        + _kpi(pendientes, "Checks pendientes", f"de {total} en total",
               "alerta" if pendientes else "ok")
        + _kpi(f"{avance:.0f}%", "Avance del control",
               "items de calidad ya marcados", "ok" if avance >= 70 else "aviso")
        + _kpi(atrasadas, "Tarjetas atrasadas", "vencieron antes de hoy",
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
    por_fam = sorted(familias.items(), key=lambda x: -x[1])

    rangos = {"Vence hoy (0 dias)": 0, "Vencida 1 dia": 0, "Vencida mas de 1 dia": 0}
    for f in filas:
        d = f["ANTIGUEDAD (dias)"]
        clave = ("Vence hoy (0 dias)" if d == 0
                 else "Vencida 1 dia" if d == 1 else "Vencida mas de 1 dia")
        rangos[clave] += 1

    pagina = PLANTILLA.format(
        titulo=_e(f"Control diario · {ajustes.NOMBRE_OBRA}"),
        obra=_e(ajustes.NOMBRE_OBRA),
        corte=_e(corte.strftime("%d/%m/%Y %H:%M")),
        tz=_e(ajustes.TZ_OBRA),
        alcance=_e(alcance),
        kpis=kpis,
        por_responsable=_barras(por_resp),
        por_familia=_barras(por_fam),
        antiguedad=_barras(list(rangos.items())),
        tabla=_tabla(filas),
        generado=_e(corte.strftime("%d/%m/%Y a las %H:%M")),
    )

    os.makedirs(os.path.dirname(ruta_salida) or ".", exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(pagina)
    return str(ruta_salida)

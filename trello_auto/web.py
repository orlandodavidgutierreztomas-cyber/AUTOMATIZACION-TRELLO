# -*- coding: utf-8 -*-
"""
============================================================================
 WEB — el aspecto comun de las paginas publicadas.
============================================================================

Aqui viven el CSS y el esqueleto que comparten el dashboard y la vista del
mapeo, para que las dos se vean como el mismo sistema y no como dos cosas
distintas pegadas.

Las paginas son AUTOCONTENIDAS: los datos van dentro del propio archivo y no
piden nada por internet. Asi se pueden publicar en GitHub Pages, descargar,
mandar por correo o abrir sin conexion, y siguen funcionando aunque el
repositorio pase a privado.
============================================================================
"""

from __future__ import annotations

import html
import os

from . import ajustes

CSS = """
  :root {
    --fondo:#f5f6f8; --panel:#ffffff; --borde:#e3e6ea; --texto:#1b2733;
    --suave:#65727f; --acento:#1f4e79; --ok:#1e7a4b; --alerta:#b3261e;
    --aviso:#b06a00; --barra:#dfe4ea; --ambar:#fff3cd;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --fondo:#12161b; --panel:#1a2027; --borde:#2b333d; --texto:#e7ecf2;
      --suave:#9aa7b4; --acento:#7fb3e8; --ok:#5cc98d; --alerta:#ff8a80;
      --aviso:#f0b45e; --barra:#2b333d; --ambar:#3a2f14;
    }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; padding:24px; background:var(--fondo); color:var(--texto);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  }
  .envoltura { max-width:1240px; margin:0 auto; }
  nav { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:20px; }
  nav a {
    padding:6px 13px; border:1px solid var(--borde); border-radius:999px;
    background:var(--panel); color:var(--suave); text-decoration:none; font-size:13.5px;
  }
  nav a:hover { color:var(--acento); border-color:var(--acento); }
  nav a.activo { background:var(--acento); color:#fff; border-color:var(--acento); }
  header { margin-bottom:22px; }
  h1 { font-size:22px; margin:0 0 4px; letter-spacing:-.01em; }
  .sub { color:var(--suave); font-size:13.5px; }
  .rejilla { display:grid; gap:14px; margin-bottom:22px;
             grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); }
  .tarjeta { background:var(--panel); border:1px solid var(--borde);
             border-radius:10px; padding:16px 18px; }
  .kpi .n { font-size:30px; font-weight:650; letter-spacing:-.02em; }
  .kpi .r { color:var(--suave); font-size:12.5px; text-transform:uppercase;
            letter-spacing:.05em; margin-top:2px; }
  .kpi .pie { font-size:12.5px; color:var(--suave); margin-top:6px; }
  .alerta .n { color:var(--alerta); }
  .ok .n { color:var(--ok); }
  .aviso .n { color:var(--aviso); }
  h2 { font-size:14px; text-transform:uppercase; letter-spacing:.06em;
       color:var(--suave); margin:0 0 14px; font-weight:600; }
  .paneles { display:grid; gap:14px; margin-bottom:22px;
             grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }
  .fila { display:grid; grid-template-columns:112px 1fr 46px; align-items:center;
          gap:10px; margin-bottom:9px; font-size:13.5px; }
  .pista { background:var(--barra); border-radius:4px; height:9px; overflow:hidden; }
  .relleno { height:100%; border-radius:4px; background:var(--acento); }
  .num { text-align:right; font-variant-numeric:tabular-nums; color:var(--suave); }
  .tabla-caja { background:var(--panel); border:1px solid var(--borde);
                border-radius:10px; overflow-x:auto; }
  table { border-collapse:collapse; width:100%; font-size:13.5px; }
  th,td { padding:9px 12px; text-align:left; border-bottom:1px solid var(--borde);
          white-space:nowrap; }
  th { color:var(--suave); font-weight:600; font-size:12px; text-transform:uppercase;
       letter-spacing:.04em; position:sticky; top:0; background:var(--panel); }
  tr:last-child td { border-bottom:none; }
  tr.revisar td { background:var(--ambar); }
  td.n { text-align:right; font-variant-numeric:tabular-nums; }
  .act { white-space:normal; min-width:260px; }
  .pill { display:inline-block; padding:1px 8px; border-radius:999px; font-size:11.5px;
          border:1px solid var(--borde); color:var(--suave); }
  .vieja { color:var(--alerta); font-weight:600; }
  a { color:var(--acento); text-decoration:none; }
  a:hover { text-decoration:underline; }
  footer { margin-top:22px; color:var(--suave); font-size:12.5px; }
  .vacio { padding:40px; text-align:center; color:var(--suave); }
  .nota { background:var(--panel); border:1px solid var(--borde); border-left:3px solid var(--aviso);
          border-radius:8px; padding:14px 16px; margin-bottom:20px; font-size:13.5px; }
"""

PAGINAS = [
    ("index.html", "Control del dia"),
    ("mapeo.html", "Mapeo de actividades"),
    ("tablero.html", "Estado del tablero"),
]


def e(x) -> str:
    """Escapa para HTML. Todo lo que venga de Trello o del Excel pasa por aqui."""
    return html.escape(str(x if x is not None else ""))


def navegacion(actual: str) -> str:
    enlaces = []
    for archivo, rotulo in PAGINAS:
        clase = ' class="activo"' if archivo == actual else ""
        enlaces.append(f'<a href="{archivo}"{clase}>{e(rotulo)}</a>')
    enlaces.append('<a href="DASHBOARD_CONTROL.xlsx">Descargar Excel</a>')
    if ajustes.BOARD_ID:
        enlaces.append(f'<a href="https://trello.com/b/{e(ajustes.BOARD_ID)}" '
                       f'target="_blank" rel="noopener">Abrir el tablero</a>')
    return "<nav>" + "".join(enlaces) + "</nav>"


def kpi(valor, rotulo, pie="", clase="") -> str:
    pie_html = f'<div class="pie">{e(pie)}</div>' if pie else ""
    return (f'<div class="tarjeta kpi {clase}"><div class="n">{e(valor)}</div>'
            f'<div class="r">{e(rotulo)}</div>{pie_html}</div>')


def barras(pares: list) -> str:
    """pares: [(rotulo, valor)] ya ordenado. Barras horizontales."""
    pares = [(r, v) for r, v in pares if v]
    if not pares:
        return '<div class="sub">Nada que mostrar.</div>'
    tope = max(v for _, v in pares)
    filas = []
    for rotulo, valor in pares:
        ancho = round(valor / tope * 100, 1) if tope else 0
        filas.append(
            f'<div class="fila"><span>{e(rotulo)}</span>'
            f'<span class="pista"><span class="relleno" style="width:{ancho}%"></span></span>'
            f'<span class="num">{valor}</span></div>')
    return "".join(filas)


def grafico_linea(puntos: list, unidad: str = "", meta: float = None,
                  alto: int = 190) -> str:
    """Grafica de linea en SVG puro, sin librerias ni internet.

    `puntos` es [(etiqueta, valor)] en orden cronologico. Dibuja la linea, el
    area bajo ella, un punto por dato y una linea de meta opcional (por
    ejemplo el 85% de PPC al que aspira el equipo).

    Se hace a mano en SVG a proposito: la pagina tiene que seguir siendo UN
    archivo que funcione sin conexion y sin cargar nada de fuera.
    """
    if len(puntos) < 2:
        return ('<div class="sub">Hara falta mas de un dato para ver la '
                'tendencia. Vuelve cuando haya corrido un par de veces.</div>')

    ancho, m_izq, m_der, m_arr, m_aba = 720, 42, 12, 14, 30
    valores = [v for _, v in puntos]
    tope = max(valores + ([meta] if meta else []))
    tope = tope * 1.15 if tope else 1
    suelo = 0

    util_x = ancho - m_izq - m_der
    util_y = alto - m_arr - m_aba

    def x(i):
        return m_izq + (i * util_x / (len(puntos) - 1))

    def y(v):
        return m_arr + util_y - ((v - suelo) / (tope - suelo) * util_y)

    # Rejilla horizontal con sus rotulos
    rejilla = []
    for parte in range(5):
        v = tope * parte / 4
        yy = round(y(v), 1)
        rejilla.append(
            f'<line x1="{m_izq}" y1="{yy}" x2="{ancho - m_der}" y2="{yy}" '
            f'stroke="currentColor" stroke-opacity=".12"/>'
            f'<text x="{m_izq - 7}" y="{yy + 3.5}" text-anchor="end" '
            f'font-size="10" fill="currentColor" fill-opacity=".55">{v:.0f}</text>')

    if meta is not None:
        ym = round(y(meta), 1)
        rejilla.append(
            f'<line x1="{m_izq}" y1="{ym}" x2="{ancho - m_der}" y2="{ym}" '
            f'stroke="var(--ok)" stroke-width="1.5" stroke-dasharray="5 4" '
            f'stroke-opacity=".8"/>'
            f'<text x="{ancho - m_der}" y="{ym - 5}" text-anchor="end" '
            f'font-size="10" fill="var(--ok)">meta {meta:.0f}{unidad}</text>')

    linea = " ".join(f"{round(x(i), 1)},{round(y(v), 1)}"
                     for i, (_, v) in enumerate(puntos))
    area = (f"{m_izq},{round(y(suelo), 1)} {linea} "
            f"{round(x(len(puntos) - 1), 1)},{round(y(suelo), 1)}")

    marcas = []
    for i, (etiqueta, v) in enumerate(puntos):
        marcas.append(f'<circle cx="{round(x(i), 1)}" cy="{round(y(v), 1)}" r="3" '
                      f'fill="var(--acento)"><title>{e(etiqueta)}: {v}{e(unidad)}'
                      f'</title></circle>')

    # Rotulos del eje X: solo los que caben, para que no se amontonen
    paso = max(1, len(puntos) // 8)
    ejex = []
    for i, (etiqueta, _) in enumerate(puntos):
        if i % paso == 0 or i == len(puntos) - 1:
            ejex.append(f'<text x="{round(x(i), 1)}" y="{alto - 9}" '
                        f'text-anchor="middle" font-size="10" fill="currentColor" '
                        f'fill-opacity=".55">{e(etiqueta)}</text>')

    return (
        f'<svg viewBox="0 0 {ancho} {alto}" width="100%" height="{alto}" '
        f'role="img" style="display:block">'
        f'{"".join(rejilla)}'
        f'<polygon points="{area}" fill="var(--acento)" fill-opacity=".10"/>'
        f'<polyline points="{linea}" fill="none" stroke="var(--acento)" '
        f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f'{"".join(marcas)}{"".join(ejex)}'
        f'</svg>')


def barra_progreso(porcentaje: float, rotulo: str = "", clase: str = "") -> str:
    """Una barra de avance ancha, para el progreso general de la obra."""
    p = max(0, min(100, porcentaje))
    color = {"ok": "var(--ok)", "alerta": "var(--alerta)",
             "aviso": "var(--aviso)"}.get(clase, "var(--acento)")
    return (f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:13px;margin-bottom:5px">'
            f'<span>{e(rotulo)}</span><span class="num">{p:.1f}%</span></div>'
            f'<div class="pista" style="height:13px">'
            f'<span class="relleno" style="width:{p}%;background:{color}"></span>'
            f'</div></div>')


def pagina(archivo: str, titulo: str, subtitulo: str, cuerpo: str, pie: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="envoltura">
{navegacion(archivo)}
<header>
  <h1>{e(titulo)}</h1>
  <div class="sub">{subtitulo}</div>
</header>
{cuerpo}
<footer>{pie}</footer>
</div>
</body>
</html>
"""


def escribir(archivo: str, contenido: str) -> str:
    ruta = ajustes.CARPETA_WEB / archivo
    os.makedirs(ruta.parent, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return str(ruta)

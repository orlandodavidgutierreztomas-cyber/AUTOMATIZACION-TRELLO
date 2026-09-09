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
    --suave:#65727f; --acento:#2a78d6; --barra:#e3e6ea; --ambar:#fff3cd;
    /* Serie categorica en ORDEN FIJO. Nunca se cicla ni se reordena: el
       color sigue a la familia, no a su posicion en el ranking. */
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
    --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
    /* Estados: reservados, nunca se usan como "serie 9" */
    --ok:#0ca30c; --aviso:#fab219; --serio:#ec835a; --alerta:#d03b3b;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --fondo:#12161b; --panel:#1a2027; --borde:#2b333d; --texto:#e7ecf2;
      --suave:#9aa7b4; --acento:#3987e5; --barra:#2b333d; --ambar:#3a2f14;
      --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
      --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
      --ok:#0ca30c; --aviso:#fab219; --serio:#ec835a; --alerta:#d03b3b;
    }
  }
  /* La eleccion del lector manda sobre la del sistema, en los dos sentidos:
     oscuro en un equipo claro, y claro en un equipo oscuro. */
  :root[data-theme="dark"] {
    --fondo:#12161b; --panel:#1a2027; --borde:#2b333d; --texto:#e7ecf2;
    --suave:#9aa7b4; --acento:#3987e5; --barra:#2b333d; --ambar:#3a2f14;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
    --ok:#0ca30c; --aviso:#fab219; --serio:#ec835a; --alerta:#d03b3b;
  }
  /* Semiclaro: para cuando el equipo esta en oscuro pero se quiere leer las
     hojas con fondo claro, sin el blanco puro que deslumbra. */
  :root[data-theme="suave"] {
    --fondo:#eceae4; --panel:#f7f6f2; --borde:#d9d6cd; --texto:#23231f;
    --suave:#5f5e57; --acento:#2a78d6; --barra:#dedbd2; --ambar:#f6ecc9;
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
    --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
    --ok:#0ca30c; --aviso:#fab219; --serio:#ec835a; --alerta:#d03b3b;
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
  .hero { display:flex; gap:26px; align-items:center; flex-wrap:wrap; }
  .hero .cifra { font-size:52px; font-weight:650; letter-spacing:-.03em; line-height:1; }
  .apilada { display:flex; height:26px; border-radius:6px; overflow:hidden; gap:2px; }
  .apilada span { display:block; }
  .leyenda { display:flex; gap:16px; flex-wrap:wrap; margin-top:12px; font-size:13px;
             color:var(--suave); }
  .leyenda i { display:inline-block; width:10px; height:10px; border-radius:3px;
               margin-right:6px; vertical-align:middle; }
  .estado { display:inline-flex; align-items:center; gap:6px; font-size:13px;
            font-weight:600; margin-top:10px; }
  .estado .pto { width:9px; height:9px; border-radius:50%; display:inline-block; }
  .limpio { text-align:center; padding:30px 20px; }
  .limpio .marca { font-size:34px; line-height:1; margin-bottom:8px; }
  .temas { margin-left:auto; display:flex; gap:4px; align-items:center; }
  .temas button {
    font:inherit; font-size:12.5px; padding:5px 11px; cursor:pointer;
    border:1px solid var(--borde); background:var(--panel); color:var(--suave);
    border-radius:999px;
  }
  .temas button[aria-pressed="true"] {
    background:var(--acento); color:#fff; border-color:var(--acento);
  }
  .seccion { margin:34px 0 18px; padding-top:20px; border-top:2px solid var(--borde); }
  .seccion h3 { font-size:17px; margin:0 0 4px; letter-spacing:-.01em; }
  .seccion .que { color:var(--suave); font-size:13.5px; }
  [hidden] { display:none !important; }
  .bloque-tabla { margin-bottom:4px; }
  /* El filtro vive en la propia cabecera de la columna: un boton pequeno
     que despliega los valores de esa columna. */
  th .filtro { position:relative; display:inline-block; margin-left:5px; }
  th .filtro > button {
    font:inherit; font-size:11px; line-height:1; cursor:pointer; padding:2px 5px;
    border:1px solid var(--borde); border-radius:5px; color:var(--suave);
    background:var(--panel);
  }
  th .filtro > button:hover { color:var(--acento); border-color:var(--acento); }
  th .filtro > button.activo {
    background:var(--acento); color:#fff; border-color:var(--acento);
  }
  th .filtro .menu {
    position:absolute; z-index:5; top:calc(100% + 5px); left:0; min-width:170px;
    background:var(--panel); border:1px solid var(--borde); border-radius:9px;
    padding:5px; box-shadow:0 8px 24px rgba(0,0,0,.16);
  }
  th .filtro .menu button {
    display:block; width:100%; text-align:left; font:inherit; font-size:13px;
    text-transform:none; letter-spacing:0; color:var(--texto); cursor:pointer;
    background:none; border:0; border-radius:6px; padding:6px 9px;
  }
  th .filtro .menu button:hover { background:var(--barra); }
  th .filtro .menu button[aria-checked="true"] { color:var(--acento); font-weight:600; }
  .cuenta { font-size:12.5px; color:var(--suave); margin-top:9px; }
  tr.desplegable { cursor:pointer; }
  tr.desplegable:hover td { background:var(--barra); }
  .flecha { display:inline-block; width:14px; color:var(--suave);
            transition:transform .15s; }
  tr[aria-expanded="true"] .flecha { transform:rotate(90deg); }
  tr.detalle > td { background:var(--fondo); padding:0; }
  .desglose { padding:14px 18px; display:flex; gap:26px; flex-wrap:wrap;
              align-items:flex-start; }
  .desglose .quien { display:grid; grid-template-columns:auto 1fr auto;
                     gap:6px 12px; align-items:center; font-size:13px;
                     min-width:280px; }
  .desglose .quien .pto { width:9px; height:9px; border-radius:3px; }
  .desglose .quien b { font-variant-numeric:tabular-nums; }
  .desglose .listo { color:var(--ok); font-size:13px; }
  .cinta { display:inline-block; font-size:11.5px; font-weight:600; padding:2px 9px;
           border-radius:999px; margin-left:8px; vertical-align:middle; }
"""

PAGINAS = [
    ("index.html", "Control del dia"),
    ("mapeo.html", "Mapeo de actividades"),
    ("tablero.html", "Estado del tablero"),
]


def e(x) -> str:
    """Escapa para HTML. Todo lo que venga de Trello o del Excel pasa por aqui."""
    return html.escape(str(x if x is not None else ""))


TEMAS = [
    ("auto", "Auto"),
    ("light", "Claro"),
    ("suave", "Suave"),
    ("dark", "Oscuro"),
]

# El selector de tema. "Auto" sigue al sistema; las otras tres mandan sobre el,
# porque a veces el equipo esta en oscuro y aun asi se quiere leer las hojas
# con fondo claro. La eleccion se recuerda en este navegador.
SCRIPT_TEMA = """
(function () {
  var raiz = document.documentElement;
  function aplicar(t) {
    if (t === 'auto') { delete raiz.dataset.theme; } else { raiz.dataset.theme = t; }
    var botones = document.querySelectorAll('.temas button');
    for (var i = 0; i < botones.length; i++) {
      botones[i].setAttribute('aria-pressed', botones[i].dataset.tema === t);
    }
  }
  var guardado = 'auto';
  try { guardado = localStorage.getItem('tema-obra') || 'auto'; } catch (e) {}
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.temas button');
    if (!b) return;
    aplicar(b.dataset.tema);
    try { localStorage.setItem('tema-obra', b.dataset.tema); } catch (e) {}
  });
  aplicar(guardado);
})();
"""


def navegacion(actual: str) -> str:
    enlaces = []
    for archivo, rotulo in PAGINAS:
        clase = ' class="activo"' if archivo == actual else ""
        enlaces.append(f'<a href="{archivo}"{clase}>{e(rotulo)}</a>')
    if ajustes.BOARD_ID:
        enlaces.append(f'<a href="https://trello.com/b/{e(ajustes.BOARD_ID)}" '
                       f'target="_blank" rel="noopener">Abrir el tablero</a>')

    botones = "".join(
        f'<button type="button" data-tema="{clave}" aria-pressed="false">{e(rotulo)}'
        f'</button>' for clave, rotulo in TEMAS)
    temas = f'<span class="temas" role="group" aria-label="Tema">{botones}</span>'

    return "<nav>" + "".join(enlaces) + temas + "</nav>"


# Filtrado de las tablas y despliegue del detalle de cada tarjeta.
# Va en la propia pagina para que siga siendo UN archivo que funciona sin
# conexion: no hay servidor al que preguntar ni libreria que cargar.
SCRIPT_TABLA = """
(function () {
  function cerrarMenus(salvo) {
    var abiertos = document.querySelectorAll('th .filtro > button[aria-expanded="true"]');
    for (var i = 0; i < abiertos.length; i++) {
      if (abiertos[i] === salvo) { continue; }
      abiertos[i].setAttribute('aria-expanded', 'false');
      abiertos[i].parentNode.querySelector('.menu').hidden = true;
    }
  }

  function filtrar(caja) {
    var filtros = caja.querySelectorAll('th .filtro');
    var criterios = {};
    for (var i = 0; i < filtros.length; i++) {
      var valor = filtros[i].dataset.valor || '';
      if (valor) { criterios[filtros[i].dataset.campo] = valor; }
    }
    var filas = caja.querySelectorAll('tbody tr.desplegable');
    var vistas = 0;
    for (var j = 0; j < filas.length; j++) {
      var fila = filas[j], ok = true;
      for (var campo in criterios) {
        // Un campo puede llevar varios valores, separados por barra
        var suyos = (fila.dataset[campo] || '').split('|');
        if (suyos.indexOf(criterios[campo]) === -1) { ok = false; break; }
      }
      fila.hidden = !ok;
      var detalle = fila.nextElementSibling;
      if (detalle && detalle.classList.contains('detalle')) {
        detalle.hidden = !ok || fila.getAttribute('aria-expanded') !== 'true';
      }
      if (ok) { vistas++; }
    }
    var cuenta = caja.querySelector('.cuenta');
    if (cuenta) {
      cuenta.textContent = vistas === filas.length
        ? filas.length + ' tarjetas'
        : vistas + ' de ' + filas.length + ' tarjetas';
    }
  }

  document.addEventListener('click', function (ev) {
    var abrir = ev.target.closest && ev.target.closest('th .filtro > button');
    if (abrir) {
      var abierto = abrir.getAttribute('aria-expanded') === 'true';
      cerrarMenus(abrir);
      abrir.setAttribute('aria-expanded', abierto ? 'false' : 'true');
      abrir.parentNode.querySelector('.menu').hidden = abierto;
      return;
    }

    var opcion = ev.target.closest && ev.target.closest('th .filtro .menu button');
    if (opcion) {
      var filtro = opcion.closest('.filtro');
      var hermanas = filtro.querySelectorAll('.menu button');
      for (var i = 0; i < hermanas.length; i++) {
        hermanas[i].setAttribute('aria-checked', hermanas[i] === opcion ? 'true' : 'false');
      }
      filtro.dataset.valor = opcion.dataset.valor || '';
      var boton = filtro.querySelector('button');
      boton.classList.toggle('activo', !!filtro.dataset.valor);
      boton.setAttribute('aria-expanded', 'false');
      filtro.querySelector('.menu').hidden = true;
      filtrar(filtro.closest('.bloque-tabla'));
      return;
    }

    cerrarMenus(null);

    if (ev.target.closest('a')) { return; }
    var fila = ev.target.closest && ev.target.closest('tr.desplegable');
    if (!fila) { return; }
    var expandido = fila.getAttribute('aria-expanded') === 'true';
    fila.setAttribute('aria-expanded', expandido ? 'false' : 'true');
    var detalle = fila.nextElementSibling;
    if (detalle && detalle.classList.contains('detalle')) {
      detalle.hidden = expandido;
    }
  });
})();
"""


def filtro_columna(campo: str, opciones: list) -> str:
    """El botoncito de filtro que va DENTRO de la cabecera de una columna.

    Devuelve cadena vacia si la columna no tiene mas de un valor distinto:
    filtrar por algo que no varia solo estorba.
    """
    opciones = [o for o in dict.fromkeys(opciones) if o]
    if len(opciones) < 2:
        return ""
    items = ['<button type="button" data-valor="" aria-checked="true">Todas</button>']
    items += [f'<button type="button" data-valor="{e(o)}" aria-checked="false">'
              f'{e(o)}</button>' for o in opciones]
    return (f'<span class="filtro" data-campo="{e(campo)}" data-valor="">'
            f'<button type="button" aria-expanded="false" '
            f'aria-label="Filtrar por {e(campo)}">▾</button>'
            f'<div class="menu" hidden>{"".join(items)}</div></span>')


def seccion(titulo: str, que_es: str, cinta: str = "", color: str = "") -> str:
    """Encabezado de un ambito, para que se vea donde empieza cada cosa."""
    marca = ""
    if cinta:
        marca = (f'<span class="cinta" style="background:{color};color:#fff">'
                 f'{e(cinta)}</span>')
    return (f'<div class="seccion"><h3>{e(titulo)}{marca}</h3>'
            f'<div class="que">{e(que_es)}</div></div>')


def kpi(valor, rotulo, pie="", clase="") -> str:
    pie_html = f'<div class="pie">{e(pie)}</div>' if pie else ""
    return (f'<div class="tarjeta kpi {clase}"><div class="n">{e(valor)}</div>'
            f'<div class="r">{e(rotulo)}</div>{pie_html}</div>')


def barras(pares: list, colores: dict = None) -> str:
    """Barras horizontales. `pares` es [(rotulo, valor)] ya ordenado.

    Cada barra lleva SIEMPRE su rotulo y su valor a la vista: es lo que
    permite usar la paleta completa en modo claro, donde tres de los tonos
    quedan por debajo del contraste minimo y el color solo no bastaria.
    """
    pares = [(r, v) for r, v in pares if v]
    if not pares:
        return '<div class="sub">Nada que mostrar.</div>'
    tope = max(v for _, v in pares)
    filas = []
    for rotulo, valor in pares:
        ancho = round(valor / tope * 100, 1) if tope else 0
        color = (colores or {}).get(rotulo, "var(--acento)")
        filas.append(
            f'<div class="fila"><span>{e(rotulo)}</span>'
            f'<span class="pista"><span class="relleno" '
            f'style="width:{ancho}%;background:{color}"></span></span>'
            f'<span class="num">{valor}</span></div>')
    return "".join(filas)


# Orden FIJO de la serie categorica. El color sigue a la entidad, nunca a su
# posicion en el ranking: si un filtro cambia el orden, cada familia conserva
# el suyo. Nunca se cicla — pasado el octavo, se agrupa en "Otras".
SERIES = [f"var(--s{i})" for i in range(1, 9)]


def color_de(nombre: str, catalogo: list) -> str:
    """Color fijo de una entidad segun su posicion en el catalogo."""
    try:
        i = list(catalogo).index(nombre)
    except ValueError:
        return "var(--suave)"
    return SERIES[i] if i < len(SERIES) else "var(--suave)"


def anillo(porcentaje: float, titulo: str, pie: str = "", tam: int = 168) -> str:
    """Medidor radial: UNA razon contra un limite.

    No es un grafico de sectores. Es un medidor: una sola magnitud sobre su
    tope, con la pista en un tono claro del mismo color. El relleno lleva la
    severidad, y va acompanado SIEMPRE de un rotulo que dice lo mismo con
    palabras — el color nunca carga el significado solo.
    """
    p = max(0, min(100, porcentaje))
    if p >= 85:
        color, rotulo = "var(--ok)", "en meta"
    elif p >= 60:
        color, rotulo = "var(--aviso)", "por debajo de la meta"
    else:
        color, rotulo = "var(--alerta)", "muy por debajo de la meta"

    r = tam / 2 - 13
    circ = 2 * 3.14159265 * r
    avance = circ * p / 100
    c = tam / 2

    return (
        f'<div class="hero">'
        f'<svg width="{tam}" height="{tam}" viewBox="0 0 {tam} {tam}" role="img" '
        f'aria-label="{e(titulo)}: {p:.0f}%">'
        # Pista: el mismo color, muy claro. Que se lea "cuanto falta".
        f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="{color}" '
        f'stroke-opacity=".16" stroke-width="15"/>'
        f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="{color}" '
        f'stroke-width="15" stroke-linecap="round" '
        f'stroke-dasharray="{avance:.1f} {circ:.1f}" '
        f'transform="rotate(-90 {c} {c})"/>'
        f'<text x="{c}" y="{c + 3}" text-anchor="middle" font-size="30" '
        f'font-weight="650" fill="currentColor">{p:.0f}%</text>'
        f'<text x="{c}" y="{c + 24}" text-anchor="middle" font-size="11.5" '
        f'fill="currentColor" fill-opacity=".6">{e(titulo)}</text>'
        f'</svg>'
        f'<div><div class="sub" style="max-width:280px">{pie}</div>'
        f'<div class="estado" style="color:{color}">'
        f'<span class="pto" style="background:{color}"></span>{e(rotulo)}</div>'
        f'</div></div>')


def barra_apilada(partes: list) -> str:
    """Parte-de-un-todo en una barra horizontal, con su leyenda.

    `partes` es [(rotulo, valor, color)]. Se usa esto y no un grafico de
    sectores: comparar angulos es mas dificil que comparar longitudes, y con
    valores parecidos un sector es directamente ilegible.
    """
    partes = [(r, v, c) for r, v, c in partes if v]
    total = sum(v for _r, v, _c in partes)
    if not total:
        return ""
    # Hueco de 2px entre segmentos: separa sin necesidad de bordes
    tramos = "".join(
        f'<span style="background:{c};width:{v / total * 100:.2f}%" '
        f'title="{e(r)}: {v}"></span>' for r, v, c in partes)
    leyenda = "".join(
        f'<span><i style="background:{c}"></i>{e(r)} · <b>{v}</b></span>'
        for r, v, c in partes)
    return f'<div class="apilada">{tramos}</div><div class="leyenda">{leyenda}</div>'


def grafico_linea(puntos: list, unidad: str = "", meta: float = None,
                  alto: int = 190, color: str = "var(--acento)") -> str:
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
                      f'fill="{color}"><title>{e(etiqueta)}: {v}{e(unidad)}'
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
        f'<polygon points="{area}" fill="{color}" fill-opacity=".10"/>'
        f'<polyline points="{linea}" fill="none" stroke="{color}" '
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
<script>{SCRIPT_TEMA}{SCRIPT_TABLA}</script>
</body>
</html>
"""


def escribir(archivo: str, contenido: str) -> str:
    ruta = ajustes.CARPETA_WEB / archivo
    os.makedirs(ruta.parent, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return str(ruta)

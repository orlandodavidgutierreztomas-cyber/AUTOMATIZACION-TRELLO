# Control diario de obra — Trello + Last Planner

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

Cinco robots que llevan solos el tablero de una obra: leen el cronograma
(Last Planner), crean las tarjetas del día copiando tus plantillas de control
de calidad, las reparten, evalúan al cierre quién cumplió, sacan el reporte y
archivan lo terminado.

Todo corre en **GitHub Actions**: gratis, en la nube, sin depender de ninguna
computadora encendida.

> **Nada de esta obra está escrito en el código.** Todo lo particular —la forma
> del Excel, las horas, las listas del tablero, las familias de trabajo— vive en
> `configuracion.json` y `mapeo.json`, y se edita **desde el navegador**.
> Para llevar el sistema a otra obra no se toca una línea de Python.

---

## El ciclo de un día

| # | Robot | Cuándo | Qué hace |
|---|---|---|---|
| 1 | **Preparar** | la tarde anterior | Lee el cronograma de **mañana** y crea las tarjetas en `ESPERA`, copiando la plantilla de cada actividad |
| 2 | **Distribuir** | de madrugada | Vacía `ESPERA` repartiendo cada tarjeta a su lista del día según su familia |
| 3 | **Cierre** | al terminar la jornada | Checklist completo → `CULMINADO`; le falta algo → `NO CUMPLIDAS` |
| 4 | **Reporte** | a demanda, o a su hora | Cuenta los checks pendientes por responsable y escribe el corte |
| 5 | **Archivar** | al final del día | Archiva lo culminado y deja el tablero limpio |

Preparar la víspera es lo que hace que el tablero de hoy no se ensucie con lo
de mañana, y que si el cronograma trae una sorpresa haya toda la tarde para verla.

**Todos son idempotentes**: si un robot corre dos veces, la segunda no duplica
ni rehace nada. Eso permite tener dos relojes sin riesgo.

---

## Cómo empareja cada tarjeta con su plantilla

1. Del cronograma sale la actividad: `ACERO INFERIOR EN ZAPATAS`.
2. Busca en el tablero una tarjeta que **lleve la palabra PLANTILLA en su nombre**
   y se llame igual: `PLANTILLA — ACERO INFERIOR EN ZAPATAS`.
3. La **duplica**: se lleva su descripción, todos sus checklists con sus ítems, y
   sus etiquetas. Le pone nombre `SECTOR — ACTIVIDAD — DD/MM/AAAA` y el horario
   de la jornada.

Una tarjeta es plantilla **por su propio nombre**, viva en la lista que viva. Así
una errata en el encabezado de una columna (`PLANTILA` con una sola L) no deja
fuera a las plantillas que contiene. Tolera `PLANTILLA`, `PLANTILA`, plurales,
emojis y guiones. La comparación ignora acentos, símbolos y mayúsculas.

**Consecuencia práctica:** todo lo que quieras que lleven las tarjetas —ítems de
calidad, etiquetas, el texto de la descripción— se edita **en la plantilla, dentro
de Trello**, y rige al día siguiente. Sin tocar código ni subir nada.

Si una actividad todavía no tiene plantilla, la tarjeta se crea igual con una
descripción generada, para no dejarla fuera del plan.

---

## Cuándo cuenta como terminada

Manda el **control de calidad**, no la marca de "completa" de Trello.

| Criterio | Terminada si… |
|---|---|
| `checklist` *(por defecto)* | **todos** los ítems de sus checklists están marcados |
| `auto` | checklist completo **o** tarjeta marcada como completa |
| `marcada` | solo la marca de Trello |

---

## 🕐 Las dos clases de hora

Es la confusión más fácil de tener, y conviene tenerla clara:

**JORNADA** — se escribe **dentro** de cada tarjeta. Es el `Vencimiento` que ve
el equipo en Trello. No ejecuta nada.

**RELOJES** — despiertan a cada robot. No aparecen en ninguna tarjeta.

Dales margen entre ellas: si la jornada vence a las 18:30, el cierre a las 19:00.
Si no, a alguien le mueven la tarjeta mientras aún está marcando su checklist.

### Cambiarlas sin tocar el código

**Actions → "Configurar" → Run workflow.** Escribes solo lo que quieras cambiar,
el resto lo dejas en blanco. El workflow valida, guarda y hace el commit.

Se puede cambiar: las dos horas de la jornada, las cinco horas de los robots,
los días hábiles, la zona horaria, el criterio de cierre y **la forma del Excel**
(hoja, fila de fechas, columna de actividades).

### Los dos relojes

GitHub Actions **no es puntual**: retrasa y a veces descarta las tareas
programadas. Por eso hay dos relojes apuntando a la misma hora:

- Un **servicio de cron externo** dispara el workflow por la API. Ese es el
  puntual, el que hace el trabajo.
- El **cron de GitHub** es la red de seguridad. Cuando llega —tarde— se encuentra
  el trabajo hecho y no repite nada.

Los cron están en los minutos **7 y 37**, nunca en punto ni a la media: son las
horas de mayor congestión y GitHub descarta citas ahí. Y el "portero"
(`trello_auto/portero.py`) deja pasar solo las citas dentro de una ventana de
90 minutos desde la hora configurada, así que perder una cita no cuesta el día.

---

## 📊 El reporte y los dos dashboards

El reporte **solo lee**: puedes correrlo a mediodía, a las tres y antes del
cierre. Cada corrida es un **corte** con su fecha y hora, y los cortes se
acumulan. Repetir un corte en el mismo minuto lo reemplaza, no lo duplica.

```
--alcance dia            las listas del día (lo que está en juego hoy)
--alcance no-cumplidas   la deuda acumulada
--alcance todo           las dos cosas
```

Produce tres cosas:

| Archivo | Para qué |
|---|---|
| `reportes/ultimo.csv` | El corte de ahora. Es lo que lee tu Excel |
| `reportes/cortes.csv` | El histórico de todos los cortes: la película, no la foto |
| `dashboard/index.html` | Dashboard web autocontenido |

### El dashboard web

Un solo archivo, con los datos dentro. Se puede publicar en GitHub Pages, verlo
desde el celular, descargarlo, mandarlo por correo o abrirlo sin conexión — y
sigue funcionando aunque el repositorio pase a privado.

### El dashboard de Excel

`dashboard/DASHBOARD_CONTROL.xlsx` conserva tus gráficos y tablas de apoyo, con
tres arreglos para que aguante la automatización:

- **Sin límite de filas.** Antes las fórmulas llegaban a la 201 y el corte 202
  desaparecía en silencio. Ahora llegan a la 5000.
- **La fecha de corte se calcula sola** (`DASHBOARD!F3`). Antes estaba escrita a
  mano: si el reporte era de las tres de la tarde y F3 decía las siete de la
  mañana, todas las antigüedades salían mal sin avisar.
- **Las familias vienen de la configuración**, no escritas a mano.

**Conectarlo (una vez):** Datos → Obtener datos → Desde web → pega la URL del
`ultimo.csv` en bruto → cárgalo sobre la hoja `DATOS`. Después, cada vez que
quieras datos frescos: **Actualizar todo**.

Y esto resuelve lo de la PC apagada: el reporte siempre se guarda, tu PC no
tiene que estar encendida ni recibir nada. Cuando la prendas y actualices, se
trae **todos los cortes que se hicieron mientras estuvo apagada**. No se pierde
ninguno y no hay que volver a ejecutar nada.

> Si el repositorio pasa a privado, ese enlace deja de responder sin credencial.
> Para que el dashboard siga actualizándose solo, deja los reportes en un repo
> público aparte y el código en el privado.

---

## 🔄 Sincronizar

**Actions → "Sincronizar cronograma y tablero" → Run workflow.** Apriétalo
cuando subas una revisión nueva del Excel o crees plantillas o listas en Trello.

Hace tres cosas y hace el commit por ti:

1. Saca del Excel **todas las actividades distintas**.
2. Vuelca el plan entero a `data/plan_obra.json`. Es el **respaldo**: si algún
   día el Excel falta o se corrompe, los robots siguen corriendo con ese archivo.
3. Lee el tablero y escribe `mapeo.json`, que dice a qué familia y a qué lista va
   cada actividad. Llega **pre-rellenado** por palabras clave —para no mapear
   decenas de actividades a mano— y **lo que corrijas se respeta** en las
   sincronizaciones siguientes. También te deja a la vista los nombres reales de
   tus listas, para que elijas de lo que existe.

Lo que no case con ninguna palabra clave cae en la familia de descarte
(`Varios`), nunca se queda sin destino ni se acumula donde no debe.

---

## 🚀 Puesta en marcha

**1. Los Secrets.** Settings → Secrets and variables → Actions:

| Nombre | Valor |
|---|---|
| `TRELLO_KEY` | tu API Key |
| `TRELLO_TOKEN` | tu Token |

Se obtienen gratis en <https://trello.com/power-ups/admin>.

**2. Sube tu Excel** a `data/` y ajusta `configuracion.json → cronograma` con la
forma que tenga (o hazlo desde el botón "Configurar").

**3. Sincroniza** una vez, para generar el mapeo y el respaldo.

**4. Prueba en seco.** Cada robot tiene `dry_run` en su formulario: muestra qué
haría sin tocar nada.

---

## 💻 Desde tu PC (opcional)

```bash
pip install -r requirements.txt
cp config.example.py config.py     # y pon tus credenciales
```

```bash
python -m trello_auto.preparar --fecha manana --dry-run
python -m trello_auto.distribuir --dry-run
python -m trello_auto.cierre --dry-run
python -m trello_auto.reporte --alcance todo
python -m trello_auto.archivar --dry-run
python -m trello_auto.sincronizar
python -m trello_auto.configurar --ver
python -m trello_auto.configurar --hora-cierre 19:00 --jornada-fin 18:30
```

### Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q                          # 44 pruebas, ninguna toca Trello
ruff check trello_auto tests
```

---

## Qué hay en cada archivo

| Ruta | Qué es |
|---|---|
| `configuracion.json` | **Toda la obra.** Horas, listas, familias, responsables, forma del Excel |
| `mapeo.json` | Actividad → familia → lista destino. Lo genera "Sincronizar" |
| `trello_auto/ajustes.py` | Lee la configuración y la resuelve por prioridad |
| `trello_auto/cronograma.py` | Lee el Excel (o el respaldo JSON) y clasifica |
| `trello_auto/trello.py` | Cliente de la API, plantillas y conteo de checklists |
| `trello_auto/horario.py` | Zonas horarias, conversiones y el portero |
| `trello_auto/preparar.py` … `archivar.py` | Los cinco robots |
| `trello_auto/reporte.py` · `tablero.py` | El corte y el dashboard web |
| `trello_auto/sincronizar.py` · `configurar.py` | Los dos botones de gestión |
| `data/` | El cronograma y su respaldo |
| `reportes/` | Los cortes acumulados |
| `dashboard/` | El Excel y el dashboard web |

---

## Próximos pasos

- **Las plantillas que faltan.** Cada actividad sin plantilla sale sin su control
  de calidad real. `mapeo.json` te dice exactamente cuáles faltan.
- **PPC semanal.** El cierre ya calcula el cumplimiento del día; falta acumularlo
  por semana, que es *la* métrica del Last Planner.
- **Causas de no cumplimiento.** Saber *por qué* no se cumplió cierra el ciclo de
  mejora. Se puede capturar con una etiqueta y contarlo en el reporte.
- **Responsable por cuadrilla**, desde la columna OPER/OFIC del Excel.

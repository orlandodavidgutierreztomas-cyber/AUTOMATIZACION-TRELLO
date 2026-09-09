# Control diario de obra — Trello + Last Planner

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

Seis robots que llevan solos el tablero de una obra: leen el cronograma, crean
las tarjetas del día copiando tus plantillas de control de calidad, las
reparten, evalúan al cierre quién cumplió, sacan el reporte y archivan lo
terminado.

Todo corre en **GitHub Actions**: gratis, en la nube, sin depender de ninguna
computadora encendida.

> **Nada de esta obra está escrito en el código.** El horario, la forma del
> Excel, los nombres de las listas, las familias de trabajo, los responsables y
> hasta qué tablero se usa viven en `configuracion.json` y `mapeo.json`, y se
> editan **desde el navegador**. Llevarlo a otra obra no exige tocar una línea
> de Python.

---

## Índice

- [El ciclo de un día](#el-ciclo-de-un-día)
- [Cómo empareja cada tarjeta con su plantilla](#cómo-empareja-cada-tarjeta-con-su-plantilla)
- [El cierre en dos fases](#el-cierre-en-dos-fases)
- [**Elegir el tablero**](#-elegir-el-tablero) ← si tienes varios
- [**La obra ya venía avanzada**](#-la-obra-ya-venía-avanzada) ← al empezar
- [**Llevarlo a otra obra**](#-llevarlo-a-otra-obra) ← guía completa
- [**Todos los parámetros**](#-todos-los-parámetros) ← referencia
- [Las horas y los relojes](#-las-horas-y-los-relojes)
- [Las páginas web](#-las-páginas-web)
- [Los botones de mantenimiento](#-los-botones-de-mantenimiento)
- [Desde tu PC](#-desde-tu-pc)

---

## El ciclo de un día

| # | Robot | Cuándo | Qué hace |
|---|---|---|---|
| 1 | **Preparar** | la tarde anterior | Lee el cronograma de **mañana** y crea las tarjetas en `ESPERA`, copiando la plantilla de cada actividad |
| 2 | **Distribuir** | de madrugada | Vacía `ESPERA` repartiendo cada tarjeta a su lista del día según su familia |
| 3 | **Cierre (gracia)** | al terminar la jornada | Completo → `CULMINADO`; pendiente → la lista **por cerrar** de su familia |
| 4 | **Cierre definitivo** | unas horas después | Lo que alcanzó a marcarse → `CULMINADO`; el resto **se queda por cerrar**, para reprogramarse |
| 5 | **Reporte** | a demanda, o a su hora | Cuenta los checks pendientes por responsable y publica el dashboard |
| 6 | **Archivar** | al final del día | Archiva **solo lo culminado**; lo que sigue abierto se queda a la vista |

Preparar la víspera es lo que hace que el tablero de hoy no se ensucie con lo de
mañana, y que si el cronograma trae una sorpresa haya toda la tarde para verla.

**Todos son idempotentes**: si un robot corre dos veces, la segunda no duplica ni
rehace nada. Eso permite tener dos relojes apuntando a la misma hora sin riesgo.

---

## Cómo empareja cada tarjeta con su plantilla

1. Del cronograma sale la actividad: `ACERO INFERIOR EN ZAPATAS`.
2. Busca en el tablero una tarjeta que **lleve la palabra PLANTILLA en su
   nombre** y se llame igual: `PLANTILLA — ACERO INFERIOR EN ZAPATAS`.
3. La **duplica**: se lleva su descripción, todos sus checklists con sus ítems y
   sus etiquetas. Le pone nombre `SECTOR - ACTIVIDAD - DD/MM/AAAA` y el horario
   de la jornada.

Una tarjeta es plantilla **por su propio nombre**, viva en la lista que viva. Así
una errata en el encabezado de una columna (`PLANTILA` con una sola L) no deja
fuera a las plantillas que contiene. Tolera `PLANTILLA`, `PLANTILA`, plurales,
emojis y guiones; la comparación ignora acentos, símbolos y mayúsculas.

**Consecuencia práctica:** todo lo que quieras que lleven las tarjetas —ítems de
calidad, etiquetas, el texto de la descripción— se edita **en la plantilla,
dentro de Trello**, y rige al día siguiente. Sin tocar código ni subir nada.

Si una actividad todavía no tiene plantilla, la tarjeta se crea igual con una
descripción generada, para no dejarla fuera del plan.

---

## El cierre en dos fases

Cuando termina la jornada los especialistas siguen ocupados. Dar por perdida una
tarjeta a la que solo le faltaba marcar un ítem sería injusto. Por eso el cierre
no es un solo golpe:

**Fase 1 — al fin de jornada.** Lo completo va a `CULMINADO`; **lo pendiente va a
la lista de por cerrar de su familia**. Las listas del día quedan limpias.

**Fase 2 — el cierre definitivo.** Lo que alcanzaron a marcar va a `CULMINADO`.
Lo que sigue sin marcar **se queda donde está**.

La fase 2 barre también las listas del día, por si la fase 1 no llegó a correr.

### No hay lista de «no cumplidas», y es a propósito

En Last Planner el trabajo que no se terminó **no se archiva: se reprograma**.
Con treinta actividades al día, mandarlas a un saco aparte obligaría a sacarlas
de ahí a mano, una por una, para volver a meterlas en la programación.

Así que lo que no cierra se queda **a la vista, en la lista de por cerrar de su
familia**, hasta que se termine o se reprograme. `Archivar` no la toca: solo
guarda lo culminado. El dashboard la sigue mostrando en el bloque *Por cerrar*,
con su antigüedad, para que se vea cuántos días lleva abierta.

**Para retirar una columna heredada** (por ejemplo, la vieja `NO CUMPLIDAS` de
un tablero anterior) está el botón **Reubicar tarjetas de una lista**: reparte
cada tarjeta a la lista de por cerrar de su familia y archiva la columna vacía.
No borra nada — la tarjeta conserva checklists, etiquetas, comentarios e
historial, y la lista archivada se recupera desde *Más → Listas archivadas*.
Córrelo primero con `dry_run` para ver el reparto.

### Cuándo cuenta como terminada

| `cierre.criterio` | Terminada si… |
|---|---|
| `auto` *(por defecto)* | tiene el checklist completo **o** está marcada como cumplida |
| `checklist` | **todos** los ítems marcados, sin excepción |
| `marcada` | solo la marca de Trello, ignora los checklists |

El criterio por defecto es `auto` porque en obra hay actividades que no
necesitan todos los checks: si el responsable la da por cumplida, está cumplida.
El checklist deja de ser un obstáculo y pasa a ser lo que es — una ayuda para no
olvidar nada.

Quien prefiera exigir el control completo sin excepciones tiene `checklist`. El
reporte trae una columna **MARCADA** para ver cuáles se cerraron por la marca y
cuáles por su checklist.

---

## 🎯 Elegir el tablero

Si tienes diez tableros, el sistema trabaja sobre **uno**: el que diga
`obra.tablero`. Es el **id corto**, lo que va después de `/b/` en la URL.

```
https://trello.com/b/gzoZo6ip/aulas-control-diario
                     ^^^^^^^^
                     esto es lo que va en obra.tablero
```

**Puedes pegar la URL entera.** El sistema se queda con el código él solo, así
que las tres formas valen y dan lo mismo:

| Lo que pegas | Lo que guarda |
|---|---|
| `https://trello.com/b/gzoZo6ip/aulas-control-diario` | `gzoZo6ip` |
| `gzoZo6ip/aulas-control-diario` | `gzoZo6ip` |
| `gzoZo6ip` | `gzoZo6ip` |

**Para cambiarlo:** Actions → **Configurar** → *Run workflow* → campo **TABLERO**.
No importa en qué espacio de trabajo esté; basta con que tus credenciales de
Trello tengan acceso a él.

**Después de cambiar de tablero, corre siempre `Sincronizar`.** Hay que releer
las listas y las plantillas de la pizarra nueva: el mapeo anterior apunta a
listas que allí quizá no existen.

**Para comprobar que apuntas al correcto**, mira la página *Estado del tablero*:
te dice qué listas encontró y cuáles faltan. Si ves varias `FALTA`, estás sobre
el tablero equivocado.

> **Un repositorio = un tablero.** Para llevar dos obras a la vez, duplica el
> repositorio: cada una con su cronograma, sus horas y su mapeo, sin
> interferirse. Cambiar `obra.tablero` **cambia** de tablero, no añade uno.

---

## 🏁 La obra ya venía avanzada

El sistema casi nunca arranca el primer día de obra. Cuando se pone en marcha,
el cronograma ya tiene cientos de actividades con fecha pasada, y muchas están
hechas: la obra avanzó, pero el sistema no lo vio.

Si nadie se lo dice, el dashboard mostraría **0% de avance** con medio primer
piso levantado, y el cumplimiento del Last Planner quedaría falseado desde el
primer día.

**Se declara una vez**, con el botón **Arranque de la obra**:

1. Pon la fecha en `obra.arranque` (vacío = hoy). Es el día en que el sistema
   toma el control; lo anterior es historia que no vio.
2. Corre el botón con `hechas: ver` para saber cuántas tareas hay antes de esa
   fecha. En esta obra son **277 de 1447**.
3. Vuelve a correrlo diciendo cuántas ya estaban hechas:

| Respuesta | Cuándo |
|---|---|
| `todas` | La obra viene al día y el sistema entra hoy |
| `ninguna` | El plan empieza de cero |
| `hasta` + una fecha | Estaba hecho lo anterior a esa fecha; lo de en medio quedó pendiente. **Es el caso real cuando la obra viene con retraso** |
| un número | La cifra exacta, si la sabes de tu propio control |

Eso queda anotado como **punto de partida** en `reportes/culminadas.csv`. A
partir de ahí el sistema sigue solo: cada cierre suma lo culminado del día.

El dashboard lo dice por separado —«de esas, 145 ya estaban hechas al arrancar y
23 se han cerrado con el sistema»— para que nadie le atribuya a los robots un
avance que ya venía hecho. Se puede corregir cuantas veces haga falta:
**reemplaza** el punto de partida, nunca lo suma dos veces.

---

## 🚚 Llevarlo a otra obra

La guía completa, en orden.

### 1. Copia el repositorio

Úsalo como plantilla o clónalo. Lo que cambiarás son dos archivos de
configuración y el Excel; el código queda igual.

### 2. Pon tus credenciales

Settings → Secrets and variables → Actions → *New repository secret*:

| Secret | De dónde sale |
|---|---|
| `TRELLO_KEY` | <https://trello.com/power-ups/admin> → tu API Key |
| `TRELLO_TOKEN` | el enlace "Token" de esa misma página |

⚠ El **token se muestra una sola vez**. Si no lo guardas, hay que generar otro.
Y una vez dentro de un Secret **nadie puede volver a leerlo**, ni tú: es
justamente lo que lo hace un secreto.

### 3. Sube el cronograma

Ponlo en `data/` y dile al sistema qué forma tiene. El Excel debe tener **una
fila con las fechas** y **una columna con el nombre de cada actividad**; en el
cruce, el código del sector que trabaja ese día:

```
                  ...  |  26/08  |  27/08  |  28/08  |   <- fila_fechas
 ACERO EN ZAPATAS      |  1CS11  |  1CS12  |         |
 ENCOFRADO DE ZAPATA   |         |  1CS15  |  1CS16  |
 ^ columna_actividad
```

En **Configurar** ajustas `hoja`, `fila_fechas`, `columna_actividad` y
`primera_fila_datos`. Si tus sectores no se parecen a `1CS6` / `2PS13`, cambia
también `cronograma.patron_sector` en `configuracion.json`.

### 4. Define las familias de trabajo

En `configuracion.json → familias`. Cada una agrupa actividades por palabras
clave y dice a qué listas van:

```json
"Acero": {
  "lista": "T. DEL DIA ACERO",
  "lista_cierre": "T. POR CERRAR - ACERO",
  "claves": ["ACERO", "ESTRIBO"]
}
```

**El orden importa**: gana la primera que case. Por eso `Trazo` va antes que
`Excavacion`, y así "TRAZO Y REPLANTEO PARA EXCAVACIÓN" cuenta como Trazo.

La familia con `"por_defecto": true` recoge lo que no case con nada, para que
ninguna actividad se quede sin destino.

### 5. Define los responsables

En `configuracion.json → responsables`. Cada plantilla lleva **un checklist por
responsable**, y se reconocen por palabras clave en el nombre del checklist:

```json
"CAL": { "nombre": "Calidad", "claves": ["CALIDAD"] }
```

El código (`CAL`) es el nombre de la columna en el reporte y en el dashboard.

### 6. Monta el tablero

Con un tablero en blanco: Actions → **Montar tablero desde el cronograma**. Crea
las columnas y una plantilla genérica por actividad. Empieza con `dry_run: true`
para ver la lista antes de crear nada.

### 7. Sincroniza y revisa

Actions → **Sincronizar**. Lee el Excel y el tablero, y genera el mapeo
pre-rellenado más las tres páginas web. Revisa el mapeo y corrige lo que haga
falta.

### 8. Ajusta las horas

Actions → **Configurar**: las seis horas de los robots y las dos de la jornada.

### 9. Publica el dashboard

Settings → Pages → *Deploy from a branch* → `main` → `/docs`.

---

## 📋 Todos los parámetros

Todo se resuelve por prioridad: **variable de entorno** → **`configuracion.json`**
→ **`config.py`** (solo en tu PC) → valor por defecto.

### Obra

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `obra.nombre` | — | Sale en los títulos de las páginas |
| `obra.tablero` | — | **Id corto del tablero de Trello** |
| `obra.zona_horaria` | `America/Lima` | Todo el reloj se calcula aquí |

### Cronograma — la forma de tu Excel

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `cronograma.archivo` | `data/…xlsx` | Ruta del Excel |
| `cronograma.respaldo_json` | `data/plan_obra.json` | Respaldo; se usa si falta el Excel |
| `cronograma.hoja` | `01_MAESTRO` | Nombre de la hoja |
| `cronograma.fila_fechas` | `6` | Fila de las fechas (se cuenta como en Excel) |
| `cronograma.primera_fila_datos` | `7` | Primera fila con actividades |
| `cronograma.columna_actividad` | `C` | Letra de la columna |
| `cronograma.patron_sector` | `^[12][A-Z]{2}\d+$` | Cómo se reconoce un código de sector |

### Jornada — se escribe DENTRO de cada tarjeta

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `jornada.inicio` | `07:00` | Hora de inicio de la tarjeta |
| `jornada.fin` | `17:00` | Vencimiento de la tarjeta |

### Relojes — despiertan a cada robot

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `relojes.preparar.hora` | `18:00` | Crea las de mañana |
| `relojes.distribuir.hora` | `05:00` | Reparte a las listas del día |
| `relojes.cierre.hora` | `18:00` | Fin de jornada → gracia |
| `relojes.cierre_final.hora` | `21:00` | Cierre definitivo: rescata lo marcado tarde |
| `relojes.reporte.hora` | `15:00` | Corte de control |
| `relojes.archivar.hora` | `21:00` | Archiva lo culminado |
| `relojes.<robot>.dias` | `1-5` | 1 = lunes … 7 = domingo |
| `ventana_minutos` | `90` | Tolerancia del portero |

### Listas del tablero

Se buscan **por palabra clave**: funcionan aunque la lista tenga emojis, acentos
o espacios de más. `T. DEL DIA ACERO` encuentra `T. DEL DÍA ACERO- 🟦🟦🟦`.

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `listas.espera` | `ESPERA` | Donde nacen las tarjetas de mañana |
| `listas.plantillas` | `PLANTILLAS` | Donde el montaje crea las plantillas |
| `listas.por_cerrar` | `T. POR CERRAR` | Por cerrar **global**: solo para familias sin la suya |
| `listas.culminado` | `CULMINADO` | Lo que cumplió |

### Familias, responsables, plantillas y cierre

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `familias.<X>.lista` | — | Lista del día de esa familia |
| `familias.<X>.lista_cierre` | — | Su lista de gracia (varias pueden compartirla) |
| `familias.<X>.claves` | — | Palabras que se buscan en la actividad |
| `familias.<X>.por_defecto` | — | `true` en la familia de descarte |
| `responsables.<COD>.nombre` | — | Nombre legible |
| `responsables.<COD>.claves` | — | Palabras que identifican su checklist |
| `plantillas.marca` | `PLANTIL` | Qué palabra declara plantilla a una tarjeta |
| `plantillas.copiar` | `checklists,labels` | Qué partes se copian de la plantilla |
| `cierre.criterio` | `checklist` | `checklist` · `auto` · `marcada` |

> En `plantillas.copiar` puedes añadir `members`, `attachments`, `comments`,
> `stickers` o `all`. **No pongas `due` ni `start`**: las fechas las calcula el
> robot con el horario del día, no se heredan de la plantilla.

### Cuántas listas de cierre quieres

Sale de lo que declaren las familias. Lo que se **crea** y lo que se **barre**
salen de la misma fuente, así que no pueden descuadrarse:

| Lo que quieras | Qué haces |
|---|---|
| Una por grupo *(por defecto)* | Acero por un lado, encofrado y concreto juntos, el resto |
| **Una sola** | El mismo nombre en todas las familias |
| Una por familia | Un nombre distinto en cada una |

---

## 🕐 Las horas y los relojes

Hay **dos clases de hora** y conviene no confundirlas:

**JORNADA** — se escribe **dentro** de cada tarjeta. Es el `Vencimiento` que ve
el equipo en Trello. No ejecuta nada.

**RELOJES** — despiertan a cada robot. No aparecen en ninguna tarjeta.

Un horario que funciona: jornada hasta 18:30, cierre de gracia 18:30, cierre
definitivo 21:00 (tres horas de margen para marcar), archivado 22:00.

### Los dos relojes

GitHub Actions **no es puntual**: retrasa y a veces descarta las tareas
programadas. Por eso hay dos relojes apuntando a la misma hora:

- Un **servicio de cron externo** dispara el workflow por la API. Ese es el
  puntual, el que hace el trabajo.
- El **cron de GitHub** es la red de seguridad. Cuando llega —tarde— se encuentra
  el trabajo hecho y no repite nada.

Los cron están en los minutos **7 y 37**, nunca en punto ni a la media: son las
horas de mayor congestión y GitHub descarta citas ahí. El portero
(`trello_auto/portero.py`) deja pasar solo las citas dentro de una ventana de 90
minutos desde la hora configurada, así que perder una cita no cuesta el día.

---

## 🌐 Las páginas web

Se publican con **GitHub Pages** desde `docs/`. Actívalo una vez en
Settings → Pages → *Deploy from a branch* → `main` → `/docs`.

| Página | Qué muestra |
|---|---|
| `index.html` | **Dashboard**: resumen, y luego un bloque por ámbito (día · por cerrar) con su anillo y sus pendientes, más el control general con avance de obra, tendencias y desgloses |
| `mapeo.html` | **Mapeo**: a qué familia y lista va cada actividad, y cuáles piden atención |
| `tablero.html` | **Estado del tablero**: qué papel juega cada lista, cuáles no toca nadie y cuántas tarjetas quedarían atrapadas |

Son **autocontenidas**: los datos van dentro del archivo y no piden nada por
internet. Se pueden descargar, mandar por correo o abrir sin conexión, y siguen
funcionando aunque el repositorio pase a privado.

### Los datos en bruto

| Archivo | Qué es |
|---|---|
| `reportes/ultimo.csv` | La foto del tablero ahora: una fila por tarjeta. Lo lee el dashboard y **se reemplaza en cada corte** |
| `reportes/culminadas.csv` | Cuántas tarjetas se culminaron cada día. Es la **memoria del avance**, y de ahí sale la gráfica de tendencia |

Del pasado solo se guarda lo cumplido, porque es lo único que hace falta para
el avance: lo que sigue abierto ya se ve en el tablero y en el bloque *Por
cerrar* del dashboard.

---

## 🔧 Los botones de mantenimiento

| Botón | Para qué |
|---|---|
| **Configurar** | Cambia horas, forma del Excel, criterio de cierre y tablero |
| **Sincronizar** | Relee el Excel y el tablero; regenera mapeo, respaldo y las tres páginas |
| **Cambiar una actividad del mapeo** | Corrige una actividad suelta sin descargar nada |
| **Aplicar mapeo revisado** | Aplica el cuadro Excel con desplegables, para cambios masivos |
| **Montar tablero** | Crea columnas y plantillas genéricas desde el cronograma |
| **Limpiar duplicadas** | Archiva copias vacías; nunca las que tienen trabajo |
| **Reubicar tarjetas de una lista** | Vacía una columna repartiendo por familia; sirve también para deshacer |
| **Arranque de la obra** | Declara qué parte ya estaba hecha antes de entrar el sistema |

### El cuadro de verificación del mapeo

Revisar el mapeo escribiendo dentro de un JSON es pedir una errata. Por eso
Sincronizar genera `mapeo/revisar_mapeo.xlsx`, donde **no se escribe: se elige**.
`FAMILIA` y `LISTA DESTINO` son desplegables con las opciones válidas, sacadas de
tu configuración y de los nombres reales de tus listas. Las filas que piden
atención salen en **ámbar**.

Para *saber* si hace falta corregir algo no descargues nada: mira `mapeo.html`.

Y para una corrección suelta, el botón **Cambiar una actividad** acepta un trozo
del nombre (`acero inferior` basta) y, si es ambiguo o no existe, **sugiere en
vez de aplicar un cambio equivocado**.

### Limpiar duplicadas

**Duplicada = el nombre completo idéntico**: sector, actividad *y* fecha. No se
compara por trozos, así que `ACERO DE ZAPATA` y `ACERO DE COLUMNA` nunca se
confunden. Lo único que se ignora son acentos, mayúsculas, emojis y el tipo de
guion — justo lo que hace que dos tarjetas iguales *parezcan* distintas.

Solo archiva una copia si **no** tiene ni un check marcado, ni comentarios, ni
adjuntos. Y **archiva, no borra**: en Trello se recupera desde el menú del
tablero.

### Reubicar tarjetas de una lista

Vacía una columna repartiendo cada tarjeta a la lista de **por cerrar** de su
familia, y archiva la columna si se lo pides. Se hizo para retirar la vieja
`NO CUMPLIDAS`, pero sirve para cualquier columna heredada de otro tablero.

| Campo | Qué poner |
|---|---|
| `desde` | Palabra clave de la columna a vaciar (ej. `NO CUMPLIDAS`) |
| `dry_run` | **Empieza siempre en `true`**: te enseña el reparto sin mover nada |
| `archivar_lista` | `true` para archivar la columna cuando quede vacía |
| `a_lista` | Vacío = repartir por familia. Con un nombre, todo va a esa lista |

`a_lista` es el que sirve para **deshacer**: si algo se cerró antes de tiempo,
lo devuelves con `desde: CULMINADO` y `a_lista: T. POR CERRAR - ACERO`. En los
dos sentidos, y sin abrir tarjeta por tarjeta.

Es idempotente: la tarjeta que ya está en su destino ni se toca. Y nada se
borra — la tarjeta conserva descripción, checklists, etiquetas, comentarios e
historial, y una lista archivada se recupera desde *Más → Listas archivadas*.

---

## 💻 Desde tu PC

**Esto es opcional. No hace falta para que la obra funcione.** Todo corre solo
en GitHub, con los Secrets que ya pusiste ahí. Esta sección es para el día que
quieras probar algo en tu computadora antes de soltarlo en el tablero real.

### ¿Qué es `config.py` y por qué habría que configurarlo?

`config.py` **existe solo en tu computadora**. Es el sustituto local de los
Secrets de GitHub, y nada más.

El programa busca la clave y el token de Trello en este orden:

1. **Variables de entorno** ← es lo que le llega desde los Secrets, en GitHub
2. **`config.py`** ← solo existe en tu PC
3. Si no encuentra ninguna de las dos, se detiene y te lo dice

En GitHub siempre gana el paso 1, así que **`config.py` nunca se usa allí**.
De hecho `.gitignore` lo bloquea: no se sube nunca, para que tus credenciales
no acaben publicadas en el repositorio.

Por eso, si trabajas solo con los botones de GitHub, **no tienes que configurar
nada en tu PC**. Solo lo necesitas si vas a correr los scripts localmente, y en
ese caso son dos datos:

```bash
pip install -r requirements.txt
cp config.example.py config.py     # y pon dentro TRELLO_KEY y TRELLO_TOKEN
```

Los sacas de <https://trello.com/power-ups/admin> — son los mismos que ya
guardaste como Secrets. Todo lo demás (el tablero, las familias, las horas) sale
de `configuracion.json`, que sí está en el repositorio y es igual en los dos
sitios.

### Los comandos

```bash
python -m trello_auto.preparar --fecha manana --dry-run
python -m trello_auto.distribuir --dry-run
python -m trello_auto.cierre --dry-run                 # fase de gracia
python -m trello_auto.cierre --fase final --dry-run    # cierre definitivo
python -m trello_auto.reporte --alcance todo
python -m trello_auto.archivar --dry-run
python -m trello_auto.limpiar_duplicadas --dry-run
python -m trello_auto.reubicar --desde "NO CUMPLIDAS" --dry-run
python -m trello_auto.montar_tablero --dry-run
python -m trello_auto.arranque --ver
python -m trello_auto.sincronizar
python -m trello_auto.configurar --ver
python -m trello_auto.revisar --vista
```

Todos aceptan `--dry-run`: muestran qué harían sin tocar nada.

### Revisar el codigo

```bash
pip install -r requirements-dev.txt
ruff check trello_auto
```

---

## Qué hay en cada archivo

| Ruta | Qué es |
|---|---|
| `configuracion.json` | **Toda la obra**: horas, listas, familias, responsables, Excel |
| `mapeo.json` | Actividad → familia → lista destino. Lo genera Sincronizar |
| `trello_auto/ajustes.py` | Lee la configuración y la resuelve por prioridad |
| `trello_auto/cronograma.py` | Lee el Excel (o el respaldo) y clasifica |
| `trello_auto/trello.py` | Cliente de la API, plantillas y conteo de checklists |
| `trello_auto/horario.py` | Zonas horarias, conversiones y el portero |
| `trello_auto/preparar.py` … `archivar.py` | Los seis robots |
| `trello_auto/reporte.py` · `tablero.py` · `web.py` | El corte y las páginas |
| `trello_auto/historico.py` | Culminadas por día y series de tendencia |
| `trello_auto/arranque.py` | Lo que ya estaba hecho antes de entrar el sistema |
| `trello_auto/estado.py` | Qué papel juega cada lista del tablero |
| `trello_auto/sincronizar.py` · `configurar.py` · `revisar.py` | Los botones |
| `trello_auto/montar_tablero.py` · `limpiar_duplicadas.py` · `reubicar.py` | Mantenimiento |
| `data/` | El cronograma y su respaldo |
| `reportes/` | La foto de ahora y las culminadas por día |
| `docs/` | Lo que publica GitHub Pages |

---

## Próximos pasos

- **Las plantillas que faltan.** Cada actividad sin plantilla sale sin su control
  de calidad real. `mapeo.html` te dice cuáles.
- **Causas de no cumplimiento.** Saber *por qué* no se cumplió cierra el ciclo de
  mejora del Last Planner. Se puede capturar con una etiqueta y contarlo.
- **Responsable por cuadrilla**, desde la columna OPER/OFIC del Excel.
- **El cron externo**, para que los relojes sean puntuales.

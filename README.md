# Automatización Trello — Construcción de Aulas

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

Crea automáticamente las tarjetas de cada día en Trello a partir del cronograma
Excel (Last Planner System), **copiando la tarjeta PLANTILLA de cada actividad**
desde el propio tablero (con su descripción y sus checklists), con **hora de
inicio y hora de fin**, y al final de la jornada mueve cada tarjeta según su
estado. Reproduce, sin intervención humana, lo que hoy se hace a mano.

Todo corre en **GitHub Actions**: gratis, en la nube, sin depender de tu PC.

> **Las horas se cambian desde el navegador, con un botón.** No hay que entrar
> al código nunca. Ver [Cambiar la hora](#-cambiar-la-hora-sin-tocar-el-código).

---

## Contenido

| Ruta | Qué es |
|---|---|
| `trello_auto/crear_tarjetas.py` | **Automatización 1.** Lee el cronograma y crea las tarjetas del día en Trello. |
| `trello_auto/cierre_del_dia.py` | **Automatización 2.** Al cierre, mueve lo terminado a *CULMINADO* y lo pendiente a *T. NO CUMPLIDAS*. |
| `trello_auto/portero.py` | Decide si la corrida programada es la de la hora configurada. Es lo que permite cambiar la hora sin tocar el código. |
| `trello_auto/guardar_horario.py` | Valida y guarda `horario.json` (lo usa el botón "Cambiar horario"). |
| `trello_auto/settings.py` | Configuración efectiva (credenciales, listas, horas, checklists). |
| `trello_auto/trello.py` | Cliente de la API de Trello (con reintentos). |
| `trello_auto/excel.py` | Lectura de la hoja `01_MAESTRO` del cronograma. |
| `horario.json` | **Las horas vigentes.** Lo escribe el workflow "Cambiar horario". |
| `data/` | Cronograma (`.xlsx`) y su respaldo ya procesado (`plan_obra.json`). |
| `.github/workflows/` | Los relojes automáticos y el CI. |
| `tests/` | Pruebas automáticas (no tocan Trello). |
| `config.example.py` | Plantilla de configuración local. Cópiala a `config.py`. |

---

## Cómo funciona

El Excel, en la hoja `01_MAESTRO`, tiene una fila de **fechas** y, por cada
**actividad** (fila), el código de **sector** (`1CS6`, `2PS13`…) escrito justo en
la columna del día que le toca. El script:

1. **Ubica la columna** de la fecha pedida y toma las actividades con sector ese día.
2. **Clasifica** cada una por tipo de trabajo (Acero / Encofrado / Concreto / Varios)
   según el nombre de la actividad.
3. **Busca su tarjeta PLANTILLA** en el tablero. Una tarjeta es plantilla porque
   **su propio nombre lo dice** (`PLANTILLA — ACERO EN ZAPATAS`), viva en la lista
   que viva: así una errata en el encabezado de una columna no deja fuera a las
   plantillas que contiene. Tolera `PLANTILA`, `PLANTILLAS`, emojis y guiones. El
   emparejamiento se hace **leyendo el tablero en vivo**, comparando nombres sin
   acentos ni símbolos — sin ningún ID escrito en el código.
4. **Crea la tarjeta** `SECTOR — ACTIVIDAD — DD/MM/AAAA` en la lista del día correcta:
   - **copiando de la plantilla** su **descripción**, **todos sus checklists** con
     sus ítems y sus **etiquetas** (vía `idCardSource` + `keepFromSource` de la API
     de Trello);
   - con **hora de inicio** (`HORA_INICIO`) y **hora de fin** (`HORA_FIN`) de ese día,
     en la hora local de la obra (por defecto 07:00 → 17:00, `America/Lima`).

Si una actividad **todavía no tiene plantilla** (fases más avanzadas: losas,
tarrajeos, acabados…), la tarjeta se crea igual, con una descripción generada y el
**checklist de respaldo** de su tipo de trabajo (`settings.CHECKLIST_POR_TIPO`), para
no dejarla sin control de calidad. En cuanto agregues esa plantilla al tablero, el
script la usa automáticamente en la siguiente corrida.

Es **idempotente**: si una tarjeta con ese nombre ya existe, no la duplica. Puedes
correrlo las veces que quieras.

### Cierre del día: cuándo cuenta como terminada

`cierre_del_dia.py` recorre las listas del día (y *EN EJECUCIÓN*) y mueve cada
tarjeta a *CULMINADO* o a *T. NO CUMPLIDAS*. El criterio se configura con
`CRITERIO_CIERRE`:

| Criterio | Una tarjeta está terminada si… |
|---|---|
| `checklist` *(por defecto)* | **todos** los ítems de sus checklists están marcados. Manda el control de calidad: no basta con tildar la tarjeta, y si le falta un ítem (o no tiene checklist) se va a *NO CUMPLIDAS* |
| `auto` | está marcada como completa **o** tiene su checklist 100% marcado |
| `marcada` | está marcada como completa en Trello |

Todas las tarjetas que crea la automatización llevan checklist —el de su plantilla,
o el de respaldo—, así que siempre hay algo que evaluar. Una tarjeta agregada a mano
al tablero, sin checklist, contará como no cumplida.

También puedes elegir otro criterio en cada corrida manual, desde el botón
*Run workflow* (déjalo en `configurado` para usar el de siempre).

### Qué se copia de la plantilla, y qué no

La API de Trello obliga a **listar** qué partes traer al duplicar una tarjeta: lo
que no se pide, no se copia. Eso se controla con `COPIAR_DE_PLANTILLA`, que por
defecto vale `checklists,labels`. Puedes añadir `members`, `attachments`,
`comments`, `stickers`, `customFields`, o poner `all` para traer todo.

**No pongas `due` ni `start`**: las fechas las calcula el script con el horario del
día, no las hereda de la plantilla. La **descripción** se copia siempre, aparte.

Así, todo lo que quieras que lleven las tarjetas —ítems de calidad, etiquetas de
color, el texto de la descripción— se edita **en la plantilla dentro de Trello**, y
rige desde el día siguiente sin tocar el código ni subir nada a GitHub.

> ⚠ Los ítems de `CHECKLIST_POR_TIPO` que trae el repo son **genéricos, para no
> dejar tarjetas sin control**. Reemplázalos por tu plantilla real de calidad
> cuando la tengas — o, mejor, crea la tarjeta PLANTILLA en el tablero: siempre
> gana la plantilla sobre el respaldo.

---

## 🚀 Puesta en marcha en GitHub (una sola vez)

**1. Crea un repositorio PRIVADO** en GitHub (importante: privado, para que tu
cronograma no quede público) y sube todo el contenido de esta carpeta.

```bash
git init
git add .
git commit -m "Automatización Trello de obra"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

`config.py` no se sube nunca: lo bloquea `.gitignore`.

**2. Crea los Secrets** con tus credenciales (van cifrados):
Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Nombre | Valor |
|---|---|
| `TRELLO_KEY` | tu API Key |
| `TRELLO_TOKEN` | tu Token |

Se obtienen gratis en <https://trello.com/power-ups/admin>: crea un Power-Up (o usa
uno), copia la **API Key** y genera un **Token** con el enlace de esa misma página.

**3. Listo.** Los relojes ya están puestos:

| Workflow | Corre solo | Qué hace |
|---|---|---|
| **1. Crear tarjetas del día** | 06:30, lunes a viernes | Crea las tarjetas del día |
| **2. Cierre del día** | 20:00, lunes a viernes | Mueve lo terminado / pendiente |
| **3. Cambiar horario** | solo a mano | Cambia las horas de todo lo anterior |
| **CI** | en cada cambio | Revisa que el proyecto siga sano |

El `BOARD_ID` por defecto es `gzoZo6ip` (tablero "AULAS — CONTROL DIARIO"). Si
alguna vez cambia de tablero, créalo como **Variable** del repo (no Secret) con
el nombre `BOARD_ID`.

**Costo:** gratis. Un repo privado incluye 2 000 minutos/mes de Actions; este
proyecto usa del orden de 30–40 minutos al mes. No pide tarjeta de crédito.

---

## 🕐 Cambiar la hora sin tocar el código

Este es el punto clave: **la hora no vive en el código**.

GitHub solo acepta un `cron:` fijo dentro del archivo del workflow, así que ahí la
hora sería intocable sin editar código. Por eso el workflow se **despierta cada
media hora** dentro de una franja amplia, y un **portero** (`trello_auto/portero.py`)
solo deja pasar las citas que caen en la ventana que abre a la hora configurada.
Esa hora está en `horario.json`, que se edita desde el navegador.

Los `cron` están puestos en los **minutos 7 y 37, nunca en punto ni a la media**:
GitHub retrasa o descarta las tareas programadas cuando tiene carga, y las horas
en punto son las más congestionadas. Por lo mismo la ventana del portero es ancha
(90 min por defecto): si una cita se pierde, la siguiente todavía sirve. Que entren
dos corridas no hace daño — crear tarjetas no duplica nada, y el cierre no
encuentra nada que mover la segunda vez.

### Opción A — el botón (recomendado)

1. Repo → pestaña **Actions**.
2. Workflow **"3. Cambiar horario"** → botón **Run workflow**.
3. Escribe solo lo que quieras cambiar (lo demás, déjalo en blanco):

   | Campo | Qué cambia | Ejemplo |
   |---|---|---|
   | `hora_crear` | a qué hora se **crean** las tarjetas | `07:00` |
   | `hora_cierre` | a qué hora corre el **cierre** | `19:30` |
   | `hora_inicio` | hora de **inicio** de cada tarjeta | `08:00` |
   | `hora_fin` | hora de **fin / vencimiento** de cada tarjeta | `18:00` |
   | `dias_habiles` | qué días corre (1 = lunes … 7 = domingo) | `1-5`, `1-6`, `1,3,5` |
   | `tz_obra` | zona horaria de la obra | `America/Lima` |

4. **Run workflow** verde. El workflow valida las horas, guarda `horario.json` y
   hace el commit por ti. **Desde la siguiente corrida ya rige la hora nueva.**

Si escribes una hora imposible (`25:00`) o una zona horaria que no existe, falla ahí
mismo con un mensaje claro y no guarda nada.

### Opción B — Variables del repositorio

Settings → Secrets and variables → **Actions** → pestaña **Variables** →
*New repository variable*. Las Variables **mandan por encima** de `horario.json`:

`HORA_CREAR`, `HORA_CIERRE`, `HORA_INICIO`, `HORA_FIN`, `DIAS_HABILES`, `TZ_OBRA`,
`BOARD_ID`.

### Opción C — solo para una corrida

En **"1. Crear tarjetas del día"** → *Run workflow*, los campos `hora_inicio` y
`hora_fin` cambian el horario **solo de esa corrida**, sin guardar nada.

### Sobre el cambio de horario (DST)

Todo se calcula en la zona horaria de la obra (`TZ_OBRA`, por defecto
`America/Lima`), nunca sumando "−5" a mano. Si la obra se mudara a una zona con
horario de verano, basta con poner esa zona en `tz_obra` y el ajuste estacional lo
hace solo.

**Franjas que cubre el reloj**, sin tocar nada:

- Crear tarjetas: cualquier hora entre las **04:00 y las 12:30**.
- Cierre del día: cualquier hora entre las **16:00 y las 23:30**.

Si alguna vez necesitas una hora fuera de esas franjas, es la única línea que se
edita: el `cron:` del workflow correspondiente.

---

## 🖱 Correr a mano, desde el navegador

No hace falta tu PC ni la terminal. Repo → **Actions** → workflow → **Run workflow**:

**1. Crear tarjetas del día**

| Campo | Para qué |
|---|---|
| `fecha` | `AAAA-MM-DD` o `hoy` |
| `fecha_fin` | opcional; corre cada día del rango (ej. toda la semana de un golpe) |
| `tipo` | `TODOS`, `ACERO`, `ENCOFRADO`, `CONCRETO`, `VARIOS` |
| `hora_inicio` / `hora_fin` | horario solo para esta corrida |
| `dry_run` | muestra qué crearía **sin crear nada** |

**2. Cierre del día**: `criterio` (`configurado` / `checklist` / `auto` / `marcada`) y
`dry_run`, por si quieres forzar un cierre fuera de horario o ver antes qué movería.

Cada corrida manual pesa lo mismo que la automática (~1 minuto) y queda su registro
completo en el log.

---

## 💻 Uso desde tu PC (opcional)

```bash
pip install -r requirements.txt
cp config.example.py config.py       # y completa tus credenciales
```

```bash
# Ver qué crearía, sin crear nada:
python crear_tarjetas.py --fecha 2026-08-27 --dry-run

# Crear las de un día / las de hoy:
python crear_tarjetas.py --fecha 2026-08-27
python crear_tarjetas.py --fecha hoy

# Toda la semana de un golpe:
python crear_tarjetas.py --fecha 2026-08-26 --fecha-fin 2026-08-29

# Solo un tipo de trabajo:
python crear_tarjetas.py --fecha hoy --tipo CONCRETO
python crear_tarjetas.py --fecha 2026-08-26 --fecha-fin 2026-09-04 --tipo ACERO

# Con otro horario solo para esta corrida:
python crear_tarjetas.py --fecha hoy --hora-inicio 08:00 --hora-fin 18:00

# Cierre del día:
python cierre_del_dia.py --dry-run
python cierre_del_dia.py --criterio checklist

# Ver o cambiar el horario guardado:
python -m trello_auto.guardar_horario --ver
python -m trello_auto.guardar_horario --hora-crear 07:00 --hora-fin 18:00
```

Los `dry-run` **leen** el tablero (para decirte si cada actividad tiene plantilla)
pero no escriben nada. Sin credenciales funcionan igual, solo con el cronograma.

### Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q          # 26 pruebas, ninguna toca Trello
ruff check trello_auto tests
```

---

## Configuración disponible

Todo se resuelve por prioridad: **variable de entorno** → **`horario.json`** →
**`config.py`** → valor por defecto.

| Nombre | Por defecto | Qué es |
|---|---|---|
| `TRELLO_KEY`, `TRELLO_TOKEN` | — | Credenciales (Secrets en GitHub) |
| `BOARD_ID` | `gzoZo6ip` | Tablero destino |
| `RUTA_EXCEL` | `data/5__LPS_PLANNING_REV_9.xlsx` | Cronograma |
| `TZ_OBRA` | `America/Lima` | Zona horaria de la obra |
| `HORA_INICIO` / `HORA_FIN` | `07:00` / `17:00` | Jornada (inicio y fin de cada tarjeta) |
| `HORA_CREAR` / `HORA_CIERRE` | `06:30` / `20:00` | Hora de cada automatización |
| `DIAS_HABILES` | `1-5` | Días que corre (1 = lunes) |
| `CRITERIO_CIERRE` | `checklist` | `checklist` / `auto` / `marcada` |
| `COPIAR_DE_PLANTILLA` | `checklists,labels` | Qué partes de la plantilla se copian |
| `VENTANA_MIN` | `90` | Tolerancia del portero, en minutos |

Los **nombres de listas** se resuelven por **palabra clave** (sin acentos ni
emojis), así que siguen funcionando aunque renombres una lista en Trello:
`T. DEL DÍA ACERO- 🟦🟦🟦🟦🟦` se encuentra buscando `T. DEL DIA ACERO`.

---

## Butler (alternativa sin código para el cierre)

El movimiento "terminada → CULMINADO / no terminada → NO CUMPLIDAS" también se
puede hacer **sin servidor**, con **Butler**, la automatización nativa y gratuita de
Trello (menú del tablero → Automatización → Butler). Ejemplo de regla:

> **Cada día a las 20:00**, en la lista "T. DEL DÍA ACERO…", mueve las tarjetas
> marcadas como completas a "CULMINADO 🎯" y las no completas a
> "T. NO CUMPLIDAS 🆘". (Repetir por cada lista del día.)

Pero Butler **solo puede mirar la marca de "completa"**: no sabe leer el checklist
ítem por ítem. Como aquí el cierre lo decide el control de calidad, `cierre_del_dia.py`
es la opción que hace lo que necesitas; Butler queda como plan B.

---

## Datos del cronograma actual

- **1 447** tareas a lo largo de todo el plan.
- **75** días con trabajo, del **12/08/2026** al **24/11/2026**.
- **75** actividades distintas; **17** ya cubiertas por plantillas del tablero
  (fase de cimentación, ~24 tarjetas plantilla).
- Distribución por tipo: Varios 474 · Concreto 369 · Acero 305 · Encofrado 299.

---

## Próximas mejoras

- Crear las **plantillas restantes** (losas, tarrajeos, acabados) para que todo el
  plan salga con su checklist real.
- Asignar **responsable** por tarjeta según la cuadrilla (columna OPER/OFIC) →
  habilita el recordatorio por persona.
- **Etiquetas de color** por cuadrilla.
- Adjuntar **metrado y rendimiento** (hoja PROPUESTA) en la descripción.

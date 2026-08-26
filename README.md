# Automatización Trello — Construcción de Aulas

Crea automáticamente las tarjetas de cada día en Trello a partir del
cronograma Excel (Last Planner System), y gestiona su cambio de estado al
cierre de la jornada. Reproduce la lógica que hoy se hace a mano.

---

## Qué incluye

| Archivo | Función |
|---|---|
| `crear_tarjetas.py` | **Automatización 1.** Lee el Excel y crea las tarjetas del día en Trello, en su lista por tipo de trabajo, con fecha de vencimiento. |
| `cierre_del_dia.py` | **Automatización 2.** Al cierre del día, mueve lo completado a *Terminadas* y lo pendiente a *No cumplidas*. |
| `config.example.py` | Plantilla de configuración. Cópiala a `config.py` y complétala. |
| `requirements.txt` | Dependencias. |

---

## Cómo funciona (la lógica)

El Excel, en la hoja `01_MAESTRO`, tiene una fila de **fechas** y, por cada
**actividad** (fila), el código de **sector** (`1CS6`, `2PS13`…) escrito justo
en la columna del día que le toca. El script:

1. Ubica la columna de la fecha pedida.
2. Recorre todas las actividades y toma las que tienen sector ese día.
3. Clasifica cada una por tipo (Acero / Encofrado / Concreto / Varios) según
   el nombre de la actividad.
4. Crea la tarjeta `SECTOR — ACTIVIDAD` en la lista correcta, con vencimiento
   ese día a las 17:00 (hora Perú).

Es **idempotente**: si una tarjeta ya existe con ese nombre, no la duplica.
Puedes correrlo las veces que quieras.

---

## Instalación

```bash
pip install -r requirements.txt
cp config.example.py config.py     # y completa tus credenciales
```

### Credenciales de Trello (gratis)
1. Entra a https://trello.com/power-ups/admin y crea un Power-Up (o usa uno).
2. Copia tu **API Key**.
3. Genera un **Token** (botón "Token" en esa misma página).
4. Pégalos en `config.py` (o mejor, expórtalos como variables de entorno
   `TRELLO_KEY` y `TRELLO_TOKEN`).

El **BOARD_ID** ya está puesto: `gzoZo6ip` (tablero "AULAS — CONTROL DIARIO
(MEJORADO)").

---

## Uso

```bash
# Ver qué crearía el 26/08 SIN crear nada:
python crear_tarjetas.py --fecha 2026-08-26 --dry-run

# Crear las tarjetas del 26/08:
python crear_tarjetas.py --fecha 2026-08-26

# Crear las de hoy:
python crear_tarjetas.py --fecha hoy

# Cierre del día (mover por estado):
python cierre_del_dia.py
```

Para cargar varios días de golpe (ej. toda la semana):

```bash
for d in 2026-08-26 2026-08-27 2026-08-28 2026-08-29; do
    python crear_tarjetas.py --fecha $d
done
```

---

## ⭐ Automatización diaria con GitHub Actions (recomendado)

Es la vía más simple y gratis para que corra solo cada día. Pasos:

**1. Crea un repositorio PRIVADO en GitHub** (importante que sea privado, para
que tu cronograma no quede público).

**2. Sube estos archivos al repo** (todos los de esta carpeta), incluyendo:
   - `crear_tarjetas.py`, `cierre_del_dia.py`, `settings.py`
   - `requirements.txt`
   - `5__LPS_PLANNING_REV_9.xlsx` (tu Excel)
   - la carpeta `.github/workflows/crear_tarjetas.yml`
   - NO subas `config.py` (no lo necesitas en GitHub; el `.gitignore` ya lo bloquea).

**3. Crea los Secrets** (tus credenciales, cifradas):
   - En el repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   - Crea dos:
     - Nombre `TRELLO_KEY`   → valor: tu API Key
     - Nombre `TRELLO_TOKEN` → valor: tu Token

**4. Listo.** El workflow ya está configurado para correr **de lunes a viernes
a las 6:30 a.m. hora Perú**. Puedes probarlo a mano: pestaña **Actions** →
elige el workflow → botón **Run workflow**.

Para cambiar la hora, edita la línea `cron:` en
`.github/workflows/crear_tarjetas.yml` (está en horario UTC; Perú = UTC-5).

**Costo:** gratis. Un repo privado tiene 2,000 minutos/mes de Actions; tú usas
~1 minuto al día. No pide tarjeta de crédito.

---

## Automatización diaria en Google Cloud

La idea es que corra solo cada mañana. Con **Cloud Functions + Cloud
Scheduler**:

1. Sube esta carpeta como una Cloud Function (entry point que llame a
   `crear_tarjetas` con `--fecha hoy`).
2. Guarda `TRELLO_KEY` y `TRELLO_TOKEN` como **variables de entorno** o en
   Secret Manager (nunca en el código).
3. Crea un **Cloud Scheduler** con expresión cron, p. ej. cada día laborable
   a las 06:30 hora Perú:
   ```
   30 6 * * 1-5      (zona horaria America/Lima)
   ```
4. El Excel debe estar accesible para la función: lo más simple es subirlo a
   un bucket de Cloud Storage y que el script lo lea desde ahí (ajusta
   `RUTA_EXCEL`).

Volumen: 1 ejecución al día entra de sobra en la **capa gratuita** de Google
Cloud. Costo ≈ $0/mes.

---

## Butler (alternativa sin código para el cierre)

El movimiento "no completada → No cumplidas / completada → Terminadas" se
puede hacer **sin servidor** con **Butler**, la automatización nativa de
Trello (menú del tablero → Automatización → Butler). Ejemplo de regla:

> **Cada día a las 20:00**, ordena el tablero:
> mueve todas las tarjetas de la lista "🟦 ACERO — DÍA" que estén marcadas como
> completas a la lista "🎯 T. TERMINADAS", y las no completas a "🆘 T. NO
> CUMPLIDAS". (Repetir por cada lista del día.)

Butler es gratis para un volumen normal y no necesita Google Cloud. Es la vía
recomendada para el **cierre**; el script `cierre_del_dia.py` queda como
alternativa si prefieres controlarlo todo desde un mismo lugar.

---

## Datos verificados de tu cronograma

- **1 447** tarjetas en total a lo largo del plan.
- **75** días con trabajo, del **12/08/2026** al **24/11/2026**.
- Distribución: Varios 474 · Concreto 369 · Acero 305 · Encofrado 299.

---

## Próximas mejoras (ideas)

- Asignar **responsable** a cada tarjeta según la cuadrilla (columna OPER/OFIC
  del Excel) → habilita el recordatorio por WhatsApp por persona.
- Añadir **etiquetas de color** por cuadrilla.
- Insertar un **checklist de control de calidad** por tipo de actividad
  (liberación, dimensiones, recubrimiento…).
- Adjuntar a cada tarjeta el **metrado y rendimiento** (hoja PROPUESTA) en la
  descripción.

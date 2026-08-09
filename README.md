# Asistente personal (Telegram + Notion + Google Calendar)

Un bot de Telegram que hace de secretaria: le escribes en lenguaje natural y él
gestiona tus **tareas en Notion** y tu **Google Calendar** usando Claude como
cerebro. También te manda **recordatorios** de tus próximos eventos.

```
        Tú (Telegram)
             │  "agenda dentista mañana a las 10"
             ▼
        bot.py  ──►  agent.py (Claude decide qué hacer)
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        notion_tools.py         calendar_tools.py
         (tareas)                (eventos)
```

---

## Cómo funciona (en 1 minuto)

1. Escribes por Telegram.
2. `bot.py` recibe el texto y se lo pasa a `agent.py`.
3. Claude lee tu mensaje y decide si tiene que **crear una tarea**, **listar el
   calendario**, **agendar un evento**, etc. Llama a la "herramienta" adecuada.
4. La herramienta habla con la API real de Notion o Google Calendar.
5. Claude te responde en español confirmando lo que hizo.

---

## Requisitos previos

- **Python 3.10 o superior** instalado en tu PC. Compruébalo con `python3 --version`.
  Si no lo tienes: https://www.python.org/downloads/
- Una cuenta en Anthropic, Notion y Google.

---

## Paso 1 — Descargar y preparar el proyecto

Abre una terminal dentro de la carpeta `asistente` y crea un entorno virtual
(recomendado para no ensuciar tu Python):

```bash
cd asistente
python3 -m venv .venv
source .venv/bin/activate        # En Windows:  .venv\Scripts\activate
pip install -r requirements.txt
```

Copia el archivo de ejemplo de claves:

```bash
cp .env.example .env             # En Windows:  copy .env.example .env
```

Iremos rellenando `.env` en los siguientes pasos.

---

## Paso 2 — Clave de Anthropic (el cerebro)

1. Entra en https://console.anthropic.com → **API Keys** → **Create Key**.
2. Copia la clave (empieza por `sk-ant-...`).
3. Pégala en `.env` en `ANTHROPIC_API_KEY=`.

> Nota: usar la API tiene un coste por uso (muy bajo para uso personal). Necesitas
> añadir saldo/crédito en la consola de Anthropic.

---

## Paso 3 — Crear el bot de Telegram

1. En Telegram, busca **@BotFather** y ábrelo.
2. Envía `/newbot` y sigue las instrucciones (nombre y un @usuario que termine en `bot`).
3. Te dará un **token** (algo como `123456789:AAxxxx...`). Pégalo en `.env` en
   `TELEGRAM_BOT_TOKEN=`.
4. Ahora obtén **tu chat_id**: busca **@userinfobot**, ábrelo y te dirá tu ID
   numérico. Pégalo en `.env` en `TELEGRAM_ALLOWED_CHAT_ID=`.
   (Esto hace que **solo tú** puedas usar el bot y que los recordatorios te lleguen a ti.)

---

## Paso 4 — Conectar Notion

1. Ve a https://www.notion.so/my-integrations → **New integration**.
   - Ponle un nombre (ej. "Asistente"), tipo **Internal**.
   - Copia el **Internal Integration Token** (`ntn_...` o `secret_...`) → `.env` en `NOTION_TOKEN=`.
2. Crea (o abre) una base de datos de tareas en Notion con estas propiedades:
   - **Nombre** → tipo *Title* (ya viene por defecto).
   - **Estado** → tipo *Status* con opciones, por ejemplo, "Pendiente" y "Hecho".
   - **Fecha** → tipo *Date* (opcional).
   > Si usas otros nombres, cámbialos arriba de `tools/notion_tools.py`.
3. **Comparte la base con tu integración**: en la base de datos, botón `•••` (arriba
   a la derecha) → **Connections / Conexiones** → añade tu integración "Asistente".
   (Sin esto, el bot no verá la base.)
4. Copia el **ID de la base de datos**: abre la base como página completa; en la URL
   verás algo como `notion.so/tuespacio/<ESTE_TROZO_DE_32_CARACTERES>?v=...`.
   Ese trozo de 32 caracteres es el ID → `.env` en `NOTION_TASKS_DB_ID=`.

---

## Paso 5 — Conectar Google Calendar

Esta es la parte más larga (autorización de Google), pero solo se hace una vez.

1. Ve a https://console.cloud.google.com/ y crea un proyecto (arriba, selector de proyecto → New Project).
2. Menú → **APIs & Services** → **Library** → busca **Google Calendar API** → **Enable**.
3. Menú → **APIs & Services** → **OAuth consent screen**:
   - Tipo **External**, rellena nombre de app y tu email.
   - En **Test users** añade tu propio correo de Gmail. (No hace falta publicar la app.)
4. Menú → **APIs & Services** → **Credentials** → **Create Credentials** →
   **OAuth client ID** → tipo de aplicación **Desktop app**.
5. Descarga el JSON, renómbralo a **`credentials.json`** y ponlo en la carpeta `asistente`.
6. En `.env`, deja `GOOGLE_CALENDAR_ID=primary` (tu calendario principal) y ajusta
   `TIMEZONE=` a tu zona (ej. `America/Mexico_City`, `Europe/Madrid`, `America/Bogota`).

La **primera vez** que arranques el bot se abrirá el navegador para que autorices
el acceso; se creará un `token.json` y ya no te lo volverá a pedir.

---

## Paso 6 — Arrancar el asistente

Con el entorno virtual activado y el `.env` completo:

```bash
python bot.py
```

- La primera vez, autoriza Google en el navegador que se abre.
- Verás en la terminal: *"Asistente en marcha. Escríbele por Telegram."*
- Abre tu bot en Telegram, escribe `/start` y pruébalo.

**Mientras `python bot.py` esté corriendo, el asistente funciona.** Si cierras la
terminal o apagas el PC, se detiene (elegiste correrlo en tu PC). Para tenerlo
siempre encendido tendrías que dejar el PC prendido o, más adelante, moverlo a la nube.

---

## Qué le puedes decir

- "Añade tarea: preparar informe para el jueves"
- "¿Qué tengo pendiente?"
- "Marca como hecha la tarea del informe"
- "¿Qué tengo hoy en el calendario?"
- "¿Y esta semana?"
- "Agenda llamada con Marta mañana a las 16:00 durante 30 minutos"

Él convierte fechas relativas ("mañana", "el viernes") a fechas reales por sí solo.

---

## Recordatorios automáticos

Ya vienen incluidos en `bot.py`:
- Cada **15 min** (configurable con `REMINDER_INTERVAL_MINUTES`) revisa tus
  próximas 24 h y, si hay eventos, te avisa.
- Cada día a las **8:00** te manda el resumen del día.

Puedes cambiar estos horarios en la función `main()` de `bot.py`.

---

## Cómo añadir más capacidades

El patrón para dar una habilidad nueva al asistente es siempre el mismo:

1. Escribe una función Python normal (ej. en un archivo dentro de `tools/`).
2. Añádela a la lista `HERRAMIENTAS` en `agent.py` (nombre, descripción, parámetros).
3. Regístrala en el diccionario `FUNCIONES` de `agent.py`.

Con eso, Claude ya sabrá cuándo usarla. Así podrías añadir Gmail, notas, control
de gastos, etc.

---

## Problemas frecuentes

- **"Faltan variables en tu archivo .env"** → revisa que copiaste `.env.example` a
  `.env` y rellenaste las claves.
- **Notion no encuentra la base / "object not found"** → falta compartir la base
  con la integración (Paso 4.3) o el `NOTION_TASKS_DB_ID` está mal.
- **Google pide autorizar cada vez / error de token** → borra `token.json` y vuelve
  a arrancar para rehacer la autorización.
- **El bot no responde** → confirma que `python bot.py` sigue corriendo y que tu
  `TELEGRAM_ALLOWED_CHAT_ID` es correcto.

---

## Seguridad

- Nunca compartas tu `.env`, `credentials.json` ni `token.json`: contienen accesos.
- El bot solo atiende a tu `chat_id`, así que otras personas no pueden usarlo aunque
  encuentren su nombre.

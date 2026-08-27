"""Punto de entrada: arranca el bot de Telegram.

Ejecuta:  python bot.py
"""
import datetime as dt
import logging

import pytz
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import os
import tempfile

import config
import agent
from tools import calendar_tools, brief_tools, voz_tools, notion_tools, ordenes_tools

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("asistente")

TZ = pytz.timezone(config.TIMEZONE)

# Historial de conversación por chat (en memoria; se borra al reiniciar)
HISTORIALES: dict[int, list] = {}


def _autorizado(update: Update) -> bool:
    """Solo responde al chat permitido (tu propio chat)."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return True  # sin restricción si no lo configuraste
    return str(update.effective_chat.id) == str(config.TELEGRAM_ALLOWED_CHAT_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu asistente. Puedes pedirme cosas como:\n"
        "• Añade tarea: llamar al dentista mañana\n"
        "• ¿Qué tareas tengo pendientes?\n"
        "• ¿Qué tengo hoy en el calendario?\n"
        "• Agenda reunión con Ana el viernes a las 10\n"
        "• Marca como hecha la tarea del dentista\n\n"
        f"(Tu chat_id es {update.effective_chat.id})"
    )


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return

    chat_id = update.effective_chat.id
    texto = update.message.text
    log.info("Mensaje de %s: %s", chat_id, texto)

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    historial = HISTORIALES.setdefault(chat_id, [])
    try:
        respuesta = agent.responder(texto, historial)
    except Exception as e:
        log.exception("Error en el agente")
        respuesta = f"Ups, hubo un error: {e}"
    # Evita que el historial crezca sin límite
    if len(historial) > 40:
        del historial[:-40]
    await update.message.reply_text(respuesta)


_YA_RECORDADOS = set()


async def recordatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    """Avisa UNA sola vez de cada evento, ~30 min antes de que empiece."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return
    try:
        proximos = calendar_tools.eventos_por_empezar(30)
    except Exception as e:
        log.warning("No pude revisar el calendario: %s", e)
        return
    for eid, titulo, cuando in proximos:
        if eid in _YA_RECORDADOS:
            continue
        _YA_RECORDADOS.add(eid)
        await context.bot.send_message(
            chat_id=config.TELEGRAM_ALLOWED_CHAT_ID,
            text=f"🔔 En breve, señor: {cuando} — {titulo}",
        )


async def brief_matutino(context: ContextTypes.DEFAULT_TYPE):
    """Resumen de cada mañana: próximos partidos de Colo-Colo."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return
    try:
        partidos = brief_tools.proximos_partidos_colocolo()
    except Exception as e:
        partidos = f"(no disponible: {e})"
    texto = "☀️ Buenos días.\n\n⚽ Próximos partidos de Colo-Colo:\n" + partidos
    await context.bot.send_message(
        chat_id=config.TELEGRAM_ALLOWED_CHAT_ID, text=texto
    )


async def manejar_voz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe una nota de voz, la transcribe, responde y contesta también en voz."""
    if not _autorizado(update):
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    ruta = os.path.join(tempfile.gettempdir(), f"voz_{chat_id}.oga")
    try:
        archivo = await update.message.voice.get_file()
        await archivo.download_to_drive(ruta)
        texto = voz_tools.transcribir(ruta)
    except Exception as e:
        log.exception("Error transcribiendo voz")
        await update.message.reply_text(f"No pude entender el audio: {e}")
        return

    if not texto:
        await update.message.reply_text("No logré escuchar nada en el audio.")
        return

    historial = HISTORIALES.setdefault(chat_id, [])
    try:
        respuesta = agent.responder(texto, historial)
    except Exception as e:
        log.exception("Error en el agente (voz)")
        respuesta = f"Ups, hubo un error: {e}"
    if len(historial) > 40:
        del historial[:-40]

    await update.message.reply_text(f"🎙️ Entendí: {texto}\n\n{respuesta}")
    try:
        voz = voz_tools.sintetizar(respuesta)
        with open(voz, "rb") as f:
            await update.message.reply_voice(voice=f)
    except Exception as e:
        log.warning("No pude generar la voz de respuesta: %s", e)


async def objetivos_dia(context: ContextTypes.DEFAULT_TYPE):
    """Cada mañana a las 8:30 envía los objetivos del día (tareas pendientes)."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return
    try:
        tareas = notion_tools.listar_tareas(True)
    except Exception as e:
        tareas = f"(no pude leer sus objetivos: {e})"
    await context.bot.send_message(
        chat_id=config.TELEGRAM_ALLOWED_CHAT_ID,
        text="📋 Buenos días, señor. Sus objetivos de hoy:\n" + tareas,
    )


async def revisar_ordenes(context: ContextTypes.DEFAULT_TYPE):
    """Cada minuto revisa si hay órdenes programadas que ya deben ejecutarse."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return
    ahora = dt.datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
    for o in ordenes_tools.ordenes_vencidas(ahora):
        try:
            resultado = agent.responder(o["texto"], [])
        except Exception as e:
            resultado = f"(no pude ejecutarla: {e})"
        await context.bot.send_message(
            chat_id=config.TELEGRAM_ALLOWED_CHAT_ID,
            text=f"⏰ Su orden, señor — «{o['texto']}»:\n{resultado}",
        )


def main():
    config.check()
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    app.add_handler(MessageHandler(filters.VOICE, manejar_voz))

    # Recordatorio periódico + un "resumen" cada mañana a las 8:00
    job = app.job_queue
    job.run_repeating(recordatorio_diario, interval=300, first=30)
    job.run_daily(brief_matutino, time=dt.time(hour=8, minute=0, tzinfo=TZ))
    job.run_daily(objetivos_dia, time=dt.time(hour=8, minute=30, tzinfo=TZ))
    job.run_repeating(revisar_ordenes, interval=60, first=20)

    log.info("Asistente en marcha. Escríbele por Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=-1)


if __name__ == "__main__":
    main()

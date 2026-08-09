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

import config
import agent
from tools import calendar_tools

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


async def recordatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta periódicamente y avisa de eventos cercanos."""
    if not config.TELEGRAM_ALLOWED_CHAT_ID:
        return
    try:
        eventos = calendar_tools.listar_eventos(dias=1)
    except Exception as e:
        log.warning("No pude revisar el calendario: %s", e)
        return
    if eventos and "No hay eventos" not in eventos:
        await context.bot.send_message(
            chat_id=config.TELEGRAM_ALLOWED_CHAT_ID,
            text="🔔 Recordatorio — próximas 24h:\n" + eventos,
        )


def main():
    config.check()
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    # Recordatorio periódico + un "resumen" cada mañana a las 8:00
    job = app.job_queue
    job.run_repeating(
        recordatorio_diario,
        interval=config.REMINDER_INTERVAL_MINUTES * 60,
        first=30,
    )
    job.run_daily(recordatorio_diario, time=dt.time(hour=8, minute=0, tzinfo=TZ))

    log.info("Asistente en marcha. Escríbele por Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

"""Configuración central: carga las variables de entorno del archivo .env."""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TASKS_DB_ID = os.getenv("NOTION_TASKS_DB_ID")

GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Madrid")

REMINDER_INTERVAL_MINUTES = int(os.getenv("REMINDER_INTERVAL_MINUTES", "15"))


def check():
    """Avisa si falta alguna clave importante."""
    faltan = [
        nombre
        for nombre, valor in {
            "GROQ_API_KEY": GROQ_API_KEY,
            "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
            "NOTION_TOKEN": NOTION_TOKEN,
            "NOTION_TASKS_DB_ID": NOTION_TASKS_DB_ID,
        }.items()
        if not valor
    ]
    if faltan:
        raise SystemExit(
            "Faltan variables en tu archivo .env: " + ", ".join(faltan)
        )

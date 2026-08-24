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

# Clave de TheSportsDB para el fútbol ("3" es la de prueba, gratis)
THESPORTSDB_KEY = os.getenv("THESPORTSDB_KEY", "3")

# Voz del asistente (Edge TTS). Voces masculinas maduras:
#   es-ES-AlvaroNeural  (España, distinguido, tipo mayordomo)
#   es-CL-LorenzoNeural (Chile)   es-MX-JorgeNeural (México)
TTS_VOICE = os.getenv("TTS_VOICE", "es-ES-AlvaroNeural")
TTS_RATE = os.getenv("TTS_RATE", "-5%")     # más lento = más pausado
TTS_PITCH = os.getenv("TTS_PITCH", "-8Hz")  # más grave = más solemne

# ---- Spotify (requiere Premium) ----
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")


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

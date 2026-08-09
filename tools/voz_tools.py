"""Voz para Telegram:
  - transcribir(): pasa un audio a texto usando Whisper de Groq (gratis).
  - sintetizar(): convierte texto a un audio de voz en español (gTTS + ffmpeg).

Requiere: la librería gTTS (pip) y el programa ffmpeg (sistema).
"""
import os
import subprocess
import tempfile

from groq import Groq
from gtts import gTTS

import config

_cliente = Groq(api_key=config.GROQ_API_KEY)
STT_MODEL = "whisper-large-v3"


def transcribir(ruta_audio: str) -> str:
    """Convierte un archivo de audio (voz de Telegram) a texto en español."""
    with open(ruta_audio, "rb") as f:
        datos = f.read()
    resultado = _cliente.audio.transcriptions.create(
        model=STT_MODEL,
        file=(os.path.basename(ruta_audio), datos),
        language="es",
    )
    return (resultado.text or "").strip()


def sintetizar(texto: str) -> str:
    """Genera un audio de voz en español y devuelve la ruta a un .ogg (Opus),
    listo para enviarse como nota de voz por Telegram."""
    tmp = tempfile.gettempdir()
    mp3 = os.path.join(tmp, "resp_voz.mp3")
    ogg = os.path.join(tmp, "resp_voz.ogg")

    # acento chileno con tld="cl"
    gTTS(text=texto, lang="es", tld="cl").save(mp3)

    # convertir a OGG/Opus (formato de nota de voz de Telegram) con ffmpeg
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3, "-c:a", "libopus", "-b:a", "32k", ogg],
        check=True,
        capture_output=True,
    )
    return ogg

"""Voz para Telegram:
  - transcribir(): pasa un audio a texto usando Whisper de Groq (gratis).
  - sintetizar(): convierte texto a una voz distinguida en español (Edge TTS).

Requiere: la librería edge-tts (pip) y el programa ffmpeg (sistema).
"""
import os
import shutil
import subprocess
import sys
import tempfile

from groq import Groq

import config

_cliente = Groq(api_key=config.GROQ_API_KEY)
STT_MODEL = "whisper-large-v3"


def transcribir(ruta_audio: str) -> str:
    """Convierte un archivo de audio (voz de Telegram) a texto en español."""
    with open(ruta_audio, "rb") as f:
        datos = f.read()
    resultado = _cliente.audio.transcriptions.create(
        model=STT_MODEL,
        file=("audio.ogg", datos),
        language="es",
    )
    return (resultado.text or "").strip()


def _edge_cmd():
    exe = shutil.which("edge-tts")
    if exe:
        return [exe]
    return [sys.executable, "-m", "edge_tts"]


def sintetizar(texto: str) -> str:
    """Genera una nota de voz en español (voz de mayordomo) y devuelve la ruta
    a un .ogg (Opus), listo para enviarse por Telegram."""
    tmp = tempfile.gettempdir()
    mp3 = os.path.join(tmp, "resp_voz.mp3")
    ogg = os.path.join(tmp, "resp_voz.ogg")

    # Voz distinguida con Edge TTS (masculina madura, configurable en .env)
    subprocess.run(
        _edge_cmd()
        + [
            "--voice", config.TTS_VOICE,
            "--rate", config.TTS_RATE,
            "--pitch", config.TTS_PITCH,
            "--text", texto,
            "--write-media", mp3,
        ],
        check=True,
        capture_output=True,
    )

    # Convertir a OGG/Opus (formato de nota de voz de Telegram)
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3, "-c:a", "libopus", "-b:a", "32k", ogg],
        check=True,
        capture_output=True,
    )
    return ogg

"""Brief matutino: próximos partidos de Colo-Colo.

Obtiene la información buscando en internet mediante el modelo de Groq con
búsqueda web integrada ('groq/compound'), en vez de una API deportiva fija.
"""
import datetime as dt

import pytz
from groq import Groq

import config

TZ = pytz.timezone(config.TIMEZONE)
WEB_MODEL = "groq/compound"  # modelo de Groq con búsqueda web
_cliente = Groq(api_key=config.GROQ_API_KEY, timeout=25, max_retries=1)


def proximos_partidos_colocolo() -> str:
    """Devuelve los próximos partidos de Colo-Colo (rival, lugar, fecha y hora)."""
    hoy = dt.datetime.now(TZ).strftime("%A %d/%m/%Y")
    prompt = (
        f"Hoy es {hoy}. Busca en internet los PRÓXIMOS partidos del club de fútbol "
        "Colo-Colo de Chile (los que aún no se juegan). Para cada uno indica en una "
        "línea: rival, torneo, fecha, hora en horario de Chile y estadio o lugar. "
        "Muestra como máximo los 3 próximos, del más cercano al más lejano. "
        "Responde breve y en español, solo la lista, sin explicaciones extra. "
        "Si no encuentras información confiable, dilo claramente."
    )
    try:
        resp = _cliente.chat.completions.create(
            model=WEB_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        texto = (resp.choices[0].message.content or "").strip()
        return texto or "No encontré los próximos partidos de Colo-Colo."
    except Exception as e:
        return f"No pude consultar los próximos partidos: {e}"

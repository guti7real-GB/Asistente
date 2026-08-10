"""Búsqueda web general para el asistente.

Usa el modelo de Groq con búsqueda web integrada ('groq/compound') para
responder preguntas que requieren información actual o que el modelo base
no conoce con certeza.
"""
from groq import Groq

import config

WEB_MODEL = "groq/compound"
_cliente = Groq(api_key=config.GROQ_API_KEY, timeout=25, max_retries=1)


def buscar_web(consulta: str) -> str:
    """Busca en internet y devuelve una respuesta a la consulta dada."""
    try:
        resp = _cliente.chat.completions.create(
            model=WEB_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Responde en español, de forma clara y concisa, usando "
                        "información actual de internet:\n" + consulta
                    ),
                }
            ],
            max_tokens=700,
        )
        return (resp.choices[0].message.content or "").strip() or "No encontré información."
    except Exception as e:
        return f"No pude buscar en la web: {e}"

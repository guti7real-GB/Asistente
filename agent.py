"""El 'cerebro' (con Groq): recibe un mensaje, deja que el modelo decida qué
herramientas usar (Notion / Calendar) y devuelve la respuesta final en texto.

Usa Groq (gratis) con un modelo Llama que soporta 'tool calling'.
"""
import datetime as dt
import json

import pytz
from groq import Groq

import config
from tools import notion_tools, calendar_tools

cliente = Groq(api_key=config.GROQ_API_KEY)
TZ = pytz.timezone(config.TIMEZONE)

# ---- Definición de las herramientas (formato de function calling) ----
HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "crear_tarea",
            "description": "Crea una nueva tarea en Notion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Título de la tarea"},
                    "fecha": {
                        "type": "string",
                        "description": "Fecha límite en formato AAAA-MM-DD (opcional)",
                    },
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_tareas",
            "description": "Lista las tareas de Notion. Por defecto solo las pendientes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "solo_pendientes": {
                        "type": "string",
                        "description": "'true' = solo pendientes; 'false' = todas",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "completar_tarea",
            "description": "Marca una tarea como hecha buscándola por su nombre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Texto del nombre a buscar",
                    }
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_eventos",
            "description": "Lista los eventos próximos de Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "string",
                        "description": "Cuántos días mirar hacia adelante como número (1 = hoy)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_evento",
            "description": "Crea un evento en Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "inicio": {
                        "type": "string",
                        "description": "AAAA-MM-DDTHH:MM (con hora) o AAAA-MM-DD (día completo)",
                    },
                    "duracion_min": {
                        "type": "string",
                        "description": "Duración en minutos como número (por defecto 60)",
                    },
                },
                "required": ["titulo", "inicio"],
            },
        },
    },
]

# Mapa nombre -> función real de Python
FUNCIONES = {
    "crear_tarea": notion_tools.crear_tarea,
    "listar_tareas": notion_tools.listar_tareas,
    "completar_tarea": notion_tools.completar_tarea,
    "listar_eventos": calendar_tools.listar_eventos,
    "crear_evento": calendar_tools.crear_evento,
}


def _system_prompt() -> str:
    ahora = dt.datetime.now(TZ)
    return (
        "Eres el asistente personal de Gxs, una secretaria eficiente y cercana. "
        "Gestionas sus tareas en Notion y su Google Calendar. "
        f"La fecha y hora actual es {ahora.strftime('%A %d/%m/%Y %H:%M')} "
        f"(zona horaria {config.TIMEZONE}). "
        "Responde SIEMPRE en español, breve y claro. Usa las herramientas cuando "
        "haga falta en vez de inventar datos. Si el usuario da una fecha relativa "
        "('mañana', 'el viernes'), conviértela tú a AAAA-MM-DD antes de llamar la herramienta. "
        "Confirma lo que hiciste de forma concisa."
    )


def responder(mensaje_usuario: str, historial: list) -> str:
    """Procesa un mensaje. 'historial' es una lista mutable de mensajes previos
    (sin incluir el 'system', que se añade en cada llamada)."""
    historial.append({"role": "user", "content": mensaje_usuario})

    while True:
        mensajes = [{"role": "system", "content": _system_prompt()}] + historial
        respuesta = cliente.chat.completions.create(
            model=config.GROQ_MODEL,
            max_tokens=1024,
            tools=HERRAMIENTAS,
            tool_choice="auto",
            messages=mensajes,
        )
        msg = respuesta.choices[0].message

        # Guardamos lo que dijo el asistente en el historial
        entrada_asistente = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            entrada_asistente["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        historial.append(entrada_asistente)

        if not msg.tool_calls:
            # No hay más herramientas: devolvemos el texto final
            return (msg.content or "Hecho.").strip()

        # Ejecutamos cada herramienta pedida y devolvemos los resultados
        for tc in msg.tool_calls:
            nombre = tc.function.name
            try:
                argumentos = json.loads(tc.function.arguments or "{}")
                salida = FUNCIONES[nombre](**argumentos)
            except Exception as e:
                salida = f"Error al ejecutar {nombre}: {e}"
            historial.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(salida),
                }
            )

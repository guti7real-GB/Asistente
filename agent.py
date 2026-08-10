"""El 'cerebro' (con Groq): recibe un mensaje, deja que el modelo decida qué
herramientas usar (Notion / Calendar) y devuelve la respuesta final en texto.

Usa Groq (gratis) con un modelo Llama que soporta 'tool calling'.
"""
import datetime as dt
import json

import pytz
from groq import Groq

import config
from tools import notion_tools, calendar_tools, brief_tools, web_tools

cliente = Groq(api_key=config.GROQ_API_KEY, timeout=30, max_retries=1)
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
            "description": "Lista los eventos próximos de Google Calendar (para consultarlos/mostrarlos).",
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
            "name": "buscar_eventos",
            "description": (
                "Lista los eventos incluyendo su identificador (id). Úsala SIEMPRE "
                "antes de editar, mover o borrar un evento, para obtener el id correcto."
            ),
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
            "description": "Crea un evento o reunión en Google Calendar. Puede incluir enlace de Google Meet e invitados.",
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
                    "invitados": {
                        "type": "string",
                        "description": "Correos de los invitados separados por coma (opcional)",
                    },
                    "descripcion": {
                        "type": "string",
                        "description": "Agenda o descripción de la reunión (opcional)",
                    },
                    "con_meet": {
                        "type": "string",
                        "description": "'true' para añadir enlace de Google Meet",
                    },
                },
                "required": ["titulo", "inicio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editar_evento",
            "description": "Edita o mueve un evento existente. Necesita el id (obtenido con buscar_eventos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "id del evento"},
                    "nuevo_titulo": {"type": "string", "description": "Nuevo nombre (opcional)"},
                    "nuevo_inicio": {
                        "type": "string",
                        "description": "Nueva fecha/hora AAAA-MM-DDTHH:MM (opcional, para mover)",
                    },
                    "nueva_duracion_min": {
                        "type": "string",
                        "description": "Nueva duración en minutos como número (opcional)",
                    },
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "borrar_evento",
            "description": "Borra un evento. Necesita el id (obtenido con buscar_eventos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "id del evento a borrar"}
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "proximos_partidos_colocolo",
            "description": (
                "Busca en internet los próximos partidos de Colo-Colo (rival, torneo, "
                "fecha, hora en Chile y estadio). Úsala para cualquier consulta sobre "
                "cuándo, dónde o contra quién juega Colo-Colo."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": (
                "Busca en internet para responder preguntas de información actual o "
                "que no conoces con certeza (noticias, datos recientes, precios, "
                "resultados, personas, definiciones específicas, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "La pregunta o tema a buscar",
                    }
                },
                "required": ["consulta"],
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
    "buscar_eventos": calendar_tools.buscar_eventos,
    "crear_evento": calendar_tools.crear_evento,
    "editar_evento": calendar_tools.editar_evento,
    "borrar_evento": calendar_tools.borrar_evento,
    "proximos_partidos_colocolo": brief_tools.proximos_partidos_colocolo,
    "buscar_web": web_tools.buscar_web,
}


def _system_prompt() -> str:
    ahora = dt.datetime.now(TZ)
    return (
        "Eres Alfred, el mayordomo personal de Gxs, al estilo del mayordomo de "
        "Batman: impecablemente cortés, formal, sereno y leal, con un ingenio "
        "seco y elegante. Te diriges a él como 'señor' y mantienes siempre un tono "
        "distinguido y respetuoso, con algún comentario ingenioso ocasional, pero "
        "sin perder la calidez ni la eficacia. "
        "Además de gestionar sus tareas en Notion, su Google Calendar y avisarle de "
        "los partidos de Colo-Colo, respondes CUALQUIER pregunta o tema que te "
        "plantee (explicaciones, ideas, consejos, cálculos, redacción, dudas "
        "generales), como lo haría un mayordomo culto y siempre servicial. "
        f"La fecha y hora actual es {ahora.strftime('%A %d/%m/%Y %H:%M')} "
        f"(zona horaria {config.TIMEZONE}). "
        "Responde SIEMPRE en español, y sé MUY conciso: 2 a 4 frases, porque tus "
        "respuestas se leen en voz alta. Evita listas largas. "
        "IMPORTANTE para la rapidez: responde directamente con tu propio conocimiento "
        "siempre que puedas. Usa 'buscar_web' SOLO para información que cambia con el "
        "tiempo (noticias de hoy, precios actuales, resultados deportivos recientes, "
        "eventos de actualidad). NUNCA uses 'buscar_web' para explicaciones, "
        "definiciones, ideas o conocimiento general: eso contéstalo tú directo, es más rápido. "
        "Usa las demás herramientas (Notion, calendario) solo cuando el usuario lo pida. "
        "Si el usuario da una fecha relativa "
        "('mañana', 'el viernes'), conviértela tú a AAAA-MM-DD antes de llamar la herramienta. "
        "Confirma lo que hiciste de forma concisa.\n"
        "Para EDITAR, MOVER o BORRAR un evento: primero llama a 'buscar_eventos', "
        "muéstrale al usuario una lista NUMERADA (1, 2, 3...) con la hora y el nombre "
        "de cada evento, y NUNCA le muestres los identificadores técnicos (id=...). "
        "Pídele el número, y luego usa el id correspondiente a ese número al llamar "
        "'editar_evento' o 'borrar_evento'.\n"
        "Para crear una REUNIÓN: si faltan datos, pregúntale al usuario lo que haga "
        "falta de a poco (título, con quién y su correo, cuándo, duración, si quiere "
        "enlace de Meet, y una breve agenda). No tienes acceso a sus contactos, así "
        "que si solo te da un nombre, pídele el correo. Cuando tengas los datos, usa "
        "'crear_evento' con con_meet='true' e 'invitados' cuando corresponda."
    )


def responder(mensaje_usuario: str, historial: list) -> str:
    """Procesa un mensaje. 'historial' es una lista mutable de mensajes previos
    (sin incluir el 'system', que se añade en cada llamada)."""
    historial.append({"role": "user", "content": mensaje_usuario})

    while True:
        mensajes = [{"role": "system", "content": _system_prompt()}] + historial
        respuesta = cliente.chat.completions.create(
            model=config.GROQ_MODEL,
            max_tokens=500,
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

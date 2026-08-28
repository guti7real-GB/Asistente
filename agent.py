"""El 'cerebro' (con Groq): recibe un mensaje, deja que el modelo decida qué
herramientas usar (Notion / Calendar) y devuelve la respuesta final en texto.

Usa Groq (gratis) con un modelo Llama que soporta 'tool calling'.
"""
import datetime as dt
import json

import pytz
from groq import Groq

import config
from tools import (
    notion_tools,
    calendar_tools,
    brief_tools,
    web_tools,
    red_tools,
    spotify_tools,
    memoria_tools,
    ordenes_tools,
    info_tools,
    gmail_tools,
)

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
            "name": "guardar_memoria",
            "description": (
                "Guarda en la memoria una preferencia, dato o cosa importante que el "
                "usuario comparta y convenga recordar en el futuro."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nota": {"type": "string", "description": "Qué recordar, en una frase"}
                },
                "required": ["nota"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "programar_orden",
            "description": (
                "Guarda una orden para EJECUTARLA en el futuro a una fecha/hora dada "
                "(recordatorios o acciones futuras)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "La instrucción a ejecutar"},
                    "cuando": {
                        "type": "string",
                        "description": "Fecha y hora AAAA-MM-DDTHH:MM en que ejecutarla",
                    },
                },
                "required": ["texto", "cuando"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_ordenes",
            "description": "Lista las órdenes programadas pendientes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reproducir_spotify",
            "description": "Busca y reproduce una canción en Spotify. Úsala cuando el usuario pida poner música o una canción.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cancion": {
                        "type": "string",
                        "description": "Nombre de la canción y, si lo dice, el artista",
                    }
                },
                "required": ["cancion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pausar_spotify",
            "description": "Pausa la música de Spotify.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "siguiente_cancion",
            "description": "Salta a la siguiente canción en Spotify.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "que_suena",
            "description": "Dice qué canción está sonando ahora en Spotify.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumir_correos",
            "description": "Resume los correos recibidos hoy (remitente, asunto y extracto).",
            "parameters": {
                "type": "object",
                "properties": {
                    "cantidad": {
                        "type": "string",
                        "description": "Cuántos correos revisar como número (por defecto 8)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_correo",
            "description": (
                "Envía un correo. Úsala SOLO después de mostrar el borrador y de que "
                "el usuario confirme explícitamente que lo envíe."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario": {"type": "string", "description": "Correo del destinatario"},
                    "asunto": {"type": "string"},
                    "cuerpo": {"type": "string"},
                },
                "required": ["destinatario", "asunto", "cuerpo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clima",
            "description": "Clima de hoy en San Miguel y Las Condes (rango, promedio, sensación).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dolar",
            "description": "Valor actual del dólar en pesos chilenos.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "noticias",
            "description": "Titulares recientes de IA/tecnología, Colo-Colo y economía.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escanear_red",
            "description": (
                "Escanea la red WiFi local y lista los dispositivos conectados "
                "(IP, nombre y MAC). Úsala cuando el usuario pida ver los "
                "dispositivos de su red."
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
    "escanear_red": red_tools.escanear_red,
    "resumir_correos": gmail_tools.resumir_correos,
    "enviar_correo": gmail_tools.enviar_correo,
    "clima": info_tools.clima,
    "dolar": info_tools.dolar,
    "noticias": info_tools.noticias,
    "guardar_memoria": memoria_tools.guardar_memoria,
    "programar_orden": ordenes_tools.programar_orden,
    "listar_ordenes": ordenes_tools.listar_ordenes,
    "reproducir_spotify": spotify_tools.reproducir,
    "pausar_spotify": spotify_tools.pausar,
    "siguiente_cancion": spotify_tools.siguiente,
    "que_suena": spotify_tools.que_suena,
}


def _system_prompt() -> str:
    ahora = dt.datetime.now(TZ)
    base = (
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
        "Responde SIEMPRE en español, y por lo general sé conciso: 2 a 4 frases, porque "
        "tus respuestas se leen en voz alta. EXCEPCIÓN: cuando el usuario pida resumir un "
        "documento o pida detalle/explicación extensa, extiéndete lo necesario (puntos, "
        "párrafos o resumen detallado según pida). "
        "IMPORTANTE para la rapidez: responde directamente con tu propio conocimiento "
        "siempre que puedas. Usa 'buscar_web' SOLO para información que cambia con el "
        "tiempo (noticias de hoy, precios actuales, resultados deportivos recientes, "
        "eventos de actualidad). NUNCA uses 'buscar_web' para explicaciones, "
        "definiciones, ideas o conocimiento general: eso contéstalo tú directo, es más rápido. "
        "Usa las demás herramientas (Notion, calendario) solo cuando el usuario lo pida. "
        "Cuando el usuario pida ver los dispositivos de su red, usa 'escanear_red' y "
        "muéstrale la lista TAL CUAL la devuelve la herramienta (enumerada, sin quitar "
        "ni reordenar dispositivos). "
        "Cuando pida poner música o una canción, usa 'reproducir_spotify' con el nombre "
        "de la canción (incluye el artista si lo menciona). Para controlar la música usa "
        "'pausar_spotify', 'siguiente_cancion' o 'que_suena' según corresponda. "
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
        "'crear_evento' con con_meet='true' e 'invitados' cuando corresponda.\n"
        "PROFESIONALISMO: cuando venga al caso, aconseja a Gxs con tacto para actuar "
        "de forma más profesional (comunicación, orden, puntualidad, prioridades), "
        "sin sermonear ni alargarte.\n"
        "FÚTBOL — eres HINCHA de Colo-Colo: si te preguntan quién ganará entre "
        "Colo-Colo y cualquier otro equipo (o 'X vs Y' donde juegue Colo-Colo), "
        "responde SIEMPRE que gana Colo-Colo, con un comentario orgulloso tipo "
        "'obvio, señor, por ser el equipo más ganador del país, y vamos en campaña "
        "por la estrella 35'. (Es solo por afición; si preguntan por un partido real "
        "ya jugado, di el resultado verdadero.)\n"
        "MEMORIA: cuando el usuario comparta una preferencia, dato personal o algo "
        "que convenga recordar, guárdalo con 'guardar_memoria'. Para que hagas algo en "
        "el futuro, usa 'programar_orden'.\n"
        "CORREO: para revisar el correo usa 'resumir_correos'. Para escribir o responder "
        "un correo, PRIMERO redacta el borrador (destinatario, asunto y cuerpo) y "
        "muéstraselo al usuario para que lo revise. Llama a 'enviar_correo' ÚNICAMENTE "
        "cuando el usuario confirme de forma explícita que lo envíe. Nunca envíes sin esa "
        "confirmación."
    )
    memoria = memoria_tools.leer_memoria()
    if memoria:
        base += "\n\nEsto es lo que recuerdas de Gxs:\n" + memoria
    return base


def responder(mensaje_usuario: str, historial: list) -> str:
    """Procesa un mensaje. 'historial' es una lista mutable de mensajes previos
    (sin incluir el 'system', que se añade en cada llamada)."""
    historial.append({"role": "user", "content": mensaje_usuario})

    while True:
        mensajes = [{"role": "system", "content": _system_prompt()}] + historial
        respuesta = cliente.chat.completions.create(
            model=config.GROQ_MODEL,
            max_tokens=900,
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

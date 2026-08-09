"""Herramientas para gestionar tareas en una base de datos de Notion.

La base de datos debe tener estas propiedades (nombres exactos):
  - "Nombre"  -> tipo Title
  - "Estado"  -> tipo Status (con opciones como "Pendiente", "Hecho")
  - "Fecha"   -> tipo Date (opcional)
Puedes cambiar los nombres abajo si tu base usa otros.
"""
from notion_client import Client
import config

PROP_NOMBRE = "Nombre"
PROP_ESTADO = "Estado"
PROP_FECHA = "Fecha"
ESTADO_HECHO = "Hecho"
ESTADO_PENDIENTE = "Pendiente"

# Fijamos la versión estable de la API de Notion (el modelo clásico de
# "database_id"), para evitar el nuevo modelo de "data sources".
notion = Client(auth=config.NOTION_TOKEN, notion_version="2022-06-28")


def crear_tarea(nombre: str, fecha: str | None = None) -> str:
    """Crea una tarea nueva. fecha en formato AAAA-MM-DD (opcional)."""
    props = {
        PROP_NOMBRE: {"title": [{"text": {"content": nombre}}]},
        PROP_ESTADO: {"status": {"name": ESTADO_PENDIENTE}},
    }
    if fecha:
        props[PROP_FECHA] = {"date": {"start": fecha}}
    notion.pages.create(
        parent={"database_id": config.NOTION_TASKS_DB_ID}, properties=props
    )
    return f"Tarea creada: '{nombre}'" + (f" para el {fecha}" if fecha else "")


def listar_tareas(solo_pendientes=True) -> str:
    """Lista las tareas de la base de datos."""
    # el modelo puede mandar el booleano como texto ("true"/"false")
    if isinstance(solo_pendientes, str):
        solo_pendientes = solo_pendientes.strip().lower() not in ("false", "0", "no", "")
    filtro = None
    if solo_pendientes:
        filtro = {"property": PROP_ESTADO, "status": {"does_not_equal": ESTADO_HECHO}}
    resp = notion.databases.query(
        database_id=config.NOTION_TASKS_DB_ID,
        filter=filtro,
        page_size=50,
    )
    lineas = []
    for pagina in resp.get("results", []):
        props = pagina["properties"]
        titulo = _texto_titulo(props.get(PROP_NOMBRE))
        estado = _texto_estado(props.get(PROP_ESTADO))
        fecha = _texto_fecha(props.get(PROP_FECHA))
        etiqueta = f"- {titulo}"
        if fecha:
            etiqueta += f" (📅 {fecha})"
        etiqueta += f" [{estado}]"
        lineas.append(etiqueta)
    if not lineas:
        return "No hay tareas."
    return "\n".join(lineas)


def completar_tarea(nombre: str) -> str:
    """Marca como 'Hecho' la primera tarea cuyo nombre contenga el texto dado."""
    resp = notion.databases.query(
        database_id=config.NOTION_TASKS_DB_ID,
        filter={"property": PROP_NOMBRE, "title": {"contains": nombre}},
        page_size=5,
    )
    resultados = resp.get("results", [])
    if not resultados:
        return f"No encontré ninguna tarea que contenga '{nombre}'."
    pagina = resultados[0]
    notion.pages.update(
        page_id=pagina["id"],
        properties={PROP_ESTADO: {"status": {"name": ESTADO_HECHO}}},
    )
    titulo = _texto_titulo(pagina["properties"].get(PROP_NOMBRE))
    return f"Marcada como hecha: '{titulo}'"


# ---- helpers para leer propiedades de Notion ----
def _texto_titulo(prop):
    if not prop:
        return "(sin nombre)"
    partes = prop.get("title", [])
    return "".join(p.get("plain_text", "") for p in partes) or "(sin nombre)"


def _texto_estado(prop):
    if not prop:
        return "?"
    estado = prop.get("status")
    return estado.get("name") if estado else "?"


def _texto_fecha(prop):
    if not prop:
        return None
    fecha = prop.get("date")
    return fecha.get("start") if fecha else None

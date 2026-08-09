"""Herramientas para Google Calendar (leer, crear, editar, mover, borrar y
crear reuniones con enlace de Google Meet e invitados).

La primera vez que ejecutes el programa se abrirá el navegador para que
autorices el acceso. Se guardará un archivo token.json para no repetirlo.
Necesitas un archivo credentials.json descargado desde Google Cloud Console
(ver README).
"""
import datetime as dt
import os.path
import uuid

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TZ = pytz.timezone(config.TIMEZONE)

_servicio = None


def _get_service():
    """Autentica (una vez) y devuelve el cliente de la API de Calendar."""
    global _servicio
    if _servicio is not None:
        return _servicio

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    _servicio = build("calendar", "v3", credentials=creds)
    return _servicio


def _eventos_en_rango(dias):
    service = _get_service()
    ahora = dt.datetime.now(TZ)
    fin = ahora + dt.timedelta(days=int(dias))
    resultado = (
        service.events()
        .list(
            calendarId=config.GOOGLE_CALENDAR_ID,
            timeMin=ahora.isoformat(),
            timeMax=fin.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return resultado.get("items", [])


def listar_eventos(dias=1) -> str:
    """Lista los eventos próximos (texto limpio, para mostrar al usuario)."""
    eventos = _eventos_en_rango(dias)
    if not eventos:
        return "No hay eventos próximos."
    lineas = []
    for ev in eventos:
        inicio = ev["start"].get("dateTime", ev["start"].get("date"))
        titulo = ev.get("summary", "(sin título)")
        lineas.append(f"- {_formatea(inicio)}  {titulo}")
    return "\n".join(lineas)


def buscar_eventos(dias=1) -> str:
    """Lista los eventos incluyendo su identificador técnico (id=...),
    para poder editarlos o borrarlos. Usar esta antes de editar/borrar.
    """
    eventos = _eventos_en_rango(dias)
    if not eventos:
        return "No hay eventos en ese rango."
    lineas = []
    for i, ev in enumerate(eventos, 1):
        inicio = ev["start"].get("dateTime", ev["start"].get("date"))
        titulo = ev.get("summary", "(sin título)")
        lineas.append(f"{i}) {_formatea(inicio)} {titulo} | id={ev['id']}")
    return "\n".join(lineas)


def crear_evento(
    titulo: str,
    inicio: str,
    duracion_min=60,
    invitados=None,
    descripcion=None,
    con_meet=False,
) -> str:
    """Crea un evento o reunión.
    inicio: 'AAAA-MM-DDTHH:MM' (con hora) o 'AAAA-MM-DD' (día completo).
    invitados: correos separados por coma (opcional).
    con_meet: True para añadir enlace de Google Meet.
    """
    duracion_min = int(duracion_min)
    con_meet = _a_bool(con_meet)
    service = _get_service()

    cuerpo = {"summary": titulo}
    if "T" in inicio:
        dt_inicio = TZ.localize(dt.datetime.fromisoformat(inicio))
        dt_fin = dt_inicio + dt.timedelta(minutes=duracion_min)
        cuerpo["start"] = {"dateTime": dt_inicio.isoformat(), "timeZone": config.TIMEZONE}
        cuerpo["end"] = {"dateTime": dt_fin.isoformat(), "timeZone": config.TIMEZONE}
    else:
        cuerpo["start"] = {"date": inicio}
        cuerpo["end"] = {"date": inicio}

    if descripcion:
        cuerpo["description"] = descripcion

    emails = _emails(invitados)
    if emails:
        cuerpo["attendees"] = [{"email": e} for e in emails]

    params = {"calendarId": config.GOOGLE_CALENDAR_ID, "body": cuerpo}
    if con_meet:
        cuerpo["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
        params["conferenceDataVersion"] = 1
    if emails:
        params["sendUpdates"] = "all"

    ev = service.events().insert(**params).execute()

    msg = f"Evento creado: '{titulo}' el {inicio}"
    link = ev.get("hangoutLink")
    if link:
        msg += f"\nEnlace de Meet: {link}"
    if emails:
        msg += f"\nInvitados avisados: {', '.join(emails)}"
    return msg


def editar_evento(
    event_id: str,
    nuevo_titulo=None,
    nuevo_inicio=None,
    nueva_duracion_min=None,
) -> str:
    """Edita o mueve un evento existente (por su id, obtenido con buscar_eventos)."""
    service = _get_service()
    ev = service.events().get(
        calendarId=config.GOOGLE_CALENDAR_ID, eventId=event_id
    ).execute()

    if nuevo_titulo:
        ev["summary"] = nuevo_titulo

    if nuevo_inicio:
        if "T" in nuevo_inicio:
            dur = int(nueva_duracion_min) if nueva_duracion_min else _duracion_actual(ev)
            dt_inicio = TZ.localize(dt.datetime.fromisoformat(nuevo_inicio))
            dt_fin = dt_inicio + dt.timedelta(minutes=dur)
            ev["start"] = {"dateTime": dt_inicio.isoformat(), "timeZone": config.TIMEZONE}
            ev["end"] = {"dateTime": dt_fin.isoformat(), "timeZone": config.TIMEZONE}
        else:
            ev["start"] = {"date": nuevo_inicio}
            ev["end"] = {"date": nuevo_inicio}
    elif nueva_duracion_min and ev["start"].get("dateTime"):
        dt_inicio = dt.datetime.fromisoformat(ev["start"]["dateTime"])
        dt_fin = dt_inicio + dt.timedelta(minutes=int(nueva_duracion_min))
        ev["end"] = {"dateTime": dt_fin.isoformat(), "timeZone": config.TIMEZONE}

    actualizado = service.events().update(
        calendarId=config.GOOGLE_CALENDAR_ID,
        eventId=event_id,
        body=ev,
        sendUpdates="all",
    ).execute()
    return f"Evento actualizado: '{actualizado.get('summary', '(sin título)')}'"


def borrar_evento(event_id: str) -> str:
    """Borra un evento por su id (obtenido con buscar_eventos)."""
    service = _get_service()
    try:
        ev = service.events().get(
            calendarId=config.GOOGLE_CALENDAR_ID, eventId=event_id
        ).execute()
        titulo = ev.get("summary", "(sin título)")
    except Exception:
        titulo = "(evento)"
    service.events().delete(
        calendarId=config.GOOGLE_CALENDAR_ID, eventId=event_id, sendUpdates="all"
    ).execute()
    return f"Evento borrado: '{titulo}'"


# ---------- helpers ----------
def _duracion_actual(ev) -> int:
    """Duración en minutos de un evento con hora; 60 por defecto."""
    try:
        ini = dt.datetime.fromisoformat(ev["start"]["dateTime"])
        fin = dt.datetime.fromisoformat(ev["end"]["dateTime"])
        return max(1, int((fin - ini).total_seconds() // 60))
    except Exception:
        return 60


def _emails(invitados):
    if not invitados:
        return []
    if isinstance(invitados, str):
        crudos = invitados.replace(";", ",").split(",")
    else:
        crudos = invitados
    return [e.strip() for e in crudos if e and "@" in str(e)]


def _a_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "si", "sí", "yes")


def _formatea(iso: str) -> str:
    try:
        if "T" in iso:
            d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
            return d.strftime("%d/%m %H:%M")
        d = dt.datetime.fromisoformat(iso)
        return d.strftime("%d/%m (todo el día)")
    except Exception:
        return iso

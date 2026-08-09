"""Herramientas para Google Calendar (leer y crear eventos).

La primera vez que ejecutes el programa se abrirá el navegador para que
autorices el acceso. Se guardará un archivo token.json para no repetirlo.
Necesitas un archivo credentials.json descargado desde Google Cloud Console
(ver README).
"""
import datetime as dt
import os.path

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


def listar_eventos(dias=1) -> str:
    """Lista los eventos desde ahora hasta 'dias' días adelante (1 = hoy)."""
    dias = int(dias)  # el modelo puede mandarlo como texto ("1")
    service = _get_service()
    ahora = dt.datetime.now(TZ)
    fin = ahora + dt.timedelta(days=dias)
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
    eventos = resultado.get("items", [])
    if not eventos:
        return "No hay eventos próximos."
    lineas = []
    for ev in eventos:
        inicio = ev["start"].get("dateTime", ev["start"].get("date"))
        titulo = ev.get("summary", "(sin título)")
        lineas.append(f"- {_formatea(inicio)}  {titulo}")
    return "\n".join(lineas)


def crear_evento(titulo: str, inicio: str, duracion_min=60) -> str:
    """Crea un evento.
    inicio: 'AAAA-MM-DDTHH:MM' (hora local) o 'AAAA-MM-DD' (día completo).
    """
    duracion_min = int(duracion_min)  # el modelo puede mandarlo como texto
    service = _get_service()
    if "T" in inicio:
        dt_inicio = TZ.localize(dt.datetime.fromisoformat(inicio))
        dt_fin = dt_inicio + dt.timedelta(minutes=duracion_min)
        cuerpo = {
            "summary": titulo,
            "start": {"dateTime": dt_inicio.isoformat(), "timeZone": config.TIMEZONE},
            "end": {"dateTime": dt_fin.isoformat(), "timeZone": config.TIMEZONE},
        }
    else:
        cuerpo = {
            "summary": titulo,
            "start": {"date": inicio},
            "end": {"date": inicio},
        }
    service.events().insert(
        calendarId=config.GOOGLE_CALENDAR_ID, body=cuerpo
    ).execute()
    return f"Evento creado: '{titulo}' el {inicio}"


def _formatea(iso: str) -> str:
    try:
        if "T" in iso:
            d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
            return d.strftime("%d/%m %H:%M")
        d = dt.datetime.fromisoformat(iso)
        return d.strftime("%d/%m (todo el día)")
    except Exception:
        return iso

"""Herramientas de Gmail: resumir correos recibidos hoy y enviar correos.

Usa el auth compartido (google_auth) con permisos de Gmail. Enviar correos debe
hacerse SIEMPRE tras mostrar el borrador y recibir confirmación del usuario.
"""
import base64
import datetime as dt
from email.mime.text import MIMEText

import pytz
from googleapiclient.discovery import build

import config
from tools import google_auth

TZ = pytz.timezone(config.TIMEZONE)
_servicio = None


def _service():
    global _servicio
    if _servicio is None:
        _servicio = build("gmail", "v1", credentials=google_auth.get_credentials())
    return _servicio


def resumir_correos(cantidad=8) -> str:
    """Lista los correos recibidos hoy (remitente, asunto y un extracto)."""
    try:
        cantidad = int(cantidad)
    except Exception:
        cantidad = 8
    svc = _service()
    hoy = dt.datetime.now(TZ).strftime("%Y/%m/%d")
    res = (
        svc.users()
        .messages()
        .list(userId="me", q=f"in:inbox after:{hoy}", maxResults=cantidad)
        .execute()
    )
    ids = res.get("messages", [])
    if not ids:
        return "No ha recibido correos nuevos hoy, señor."
    lineas = []
    for i, m in enumerate(ids, 1):
        msg = (
            svc.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"],
            )
            .execute()
        )
        h = {x["name"]: x["value"] for x in msg["payload"]["headers"]}
        de = h.get("From", "")
        asunto = h.get("Subject", "(sin asunto)")
        extracto = (msg.get("snippet", "") or "")[:140]
        lineas.append(f"{i}) De: {de}\n   Asunto: {asunto}\n   {extracto}")
    return f"Correos de hoy ({len(ids)}):\n" + "\n".join(lineas)


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> str:
    """Envía un correo. Usar SOLO después de que el usuario confirme el borrador."""
    try:
        svc = _service()
        mensaje = MIMEText(cuerpo)
        mensaje["to"] = destinatario
        mensaje["subject"] = asunto
        raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Correo enviado a {destinatario}, señor."
    except Exception as e:
        return f"No pude enviar el correo: {e}"

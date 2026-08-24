"""Servidor web para la app 'Alfred' (voz manos libres desde otro teléfono).

Reusa el mismo cerebro (agent.responder). Sirve la página y responde preguntas.
Protegido por una clave (WEB_PASSWORD) que se envía en cada petición.
Se expone al exterior con un túnel de Cloudflare.

Ejecuta:  python3 web_server.py
"""
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import agent

app = FastAPI()
HISTORIAL = []  # conversación de la app web (en memoria)

_AQUI = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_AQUI, "static")

app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def _clave_ok(req: Request) -> bool:
    return req.headers.get("x-alfred-key", "") == (config.WEB_PASSWORD or "")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(_STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/auth")
async def auth(req: Request):
    return JSONResponse({"ok": _clave_ok(req)})


@app.post("/preguntar")
async def preguntar(req: Request):
    if not _clave_ok(req):
        return JSONResponse({"respuesta": "Acceso denegado."}, status_code=401)
    data = await req.json()
    texto = (data.get("texto") or "").strip()
    if not texto:
        return JSONResponse({"respuesta": "No entendí la pregunta, señor."})
    try:
        respuesta = agent.responder(texto, HISTORIAL)
    except Exception as e:
        respuesta = f"Le pido disculpas, señor; hubo un error: {e}"
    if len(HISTORIAL) > 40:
        del HISTORIAL[:-40]
    return JSONResponse({"respuesta": respuesta})


if __name__ == "__main__":
    config.check()
    if not config.WEB_PASSWORD:
        raise SystemExit(
            "Define WEB_PASSWORD en tu .env para proteger la app web, señor."
        )
    print("Servidor Alfred en marcha en http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

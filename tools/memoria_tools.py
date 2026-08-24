"""Memoria persistente de Alfred.

Guarda notas (preferencias, datos, cosas aprendidas) en memoria.json, que
sobrevive a reinicios. El contenido se inyecta en el 'system prompt' para que
Alfred lo tenga presente en cada conversación.
"""
import datetime as dt
import json
import os

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO = os.path.join(_RAIZ, "memoria.json")


def _cargar():
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _guardar(lista):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def guardar_memoria(nota: str) -> str:
    """Guarda algo importante para recordarlo en el futuro."""
    nota = (nota or "").strip()
    if not nota:
        return "No había nada que anotar, señor."
    lista = _cargar()
    lista.append({"fecha": dt.date.today().isoformat(), "nota": nota})
    _guardar(lista[-100:])  # conserva las últimas 100
    return f"Lo tendré presente, señor: {nota}"


def leer_memoria() -> str:
    """Devuelve todo lo recordado (para inyectar en el system prompt)."""
    lista = _cargar()
    if not lista:
        return ""
    return "\n".join(f"- {x.get('nota', '')}" for x in lista)

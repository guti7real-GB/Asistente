"""Órdenes programadas: cosas que Alfred debe ejecutar en el futuro.

Guarda órdenes con su fecha/hora en ordenes.json. El bot revisa cada minuto
y ejecuta las que ya vencieron.
"""
import json
import os

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO = os.path.join(_RAIZ, "ordenes.json")


def _cargar():
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _guardar(lista):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def programar_orden(texto: str, cuando: str) -> str:
    """Guarda una orden para ejecutarla en el futuro.
    cuando: 'AAAA-MM-DDTHH:MM' (fecha y hora en que debe ejecutarse).
    texto: la instrucción, tal como se la darías a Alfred.
    """
    texto = (texto or "").strip()
    if not texto or not cuando:
        return "Necesito la orden y la fecha/hora, señor."
    lista = _cargar()
    lista.append({"texto": texto, "cuando": cuando[:16]})
    _guardar(lista)
    return f"A la orden, señor. Ejecutaré «{texto}» el {cuando[:16].replace('T', ' a las ')}."


def listar_ordenes() -> str:
    """Lista las órdenes programadas pendientes."""
    lista = _cargar()
    if not lista:
        return "No tiene órdenes programadas, señor."
    lista.sort(key=lambda x: x.get("cuando", ""))
    return "\n".join(
        f"{i}) {x['cuando'].replace('T', ' a las ')} — {x['texto']}"
        for i, x in enumerate(lista, 1)
    )


def ordenes_vencidas(ahora_iso: str):
    """Devuelve las órdenes cuya hora ya llegó y las quita del archivo."""
    lista = _cargar()
    vencidas = [x for x in lista if x.get("cuando", "") <= ahora_iso]
    if vencidas:
        restantes = [x for x in lista if x.get("cuando", "") > ahora_iso]
        _guardar(restantes)
    return vencidas

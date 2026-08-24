"""Control de Spotify (requiere Spotify Premium).

Reproduce, pausa, salta canciones y dice qué suena, usando la API de Spotify
a través de la librería spotipy. La autorización se hace una sola vez (ver
spotify_auth.py) y queda guardada en el archivo .spotify_cache.
"""
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import config

SCOPE = "user-modify-playback-state user-read-playback-state"
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(_RAIZ, ".spotify_cache")


def _sp():
    auth = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE,
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth)


def _dispositivo(sp):
    devs = sp.devices().get("devices", [])
    if not devs:
        return None
    for d in devs:
        if d.get("is_active"):
            return d["id"]
    return devs[0]["id"]


def reproducir(cancion: str) -> str:
    """Busca una canción y la reproduce en el dispositivo de Spotify activo."""
    try:
        sp = _sp()
        res = sp.search(q=cancion, type="track", limit=1)
        items = res.get("tracks", {}).get("items", [])
        if not items:
            return f"No encontré '{cancion}' en Spotify, señor."
        t = items[0]
        nombre = t["name"]
        artista = ", ".join(a["name"] for a in t["artists"])
        dev = _dispositivo(sp)
        if not dev:
            return (
                "No hay ningún dispositivo de Spotify disponible. Abra la app de "
                "Spotify en el S9 y déle play una vez para activarlo, señor."
            )
        sp.start_playback(device_id=dev, uris=[t["uri"]])
        return f"Reproduciendo «{nombre}» de {artista}, señor."
    except Exception as e:
        return f"No pude reproducir en Spotify: {e}"


def pausar() -> str:
    try:
        _sp().pause_playback()
        return "Música en pausa, señor."
    except Exception as e:
        return f"No pude pausar: {e}"


def siguiente() -> str:
    try:
        _sp().next_track()
        return "Pasando a la siguiente canción, señor."
    except Exception as e:
        return f"No pude cambiar de canción: {e}"


def que_suena() -> str:
    try:
        p = _sp().current_playback()
        if not p or not p.get("item"):
            return "Ahora mismo no hay nada sonando, señor."
        t = p["item"]
        artista = ", ".join(a["name"] for a in t["artists"])
        return f"Está sonando «{t['name']}» de {artista}, señor."
    except Exception as e:
        return f"No pude consultar la reproducción: {e}"

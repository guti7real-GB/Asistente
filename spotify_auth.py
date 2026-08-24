"""Autoriza Spotify UNA sola vez. Ejecuta esto en el S9:  python3 spotify_auth.py

Imprimirá un enlace: ábrelo en el navegador de cualquier teléfono, aprueba el
acceso, y copia la dirección a la que te redirige (empieza por
http://127.0.0.1:8888/callback?code=...). Pega esa dirección aquí cuando te lo
pida. Al terminar, crea el archivo .spotify_cache en esta misma carpeta.
"""
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import config

SCOPE = "user-modify-playback-state user-read-playback-state"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".spotify_cache")


def main():
    if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
        raise SystemExit(
            "Faltan SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET en tu .env"
        )
    auth = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE,
        open_browser=False,
    )
    sp = spotipy.Spotify(auth_manager=auth)
    yo = sp.me()
    print("¡Autorizado correctamente!")
    print("Cuenta:", yo.get("display_name"), "-", yo.get("product"))
    print("Se creó el archivo:", CACHE)


if __name__ == "__main__":
    main()

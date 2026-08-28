"""Info del día: clima, dólar y noticias. Fuentes gratuitas sin API key.

- Clima: Open-Meteo (San Miguel y Las Condes).
- Dólar: mindicador.cl.
- Noticias: Google News RSS filtrado por temas.
Solo usa librerías estándar.
"""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# (nombre, latitud, longitud) — puedes editar las comunas aquí
COMUNAS = [
    ("San Miguel", -33.497, -70.652),
    ("Las Condes", -33.409, -70.568),
]

# (etiqueta, búsqueda) — temas de noticias
TEMAS = [
    ("IA / Tecnología", "inteligencia artificial"),
    ("Colo-Colo", "Colo Colo"),
    ("Economía Chile", "economía Chile"),
    ("Economía mundial", "economía mundial"),
]

_UA = {"User-Agent": "Mozilla/5.0 (compatible; AlfredBot/1.0)"}


def _get_json(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def clima() -> str:
    """Clima de hoy en San Miguel y Las Condes: rango, promedio y sensación."""
    lineas = []
    for nombre, lat, lon in COMUNAS:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                "&daily=temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min"
                "&timezone=America/Santiago&forecast_days=1"
            )
            d = _get_json(url)["daily"]
            tmax = d["temperature_2m_max"][0]
            tmin = d["temperature_2m_min"][0]
            amax = d["apparent_temperature_max"][0]
            amin = d["apparent_temperature_min"][0]
            prom = round((tmax + tmin) / 2)
            sens = round((amax + amin) / 2)
            lineas.append(
                f"{nombre}: {round(tmin)}° a {round(tmax)}° "
                f"(promedio {prom}°, sensación ~{sens}°)"
            )
        except Exception:
            lineas.append(f"{nombre}: clima no disponible")
    return "\n".join(lineas)


def dolar() -> str:
    """Valor del dólar observado en pesos chilenos (mindicador.cl)."""
    try:
        d = _get_json("https://mindicador.cl/api/dolar")
        v = d["serie"][0]["valor"]
        return f"Dólar: ${round(v)} CLP"
    except Exception:
        return "Dólar: no disponible"


def _titulares(query, n=2):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "es-419", "gl": "CL", "ceid": "CL:es-419"}
    )
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()
    root = ET.fromstring(data)
    items = root.findall(".//item")[:n]
    return [(it.findtext("title") or "").strip() for it in items if it.findtext("title")]


def noticias() -> str:
    """Titulares recientes por tema (IA, Colo-Colo, economía)."""
    bloques = []
    for etiqueta, q in TEMAS:
        try:
            tits = _titulares(q, 2)
            if tits:
                bloques.append(etiqueta + ":\n" + "\n".join("• " + t for t in tits))
        except Exception:
            pass
    return "\n\n".join(bloques) if bloques else "Sin noticias por ahora."

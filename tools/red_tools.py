"""Escáner de dispositivos de la red local (WiFi).

Barre la subred del S9 y devuelve una lista enumerada de los aparatos vivos,
con su IP, nombre (si se puede resolver) y MAC (si aparece en la tabla ARP).

Solo usa librerías estándar. Funciona sin permisos de root (mejor esfuerzo):
detecta hosts que respondan a ping o a una conexión TCP en puertos comunes.
"""
import concurrent.futures
import ipaddress
import socket
import subprocess

PUERTOS = [80, 443, 22, 8080, 445, 139, 8009, 62078, 5555, 53]


def _ip_local():
    """Averigua la IP local del S9 en la red WiFi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def _ping(ip: str) -> bool:
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return r.returncode == 0
    except Exception:
        return False


def _tcp(ip: str) -> bool:
    for p in PUERTOS:
        try:
            with socket.create_connection((ip, p), timeout=0.35):
                return True
        except ConnectionRefusedError:
            return True  # el host respondió (puerto cerrado) => existe
        except OSError:
            continue
    return False


def _vivo(ip: str) -> bool:
    return _ping(ip) or _tcp(ip)


def _nombre(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def _tabla_arp():
    """Lee /proc/net/arp y devuelve {ip: mac} (mejor esfuerzo)."""
    macs = {}
    try:
        with open("/proc/net/arp") as f:
            for linea in f.readlines()[1:]:
                partes = linea.split()
                if len(partes) >= 4:
                    ip, mac = partes[0], partes[3]
                    if mac and mac != "00:00:00:00:00:00":
                        macs[ip] = mac
    except Exception:
        pass
    return macs


def escanear_red() -> str:
    """Escanea la red local y devuelve una lista enumerada de dispositivos."""
    ip = _ip_local()
    if not ip:
        return "No pude determinar la red WiFi del servidor, señor."
    try:
        red = ipaddress.ip_network(ip + "/24", strict=False)
    except Exception:
        return f"No pude interpretar la red a partir de {ip}."

    hosts = [str(h) for h in red.hosts()]
    vivos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=120) as ex:
        for h, ok in zip(hosts, ex.map(_vivo, hosts)):
            if ok:
                vivos.append(h)

    if not vivos:
        return (
            "No detecté dispositivos, señor. Puede que la red bloquee el "
            "sondeo o que el entorno tenga acceso limitado."
        )

    vivos.sort(key=lambda x: int(x.split(".")[-1]))
    macs = _tabla_arp()

    lineas = [f"Dispositivos en su red ({ip} · {len(vivos)} encontrados):"]
    for i, h in enumerate(vivos, 1):
        nombre = _nombre(h)
        mac = macs.get(h, "")
        extra = "  ·  ".join([p for p in [nombre, mac] if p])
        etiqueta = f" — {extra}" if extra else ""
        marca = "  (este servidor)" if h == ip else ""
        lineas.append(f"{i}) {h}{etiqueta}{marca}")
    return "\n".join(lineas)

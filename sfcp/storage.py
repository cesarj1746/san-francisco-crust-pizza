"""Almacenamiento: creación de carpetas, respaldos, restauración e historial."""
from __future__ import annotations

import csv
import getpass
import json
import logging
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import ARCHIVOS, SEED_DIR, Rutas, rutas

def _copiar(origen, destino) -> None:
    """Copia contenido y fechas sin usar CopyFile2 (compatible con Windows y Wine)."""
    shutil.copyfile(origen, destino)
    try:
        shutil.copystat(origen, destino)
    except OSError:
        pass


HIST_CAMPOS = ["fecha", "accion", "tipo", "archivo", "filas", "resultado", "detalle", "usuario"]
_LOGGER_READY = False


def get_logger(r: Rutas | None = None) -> logging.Logger:
    global _LOGGER_READY
    log = logging.getLogger("sfcp")
    if not _LOGGER_READY:
        r = r or rutas()
        try:
            r.logs.mkdir(parents=True, exist_ok=True)
            h = RotatingFileHandler(r.logs / "aplicacion.log", maxBytes=1_000_000,
                                    backupCount=3, encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            log.addHandler(h)
        except OSError:
            log.addHandler(logging.StreamHandler())
        log.setLevel(logging.INFO)
        _LOGGER_READY = True
    return log


def initialize(r: Rutas | None = None) -> dict:
    """Crea la estructura de carpetas y copia las bases iniciales si faltan.

    Devuelve un resumen con lo que se creó. Nunca sobrescribe datos existentes.
    """
    r = r or rutas()
    creado = {"carpetas": [], "archivos": []}
    for c in r.carpetas():
        if not c.exists():
            c.mkdir(parents=True, exist_ok=True)
            creado["carpetas"].append(str(c))
    originales = r.respaldos / "originales"
    for tipo, (interno, original) in ARCHIVOS.items():
        destino = r.archivo(tipo)
        semilla = SEED_DIR / interno
        if not destino.exists() and semilla.exists():
            _copiar(semilla, destino)
            creado["archivos"].append(str(destino))
            originales.mkdir(parents=True, exist_ok=True)
            orig = originales / original
            if not orig.exists():
                _copiar(semilla, orig)
            registrar(r, "instalacion", tipo, original, None, "OK",
                      f"Base inicial copiada como {interno}")
    if not r.ajustes.exists():
        r.ajustes.write_text(json.dumps({"bucle_eventos": "selector", "puerto_inicial": 8501},
                                        indent=2), encoding="utf-8")
    semilla_eq = SEED_DIR / "equipo.json"
    if semilla_eq.exists() and not r.equipo.exists():
        _copiar(semilla_eq, r.equipo)
        creado["archivos"].append(str(r.equipo))
    if creado["carpetas"] or creado["archivos"]:
        get_logger(r).info("Inicialización: %s", creado)
    return creado


def faltantes(r: Rutas | None = None) -> list[str]:
    r = r or rutas()
    return [t for t in ARCHIVOS if not r.archivo(t).exists()]


# ---------------------------------------------------------------- historial
def registrar(r: Rutas, accion: str, tipo: str, archivo: str, filas, resultado: str,
              detalle: str = "") -> None:
    r.respaldos.mkdir(parents=True, exist_ok=True)
    nuevo = not r.historial.exists()
    try:
        usuario = getpass.getuser()
    except Exception:  # noqa: BLE001
        usuario = "desconocido"
    with open(r.historial, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=HIST_CAMPOS)
        if nuevo:
            w.writeheader()
        w.writerow({"fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "accion": accion,
                    "tipo": tipo, "archivo": archivo, "filas": "" if filas is None else filas,
                    "resultado": resultado, "detalle": detalle[:500], "usuario": usuario})
    get_logger(r).info("%s %s %s %s %s", accion, tipo, archivo, resultado, detalle[:200])


def leer_historial(r: Rutas | None = None) -> list[dict]:
    r = r or rutas()
    if not r.historial.exists():
        return []
    with open(r.historial, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))[::-1]


# ---------------------------------------------------------------- respaldos
def respaldar(r: Rutas, tipo: str, motivo: str = "reemplazo") -> Path | None:
    actual = r.archivo(tipo)
    if not actual.exists():
        return None
    carpeta = r.respaldos / tipo
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    destino = carpeta / f"{marca}_{actual.name}"
    shutil.copyfile(actual, destino)  # la fecha del respaldo = momento en que se crea
    registrar(r, "respaldo", tipo, destino.name, None, "OK", f"Motivo: {motivo}")
    return destino


def listar_respaldos(r: Rutas | None = None, tipo: str | None = None) -> list[dict]:
    r = r or rutas()
    tipos = [tipo] if tipo else list(ARCHIVOS)
    out = []
    for t in tipos:
        carpeta = r.respaldos / t
        if carpeta.exists():
            for p in carpeta.glob("*.xlsx"):
                st = p.stat()
                out.append({"tipo": t, "archivo": p.name, "ruta": str(p),
                            "tamano_kb": round(st.st_size / 1024, 1),
                            "fecha": datetime.fromtimestamp(st.st_mtime)})
    originales = r.respaldos / "originales"
    if originales.exists():
        for p in originales.glob("*.xlsx"):
            t = next((k for k, v in ARCHIVOS.items() if v[1] == p.name), None)
            if t and (tipo is None or t == tipo):
                st = p.stat()
                out.append({"tipo": t, "archivo": f"ORIGINAL · {p.name}", "ruta": str(p),
                            "tamano_kb": round(st.st_size / 1024, 1),
                            "fecha": datetime.fromtimestamp(st.st_mtime)})
    return sorted(out, key=lambda x: x["fecha"], reverse=True)


def guardar_archivo(r: Rutas, tipo: str, contenido: bytes, nombre_origen: str, filas: int,
                    detalle: str = "") -> Path | None:
    """Respaldar la versión vigente y escribir la nueva de forma atómica."""
    respaldo = respaldar(r, tipo, f"antes de cargar {nombre_origen}")
    destino = r.archivo(tipo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_bytes(contenido)
    tmp.replace(destino)
    registrar(r, "carga", tipo, nombre_origen, filas, "OK", detalle)
    return respaldo


def restaurar(r: Rutas, tipo: str, ruta_respaldo: str) -> Path | None:
    origen = Path(ruta_respaldo)
    if not origen.exists():
        raise FileNotFoundError(ruta_respaldo)
    previo = respaldar(r, tipo, f"antes de restaurar {origen.name}")
    destino = r.archivo(tipo)
    tmp = destino.with_suffix(".tmp")
    _copiar(origen, tmp)
    tmp.replace(destino)
    registrar(r, "restauracion", tipo, origen.name, None, "OK", "Versión restaurada")
    return previo


def migrar(origen: Rutas, destino: Rutas) -> None:
    """Copia datos, configuración y respaldos a una nueva ubicación."""
    for c in destino.carpetas():
        c.mkdir(parents=True, exist_ok=True)
    for sub in ("data", "config"):
        src = origen.root / sub
        if src.exists():
            shutil.copytree(src, destino.root / sub, dirs_exist_ok=True, copy_function=_copiar)


# ---------------------------------------------------------------- equipo
EQUIPO_VACIO = {"numero_equipo": "", "integrantes": [], "asignatura":
                "Sistemas de Información para la Toma de Decisiones Comerciales",
                "programa": "Maestría en Dirección Comercial y Ventas", "profesor": "",
                "universidad": "UNIR", "fecha_entrega": ""}


def leer_equipo(r: Rutas | None = None) -> dict:
    r = r or rutas()
    datos = dict(EQUIPO_VACIO)
    if r.equipo.exists():
        try:
            datos.update(json.loads(r.equipo.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return datos


def guardar_equipo(r: Rutas, datos: dict) -> None:
    r.config.mkdir(parents=True, exist_ok=True)
    r.equipo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar(r, "equipo", "config", "equipo.json", None, "OK", "Identificación actualizada")

"""Resolución de rutas y configuración.

Separa por completo el código (carpeta de la aplicación) de los datos
(carpeta de almacenamiento). La carpeta de almacenamiento se decide así:

1. Variable de entorno SFCP_HOME (útil para servidores y pruebas).
2. Archivo "puntero" en el perfil del usuario, escrito cuando el usuario
   cambia la ubicación desde la aplicación.
3. Valor predeterminado:
   - Windows: C:\\SanFranciscoCrustPizza si se puede escribir; si no,
     %LOCALAPPDATA%\\SanFranciscoCrustPizza.
   - Servidor/Linux/macOS: carpeta "almacenamiento" junto al código.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "SanFranciscoCrustPizza"
APP_TITLE = "SAN FRANCISCO CRUST PIZZA"
APP_SUBTITLE = "Sistema Inteligente de Información y Decisiones Comerciales"
APP_VERSION = "1.0.0"
IS_WINDOWS = os.name == "nt"
DEFAULT_PORT = 8501

# Carpeta del código fuente (sfcp_src). En el ejecutable congelado,
# PyInstaller coloca los archivos en sys._MEIPASS.
if getattr(sys, "frozen", False):
    CODE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    CODE_DIR = Path(__file__).resolve().parent.parent

SEED_DIR = CODE_DIR / "datos_iniciales"

# Nombres normalizados  <->  nombres originales entregados por la empresa
ARCHIVOS = {
    "ventas": ("ventas.xlsx", "San_Francisco_Crust_Pizza_Ventas.xlsx"),
    "clientes": ("clientes.xlsx", "San_Francisco_Crust_Pizza_Clientes.xlsx"),
    "productos": ("productos.xlsx", "San_Francisco_Crust_Pizza_Productos.xlsx"),
}


def is_cloud() -> bool:
    """Detecta ejecución en un servidor público (p. ej. Streamlit Community Cloud)."""
    if os.environ.get("SFCP_CLOUD") == "1":
        return True
    return str(CODE_DIR).startswith("/mount/src")


def _local_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), "AppData", "Local")
    return Path(base) / APP_NAME


def pointer_file() -> Path:
    if IS_WINDOWS:
        return _local_appdata() / "ubicacion.json"
    return Path.home() / ".sfcp" / "ubicacion.json"


def is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".prueba_", delete=True):
            pass
        return True
    except OSError:
        return False


def default_root() -> Path:
    if IS_WINDOWS and not is_cloud():
        preferred = Path("C:/SanFranciscoCrustPizza")
        if is_writable(preferred):
            return preferred
        return _local_appdata() / "datos"
    return CODE_DIR / "almacenamiento"


def get_root() -> Path:
    env = os.environ.get("SFCP_HOME")
    if env:
        return Path(env)
    pf = pointer_file()
    if pf.exists():
        try:
            p = Path(json.loads(pf.read_text(encoding="utf-8"))["ruta"])
            if is_writable(p):
                return p
        except (OSError, ValueError, KeyError):
            pass
    return default_root()


def set_root(new_root: Path) -> None:
    """Guarda la nueva ubicación de almacenamiento elegida por el usuario."""
    new_root = Path(new_root)
    if not is_writable(new_root):
        raise PermissionError(f"No se puede escribir en {new_root}")
    pf = pointer_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(json.dumps({"ruta": str(new_root)}, ensure_ascii=False), encoding="utf-8")


@dataclass(frozen=True)
class Rutas:
    root: Path

    @property
    def app(self) -> Path: return self.root / "app"
    @property
    def data(self) -> Path: return self.root / "data"
    @property
    def ventas_dir(self) -> Path: return self.data / "ventas"
    @property
    def maestros_dir(self) -> Path: return self.data / "maestros"
    @property
    def respaldos(self) -> Path: return self.data / "respaldos"
    @property
    def config(self) -> Path: return self.root / "config"
    @property
    def logs(self) -> Path: return self.root / "logs"
    @property
    def documentacion(self) -> Path: return self.root / "documentacion"
    @property
    def reportes(self) -> Path: return self.root / "reportes"

    def archivo(self, tipo: str) -> Path:
        nombre = ARCHIVOS[tipo][0]
        return (self.ventas_dir if tipo == "ventas" else self.maestros_dir) / nombre

    @property
    def historial(self) -> Path: return self.respaldos / "historial_cargas.csv"
    @property
    def equipo(self) -> Path: return self.config / "equipo.json"
    @property
    def ajustes(self) -> Path: return self.config / "config.json"

    def carpetas(self) -> list[Path]:
        return [self.app, self.data, self.ventas_dir, self.maestros_dir, self.respaldos,
                self.config, self.logs, self.documentacion, self.reportes]


def rutas() -> Rutas:
    return Rutas(get_root())

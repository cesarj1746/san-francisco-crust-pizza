"""Lanzador de escritorio de San Francisco Crust Pizza (SanFranciscoCrustPizza.exe).

Modos:
    SanFranciscoCrustPizza.exe               -> inicia la aplicación (modo normal)
    SanFranciscoCrustPizza.exe --detener     -> cierra una instancia en ejecución
                                  (añadir --silencioso para no mostrar mensajes)
    SanFranciscoCrustPizza.exe --servidor N  -> (interno) servidor Streamlit en el puerto N

Pasos del modo normal:
 1. Verifica la configuración y crea la estructura de carpetas.
 2. Verifica las bases maestras y de ventas.
 3. Si ya hay una instancia activa, solo abre el navegador.
 4. Busca un puerto libre (8501 por defecto).
 5. Inicia el servidor Streamlit en segundo plano, sin ventana de consola.
 6. Comprueba que el servidor responda.
 7. Abre el navegador y muestra una pequeña ventana de control para cerrar la aplicación.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(BASE))

from sfcp import config, storage  # noqa: E402

CREATE_NO_WINDOW = 0x08000000
log = logging.getLogger("lanzador")


def _setup_log(r: config.Rutas) -> None:
    r.logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=r.logs / "lanzador.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(message)s")


def _puerto_libre(inicio: int = config.DEFAULT_PORT, fin: int = 8600) -> int:
    for p in range(inicio, fin):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("No hay puertos libres entre 8501 y 8600")


def _salud(puerto: int, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{puerto}/_stcore/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _archivo_instancia(r: config.Rutas) -> Path:
    return r.config / "instancia.json"


def _pid_vivo(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                             creationflags=CREATE_NO_WINDOW)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _matar(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=CREATE_NO_WINDOW)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def _cmd_servidor(puerto: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--servidor", str(puerto)]
    return [sys.executable, str(Path(__file__).resolve()), "--servidor", str(puerto)]


# ------------------------------------------------------------------ servidor
def servidor(puerto: int) -> None:
    try:  # salida del servidor a un archivo de registro (en modo ventana no hay consola)
        r = config.rutas()
        r.logs.mkdir(parents=True, exist_ok=True)
        f = open(r.logs / "servidor.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stderr = f
    except OSError:
        pass
    bucle = "selector"
    try:
        aj = json.loads(config.rutas().ajustes.read_text(encoding="utf-8"))
        bucle = aj.get("bucle_eventos", bucle)
    except (OSError, ValueError):
        pass
    if os.environ.get("SFCP_PROACTOR") == "1":
        bucle = "proactor"
    if os.name == "nt" and bucle != "proactor":
        # Bucle de eventos "selector": el mismo que usaba Streamlit con Tornado en Windows.
        # Evita bloqueos de E/S superpuesta observados en algunos entornos (p. ej. Wine).
        import asyncio
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from streamlit.web import bootstrap
    opciones = {
        "server.port": puerto, "server.headless": True, "server.address": "localhost",
        "global.developmentMode": False, "browser.gatherUsageStats": False,
        "server.fileWatcherType": "none", "server.runOnSave": False, "server.maxUploadSize": 200,
        "theme.primaryColor": "#1F5F99", "theme.backgroundColor": "#F5F7FA",
        "theme.secondaryBackgroundColor": "#E9EDF2", "theme.textColor": "#1D2A3A",
        "client.toolbarMode": "minimal",
    }
    bootstrap.load_config_options(flag_options=opciones)
    bootstrap.run(str(BASE / "app.py"), False, [], opciones)


# ------------------------------------------------------------------ detener
def detener(r: config.Rutas, silencioso: bool = False) -> bool:
    f = _archivo_instancia(r)
    if not f.exists():
        if not silencioso:
            _mensaje("San Francisco Crust Pizza", "La aplicación no está en ejecución.")
        return False
    info = json.loads(f.read_text(encoding="utf-8"))
    _matar(int(info["pid"]))
    f.unlink(missing_ok=True)
    log.info("Instancia detenida: %s", info)
    if not silencioso:
        _mensaje("San Francisco Crust Pizza", "La aplicación se cerró correctamente.")
    return True


def _mensaje(titulo: str, texto: str, error: bool = False) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)(titulo, texto)
        root.destroy()
    except Exception:  # noqa: BLE001
        print(f"{titulo}: {texto}")


# ------------------------------------------------------------------ ventana
def ventana(r: config.Rutas, proc: subprocess.Popen, url: str) -> None:
    import tkinter as tk
    root = tk.Tk()
    root.title("San Francisco Crust Pizza")
    root.geometry("460x270")
    root.resizable(False, False)
    root.configure(bg="#0B2545")
    try:
        ico = BASE / "recursos" / "icono.ico"
        if ico.exists():
            root.iconbitmap(str(ico))
    except Exception:  # noqa: BLE001
        pass
    tk.Label(root, text="SAN FRANCISCO CRUST PIZZA", fg="white", bg="#0B2545",
             font=("Segoe UI", 14, "bold")).pack(pady=(16, 0))
    tk.Label(root, text="Sistema Inteligente de Información y Decisiones Comerciales", fg="#B8C9DD",
             bg="#0B2545", font=("Segoe UI", 9)).pack()
    estado = tk.StringVar(value=f"● En ejecución en {url}")
    tk.Label(root, textvariable=estado, fg="#9BE3B4", bg="#0B2545", font=("Segoe UI", 10)).pack(pady=10)
    tk.Label(root, text=f"Datos: {r.root}", fg="#8DA9C4", bg="#0B2545", font=("Segoe UI", 8)).pack()
    marco = tk.Frame(root, bg="#0B2545")
    marco.pack(pady=14)

    def abrir():
        webbrowser.open(url)

    def carpeta():
        try:
            os.startfile(str(r.root))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def cerrar():
        estado.set("Cerrando…")
        root.update()
        _matar(proc.pid)
        _archivo_instancia(r).unlink(missing_ok=True)
        log.info("Aplicación cerrada por el usuario")
        root.destroy()

    est = dict(font=("Segoe UI", 10), relief="flat", padx=10, pady=6, cursor="hand2")
    tk.Button(marco, text="Abrir dashboard", command=abrir, bg="#4A90C2", fg="white", **est).grid(row=0, column=0, padx=5)
    tk.Button(marco, text="Carpeta de datos", command=carpeta, bg="#13315C", fg="white", **est).grid(row=0, column=1, padx=5)
    tk.Button(marco, text="Cerrar aplicación", command=cerrar, bg="#B3261E", fg="white", **est).grid(row=0, column=2, padx=5)
    tk.Label(root, text="Cerrar esta ventana también detiene la aplicación.", fg="#8DA9C4", bg="#0B2545",
             font=("Segoe UI", 8)).pack()
    root.protocol("WM_DELETE_WINDOW", cerrar)

    def vigilar():
        if proc.poll() is not None:
            estado.set("⚠ El servidor se detuvo. Revise la carpeta logs.")
        else:
            root.after(3000, vigilar)
    root.after(3000, vigilar)
    root.mainloop()


# ------------------------------------------------------------------ principal
def principal() -> int:
    r = config.rutas()
    try:
        storage.initialize(r)
    except PermissionError:
        destino = config.Rutas(config._local_appdata() / "datos")  # noqa: SLF001
        config.set_root(destino.root)
        r = destino
        storage.initialize(r)
    _setup_log(r)
    log.info("Inicio. Código: %s · Datos: %s", BASE, r.root)
    faltan = storage.faltantes(r)
    if faltan:
        log.warning("Bases faltantes: %s", faltan)

    f = _archivo_instancia(r)
    if f.exists():
        try:
            info = json.loads(f.read_text(encoding="utf-8"))
            if _pid_vivo(int(info["pid"])) and _salud(int(info["puerto"])):
                webbrowser.open(info["url"])
                log.info("Instancia ya activa; se abre el navegador en %s", info["url"])
                return 0
        except Exception:  # noqa: BLE001
            pass
        f.unlink(missing_ok=True)

    puerto = _puerto_libre()
    url = f"http://localhost:{puerto}"
    env = dict(os.environ, SFCP_HOME=str(r.root), PYINSTALLER_RESET_ENVIRONMENT="1")
    for k in [k for k in env if k.startswith("_PYI") or k in ("TCL_LIBRARY", "TK_LIBRARY")]:
        env.pop(k, None)
    kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
    proc = subprocess.Popen(_cmd_servidor(puerto), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, cwd=str(BASE), **kw)
    log.info("Servidor iniciado PID %s en %s", proc.pid, url)
    t0 = time.time()
    while time.time() - t0 < 180:
        if proc.poll() is not None:
            log.error("El servidor terminó con código %s", proc.returncode)
            _mensaje("San Francisco Crust Pizza", "No se pudo iniciar el servidor. Revise "
                     f"{r.logs / 'servidor.log'}", error=True)
            return 1
        if _salud(puerto):
            break
        time.sleep(0.5)
    else:
        _matar(proc.pid)
        _mensaje("San Francisco Crust Pizza", "El servidor no respondió a tiempo.", error=True)
        return 1
    log.info("Servidor operativo en %.1f s", time.time() - t0)
    f.write_text(json.dumps({"pid": proc.pid, "puerto": puerto, "url": url}), encoding="utf-8")
    if os.environ.get("SFCP_NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        ventana(r, proc, url)
    except Exception as e:  # noqa: BLE001
        log.warning("Sin ventana de control (%s); esperando al servidor", e)
        proc.wait()
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    args = sys.argv[1:]
    if args[:1] == ["--servidor"]:
        servidor(int(args[1]))
    elif args[:1] == ["--detener"]:
        rr = config.rutas()
        _setup_log(rr)
        detener(rr, silencioso="--silencioso" in args)
    else:
        sys.exit(principal())

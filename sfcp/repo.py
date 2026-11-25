"""Repositorio de datos con caché: se recarga automáticamente cuando cambia
cualquier archivo (fecha de modificación o tamaño)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from . import data, storage
from .config import Rutas, rutas


@dataclass
class Datos:
    ventas: pd.DataFrame
    clientes: pd.DataFrame
    productos: pd.DataFrame
    modelo: pd.DataFrame
    firma: tuple


def _firma(r: Rutas) -> tuple:
    out = []
    for t in ("ventas", "clientes", "productos"):
        p = r.archivo(t)
        s = p.stat()
        out.append((str(p), s.st_mtime_ns, s.st_size))
    return tuple(out)


@st.cache_data(show_spinner="Cargando bases de datos…", max_entries=3)
def _cargar(firma: tuple) -> tuple:
    rv, rc, rp = (f[0] for f in firma)
    v = data.preparar_ventas(data.leer_tabla(rv))
    c = data.preparar_clientes(data.leer_tabla(rc))
    p = data.preparar_productos(data.leer_tabla(rp))
    m = data.construir_modelo(v, c, p)
    return v, c, p, m


def obtener() -> Datos:
    r = rutas()
    storage.initialize(r)
    faltan = storage.faltantes(r)
    if faltan:
        raise FileNotFoundError("Faltan bases: " + ", ".join(faltan))
    f = _firma(r)
    v, c, p, m = _cargar(f)
    return Datos(v, c, p, m, f)


def invalidar() -> None:
    _cargar.clear()

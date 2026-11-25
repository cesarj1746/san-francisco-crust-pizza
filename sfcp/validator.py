"""Validación de archivos antes de aceptarlos.

Errores  -> el archivo se rechaza y la base vigente NO se modifica.
Advertencias -> el archivo se acepta, pero se informa al usuario.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import normalizar_columnas, preparar_clientes, preparar_productos, preparar_ventas
from .schema import ESQUEMAS, VENTAS_NUM


@dataclass
class Resultado:
    tipo: str
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)
    df: pd.DataFrame | None = None

    @property
    def ok(self) -> bool:
        return not self.errores


def _ej(serie, n=5) -> str:
    vals = [str(x) for x in list(dict.fromkeys(serie.tolist()))[:n]]
    return ", ".join(vals) + ("…" if serie.nunique() > n else "")


def _estructura(df: pd.DataFrame, tipo: str, res: Resultado) -> bool:
    req, opc, clave = ESQUEMAS[tipo]
    if df is None or df.empty:
        res.errores.append("El archivo está vacío o no tiene filas de datos.")
        return False
    faltan = [c for c in req if c not in df.columns]
    if faltan:
        res.errores.append("Faltan columnas obligatorias: " + ", ".join(faltan)
                           + ". Columnas encontradas: " + ", ".join(map(str, df.columns)))
        return False
    extra = [c for c in df.columns if c not in req + opc]
    if extra:
        res.advertencias.append("Columnas adicionales que la aplicación no utiliza: "
                                + ", ".join(map(str, extra)))
    ids = df[clave].astype("string").str.strip()
    if ids.isna().any() or (ids == "").any():
        res.errores.append(f"Hay {int(ids.isna().sum() + (ids == '').sum())} filas sin {clave}.")
    dup = ids[ids.duplicated(keep=False) & ids.notna()]
    if len(dup):
        res.errores.append(f"{clave} duplicados ({dup.nunique()} identificadores repetidos): "
                           + _ej(dup))
    filas_dup = int(df.duplicated().sum())
    if filas_dup:
        res.errores.append(f"Hay {filas_dup} filas completamente duplicadas.")
    nulos = df[req].isna().sum()
    nulos = nulos[nulos > 0]
    if len(nulos):
        res.errores.append("Valores vacíos en columnas obligatorias: "
                           + ", ".join(f"{k} ({v})" for k, v in nulos.items()))
    return True


def validar_ventas(df: pd.DataFrame, clientes: pd.DataFrame | None,
                   productos: pd.DataFrame | None) -> Resultado:
    res = Resultado("ventas")
    df = normalizar_columnas(df, "ventas")
    if not _estructura(df, "ventas", res):
        return res
    fechas = pd.to_datetime(df["Fecha"], errors="coerce")
    malas = df.loc[fechas.isna() & df["Fecha"].notna(), "VentaID"]
    if len(malas):
        res.errores.append(f"{len(malas)} fechas no válidas (VentaID: {_ej(malas)}).")
    if fechas.notna().any():
        futuro = fechas > pd.Timestamp.now() + pd.Timedelta(days=1)
        if futuro.any():
            res.advertencias.append(f"{int(futuro.sum())} ventas con fecha futura.")
    for c in VENTAS_NUM:
        num = pd.to_numeric(df[c], errors="coerce")
        bad = num.isna() & df[c].notna()
        if bad.any():
            res.errores.append(f"La columna {c} tiene {int(bad.sum())} valores no numéricos.")
        if (num < 0).any() and c != "UtilidadBruta":
            res.errores.append(f"La columna {c} tiene {int((num < 0).sum())} valores negativos.")
    cant = pd.to_numeric(df["Cantidad"], errors="coerce")
    if (cant <= 0).any():
        res.errores.append(f"{int((cant <= 0).sum())} ventas con Cantidad igual o menor a cero.")
    if res.errores:
        return res
    v = preparar_ventas(df)
    # Coherencia de cálculos (advertencia, la app usa los valores del archivo)
    calc_vn = (v.Cantidad * v.PrecioUnitario * (1 - v.DescuentoPct / 100)).round(2)
    d1 = (calc_vn - v.VentaNeta).abs() > 0.05
    d2 = ((v.VentaNeta - v.CostoTotal) - v.UtilidadBruta).abs() > 0.05
    if d1.any():
        res.advertencias.append(f"{int(d1.sum())} filas donde VentaNeta no coincide con "
                                "Cantidad × Precio × (1 − Descuento).")
    if d2.any():
        res.advertencias.append(f"{int(d2.sum())} filas donde UtilidadBruta ≠ VentaNeta − CostoTotal.")
    if (v.UtilidadBruta < 0).any():
        res.advertencias.append(f"{int((v.UtilidadBruta < 0).sum())} ventas con utilidad negativa.")
    # Integridad referencial
    if clientes is not None and "ClienteID" in clientes:
        ids = set(clientes["ClienteID"].astype("string").str.strip())
        sin = v.loc[~v.ClienteID.isin(ids), "ClienteID"]
        if len(sin):
            res.errores.append(f"{sin.nunique()} ClienteID no existen en el maestro de clientes "
                               f"({len(sin)} ventas): {_ej(sin)}. Actualice primero el maestro.")
    if productos is not None and "ProductoID" in productos:
        ids = set(productos["ProductoID"].astype("string").str.strip())
        sin = v.loc[~v.ProductoID.isin(ids), "ProductoID"]
        if len(sin):
            res.errores.append(f"{sin.nunique()} ProductoID no existen en el maestro de productos "
                               f"({len(sin)} ventas): {_ej(sin)}. Actualice primero el maestro.")
    # Jerarquía ciudad -> sucursal
    jer = v.groupby("Sucursal")["Ciudad"].nunique()
    if (jer > 1).any():
        res.advertencias.append("Sucursales asociadas a más de una ciudad: "
                                + ", ".join(jer[jer > 1].index))
    res.info = {"filas": len(v), "desde": v.Fecha.min(), "hasta": v.Fecha.max(),
                "ventas_netas": float(v.VentaNeta.sum()), "clientes": v.ClienteID.nunique(),
                "productos": v.ProductoID.nunique(), "sucursales": v.Sucursal.nunique()}
    res.df = v
    return res


def validar_clientes(df: pd.DataFrame, ventas: pd.DataFrame | None) -> Resultado:
    res = Resultado("clientes")
    df = normalizar_columnas(df, "clientes")
    if not _estructura(df, "clientes", res):
        return res
    c = preparar_clientes(df)
    if "Edad" in c and ((c.Edad < 0) | (c.Edad > 120)).any():
        res.advertencias.append("Hay edades fuera del rango 0–120.")
    if "NPS" in c and ((c.NPS < 0) | (c.NPS > 10)).any():
        res.advertencias.append("Hay valores de NPS fuera de la escala 0–10.")
    if ventas is not None:
        usados = set(ventas["ClienteID"].astype("string").str.strip())
        faltan = usados - set(c.ClienteID)
        if faltan:
            res.errores.append(f"El nuevo maestro no contiene {len(faltan)} clientes que sí "
                               f"aparecen en la base de ventas vigente: {_ej(pd.Series(sorted(faltan)))}.")
    res.info = {"filas": len(c), "segmentos": c.Segmento.nunique()}
    res.df = c
    return res


def validar_productos(df: pd.DataFrame, ventas: pd.DataFrame | None) -> Resultado:
    res = Resultado("productos")
    df = normalizar_columnas(df, "productos")
    if not _estructura(df, "productos", res):
        return res
    p = preparar_productos(df)
    if {"CostoUSD", "PrecioVentaUSD"} <= set(p.columns):
        neg = (p.PrecioVentaUSD < p.CostoUSD)
        if neg.any():
            res.advertencias.append(f"{int(neg.sum())} productos con precio de catálogo menor al costo.")
    if ventas is not None:
        usados = set(ventas["ProductoID"].astype("string").str.strip())
        faltan = usados - set(p.ProductoID)
        if faltan:
            res.errores.append(f"El nuevo maestro no contiene {len(faltan)} productos que sí "
                               f"aparecen en la base de ventas vigente: {_ej(pd.Series(sorted(faltan)))}.")
    res.info = {"filas": len(p), "categorias": p.Categoria.nunique()}
    res.df = p
    return res


_ = np  # (numpy disponible para futuras reglas)

"""Lectura, normalización y modelo integrado (ventas + clientes + productos)."""
from __future__ import annotations

import io
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import ESQUEMAS


def _clave(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return "".join(ch for ch in s.lower() if ch.isalnum())


def leer_tabla(fuente, nombre: str = "") -> pd.DataFrame:
    """Lee .xlsx/.xls/.csv desde ruta o bytes. Usa la primera hoja."""
    nombre = nombre or (str(fuente) if not isinstance(fuente, (bytes, bytearray)) else "")
    buf = io.BytesIO(fuente) if isinstance(fuente, (bytes, bytearray)) else fuente
    if nombre.lower().endswith(".csv"):
        raw = buf.getvalue() if isinstance(buf, io.BytesIO) else Path(buf).read_bytes()
        for enc in ("utf-8-sig", "latin-1"):
            try:
                txt = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        sep = ";" if txt.splitlines()[0].count(";") > txt.splitlines()[0].count(",") else ","
        return pd.read_csv(io.StringIO(txt), sep=sep)
    try:
        return pd.read_excel(buf, engine="calamine")
    except Exception:  # noqa: BLE001  (sin calamine o formato raro)
        if isinstance(buf, io.BytesIO):
            buf.seek(0)
        return pd.read_excel(buf)


def normalizar_columnas(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    req, opc, _ = ESQUEMAS[tipo]
    mapa = {_clave(c): c for c in req + opc}
    ren = {}
    for c in df.columns:
        k = _clave(c)
        if k in mapa and c != mapa[k]:
            ren[c] = mapa[k]
    df = df.rename(columns=ren)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def preparar_ventas(v: pd.DataFrame) -> pd.DataFrame:
    v = normalizar_columnas(v.copy(), "ventas")
    v["Fecha"] = pd.to_datetime(v["Fecha"], errors="coerce", dayfirst=False)
    for c in ["Cantidad", "PrecioUnitario", "CostoUnitario", "DescuentoPct", "VentaNeta",
              "CostoTotal", "UtilidadBruta", "TiempoEntregaMin", "TiempoPreparacionMin"]:
        if c in v:
            v[c] = pd.to_numeric(v[c], errors="coerce")
    # Año/Mes/Trimestre siempre derivados de la fecha (garantiza coherencia)
    v["Año"] = v["Fecha"].dt.year
    v["Mes"] = v["Fecha"].dt.month
    v["Trimestre"] = v["Fecha"].dt.quarter
    v["Periodo"] = v["Fecha"].dt.to_period("M").dt.to_timestamp()
    for c in ["VentaID", "ClienteID", "ProductoID", "Ciudad", "Sucursal", "Canal", "FormaPago"]:
        v[c] = v[c].astype("string").str.strip()
    return v


def preparar_clientes(c: pd.DataFrame) -> pd.DataFrame:
    c = normalizar_columnas(c.copy(), "clientes")
    c["ClienteID"] = c["ClienteID"].astype("string").str.strip()
    for col in ["FechaRegistro", "UltimaCompra"]:
        if col in c:
            c[col] = pd.to_datetime(c[col], errors="coerce")
    for col in ["Edad", "NPS", "TotalCompras", "GastoAcumuladoUSD", "TicketPromedioUSD",
                "FrecuenciaCompraMensual"]:
        if col in c:
            c[col] = pd.to_numeric(c[col], errors="coerce")
    return c


def preparar_productos(p: pd.DataFrame) -> pd.DataFrame:
    p = normalizar_columnas(p.copy(), "productos")
    p["ProductoID"] = p["ProductoID"].astype("string").str.strip()
    for col in ["CostoUSD", "PrecioVentaUSD", "MargenBrutoUSD", "MargenPorcentaje"]:
        if col in p:
            p[col] = pd.to_numeric(p[col], errors="coerce")
    tam = p["Tamaño"].astype("string").fillna("") if "Tamaño" in p else ""
    p["ProductoNombre"] = (p["Producto"].astype("string") + " " + tam).str.replace(
        " Único", "", regex=False).str.strip()
    p["Etiqueta"] = p["ProductoID"] + " · " + p["ProductoNombre"]
    return p


def construir_modelo(v: pd.DataFrame, c: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    """Une las ventas con los atributos descriptivos de los maestros.

    Las métricas se calculan SIEMPRE desde las ventas; de los maestros solo
    se toman atributos descriptivos (segmento, edad, NPS, categoría...).
    """
    cols_c = [x for x in ["ClienteID", "Segmento", "Edad", "Sexo", "NPS", "ClienteActivo",
                          "MotivoPerdida", "Ciudad", "Nombre"] if x in c]
    cc = c[cols_c].rename(columns={"Ciudad": "CiudadCliente", "Nombre": "NombreCliente"})
    cols_p = [x for x in ["ProductoID", "Categoria", "Producto", "Tamaño", "ProductoNombre",
                          "Etiqueta", "Activo", "PrecioVentaUSD", "CostoUSD"] if x in p]
    m = v.merge(cc, on="ClienteID", how="left", validate="many_to_one")
    m = m.merge(p[cols_p], on="ProductoID", how="left", validate="many_to_one")
    for col in ["Segmento", "Categoria", "ProductoNombre", "Etiqueta"]:
        if col in m:
            m[col] = m[col].astype("string").fillna("Sin dato en maestro")
    m["ConDescuento"] = m["DescuentoPct"] > 0
    m["Bruto"] = m["Cantidad"] * m["PrecioUnitario"]
    m["DescuentoUSD"] = m["Bruto"] - m["VentaNeta"]
    return m


def resumen_archivo(df: pd.DataFrame, tipo: str) -> dict:
    out = {"filas": len(df), "columnas": len(df.columns)}
    if tipo == "ventas" and "Fecha" in df:
        f = pd.to_datetime(df["Fecha"], errors="coerce")
        out["desde"] = f.min()
        out["hasta"] = f.max()
    return out


def rango_edad(e) -> str:
    if pd.isna(e):
        return "Sin dato"
    bins = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 200)]
    for a, b in bins:
        if a <= e <= b:
            return f"{a}-{b}" if b < 200 else "65+"
    return "Menor de 18"


NP_NAN = np.nan

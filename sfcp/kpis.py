"""Fórmulas comerciales oficiales. Toda la aplicación (dashboard, análisis,
asistente, informes y pruebas) usa estas funciones; no hay cálculos duplicados.

Definiciones:
- Ventas totales      = Σ VentaNeta
- Utilidad bruta      = Σ UtilidadBruta
- Margen bruto (%)    = Σ UtilidadBruta / Σ VentaNeta × 100   (ponderado, nunca promedio simple)
- Ticket promedio     = Σ VentaNeta / nº de VentaID únicos
- Clientes            = nº de ClienteID únicos con ventas en el período
- Transacciones       = nº de VentaID únicos
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

DEFINICIONES = {
    "Ventas totales": "Suma de la venta neta (después de descuentos) de todas las transacciones del período filtrado.",
    "Utilidad bruta": "Suma de la utilidad bruta (venta neta − costo total) de las transacciones del período.",
    "Margen bruto": "Utilidad bruta total ÷ ventas netas totales × 100. Es un margen ponderado: los productos que más venden pesan más.",
    "Ticket promedio": "Ventas netas totales ÷ número de transacciones únicas (VentaID). En esta base cada transacción registra un solo producto.",
    "Clientes": "Número de clientes distintos (ClienteID) que compraron en el período filtrado. No es el total de clientes registrados.",
    "Transacciones": "Número de ventas distintas (VentaID) del período filtrado.",
    "Unidades": "Suma de las cantidades vendidas.",
}


def resumen(df: pd.DataFrame) -> dict:
    vn = float(df["VentaNeta"].sum()) if len(df) else 0.0
    ub = float(df["UtilidadBruta"].sum()) if len(df) else 0.0
    tx = int(df["VentaID"].nunique()) if len(df) else 0
    return {
        "ventas": vn,
        "utilidad": ub,
        "margen": (ub / vn * 100) if vn else np.nan,
        "ticket": (vn / tx) if tx else np.nan,
        "clientes": int(df["ClienteID"].nunique()) if len(df) else 0,
        "transacciones": tx,
        "unidades": int(df["Cantidad"].sum()) if len(df) else 0,
        "costo": float(df["CostoTotal"].sum()) if len(df) else 0.0,
        "descuento": float(df["DescuentoUSD"].sum()) if "DescuentoUSD" in df and len(df) else 0.0,
    }


def por(df: pd.DataFrame, dims, orden: str | None = "ventas") -> pd.DataFrame:
    """Indicadores agregados por una o varias dimensiones."""
    if isinstance(dims, str):
        dims = [dims]
    if df.empty:
        return pd.DataFrame(columns=dims + ["ventas", "utilidad", "margen", "transacciones",
                                            "ticket", "clientes", "unidades", "participacion"])
    g = df.groupby(dims, observed=True, dropna=False).agg(
        ventas=("VentaNeta", "sum"), utilidad=("UtilidadBruta", "sum"),
        transacciones=("VentaID", "nunique"), clientes=("ClienteID", "nunique"),
        unidades=("Cantidad", "sum"), costo=("CostoTotal", "sum")).reset_index()
    g["margen"] = np.where(g.ventas > 0, g.utilidad / g.ventas * 100, np.nan)
    g["ticket"] = np.where(g.transacciones > 0, g.ventas / g.transacciones, np.nan)
    tot = g.ventas.sum()
    g["participacion"] = g.ventas / tot * 100 if tot else np.nan
    if orden:
        g = g.sort_values(orden, ascending=False)
    return g.reset_index(drop=True)


def mensual(df: pd.DataFrame) -> pd.DataFrame:
    g = por(df, "Periodo", orden=None).sort_values("Periodo")
    g["Año"] = g.Periodo.dt.year
    g["Mes"] = g.Periodo.dt.month
    return g


MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


# ------------------------------------------------------------ períodos
@dataclass
class Periodo:
    inicio: pd.Timestamp
    fin: pd.Timestamp

    def texto(self) -> str:
        return f"{self.inicio:%d/%m/%Y} – {self.fin:%d/%m/%Y}"


def periodo_anterior(inicio: pd.Timestamp, fin: pd.Timestamp,
                     data_min: pd.Timestamp) -> Periodo | None:
    """Período equivalente inmediatamente anterior.

    - Si el rango abarca meses completos, se desplaza en meses (p. ej. 2025 → 2024).
    - En otro caso se desplaza el mismo número de días.
    Devuelve None si el período anterior no está completamente cubierto por los datos.
    """
    inicio, fin = pd.Timestamp(inicio).normalize(), pd.Timestamp(fin).normalize()
    meses_completos = inicio.day == 1 and (fin + pd.Timedelta(days=1)).day == 1
    if meses_completos:
        n = (fin.year - inicio.year) * 12 + fin.month - inicio.month + 1
        p_ini = inicio - pd.DateOffset(months=n)
        p_fin = inicio - pd.Timedelta(days=1)
    else:
        dias = (fin - inicio).days + 1
        p_fin = inicio - pd.Timedelta(days=1)
        p_ini = p_fin - pd.Timedelta(days=dias - 1)
    if p_ini < pd.Timestamp(data_min).replace(day=1):
        return None
    return Periodo(pd.Timestamp(p_ini), pd.Timestamp(p_fin))


def variacion(actual: float, anterior: float) -> float:
    if anterior is None or pd.isna(anterior) or anterior == 0 or pd.isna(actual):
        return np.nan
    return (actual - anterior) / abs(anterior) * 100


# ------------------------------------------------------------ clientes
def clientes_desde_ventas(df: pd.DataFrame, fecha_corte: pd.Timestamp) -> pd.DataFrame:
    """Métricas por cliente calculadas exclusivamente desde la base de ventas."""
    if df.empty:
        return pd.DataFrame()
    meses = max(1, df["Periodo"].nunique())
    g = df.groupby("ClienteID").agg(
        compras=("VentaID", "nunique"), gasto=("VentaNeta", "sum"),
        utilidad=("UtilidadBruta", "sum"), primera=("Fecha", "min"), ultima=("Fecha", "max"),
        unidades=("Cantidad", "sum")).reset_index()
    g["ticket"] = g.gasto / g.compras
    g["frecuencia_mensual"] = g.compras / meses
    g["dias_sin_comprar"] = (pd.Timestamp(fecha_corte) - g.ultima).dt.days
    attrs = [c for c in ["ClienteID", "NombreCliente", "Segmento", "Edad", "Sexo", "NPS",
                         "ClienteActivo", "MotivoPerdida", "CiudadCliente"] if c in df]
    a = df[attrs].drop_duplicates("ClienteID")
    return g.merge(a, on="ClienteID", how="left")


def nps(scores: pd.Series) -> float:
    """NPS = % promotores (9–10) − % detractores (0–6). Ignora valores faltantes."""
    s = pd.to_numeric(scores, errors="coerce").dropna()
    if s.empty:
        return np.nan
    return ((s >= 9).mean() - (s <= 6).mean()) * 100


# ------------------------------------------------------------ sucursales
INDICADORES_SUC = {"ventas": "Ventas", "utilidad": "Utilidad bruta", "margen": "Margen bruto",
                   "transacciones": "Transacciones", "ticket": "Ticket promedio",
                   "unidades": "Unidades"}


def ranking_sucursales(df: pd.DataFrame, df_prev: pd.DataFrame | None = None) -> pd.DataFrame:
    """Evaluación multicriterio: promedio de la posición en 6 indicadores
    (1 = mejor). No se ordena solo por ventas."""
    s = por(df, ["Sucursal", "Ciudad"], orden=None)
    if s.empty:
        return s
    for k in INDICADORES_SUC:
        s[f"pos_{k}"] = s[k].rank(ascending=False, method="min")
    s["puntaje"] = s[[f"pos_{k}" for k in INDICADORES_SUC]].mean(axis=1)
    if df_prev is not None and not df_prev.empty:
        p = por(df_prev, "Sucursal", orden=None)[["Sucursal", "ventas"]].rename(
            columns={"ventas": "ventas_prev"})
        s = s.merge(p, on="Sucursal", how="left")
        s["crec_ventas"] = (s.ventas - s.ventas_prev) / s.ventas_prev * 100
    return s.sort_values(["puntaje", "utilidad"], ascending=[True, False]).reset_index(drop=True)

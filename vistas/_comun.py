from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from sfcp import kpis, storage, ui
from sfcp.repo import Datos


@dataclass
class Contexto:
    datos: Datos
    f: dict
    df: pd.DataFrame            # ventas filtradas (período + filtros)
    prev: pd.DataFrame | None   # período anterior equivalente (mismos filtros)
    periodo_prev: kpis.Periodo | None
    fecha_corte: pd.Timestamp   # última fecha de la base completa


def contexto() -> Contexto:
    datos: Datos = st.session_state["_datos"]
    f = st.session_state["_filtros"]
    df = ui.aplicar(datos.modelo, f)
    sin_fecha = ui.aplicar(datos.modelo, f, con_fecha=False)
    pp = kpis.periodo_anterior(f["inicio"], f["fin"], datos.modelo["Fecha"].min())
    prev = None
    if pp is not None:
        prev = sin_fecha[(sin_fecha.Fecha >= pp.inicio) & (sin_fecha.Fecha <= pp.fin)]
    return Contexto(datos, f, df, prev, pp, datos.modelo["Fecha"].max())


def cabecera(titulo: str, ctx: Contexto | None = None) -> None:
    ui.encabezado(storage.leer_equipo())
    st.markdown(f"## {titulo}")
    if ctx is not None:
        ui.barra_periodo(ctx.f, ctx.df)


def descarga(df: pd.DataFrame, nombre: str, etiqueta="⬇️ Descargar datos (CSV)") -> None:
    st.download_button(etiqueta, df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name=nombre, mime="text/csv")

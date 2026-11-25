"""Componentes visuales compartidos: estilos, encabezado, tarjetas KPI, gráficos y filtros."""
from __future__ import annotations

import html
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import kpis
from .config import APP_SUBTITLE, APP_TITLE, is_cloud

AZUL = "#0B2545"
AZUL2 = "#13315C"
AZUL3 = "#1F5F99"
AZUL4 = "#4A90C2"
AZUL5 = "#8DA9C4"
GRIS = "#6C757D"
GRIS_CLARO = "#E9EDF2"
VERDE = "#1B7F4C"
ROJO = "#B3261E"
PALETA = [AZUL, AZUL4, "#8C6D1F", "#5E8C6A", "#9C4F5E", AZUL5, GRIS, "#C08A3E"]

CSS = f"""
<style>
.stApp {{ background: #F5F7FA; }}
[data-testid="stSidebar"] {{ background: {AZUL}; }}
[data-testid="stSidebar"] * {{ color: #F1F4F8; }}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{ background: {AZUL4}; }}
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] div {{ color: #0B2545 !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] > div, [data-testid="stSidebar"] [data-baseweb="input"] > div {{ background: #FFFFFF; }}
[data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: #FFFFFF !important; }}
[data-testid="stSidebar"] button {{ background: {AZUL4}; border: 0; }}
[data-testid="stSidebar"] button p {{ color: #FFFFFF !important; }}
[data-testid="stSidebarNav"] a span {{ color: #F1F4F8 !important; }}
.sf-header {{ background: linear-gradient(90deg, {AZUL} 0%, {AZUL2} 70%, {AZUL3} 100%);
  color: white; padding: 18px 26px; border-radius: 12px; margin-bottom: 14px; }}
.sf-header h1 {{ color: white; font-size: 1.65rem; letter-spacing: .06em; margin: 0; padding: 0; font-weight: 800; }}
.sf-header p {{ color: #D6E2F0; margin: 2px 0 0 0; font-size: .98rem; }}
.sf-header .sf-meta {{ color: #B8C9DD; font-size: .8rem; margin-top: 6px; }}
.sf-card {{ background: white; border-radius: 12px; padding: 14px 16px; border: 1px solid #DDE3EA;
  border-top: 4px solid {AZUL3}; box-shadow: 0 1px 3px rgba(11,37,69,.06); height: 100%; }}
.sf-card .t {{ color: {GRIS}; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 600; }}
.sf-card .v {{ color: {AZUL}; font-size: 1.55rem; font-weight: 800; margin-top: 2px; white-space: nowrap; }}
.sf-card .d {{ font-size: .8rem; margin-top: 2px; }}
.sf-card .h {{ color: #8A94A0; font-size: .72rem; margin-top: 6px; line-height: 1.25; }}
.up {{ color: {VERDE}; }} .down {{ color: {ROJO}; }} .flat {{ color: {GRIS}; }}
.sf-section {{ color: {AZUL}; font-weight: 700; font-size: 1.05rem; margin: 10px 0 2px 0;
  border-left: 4px solid {AZUL3}; padding-left: 8px; }}
.sf-note {{ background: #EEF3F9; border-left: 4px solid {AZUL4}; padding: 10px 14px; border-radius: 6px;
  color: #23344D; font-size: .9rem; margin: 6px 0 10px 0; }}
.sf-warn {{ background: #FFF6E5; border-left: 4px solid #C08A3E; padding: 10px 14px; border-radius: 6px;
  color: #4D3A12; font-size: .9rem; margin: 6px 0 10px 0; }}
.sf-badge {{ display:inline-block; background:{GRIS_CLARO}; color:{AZUL}; border-radius: 999px;
  padding: 2px 10px; font-size: .78rem; margin: 0 6px 4px 0; }}
div[data-testid="stPlotlyChart"] {{ background: white; border-radius: 12px; border: 1px solid #DDE3EA; padding: 4px; }}
.block-container {{ padding-top: 1.4rem; max-width: 1500px; }}
</style>
"""


def estilos() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado(equipo: dict | None = None) -> None:
    meta = ""
    if equipo and (equipo.get("numero_equipo") or equipo.get("integrantes")):
        integ = ", ".join(equipo.get("integrantes") or [])
        partes = []
        if equipo.get("numero_equipo"):
            partes.append(f"Equipo {html.escape(str(equipo['numero_equipo']))}")
        if integ:
            partes.append(html.escape(integ))
        meta = f'<div class="sf-meta">{" · ".join(partes)}</div>'
    st.markdown(f'<div class="sf-header"><h1>🍕 {APP_TITLE}</h1><p>{APP_SUBTITLE}</p>{meta}</div>',
                unsafe_allow_html=True)


def seccion(t: str) -> None:
    st.markdown(f'<div class="sf-section">{html.escape(t)}</div>', unsafe_allow_html=True)


def nota(t: str, tipo: str = "note") -> None:
    st.markdown(f'<div class="sf-{tipo}">{t}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------- formatos
def usd(x, dec=0) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"${x:,.{dec}f}"


def num(x, dec=0) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{dec}f}"


def pct(x, dec=1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{dec}f}%"


def tarjeta(titulo: str, valor: str, delta: float | None = None, delta_txt: str | None = None,
            ayuda: str = "", invertir: bool = False, unidad_delta: str = "%") -> str:
    d = ""
    if delta is not None and not pd.isna(delta):
        bueno = delta >= 0 if not invertir else delta <= 0
        cls = "flat" if abs(delta) < 0.05 else ("up" if bueno else "down")
        flecha = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
        d = f'<div class="d {cls}">{flecha} {delta:+,.1f}{unidad_delta} {html.escape(delta_txt or "")}</div>'
    elif delta_txt:
        d = f'<div class="d flat">{html.escape(delta_txt)}</div>'
    h = f'<div class="h">{html.escape(ayuda)}</div>' if ayuda else ""
    return (f'<div class="sf-card" title="{html.escape(ayuda)}"><div class="t">{html.escape(titulo)}</div>'
            f'<div class="v">{valor}</div>{d}{h}</div>')


def fila_tarjetas(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for c, h in zip(cols, cards):
        c.markdown(h, unsafe_allow_html=True)


# ----------------------------------------------------------------- gráficos
def _base(fig: go.Figure, titulo: str = "", alto: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font=dict(size=15, color=AZUL), x=0.01) if titulo else None,
        height=alto, margin=dict(l=10, r=16, t=48 if titulo else 16, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#33404F"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
        hoverlabel=dict(bgcolor="white"), separators=".,",
    )
    fig.update_xaxes(showgrid=False, linecolor="#CBD3DC", title=None)
    fig.update_yaxes(gridcolor="#EDF0F4", zeroline=False, title=None)
    return fig


def barras(df: pd.DataFrame, x: str, y: str, titulo: str, horizontal=True, formato="usd",
           alto=360, color=AZUL3, resaltar: dict | None = None, texto=True) -> go.Figure:
    d = df.copy()
    fmt = {"usd": lambda v: usd(v), "pct": lambda v: pct(v), "num": lambda v: num(v),
           "usd2": lambda v: usd(v, 2), "dec": lambda v: num(v, 2),
           "min": lambda v: f"{num(v, 1)} min"}[formato]
    colores = [color] * len(d)
    if resaltar:
        for i, k in enumerate(d[x]):
            if k in resaltar:
                colores[i] = resaltar[k]
    textos = [fmt(v) for v in d[y]] if texto else None
    if horizontal:
        d = d.iloc[::-1]
        colores = colores[::-1]
        textos = textos[::-1] if textos else None
        fig = go.Figure(go.Bar(x=d[y], y=d[x].astype(str), orientation="h", marker_color=colores,
                               text=textos, textposition="auto", hovertemplate="%{y}: %{text}<extra></extra>"))
    else:
        fig = go.Figure(go.Bar(x=d[x].astype(str), y=d[y], marker_color=colores, text=textos,
                               textposition="auto", hovertemplate="%{x}: %{text}<extra></extra>"))
    fig.update_traces(cliponaxis=False, textfont_size=11)
    return _base(fig, titulo, alto)


def linea_mensual(m: pd.DataFrame, cols: dict, titulo: str, alto=360, formato="usd") -> go.Figure:
    fig = go.Figure()
    colores = [AZUL, AZUL4, "#8C6D1F", GRIS]
    for i, (c, nombre) in enumerate(cols.items()):
        fig.add_trace(go.Scatter(x=m["Periodo"], y=m[c], name=nombre, mode="lines+markers",
                                 line=dict(color=colores[i % 4], width=2.5), marker=dict(size=5),
                                 hovertemplate="%{x|%b %Y}: " + ("$%{y:,.0f}" if formato == "usd" else "%{y:,.1f}") + "<extra>" + nombre + "</extra>"))
    _ticks_es(fig, m["Periodo"])
    if formato == "usd":
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return _base(fig, titulo, alto)


def _ticks_es(fig: go.Figure, periodos: pd.Series) -> None:
    p = pd.Series(sorted(pd.to_datetime(periodos).unique()))
    if p.empty:
        return
    paso = 1 if len(p) <= 12 else (2 if len(p) <= 24 else 3)
    vals = p.iloc[::paso]
    fig.update_xaxes(tickvals=vals, ticktext=[f"{kpis.MESES[d.month - 1]}<br>{d.year}" for d in vals])


def comparacion_anual(m: pd.DataFrame, col: str, titulo: str, alto=360, formato="usd") -> go.Figure:
    fig = go.Figure()
    anios = sorted(m["Año"].unique())
    colores = {a: c for a, c in zip(anios, [AZUL5, AZUL3, AZUL, "#8C6D1F", GRIS][-len(anios):] if len(anios) <= 5 else PALETA)}
    for a in anios:
        s = m[m["Año"] == a]
        fig.add_trace(go.Scatter(x=[kpis.MESES[i - 1] for i in s["Mes"]], y=s[col], name=str(a),
                                 mode="lines+markers", line=dict(color=colores[a], width=2.5),
                                 hovertemplate="%{x}: " + ("$%{y:,.0f}" if formato == "usd" else "%{y:,.1f}") + f"<extra>{a}</extra>"))
    fig.update_xaxes(categoryorder="array", categoryarray=kpis.MESES)
    if formato == "usd":
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return _base(fig, titulo, alto)


def dona(df: pd.DataFrame, nombres: str, valores: str, titulo: str, alto=340) -> go.Figure:
    fig = go.Figure(go.Pie(labels=df[nombres], values=df[valores], hole=.55, sort=False,
                           marker=dict(colors=PALETA, line=dict(color="white", width=2)),
                           texttemplate="%{percent:.1%}", textposition="inside", insidetextfont=dict(color="white"),
                           hovertemplate="%{label}: $%{value:,.0f} (%{percent:.1%})<extra></extra>"))
    fig = _base(fig, titulo, alto)
    fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.0, xanchor="left", y=0.5, yanchor="middle"))
    return fig


def tabla(df: pd.DataFrame, formatos: dict, alto: int | None = None, **kw) -> None:
    cfg = {}
    for c, f in formatos.items():
        if f == "usd":
            cfg[c] = st.column_config.NumberColumn(c, format="$%,.0f")
        elif f == "usd2":
            cfg[c] = st.column_config.NumberColumn(c, format="$%,.2f")
        elif f == "pct":
            cfg[c] = st.column_config.NumberColumn(c, format="%.1f%%")
        elif f == "num":
            cfg[c] = st.column_config.NumberColumn(c, format="%,d")
        elif f == "dec":
            cfg[c] = st.column_config.NumberColumn(c, format="%.2f")
        elif f == "fecha":
            cfg[c] = st.column_config.DateColumn(c, format="DD/MM/YYYY")
    st.dataframe(df, column_config=cfg, hide_index=True, width="stretch",
                 height=alto if alto else "auto", **kw)


def renombrar(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"ventas": "Ventas", "utilidad": "Utilidad bruta", "margen": "Margen %",
                              "transacciones": "Transacciones", "ticket": "Ticket promedio",
                              "clientes": "Clientes", "unidades": "Unidades",
                              "participacion": "Participación %", "costo": "Costo total"})


FMT_STD = {"Ventas": "usd", "Utilidad bruta": "usd", "Margen %": "pct", "Transacciones": "num",
           "Ticket promedio": "usd2", "Clientes": "num", "Unidades": "num", "Participación %": "pct",
           "Costo total": "usd"}


# ----------------------------------------------------------------- filtros globales
FILTROS = ["f_preset", "f_rango", "f_ciudad", "f_sucursal", "f_segmento", "f_producto"]


def limpiar_filtros() -> None:
    st.session_state["f_preset"] = "Todo el período"
    for k in ["f_ciudad", "f_sucursal", "f_segmento", "f_producto"]:
        st.session_state[k] = []
    st.session_state.pop("f_rango", None)


def filtros_sidebar(modelo: pd.DataFrame, productos: pd.DataFrame) -> dict:
    """Dibuja los filtros globales en la barra lateral y devuelve la selección."""
    sb = st.sidebar
    sb.markdown("### 🔎 Filtros globales")
    fmin, fmax = modelo["Fecha"].min().date(), modelo["Fecha"].max().date()
    anios = sorted(modelo["Año"].dropna().unique().astype(int))
    opciones = ["Todo el período"] + [f"Año {a}" for a in anios] + ["Personalizado"]
    if st.session_state.get("f_preset") not in opciones:
        st.session_state["f_preset"] = "Todo el período"
    preset = sb.selectbox("Fecha", opciones, key="f_preset")
    if preset == "Todo el período":
        ini, fin = fmin, fmax
    elif preset.startswith("Año"):
        a = int(preset.split()[1])
        ini, fin = date(a, 1, 1), date(a, 12, 31)
    else:
        val = st.session_state.get("f_rango", (fmin, fmax))
        if not isinstance(val, (tuple, list)) or len(val) != 2 or val[0] < fmin or val[1] > fmax:
            st.session_state["f_rango"] = (fmin, fmax)
        rango = sb.date_input("Rango de fechas", key="f_rango", min_value=fmin, max_value=fmax,
                              format="DD/MM/YYYY")
        if isinstance(rango, (tuple, list)) and len(rango) == 2:
            ini, fin = rango
        else:
            ini = rango[0] if isinstance(rango, (tuple, list)) and rango else fmin
            fin = ini

    ciudades = sorted(modelo["Ciudad"].dropna().unique())
    _sanear("f_ciudad", ciudades)
    sel_ciudad = sb.multiselect("Ciudad", ciudades, key="f_ciudad", placeholder="Todas")
    base_suc = modelo[modelo["Ciudad"].isin(sel_ciudad)] if sel_ciudad else modelo
    sucursales = sorted(base_suc["Sucursal"].dropna().unique())
    _sanear("f_sucursal", sucursales)
    sel_suc = sb.multiselect("Sucursal", sucursales, key="f_sucursal", placeholder="Todas")
    segmentos = sorted(modelo["Segmento"].dropna().unique())
    _sanear("f_segmento", segmentos)
    sel_seg = sb.multiselect("Segmento de cliente", segmentos, key="f_segmento", placeholder="Todos")
    etiquetas = productos.sort_values("ProductoID")["Etiqueta"].tolist()
    _sanear("f_producto", etiquetas)
    sel_prod = sb.multiselect("Producto", etiquetas, key="f_producto", placeholder="Todos")
    sb.button("🧹 Limpiar filtros", on_click=limpiar_filtros, width="stretch")
    return {"inicio": pd.Timestamp(ini), "fin": pd.Timestamp(fin), "preset": preset,
            "ciudad": sel_ciudad, "sucursal": sel_suc, "segmento": sel_seg,
            "producto": [e.split(" · ")[0] for e in sel_prod], "producto_etq": sel_prod}


def _sanear(key: str, validas: list) -> None:
    if key in st.session_state:
        st.session_state[key] = [x for x in st.session_state[key] if x in validas]


def aplicar(modelo: pd.DataFrame, f: dict, con_fecha: bool = True) -> pd.DataFrame:
    m = pd.Series(True, index=modelo.index)
    if con_fecha:
        m &= (modelo["Fecha"] >= f["inicio"]) & (modelo["Fecha"] <= f["fin"] + pd.Timedelta(hours=23, minutes=59))
    if f["ciudad"]:
        m &= modelo["Ciudad"].isin(f["ciudad"])
    if f["sucursal"]:
        m &= modelo["Sucursal"].isin(f["sucursal"])
    if f["segmento"]:
        m &= modelo["Segmento"].isin(f["segmento"])
    if f["producto"]:
        m &= modelo["ProductoID"].isin(f["producto"])
    return modelo[m]


def describir_filtros(f: dict, df: pd.DataFrame) -> str:
    partes = [f"<b>Período:</b> {f['inicio']:%d/%m/%Y} – {f['fin']:%d/%m/%Y}"]
    if len(df):
        partes[0] += f" <span style='color:#6C757D'>(datos: {df.Fecha.min():%d/%m/%Y} – {df.Fecha.max():%d/%m/%Y})</span>"
    for k, n in [("ciudad", "Ciudad"), ("sucursal", "Sucursal"), ("segmento", "Segmento"),
                 ("producto_etq", "Producto")]:
        if f[k]:
            txt = ", ".join(f[k][:4]) + (f" y {len(f[k]) - 4} más" if len(f[k]) > 4 else "")
            partes.append(f"<b>{n}:</b> {html.escape(txt)}")
    return " &nbsp;|&nbsp; ".join(partes)


def barra_periodo(f: dict, df: pd.DataFrame) -> None:
    st.markdown(f"<div class='sf-note'>📅 {describir_filtros(f, df)}</div>", unsafe_allow_html=True)


def sin_datos(df: pd.DataFrame) -> bool:
    if df.empty:
        st.warning("No hay ventas que cumplan los filtros seleccionados. Ajuste o limpie los filtros.")
        return True
    return False


def aviso_nube() -> None:
    if is_cloud():
        nota("☁️ Versión web: los archivos que cargue aquí se aplican de inmediato a todos los indicadores, "
             "pero se conservan mientras el servidor esté activo. Para que una base quede de forma permanente, "
             "súbala con el mismo nombre a la carpeta <b>datos_iniciales</b> del repositorio de GitHub.", "warn")


_ = (np, px)
__all__ = ['go']

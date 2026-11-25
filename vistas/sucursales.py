from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from sfcp import kpis, ui
from vistas._comun import cabecera, contexto, descarga


def render() -> None:
    ctx = contexto()
    cabecera("🏪 Análisis de sucursales", ctx)
    df = ctx.df
    if ui.sin_datos(df):
        return
    r = kpis.ranking_sucursales(df, ctx.prev)
    if len(r) < 2:
        st.info("Seleccione al menos dos sucursales para compararlas.")
    mejor, peor = r.iloc[0], r.iloc[-1]
    prom = kpis.resumen(df)

    ui.nota("La evaluación es <b>multicriterio</b>: cada sucursal recibe una posición (1 = mejor) en seis "
            "indicadores —ventas, utilidad bruta, margen bruto, transacciones, ticket promedio y unidades— y el "
            "puntaje es el promedio de esas posiciones. Un puntaje menor indica mejor desempeño integral.")
    c1, c2 = st.columns(2)

    def explica(s, tipo):
        fuertes = [kpis.INDICADORES_SUC[k] for k in kpis.INDICADORES_SUC if s[f"pos_{k}"] <= 2]
        debiles = [kpis.INDICADORES_SUC[k] for k in kpis.INDICADORES_SUC if s[f"pos_{k}"] >= len(r) - 1]
        txt = (f"Ventas {ui.usd(s.ventas)} · Utilidad {ui.usd(s.utilidad)} · Margen {ui.pct(s.margen)} "
               f"(global {ui.pct(prom['margen'])}) · Ticket {ui.usd(s.ticket, 2)} · {ui.num(s.transacciones)} transacciones")
        if "crec_ventas" in s and s.crec_ventas == s.crec_ventas:
            txt += f" · Variación de ventas vs período anterior: {s.crec_ventas:+.1f}%"
        det = (f"Entre las 2 mejores en: {', '.join(fuertes)}." if tipo == "m" and fuertes else
               f"Entre las 2 últimas en: {', '.join(debiles)}." if tipo == "p" and debiles else "")
        return txt, det

    t, d = explica(mejor, "m")
    c1.markdown(ui.tarjeta("🏆 Mejor desempeño integral", mejor.Sucursal,
                           delta_txt=f"Puntaje {mejor.puntaje:.2f} · {mejor.Ciudad}", ayuda=t + " " + d),
                unsafe_allow_html=True)
    t, d = explica(peor, "p")
    c2.markdown(ui.tarjeta("⚠️ Menor desempeño integral", peor.Sucursal,
                           delta_txt=f"Puntaje {peor.puntaje:.2f} · {peor.Ciudad}", ayuda=t + " " + d),
                unsafe_allow_html=True)

    ui.seccion("Tabla comparativa")
    cols = ["Sucursal", "Ciudad", "ventas", "utilidad", "margen", "transacciones", "ticket", "unidades",
            "participacion", "puntaje"] + (["crec_ventas"] if "crec_ventas" in r else [])
    t = ui.renombrar(r[cols]).rename(columns={"puntaje": "Puntaje (menor = mejor)",
                                              "crec_ventas": "Var. ventas vs período anterior %"})
    ui.tabla(t, {**ui.FMT_STD, "Puntaje (menor = mejor)": "dec", "Var. ventas vs período anterior %": "pct"})
    descarga(r, "ranking_sucursales.csv")

    c1, c2 = st.columns([3, 2])
    pos = r.set_index("Sucursal")[[f"pos_{k}" for k in kpis.INDICADORES_SUC]]
    fig = go.Figure(go.Heatmap(
        z=pos.values, x=list(kpis.INDICADORES_SUC.values()), y=pos.index, text=pos.values.astype(int),
        texttemplate="%{text}", colorscale=[[0, ui.AZUL], [0.5, "#C9D6E5"], [1, "#F2D7D5"]],
        showscale=False, hovertemplate="%{y} · %{x}: posición %{z}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    c1.plotly_chart(ui._base(fig, "Posición de cada sucursal por indicador (1 = mejor)", 380), width="stretch")
    c2.plotly_chart(ui.barras(r, "Sucursal", "puntaje", "Puntaje integral (menor = mejor)",
                              alto=380, color=ui.AZUL5, formato="dec",
                              resaltar={mejor.Sucursal: ui.VERDE, peor.Sucursal: ui.ROJO}), width="stretch")

    met = st.radio("Comparar sucursales por", list(kpis.INDICADORES_SUC.values()), horizontal=True, key="suc_met")
    k = [x for x, v in kpis.INDICADORES_SUC.items() if v == met][0]
    fmt = {"ventas": "usd", "utilidad": "usd", "margen": "pct", "transacciones": "num", "ticket": "usd2",
           "unidades": "num"}[k]
    c1, c2 = st.columns(2)
    c1.plotly_chart(ui.barras(r.sort_values(k, ascending=False), "Sucursal", k, f"{met} por sucursal",
                              formato=fmt, alto=360), width="stretch")
    mm = kpis.por(df, ["Sucursal", "Periodo"], orden=None).sort_values("Periodo")
    fig = go.Figure()
    ui._ticks_es(fig, mm.Periodo)
    for i, s in enumerate(r.Sucursal):
        x = mm[mm.Sucursal == s]
        fig.add_scatter(x=x.Periodo, y=x[k], name=s, mode="lines",
                        line=dict(color=ui.PALETA[i % len(ui.PALETA)], width=2))
    fig = ui._base(fig, f"{met} mensual por sucursal", 420)
    fig.update_layout(legend=dict(orientation="h", y=-0.18, yanchor="top", x=0, xanchor="left"))
    c2.plotly_chart(fig, width="stretch")
    if "TiempoEntregaMin" in df:
        dl = df[(df.Canal == "Delivery") & (df.TiempoEntregaMin > 0)]
        if len(dl):
            ui.seccion("Indicador operativo complementario: tiempo de entrega a domicilio")
            te = dl.groupby("Sucursal").TiempoEntregaMin.mean().reset_index().sort_values("TiempoEntregaMin", ascending=False)
            prom_te = dl.TiempoEntregaMin.mean()
            st.plotly_chart(ui.barras(te, "Sucursal", "TiempoEntregaMin",
                                      f"Tiempo medio de entrega (Delivery) · promedio {prom_te:.1f} min",
                                      formato="min", alto=330, color=ui.AZUL5,
                                      resaltar={k: ui.ROJO for k, v in zip(te.Sucursal, te.TiempoEntregaMin) if v > prom_te * 1.2}),
                            width="stretch")
            st.caption("No forma parte del puntaje integral; se muestra como contexto operativo. Solo aplica al canal Delivery.")

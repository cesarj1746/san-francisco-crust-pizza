from __future__ import annotations

import streamlit as st

from sfcp import kpis, ui
from vistas._comun import cabecera, contexto, descarga

METRICAS = {"Ventas": ("ventas", "usd"), "Utilidad bruta": ("utilidad", "usd"),
            "Transacciones": ("transacciones", "num"), "Unidades": ("unidades", "num"),
            "Margen bruto %": ("margen", "pct"), "Ticket promedio": ("ticket", "usd2")}


def render() -> None:
    ctx = contexto()
    cabecera("📈 Análisis de ventas", ctx)
    df = ctx.df
    if ui.sin_datos(df):
        return
    a = kpis.resumen(df)
    ui.fila_tarjetas([
        ui.tarjeta("Ventas netas", ui.usd(a["ventas"])),
        ui.tarjeta("Utilidad bruta", ui.usd(a["utilidad"])),
        ui.tarjeta("Unidades vendidas", ui.num(a["unidades"])),
        ui.tarjeta("Transacciones", ui.num(a["transacciones"])),
        ui.tarjeta("Descuentos otorgados", ui.usd(a["descuento"])),
    ])

    m = kpis.mensual(df)
    t1, t2, t3, t4 = st.tabs(["Evolución mensual", "Comparación anual", "Utilidad bruta", "Descuentos y entrega"])
    with t1:
        st.plotly_chart(ui.linea_mensual(m, {"ventas": "Ventas"}, "Ventas netas por mes", alto=380),
                        width="stretch")
        st.plotly_chart(ui.barras(m.assign(Mes_=m.Periodo.dt.strftime("%b %Y")), "Mes_", "unidades",
                                  "Cantidades vendidas por mes (unidades)", horizontal=False,
                                  formato="num", alto=320, texto=False), width="stretch")
    with t2:
        st.plotly_chart(ui.comparacion_anual(m, "ventas", "Ventas mensuales por año"), width="stretch")
        anual = kpis.por(df, "Año", orden=None).sort_values("Año")
        anual["Variación ventas %"] = anual.ventas.pct_change() * 100
        anual["Año"] = anual["Año"].astype(int).astype(str)
        ui.tabla(ui.renombrar(anual[["Año", "ventas", "utilidad", "margen", "transacciones", "ticket",
                                     "clientes", "unidades", "Variación ventas %"]]),
                 {**ui.FMT_STD, "Variación ventas %": "pct"})
        ui.nota("La variación anual solo es comparable entre años completos. Revise el rango de "
                "fechas de cada año antes de concluir.")
    with t3:
        st.plotly_chart(ui.linea_mensual(m, {"utilidad": "Utilidad bruta"}, "Utilidad bruta por mes"),
                        width="stretch")
        st.plotly_chart(ui.linea_mensual(m, {"margen": "Margen bruto %"}, "Margen bruto mensual (%)",
                                         formato="pct", alto=300), width="stretch")

    with t4:
        c1, c2 = st.columns(2)
        g = kpis.por(df, "DescuentoPct", orden=None).sort_values("DescuentoPct")
        g["Nivel"] = g.DescuentoPct.astype(int).astype(str) + "%"
        c1.plotly_chart(ui.barras(g, "Nivel", "margen", "Margen bruto según nivel de descuento", horizontal=False,
                                  formato="pct", alto=320), width="stretch")
        dc = df.groupby(["Ciudad", "Periodo"]).ConDescuento.mean().mul(100).reset_index()
        fig = ui.go.Figure()
        for i, cdd in enumerate(sorted(dc.Ciudad.unique())):
            x = dc[dc.Ciudad == cdd]
            fig.add_scatter(x=x.Periodo, y=x.ConDescuento, name=cdd, mode="lines",
                            line=dict(color=ui.PALETA[i % len(ui.PALETA)], width=2.5))
        ui._ticks_es(fig, dc.Periodo)
        fig.update_yaxes(ticksuffix="%")
        c2.plotly_chart(ui._base(fig, "% de transacciones con descuento por ciudad", 320), width="stretch")
        if "TiempoEntregaMin" in df:
            dl = df[(df.Canal == "Delivery") & (df.TiempoEntregaMin > 0)]
            if len(dl):
                te = dl.groupby(["Ciudad", "Periodo"]).TiempoEntregaMin.mean().reset_index()
                fig = ui.go.Figure()
                for i, cdd in enumerate(sorted(te.Ciudad.unique())):
                    x = te[te.Ciudad == cdd]
                    fig.add_scatter(x=x.Periodo, y=x.TiempoEntregaMin, name=cdd, mode="lines",
                                    line=dict(color=ui.PALETA[i % len(ui.PALETA)], width=2.5))
                ui._ticks_es(fig, te.Periodo)
                fig.update_yaxes(ticksuffix=" min")
                st.plotly_chart(ui._base(fig, "Tiempo medio de entrega a domicilio por ciudad (solo Delivery)", 320),
                                width="stretch")

    st.write("")
    ui.seccion("Distribución por dimensión")
    met = st.radio("Métrica", list(METRICAS), horizontal=True, key="ventas_metrica")
    col, fmt = METRICAS[met]
    c1, c2 = st.columns(2)
    for c, (dim, tit) in zip([c1, c2, c1, c2, c1, c2],
                             [("Ciudad", "por ciudad"), ("Sucursal", "por sucursal"),
                              ("Segmento", "por segmento"), ("Canal", "por canal"),
                              ("FormaPago", "por forma de pago"), ("Categoria", "por categoría")]):
        g = kpis.por(df, dim, orden=col)
        c.plotly_chart(ui.barras(g, dim, col, f"{met} {tit}", formato=fmt, alto=300), width="stretch")

    with st.expander("📋 Ver tabla detallada por sucursal y mes"):
        t = kpis.por(df, ["Sucursal", "Periodo"], orden=None).sort_values(["Sucursal", "Periodo"])
        t["Periodo"] = t.Periodo.dt.strftime("%Y-%m")
        ui.tabla(ui.renombrar(t[["Sucursal", "Periodo", "ventas", "utilidad", "margen", "transacciones",
                                 "ticket", "unidades"]]), ui.FMT_STD, alto=380)
        descarga(t, "ventas_sucursal_mes.csv")

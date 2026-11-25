from __future__ import annotations

import streamlit as st

from sfcp import kpis, ui
from vistas._comun import cabecera, contexto


def render() -> None:
    ctx = contexto()
    cabecera("📊 Dashboard ejecutivo", ctx)
    df = ctx.df
    if ui.sin_datos(df):
        return
    a = kpis.resumen(df)
    p = kpis.resumen(ctx.prev) if ctx.prev is not None and len(ctx.prev) else None
    txt = "vs período anterior" if p else None

    def dv(k):
        return kpis.variacion(a[k], p[k]) if p else None

    D = kpis.DEFINICIONES
    ui.fila_tarjetas([
        ui.tarjeta("Ventas totales", ui.usd(a["ventas"]), dv("ventas"), txt, D["Ventas totales"]),
        ui.tarjeta("Utilidad bruta", ui.usd(a["utilidad"]), dv("utilidad"), txt, D["Utilidad bruta"]),
        ui.tarjeta("Margen bruto", ui.pct(a["margen"]), (a["margen"] - p["margen"]) if p else None,
                   txt, D["Margen bruto"], unidad_delta=" p.p."),
        ui.tarjeta("Ticket promedio", ui.usd(a["ticket"], 2), dv("ticket"), txt, D["Ticket promedio"]),
        ui.tarjeta("Clientes", ui.num(a["clientes"]), dv("clientes"), txt, D["Clientes"]),
        ui.tarjeta("Transacciones", ui.num(a["transacciones"]), dv("transacciones"), txt,
                   D["Transacciones"]),
    ])
    if p:
        st.caption(f"Variaciones calculadas frente al período anterior equivalente: {ctx.periodo_prev.texto()}, con los mismos filtros.")
    else:
        st.caption("ℹ️ Las variaciones aparecen cuando existe un período anterior equivalente "
                   "dentro de los datos (por ejemplo, al elegir «Año 2025» se compara con 2024).")

    st.write("")
    c1, c2 = st.columns([3, 2])
    m = kpis.mensual(df)
    c1.plotly_chart(ui.linea_mensual(m, {"ventas": "Ventas", "utilidad": "Utilidad bruta"},
                                     "Evolución mensual de ventas y utilidad"), width="stretch")
    ciu = kpis.por(df, "Ciudad")
    c2.plotly_chart(ui.barras(ciu, "Ciudad", "ventas", "Ventas por ciudad"), width="stretch")

    c1, c2 = st.columns([3, 2])
    suc = kpis.por(df, "Sucursal")
    c1.plotly_chart(ui.barras(suc, "Sucursal", "ventas", "Ventas por sucursal", alto=380),
                    width="stretch")
    seg = kpis.por(df, "Segmento")
    c2.plotly_chart(ui.dona(seg, "Segmento", "ventas", "Ventas por segmento de cliente", alto=380),
                    width="stretch")

    c1, c2 = st.columns([3, 2])
    pr = kpis.por(df, "ProductoNombre", orden="unidades").head(10)
    c1.plotly_chart(ui.barras(pr, "ProductoNombre", "unidades", "Top 10 productos más vendidos (unidades)",
                              formato="num", alto=400), width="stretch")
    with c2:
        ui.seccion("Principales indicadores de rentabilidad")
        sin_desc = df[~df.ConDescuento]
        con_desc = df[df.ConDescuento]
        filas = [
            ("Costo total de ventas", ui.usd(a["costo"])),
            ("Utilidad bruta por transacción", ui.usd(a["utilidad"] / a["transacciones"], 2)),
            ("Unidades vendidas", ui.num(a["unidades"])),
            ("Descuentos otorgados (USD)", ui.usd(a["descuento"])),
            ("Transacciones con descuento", ui.pct(df.ConDescuento.mean() * 100)),
            ("Margen sin descuento", ui.pct(kpis.resumen(sin_desc)["margen"]) if len(sin_desc) else "—"),
            ("Margen con descuento", ui.pct(kpis.resumen(con_desc)["margen"]) if len(con_desc) else "—"),
        ]
        cat = kpis.por(df, "Categoria", orden="margen")
        if len(cat):
            filas.append(("Categoría con mayor margen", f"{cat.iloc[0].Categoria} ({ui.pct(cat.iloc[0].margen)})"))
            filas.append(("Categoría con menor margen", f"{cat.iloc[-1].Categoria} ({ui.pct(cat.iloc[-1].margen)})"))
        html_rows = "".join(f"<tr><td style='padding:6px 4px;color:#33404F'>{k}</td>"
                            f"<td style='padding:6px 4px;text-align:right;font-weight:700;color:#0B2545'>{v}</td></tr>"
                            for k, v in filas)
        st.markdown(f"<div class='sf-card' style='border-top-color:#0B2545'><table style='width:100%;"
                    f"border-collapse:collapse;font-size:.9rem'>{html_rows}</table></div>",
                    unsafe_allow_html=True)

    with st.expander("📘 Definición de los indicadores"):
        for k, v in kpis.DEFINICIONES.items():
            st.markdown(f"**{k}:** {v}")
        st.markdown("**Variación:** comparación con el período anterior de igual duración y con los "
                    "mismos filtros. El margen se compara en puntos porcentuales (p.p.).")

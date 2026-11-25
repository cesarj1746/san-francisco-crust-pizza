from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from sfcp import kpis, ui
from vistas._comun import cabecera, contexto, descarga


def render() -> None:
    ctx = contexto()
    cabecera("🍕 Análisis de productos", ctx)
    df = ctx.df
    if ui.sin_datos(df):
        return
    pr = kpis.por(df, ["ProductoID", "ProductoNombre", "Categoria"])
    pr["precio_prom"] = pr.ventas / pr.unidades
    pr["costo_prom"] = pr.costo / pr.unidades
    pr["utilidad_unidad"] = pr.utilidad / pr.unidades

    def top(col):
        return pr.sort_values(col, ascending=False).iloc[0]

    u, v, ut, mg = top("unidades"), top("ventas"), top("utilidad"), top("margen")
    ui.fila_tarjetas([
        ui.tarjeta("Más vendido (unidades)", u.ProductoNombre, delta_txt=f"{ui.num(u.unidades)} unidades",
                   ayuda="Producto con más unidades vendidas."),
        ui.tarjeta("Mayor facturación", v.ProductoNombre, delta_txt=f"{ui.usd(v.ventas)} en ventas",
                   ayuda="Producto con mayor venta neta en dólares."),
        ui.tarjeta("Mayor utilidad bruta", ut.ProductoNombre, delta_txt=f"{ui.usd(ut.utilidad)} de utilidad",
                   ayuda="Producto que más utilidad bruta aporta en dólares."),
        ui.tarjeta("Mayor margen %", mg.ProductoNombre, delta_txt=f"{ui.pct(mg.margen)} de margen",
                   ayuda="Producto con mayor utilidad por cada dólar vendido."),
    ])
    nombres = {u.ProductoNombre, v.ProductoNombre, ut.ProductoNombre, mg.ProductoNombre}
    if len(nombres) > 1:
        ui.nota("💡 El producto más vendido no es necesariamente el más rentable: en el período "
                f"seleccionado hay <b>{len(nombres)} productos distintos</b> liderando volumen, "
                "facturación, utilidad y margen.")

    t1, t2, t3, t4 = st.tabs(["Rankings", "Bajo desempeño", "Rentabilidad por categoría",
                              "Costo vs. precio"])
    with t1:
        n = st.slider("Número de productos a mostrar", 5, len(pr), min(10, len(pr)), key="prod_n")
        c1, c2 = st.columns(2)
        c1.plotly_chart(ui.barras(pr.sort_values("unidades", ascending=False).head(n), "ProductoNombre",
                                  "unidades", "Más vendidos por unidades", formato="num", alto=60 + 28 * n),
                        width="stretch")
        c2.plotly_chart(ui.barras(pr.sort_values("ventas", ascending=False).head(n), "ProductoNombre",
                                  "ventas", "Mayores ventas (USD)", alto=60 + 28 * n), width="stretch")
        c1.plotly_chart(ui.barras(pr.sort_values("utilidad", ascending=False).head(n), "ProductoNombre",
                                  "utilidad", "Mayor utilidad bruta (USD)", alto=60 + 28 * n, color=ui.AZUL),
                        width="stretch")
        c2.plotly_chart(ui.barras(pr.sort_values("margen", ascending=False).head(n), "ProductoNombre",
                                  "margen", "Mayor margen bruto (%)", formato="pct", alto=60 + 28 * n,
                                  color=ui.AZUL4), width="stretch")
    with t2:
        prom_m = kpis.resumen(df)["margen"]
        st.markdown(f"Margen bruto global del período: **{ui.pct(prom_m)}**. Se listan los productos "
                    "con menor volumen y menor margen para revisión.")
        c1, c2 = st.columns(2)
        bajo_v = pr.sort_values("unidades").head(10)
        bajo_m = pr.sort_values("margen").head(10)
        c1.plotly_chart(ui.barras(bajo_v, "ProductoNombre", "unidades", "10 productos con menor volumen",
                                  formato="num", alto=360, color=ui.GRIS), width="stretch")
        c2.plotly_chart(ui.barras(bajo_m, "ProductoNombre", "margen", "10 productos con menor margen %",
                                  formato="pct", alto=360, color=ui.ROJO), width="stretch")
        ambos = set(bajo_v.ProductoID) & set(bajo_m.ProductoID)
        if ambos:
            ui.nota("⚠️ Aparecen en ambas listas (bajo volumen y bajo margen): <b>"
                    + ", ".join(pr[pr.ProductoID.isin(ambos)].ProductoNombre) + "</b>.", "warn")
        prod_m = ctx.datos.productos
        if "Activo" in prod_m:
            inact = prod_m[prod_m.Activo.astype(str).str.lower().isin(["no", "n", "false", "0"])]
            vend = pr[pr.ProductoID.isin(inact.ProductoID)]
            if len(vend):
                ui.nota("ℹ️ Productos marcados como <b>inactivos</b> en el maestro que registran ventas "
                        "en el período: " + ", ".join(f"{r.ProductoNombre} ({ui.num(r.unidades)} u.)"
                                                      for r in vend.itertuples()) + ".", "warn")
    with t3:
        cat = kpis.por(df, "Categoria")
        c1, c2 = st.columns(2)
        fig = go.Figure()
        fig.add_bar(x=cat.Categoria, y=cat.ventas, name="Ventas", marker_color=ui.AZUL5,
                    hovertemplate="%{x}: $%{y:,.0f}<extra>Ventas</extra>")
        fig.add_bar(x=cat.Categoria, y=cat.utilidad, name="Utilidad bruta", marker_color=ui.AZUL,
                    hovertemplate="%{x}: $%{y:,.0f}<extra>Utilidad</extra>")
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        c1.plotly_chart(ui._base(fig, "Ventas y utilidad por categoría"), width="stretch")
        c2.plotly_chart(ui.barras(cat.sort_values("margen", ascending=False), "Categoria", "margen",
                                  "Margen bruto por categoría (%)", formato="pct"), width="stretch")
        ui.tabla(ui.renombrar(cat[["Categoria", "ventas", "utilidad", "margen", "unidades", "transacciones",
                                   "participacion"]]), ui.FMT_STD)
    with t4:
        st.markdown("Precio y costo **promedio por unidad efectivamente registrados en las ventas** "
                    "(después de descuentos). El tamaño de la burbuja representa las unidades vendidas.")
        fig = go.Figure(go.Scatter(
            x=pr.costo_prom, y=pr.precio_prom, mode="markers", text=pr.ProductoNombre,
            marker=dict(size=pr.unidades / pr.unidades.max() * 28 + 6, color=pr.margen,
                        colorscale=[[0, ui.ROJO], [0.5, "#E8D9A8"], [1, ui.AZUL]], showscale=True,
                        colorbar=dict(title="Margen %"), line=dict(color="white", width=1)),
            hovertemplate="<b>%{text}</b><br>Costo: $%{x:.2f}<br>Precio: $%{y:.2f}<extra></extra>"))
        lim = max(pr.precio_prom.max(), pr.costo_prom.max()) * 1.05
        fig.add_shape(type="line", x0=0, y0=0, x1=lim / 2.5, y1=lim, line=dict(color=ui.GRIS, dash="dot"))
        fig.update_xaxes(title="Costo unitario promedio (USD)", tickprefix="$")
        fig.update_yaxes(title="Precio unitario promedio (USD)", tickprefix="$")
        st.plotly_chart(ui._base(fig, "Costo vs. precio de venta por producto", 480), width="stretch")
        st.caption("La línea punteada marca un margen de referencia del 60 % (precio = costo × 2,5).")
        pm = ctx.datos.productos
        if {"PrecioVentaUSD", "CostoUSD"} <= set(pm.columns):
            comp = pr.merge(pm[["ProductoID", "PrecioVentaUSD", "CostoUSD", "MargenPorcentaje"]],
                            on="ProductoID", how="left")
            comp["Dif. precio %"] = (comp.precio_prom / comp.PrecioVentaUSD - 1) * 100
            ui.seccion("Comparación con la lista de precios del maestro de productos")
            ui.nota("Los precios y costos registrados en la base de ventas <b>no coinciden</b> con los del "
                    "maestro de productos. Todos los indicadores se calculan con la base de ventas; el "
                    "maestro se muestra solo como referencia de catálogo.", "warn")
            t = comp[["ProductoNombre", "Categoria", "precio_prom", "PrecioVentaUSD", "Dif. precio %",
                      "costo_prom", "CostoUSD", "margen", "MargenPorcentaje"]].rename(columns={
                "ProductoNombre": "Producto", "Categoria": "Categoría",
                "precio_prom": "Precio en ventas", "PrecioVentaUSD": "Precio catálogo",
                "costo_prom": "Costo en ventas", "CostoUSD": "Costo catálogo",
                "margen": "Margen real %", "MargenPorcentaje": "Margen catálogo %"})
            ui.tabla(t, {"Precio en ventas": "usd2", "Precio catálogo": "usd2", "Dif. precio %": "pct",
                         "Costo en ventas": "usd2", "Costo catálogo": "usd2", "Margen real %": "pct",
                         "Margen catálogo %": "pct"}, alto=400)

    with st.expander("📋 Tabla completa de productos"):
        t = pr[["ProductoID", "ProductoNombre", "Categoria", "unidades", "ventas", "utilidad", "margen",
                "transacciones", "precio_prom", "costo_prom", "utilidad_unidad", "participacion"]]
        ui.tabla(ui.renombrar(t).rename(columns={"ProductoNombre": "Producto", "precio_prom": "Precio prom.",
                                                 "costo_prom": "Costo prom.", "utilidad_unidad": "Utilidad/unidad"}),
                 {**ui.FMT_STD, "Precio prom.": "usd2", "Costo prom.": "usd2", "Utilidad/unidad": "usd2"},
                 alto=420)
        descarga(t, "productos.csv")

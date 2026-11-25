from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sfcp import kpis, ui
from sfcp.data import rango_edad
from vistas._comun import cabecera, contexto, descarga


def render() -> None:
    ctx = contexto()
    cabecera("👥 Análisis de clientes", ctx)
    df = ctx.df
    if ui.sin_datos(df):
        return
    maestro = ctx.datos.clientes
    reg = maestro if not ctx.f["segmento"] else maestro[maestro.Segmento.isin(ctx.f["segmento"])]
    cl = kpis.clientes_desde_ventas(df, ctx.fecha_corte)
    dias_inact = st.session_state.get("cli_dias", 90)
    cl["Estado (ventas)"] = (cl.dias_sin_comprar > dias_inact).map({True: "Inactivo", False: "Activo"})

    a = kpis.resumen(df)
    ui.fila_tarjetas([
        ui.tarjeta("Clientes registrados", ui.num(len(reg)), ayuda="Total de clientes en el maestro (según filtro de segmento)."),
        ui.tarjeta("Clientes compradores", ui.num(a["clientes"]), delta_txt=f"{ui.pct(a['clientes'] / len(reg) * 100 if len(reg) else None)} de los registrados",
                   ayuda="Clientes distintos con al menos una compra en el período filtrado."),
        ui.tarjeta("Compras por cliente", ui.num(cl.compras.mean(), 1), ayuda="Promedio de transacciones por cliente comprador en el período."),
        ui.tarjeta("Gasto medio por cliente", ui.usd(cl.gasto.mean()), ayuda="Venta neta total ÷ clientes compradores."),
        ui.tarjeta("NPS (maestro)", ui.num(kpis.nps(cl.NPS), 1) if "NPS" in cl else "—",
                   ayuda="% promotores (9–10) − % detractores (0–6) de los clientes compradores, según la puntuación registrada en el maestro."),
    ])
    ui.nota("Métricas de compra (frecuencia, gasto, recencia) calculadas <b>desde la base de ventas</b>. "
            "Segmento, edad, ciudad de residencia, NPS y motivo de pérdida provienen del <b>maestro de clientes</b> (referencia).")

    t1, t2, t3, t4, t5 = st.tabs(["Segmentos", "Frecuencia y actividad", "Perfil (ciudad y edad)",
                                  "Mayor gasto y recuperación", "Calidad del maestro"])
    with t1:
        seg = kpis.por(df, "Segmento")
        nps_seg = cl.groupby("Segmento")["NPS"].apply(kpis.nps).rename("nps") if "NPS" in cl else None
        frec = cl.groupby("Segmento").agg(frecuencia=("frecuencia_mensual", "mean"),
                                          gasto_cliente=("gasto", "mean")).reset_index()
        regs = reg.groupby("Segmento").size().rename("registrados").reset_index()
        seg = seg.merge(frec, on="Segmento", how="left").merge(regs, on="Segmento", how="left")
        if nps_seg is not None:
            seg = seg.merge(nps_seg.reset_index(), on="Segmento", how="left")
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(ui.barras(seg, "Segmento", "clientes", "Clientes compradores por segmento",
                                  formato="num", alto=300), width="stretch")
        c2.plotly_chart(ui.barras(seg, "Segmento", "ventas", "Ventas por segmento", alto=300), width="stretch")
        c3.plotly_chart(ui.barras(seg.sort_values("ticket", ascending=False), "Segmento", "ticket",
                                  "Ticket promedio por segmento", formato="usd2", alto=300), width="stretch")
        if "nps" in seg:
            col = {s: (ui.VERDE if v >= 0 else ui.ROJO) for s, v in zip(seg.Segmento, seg.nps)}
            st.plotly_chart(ui.barras(seg.sort_values("nps", ascending=False), "Segmento", "nps",
                                      "NPS por segmento (maestro de clientes)", formato="num", alto=280,
                                      resaltar=col), width="stretch")
        t = seg[["Segmento", "registrados", "clientes", "ventas", "participacion", "utilidad", "margen",
                 "ticket", "frecuencia", "gasto_cliente"] + (["nps"] if "nps" in seg else [])]
        ui.tabla(ui.renombrar(t).rename(columns={"registrados": "Registrados", "Clientes": "Compradores",
                                                 "frecuencia": "Compras/mes por cliente",
                                                 "gasto_cliente": "Gasto por cliente", "nps": "NPS"}),
                 {**ui.FMT_STD, "Registrados": "num", "Compradores": "num", "Compras/mes por cliente": "dec",
                  "Gasto por cliente": "usd", "NPS": "dec"})
    with t2:
        c1, c2 = st.columns(2)
        fig = go.Figure(go.Histogram(x=cl.compras, nbinsx=25, marker_color=ui.AZUL3,
                                     hovertemplate="%{x} compras: %{y} clientes<extra></extra>"))
        fig.update_xaxes(title="Número de compras en el período")
        fig.update_yaxes(title="Clientes")
        c1.plotly_chart(ui._base(fig, "Distribución de la frecuencia de compra"), width="stretch")
        fig = go.Figure(go.Histogram(x=cl.dias_sin_comprar, nbinsx=30, marker_color=ui.AZUL5,
                                     hovertemplate="%{x} días: %{y} clientes<extra></extra>"))
        fig.update_xaxes(title=f"Días desde la última compra (al {ctx.fecha_corte:%d/%m/%Y})")
        c2.plotly_chart(ui._base(fig, "Recencia: días sin comprar"), width="stretch")
        st.slider("Días sin comprar para considerar a un cliente inactivo (regla de la aplicación)",
                  30, 180, 90, 15, key="cli_dias")
        act = cl["Estado (ventas)"].value_counts()
        c1, c2 = st.columns([1, 2])
        c1.markdown(ui.tarjeta("Activos según ventas", ui.num(act.get("Activo", 0)),
                               delta_txt=f"Inactivos: {ui.num(act.get('Inactivo', 0))}",
                               ayuda=f"Inactivo = sin compras en los últimos {dias_inact} días respecto a la última fecha de la base."),
                    unsafe_allow_html=True)
        if "ClienteActivo" in cl:
            ct = pd.crosstab(cl["ClienteActivo"].fillna("Sin dato").rename("Maestro: ClienteActivo"),
                             cl["Estado (ventas)"])
            c2.markdown("**Comparación con el indicador del maestro**")
            c2.dataframe(ct, width="stretch")
            no_m = cl[(cl.ClienteActivo == "No")]
            if len(no_m):
                ui.nota(f"De los {ui.num(len(no_m))} clientes marcados como inactivos en el maestro, "
                        f"{ui.num((no_m['Estado (ventas)'] == 'Activo').sum())} registran compras en los "
                        f"últimos {dias_inact} días según la base de ventas. El indicador del maestro no "
                        "coincide con la actividad real registrada.", "warn")
    with t3:
        c1, c2 = st.columns(2)
        if "CiudadCliente" in cl:
            g = cl.groupby("CiudadCliente").agg(clientes=("ClienteID", "nunique")).reset_index().sort_values("clientes", ascending=False)
            c1.plotly_chart(ui.barras(g, "CiudadCliente", "clientes", "Clientes por ciudad de residencia (maestro)",
                                      formato="num", alto=300), width="stretch")
        g2 = df.groupby("Ciudad").ClienteID.nunique().reset_index(name="clientes").sort_values("clientes", ascending=False)
        c2.plotly_chart(ui.barras(g2, "Ciudad", "clientes", "Clientes por ciudad de compra (ventas)",
                                  formato="num", alto=300), width="stretch")
        if "Edad" in cl:
            cl["Rango de edad"] = cl.Edad.apply(rango_edad)
            e = cl.groupby("Rango de edad").agg(clientes=("ClienteID", "size"), gasto=("gasto", "mean"),
                                                ventas=("gasto", "sum")).reset_index()
            c1, c2 = st.columns(2)
            c1.plotly_chart(ui.barras(e, "Rango de edad", "clientes", "Clientes compradores por edad",
                                      horizontal=False, formato="num", alto=300), width="stretch")
            c2.plotly_chart(ui.barras(e, "Rango de edad", "gasto", "Gasto promedio por cliente según edad",
                                      horizontal=False, alto=300), width="stretch")
    with t4:
        n = st.slider("Clientes a mostrar", 5, 50, 15, key="cli_top")
        top = cl.sort_values("gasto", ascending=False).head(n)
        cols = [c for c in ["ClienteID", "NombreCliente", "Segmento", "compras", "gasto", "utilidad",
                            "ticket", "ultima", "NPS"] if c in top]
        ui.seccion(f"Top {n} clientes por gasto acumulado en el período (base de ventas)")
        ui.tabla(top[cols].rename(columns={"NombreCliente": "Nombre", "compras": "Compras", "gasto": "Gasto",
                                           "utilidad": "Utilidad", "ticket": "Ticket", "ultima": "Última compra"}),
                 {"Gasto": "usd", "Utilidad": "usd", "Ticket": "usd2", "Compras": "num", "Última compra": "fecha"})
        ui.seccion("Oportunidades de recuperación")
        mitad = ctx.f["inicio"] + (min(ctx.f["fin"], ctx.fecha_corte) - ctx.f["inicio"]) / 2
        g1 = df[df.Fecha < mitad].groupby("ClienteID").VentaNeta.sum()
        g2 = df[df.Fecha >= mitad].groupby("ClienteID").VentaNeta.sum()
        cl["gasto_1a_mitad"] = cl.ClienteID.map(g1).fillna(0)
        cl["gasto_2a_mitad"] = cl.ClienteID.map(g2).fillna(0)
        cl["cambio_%"] = (cl.gasto_2a_mitad / cl.gasto_1a_mitad.replace(0, pd.NA) - 1) * 100
        caida = st.slider("Caída mínima del gasto entre la 1.ª y 2.ª mitad del período (%)", 10, 90, 50, 10,
                          key="cli_caida")
        rec = cl[(cl["Estado (ventas)"] == "Inactivo") | (cl["cambio_%"] <= -caida)].copy()
        rec["Criterio"] = rec.apply(lambda r: "Sin compras recientes" if r["Estado (ventas)"] == "Inactivo"
                                    else f"Gasto cayó {abs(r['cambio_%']):.0f}%", axis=1)
        st.markdown(f"**{ui.num(len(rec))} clientes** cumplen al menos un criterio: inactivo según la regla de "
                    f"{dias_inact} días, o caída de gasto ≥ {caida}% entre las dos mitades del período "
                    f"(corte: {mitad:%d/%m/%Y}).")
        cols = [c for c in ["ClienteID", "NombreCliente", "Segmento", "Criterio", "gasto_1a_mitad", "gasto_2a_mitad",
                            "cambio_%", "dias_sin_comprar", "ClienteActivo", "MotivoPerdida"] if c in rec]
        ui.tabla(rec.sort_values("gasto_1a_mitad", ascending=False)[cols].rename(columns={
            "NombreCliente": "Nombre", "gasto_1a_mitad": "Gasto 1.ª mitad", "gasto_2a_mitad": "Gasto 2.ª mitad",
            "cambio_%": "Cambio %", "dias_sin_comprar": "Días sin comprar", "ClienteActivo": "Activo (maestro)",
            "MotivoPerdida": "Motivo de pérdida (maestro)"}),
            {"Gasto 1.ª mitad": "usd", "Gasto 2.ª mitad": "usd", "Cambio %": "pct", "Días sin comprar": "num"},
            alto=360)
        st.caption("El motivo de pérdida se muestra tal como está registrado en el maestro; la aplicación no "
                   "infiere motivos. Un valor vacío significa que el maestro no registra motivo.")
        descarga(rec[cols], "clientes_recuperacion.csv")
    with t5:
        calidad_maestro(ctx, cl)


def calidad_maestro(ctx, cl) -> None:
    m = ctx.datos.clientes
    v = ctx.datos.ventas
    st.markdown("Comparación entre los campos resumen del **maestro de clientes** y lo que realmente "
                "registra la **base de ventas completa** (sin filtros).")
    full = kpis.clientes_desde_ventas(ctx.datos.modelo, ctx.fecha_corte)
    j = full.merge(m, on="ClienteID", how="left", suffixes=("", "_m"))
    filas = []
    if "TotalCompras" in j:
        filas.append(("TotalCompras (maestro) ≠ compras en ventas", int((j.TotalCompras != j.compras).sum())))
    if "GastoAcumuladoUSD" in j:
        filas.append(("GastoAcumuladoUSD difiere > 5% del gasto en ventas",
                      int(((j.GastoAcumuladoUSD - j.gasto).abs() > j.gasto * 0.05).sum())))
    if "UltimaCompra" in j:
        filas.append(("UltimaCompra (maestro) ≠ última compra en ventas",
                      int((j.UltimaCompra.dt.normalize() != j.ultima.dt.normalize()).sum())))
        filas.append((f"UltimaCompra posterior al fin de la base de ventas ({ctx.fecha_corte:%d/%m/%Y})",
                      int((m.UltimaCompra > ctx.fecha_corte).sum())))
    if "FechaRegistro" in j:
        filas.append(("Clientes con compras anteriores a su FechaRegistro",
                      int((j.primera < j.FechaRegistro).sum())))
    if "Ciudad" in m:
        mc = v.merge(m[["ClienteID", "Ciudad"]], on="ClienteID", suffixes=("", "_m"))
        filas.append(("Ventas realizadas en una ciudad distinta a la de residencia (%)",
                      round((mc.Ciudad != mc.Ciudad_m).mean() * 100, 1)))
    if "ClienteActivo" in j:
        filas.append(("Clientes 'No activos' en el maestro con compras en la base",
                      int((j.ClienteActivo == "No").sum())))
    filas.append(("Clientes del maestro sin ninguna compra", int((~m.ClienteID.isin(v.ClienteID)).sum())))
    st.dataframe(pd.DataFrame(filas, columns=["Verificación", "Resultado"]), hide_index=True, width="stretch")
    ui.nota("Por esta razón, la aplicación calcula frecuencia, gasto y recencia exclusivamente desde la base "
            "de ventas, y usa el maestro solo para atributos descriptivos. No se corrigen ni se inventan datos.",
            "warn")

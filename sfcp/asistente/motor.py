"""Motor local de análisis y recomendaciones comerciales (basado en reglas).

No es un modelo generativo de lenguaje. Identifica la intención de la pregunta
mediante palabras clave, calcula los indicadores con las mismas fórmulas del
dashboard (kpis.py) sobre los datos FILTRADOS y aplica reglas de negocio
explícitas. Cada respuesta separa hechos (cifras verificables), interpretación,
recomendaciones, criterio aplicado y limitaciones.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import kpis

NOMBRE = "Motor de análisis y recomendaciones comerciales basado en reglas"
DESCRIPCION = ("Funciona dentro de la aplicación, sin servicios externos ni modelos generativos: interpreta la pregunta por palabras clave, "
               "calcula indicadores reales con los filtros activos y aplica reglas de negocio documentadas.")


def _u(x, d=0):
    return "—" if x is None or pd.isna(x) else f"${x:,.{d}f}"


def _p(x, d=1):
    return "—" if x is None or pd.isna(x) else f"{x:,.{d}f}%"


def _n(x, d=0):
    return "—" if x is None or pd.isna(x) else f"{x:,.{d}f}"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return "".join(ch if ch.isalnum() else " " for ch in t)


@dataclass
class Respuesta:
    titulo: str
    hechos: list[str] = field(default_factory=list)
    interpretacion: list[str] = field(default_factory=list)
    recomendaciones: list[str] = field(default_factory=list)
    criterio: str = ""
    limitaciones: list[str] = field(default_factory=list)
    tabla: pd.DataFrame | None = None
    intencion: str = ""

    def markdown(self) -> str:
        bloques = [f"#### {self.titulo}"]
        if self.hechos:
            bloques.append("**📌 Hechos (cifras verificables en el dashboard)**\n\n" + "\n".join(f"- {h}" for h in self.hechos))
        if self.interpretacion:
            bloques.append("**🔎 Interpretación**\n\n" + "\n".join(f"- {h}" for h in self.interpretacion))
        if self.recomendaciones:
            bloques.append("**✅ Recomendaciones**\n\n" + "\n".join(f"{i}. {h}" for i, h in enumerate(self.recomendaciones, 1)))
        if self.criterio:
            bloques.append(f"**📐 Criterio aplicado:** {self.criterio}")
        if self.limitaciones:
            bloques.append("**⚠️ Limitaciones**\n\n" + "\n".join(f"- {h}" for h in self.limitaciones))
        return "\n\n".join(bloques)


INTENCIONES = {
    "sucursales": (["sucursal", "sucursales", "tienda", "local", "locales"], ["mejor", "peor", "desempeno", "ranking", "comparar", "compar"]),
    "productos_revisar": (["producto", "productos", "menu", "item"], ["revis", "bajo", "baja", "peor", "eliminar", "debil", "menor"]),
    "productos_utilidad": (["producto", "productos", "menu"], ["utilidad", "rentab", "ganancia", "margen", "mejor", "mas vendido", "estrella"]),
    "segmentos": (["segmento", "segmentos", "crecimiento", "oportunidad"], []),
    "ciudades": (["ciudad", "ciudades", "mercado", "plaza", "dallas", "houston", "austin", "antonio"], []),
    "ticket": (["ticket", "gasto por", "valor por transaccion", "valor promedio"], []),
    "descuentos": (["descuento", "descuentos", "promocion", "promociones", "rebaja"], []),
    "rentabilidad": (["rentabilidad", "margen", "utilidad bruta", "costos", "costo"], ["mejorar", "incrementar", "aumentar", "acciones", "como"]),
    "tendencia": (["tendencia", "evolucion", "caida", "crecimiento de ventas", "mensual", "anual", "comportamiento de las ventas", "ventas"], []),
    "recuperacion": (["recuper", "inactiv", "perdid", "abandono", "fideliz", "retencion", "frecuencia"], []),
    "canales": (["canal", "canales", "delivery", "pickup", "restaurante", "domicilio"], []),
    "pagos": (["pago", "pagos", "efectivo", "tarjeta", "apple", "google pay"], []),
    "categorias": (["categoria", "categorias", "pizzas", "bebidas", "postres", "entradas"], []),
    "tiempos": (["tiempo de entrega", "entrega", "preparacion", "demora"], []),
    "resumen": (["hallazgo", "hallazgos", "resumen", "diagnostico", "general", "situacion", "informe", "principales"], []),
}

PREGUNTAS_SUGERIDAS = [
    "¿Cuál es la sucursal con mejor desempeño?",
    "¿Qué productos generan mayor utilidad?",
    "¿Qué segmento representa una oportunidad de crecimiento?",
    "¿Qué ciudad necesita atención comercial?",
    "¿Qué productos deberían revisarse?",
    "¿Cómo mejorar el ticket promedio?",
    "¿Qué acciones pueden incrementar la rentabilidad?",
    "¿Cuáles son los principales hallazgos?",
    "¿Cómo están afectando los descuentos?",
    "¿Cuál es la tendencia de las ventas?",
    "¿Qué clientes debemos recuperar?",
    "¿Qué canal de venta funciona mejor?",
]


class MotorReglas:
    def __init__(self, df: pd.DataFrame, prev: pd.DataFrame | None, fecha_corte: pd.Timestamp,
                 periodo_txt: str = "", periodo_prev_txt: str = "", filtros_txt: str = ""):
        self.df = df
        self.prev = prev if prev is not None and len(prev) else None
        self.corte = fecha_corte
        self.per = periodo_txt
        self.per_prev = periodo_prev_txt
        self.filtros = filtros_txt
        self.tot = kpis.resumen(df)

    # ------------------------------------------------------------ enrutamiento
    def intencion(self, pregunta: str) -> str | None:
        t = " " + _norm(pregunta) + " "
        mejor, puntaje = None, 0
        for k, (claves, refuerzo) in INTENCIONES.items():
            s = sum(2 for c in claves if c in t)
            if s and refuerzo:
                r = sum(1 for c in refuerzo if c in t)
                s = s + r if r else s * 0.5
            if s > puntaje:
                mejor, puntaje = k, s
        return mejor

    def responder(self, pregunta: str) -> Respuesta:
        if self.df.empty:
            return Respuesta("Sin datos suficientes", limitaciones=[
                "No hay ventas con los filtros activos. Amplíe el período o limpie los filtros."])
        k = self.intencion(pregunta)
        if k is None:
            return Respuesta("No identifiqué la pregunta", interpretacion=[
                "Este motor responde preguntas sobre: sucursales, productos (utilidad o revisión), segmentos, "
                "ciudades, ticket promedio, rentabilidad, descuentos, tendencia de ventas, recuperación de "
                "clientes, canales, formas de pago, categorías, tiempos de entrega y hallazgos generales."],
                limitaciones=["No es un modelo generativo: reconoce temas por palabras clave. Reformule la pregunta "
                              "usando alguno de esos temas o elija una pregunta sugerida."])
        r = getattr(self, f"_{k}")()
        r.intencion = k
        if self.filtros:
            r.limitaciones.append(f"Resultados calculados con los filtros activos: {self.filtros}.")
        return r

    # ------------------------------------------------------------ utilidades
    def _desc_share(self, df):
        return df.ConDescuento.mean() * 100 if len(df) else np.nan

    def _var(self, dim: str) -> pd.DataFrame:
        a = kpis.por(self.df, dim, orden=None)
        if self.prev is not None:
            b = kpis.por(self.prev, dim, orden=None)[[dim, "ventas", "margen"]].rename(
                columns={"ventas": "ventas_prev", "margen": "margen_prev"})
            a = a.merge(b, on=dim, how="left")
            a["var_ventas"] = (a.ventas / a.ventas_prev - 1) * 100
            a["var_margen_pp"] = a.margen - a.margen_prev
        d = self.df.groupby(dim).ConDescuento.mean().mul(100).rename("pct_desc").reset_index()
        return a.merge(d, on=dim, how="left")

    def _tendencia_interna(self) -> tuple[float, pd.DataFrame]:
        m = kpis.mensual(self.df)
        if len(m) < 3:
            return np.nan, m
        x = np.arange(len(m))
        pend = np.polyfit(x, m.ventas.values, 1)[0]
        return pend / m.ventas.mean() * 100, m

    # ------------------------------------------------------------ intenciones
    def _sucursales(self) -> Respuesta:
        r = kpis.ranking_sucursales(self.df, self.prev)
        if len(r) < 2:
            return Respuesta("Desempeño de sucursales", limitaciones=[
                "Con los filtros actuales solo hay una sucursal; se necesitan al menos dos para comparar."])
        d = self.df.groupby("Sucursal").ConDescuento.mean().mul(100)
        b, w = r.iloc[0], r.iloc[-1]
        res = Respuesta("Sucursal con mejor y peor desempeño")
        for etq, s in (("Mejor", b), ("Peor", w)):
            txt = (f"**{etq}: {s.Sucursal}** ({s.Ciudad}) — puntaje {s.puntaje:.2f}; ventas {_u(s.ventas)}, "
                   f"utilidad {_u(s.utilidad)}, margen {_p(s.margen)}, ticket {_u(s.ticket, 2)}, "
                   f"{_n(s.transacciones)} transacciones, {_n(s.unidades)} unidades, "
                   f"{_p(d.get(s.Sucursal))} de transacciones con descuento")
            if "crec_ventas" in r and not pd.isna(s.get("crec_ventas", np.nan)):
                txt += f"; variación de ventas vs período anterior {s.crec_ventas:+.1f}%"
            res.hechos.append(txt + ".")
        res.hechos.append(f"Margen bruto del conjunto filtrado: {_p(self.tot['margen'])}; "
                          f"diferencia de utilidad entre la mejor y la peor: {_u(b.utilidad - w.utilidad)}.")
        dif_m = b.margen - w.margen
        if dif_m > 1:
            res.interpretacion.append(f"La brecha de margen ({dif_m:.1f} p.p.) explica buena parte de la diferencia "
                                      "de utilidad: la peor sucursal convierte menos de cada dólar vendido en utilidad.")
        if d.get(w.Sucursal, 0) - d.mean() > 10:
            res.interpretacion.append(f"{w.Sucursal} aplica descuentos en {_p(d.get(w.Sucursal))} de sus transacciones, "
                                      f"frente a un promedio de {_p(d.mean())}; los descuentos reducen el margen.")
        rng = (r.ventas.max() - r.ventas.min()) / r.ventas.mean() * 100
        res.interpretacion.append(f"La diferencia de ventas entre la sucursal que más y menos vende es de {rng:.1f}% "
                                  "del promedio; por eso el ranking no se basa solo en ventas.")
        res.recomendaciones.append(f"Documentar las prácticas de {b.Sucursal} (política de precios, mezcla de productos "
                                   "y atención) y replicarlas en las sucursales con menor puntaje.")
        if d.get(w.Sucursal, 0) - d.mean() > 10:
            res.recomendaciones.append(f"Revisar y acotar la política de descuentos de {w.Sucursal}: fijar un tope de "
                                       "transacciones con descuento similar al promedio de la cadena y medir el margen mensual.")
        if w.pos_ticket >= len(r) - 1:
            res.recomendaciones.append(f"Impulsar en {w.Sucursal} la venta de combos y productos de mayor precio para elevar el ticket.")
        if w.pos_transacciones >= len(r) - 1:
            res.recomendaciones.append(f"Diseñar acciones de tráfico en {w.Sucursal} (campañas locales, alianzas) para "
                                       "aumentar el número de transacciones.")
        res.criterio = ("Promedio de la posición (1 = mejor) en seis indicadores: ventas, utilidad bruta, margen bruto, "
                        "transacciones, ticket promedio y unidades. Desempate por utilidad.")
        res.tabla = r[["Sucursal", "Ciudad", "ventas", "utilidad", "margen", "ticket", "transacciones",
                       "unidades", "puntaje"]].round(2)
        res.limitaciones.append("La base no incluye costos operativos (alquiler, personal), por lo que el desempeño "
                                "se evalúa a nivel de utilidad bruta, no de utilidad neta.")
        return res

    def _productos_utilidad(self) -> Respuesta:
        pr = kpis.por(self.df, "ProductoNombre", orden="utilidad")
        tot = pr.utilidad.sum()
        res = Respuesta("Productos que generan mayor utilidad")
        for s in pr.head(5).itertuples():
            res.hechos.append(f"**{s.ProductoNombre}**: utilidad {_u(s.utilidad)} ({s.utilidad / tot * 100:.1f}% del total), "
                              f"margen {_p(s.margen)}, {_n(s.unidades)} unidades, ventas {_u(s.ventas)}.")
        top5 = pr.head(5).utilidad.sum() / tot * 100
        res.hechos.append(f"Los 5 primeros concentran {top5:.1f}% de la utilidad bruta de {len(pr)} productos.")
        u = pr.sort_values("unidades", ascending=False).iloc[0]
        mg = pr.sort_values("margen", ascending=False).iloc[0]
        res.interpretacion.append(f"El más vendido en unidades es **{u.ProductoNombre}** ({_n(u.unidades)} u.) y el de mayor "
                                  f"margen porcentual es **{mg.ProductoNombre}** ({_p(mg.margen)}); ninguno coincide "
                                  f"necesariamente con el que más utilidad aporta (**{pr.iloc[0].ProductoNombre}**)."
                                  if u.ProductoNombre != pr.iloc[0].ProductoNombre else
                                  f"El producto más vendido también es el de mayor utilidad: {u.ProductoNombre}.")
        if top5 < 25:
            res.interpretacion.append("La utilidad está poco concentrada: depende de un portafolio amplio y no de pocos productos.")
        res.recomendaciones += [
            f"Asegurar disponibilidad y destacar en menú y canales digitales a {', '.join(pr.head(3).ProductoNombre)}.",
            "Usar los productos de mayor utilidad como base de combos con bebidas o entradas de alto margen.",
            "Priorizar la medición de utilidad (no solo unidades) en las metas comerciales de las sucursales."]
        res.criterio = "Orden por utilidad bruta en dólares (Σ UtilidadBruta) del período filtrado."
        res.tabla = pr.head(10)[["ProductoNombre", "utilidad", "margen", "unidades", "ventas"]].round(2)
        return res

    def _productos_revisar(self) -> Respuesta:
        pr = kpis.por(self.df, ["ProductoID", "ProductoNombre", "Categoria"], orden="utilidad")
        if len(pr) < 4:
            return Respuesta("Productos a revisar", limitaciones=["Se necesitan al menos 4 productos para comparar."])
        q_m, q_u, q_v = pr.margen.quantile(.25), pr.utilidad.quantile(.25), pr.unidades.quantile(.25)
        cat_m = pr.groupby("Categoria").apply(lambda g: g.utilidad.sum() / g.ventas.sum() * 100)
        pr["bajo_margen"] = pr.margen <= q_m
        pr["baja_utilidad"] = pr.utilidad <= q_u
        pr["bajo_volumen"] = pr.unidades <= q_v
        pr["n"] = pr[["bajo_margen", "baja_utilidad", "bajo_volumen"]].sum(axis=1)
        cand = pr[pr.n >= 2].sort_values(["n", "utilidad"], ascending=[False, True])
        if cand.empty:
            cand = pr[pr.bajo_margen].sort_values("margen")
        res = Respuesta("Productos que deberían revisarse")
        for s in cand.head(8).itertuples():
            motivos = [m for m, f in (("margen bajo", s.bajo_margen), ("utilidad baja", s.baja_utilidad),
                                      ("volumen bajo", s.bajo_volumen)) if f]
            res.hechos.append(f"**{s.ProductoNombre}** ({s.Categoria}): margen {_p(s.margen)} (promedio de su categoría "
                              f"{_p(cat_m.get(s.Categoria))}), utilidad {_u(s.utilidad)}, {_n(s.unidades)} u. → {', '.join(motivos)}.")
        cv = pr.unidades.std() / pr.unidades.mean() * 100
        res.hechos.append(f"Umbrales (cuartil inferior): margen ≤ {_p(q_m)}, utilidad ≤ {_u(q_u)}, unidades ≤ {_n(q_v)}.")
        if cv < 10:
            res.interpretacion.append(f"Las unidades vendidas por producto son muy parecidas (coef. de variación {cv:.1f}%): "
                                      "el problema principal no es el volumen sino el margen y el precio.")
        res.interpretacion.append("Un margen inferior al de su categoría sugiere revisar precio de venta, costo de receta "
                                  "o descuentos aplicados; es una hipótesis a validar, no una causa comprobada.")
        res.recomendaciones += [
            "Revisar precio y costo unitario de los productos listados frente al promedio de su categoría.",
            "Evitar incluir productos de margen bajo en promociones con descuento.",
            "Antes de retirar un producto, verificar si complementa ventas de otros (p. ej. se vende junto a pizzas); "
            "la base actual registra un producto por transacción, por lo que ese efecto no es medible aquí."]
        inact = self.df[self.df.get("Activo", pd.Series(index=self.df.index, dtype=str)).astype(str).str.lower() == "no"]
        if len(inact):
            res.hechos.append(f"Productos marcados como inactivos en el maestro que sí registran ventas: "
                              f"{', '.join(sorted(inact.ProductoNombre.unique()))} ({_n(len(inact))} transacciones).")
            res.recomendaciones.append("Actualizar el estado «Activo» del maestro de productos para que refleje la oferta real.")
        res.criterio = ("Se marcan productos en el cuartil inferior de margen %, utilidad USD o unidades; se priorizan "
                        "los que cumplen dos o más condiciones.")
        res.tabla = cand.head(10)[["ProductoNombre", "Categoria", "margen", "utilidad", "unidades"]].round(2)
        return res

    def _segmentos(self) -> Respuesta:
        s = self._var("Segmento")
        if len(s) < 2:
            return Respuesta("Segmentos", limitaciones=["Seleccione más de un segmento para comparar."])
        cl = kpis.clientes_desde_ventas(self.df, self.corte)
        n = cl.groupby("Segmento").NPS.apply(kpis.nps).rename("nps") if "NPS" in cl else pd.Series(dtype=float)
        f = cl.groupby("Segmento").frecuencia_mensual.mean().rename("frec")
        s = s.merge(n.reset_index(), on="Segmento", how="left").merge(f.reset_index(), on="Segmento", how="left")
        s["r_nps"] = s.nps.rank(ascending=False)
        s["r_ticket"] = s.ticket.rank(ascending=False)
        s["r_espacio"] = s.participacion.rank(ascending=True)
        crit = ["r_nps", "r_ticket", "r_espacio"]
        if "var_ventas" in s:
            s["r_crec"] = s.var_ventas.rank(ascending=False)
            crit.append("r_crec")
        s["score"] = s[crit].mean(axis=1)
        s = s.sort_values("score")
        o = s.iloc[0]
        res = Respuesta("Segmento con mayor oportunidad de crecimiento")
        for x in s.sort_values("ventas", ascending=False).itertuples():
            t = (f"**{x.Segmento}**: {_p(x.participacion)} de las ventas, {_n(x.clientes)} clientes, ticket {_u(x.ticket, 2)}, "
                 f"{_n(x.frec, 2)} compras/mes por cliente, NPS {_n(x.nps, 1)}")
            if "var_ventas" in s:
                t += f", variación de ventas {x.var_ventas:+.1f}%"
            res.hechos.append(t + ".")
        res.interpretacion.append(f"**{o.Segmento}** combina la mejor satisfacción relativa (NPS {_n(o.nps, 1)}) y ticket "
                                  f"{_u(o.ticket, 2)} con una participación de solo {_p(o.participacion)}: hay espacio para "
                                  "crecer captando más clientes de ese perfil.")
        lider = s.sort_values("ventas", ascending=False).iloc[0]
        res.interpretacion.append(f"{lider.Segmento} es el segmento de mayor peso ({_p(lider.participacion)}); su retención es "
                                  "prioritaria aunque su potencial de crecimiento relativo sea menor.")
        bajo = s.sort_values("nps").iloc[0]
        if bajo.nps < 0:
            res.interpretacion.append(f"{bajo.Segmento} tiene NPS negativo ({_n(bajo.nps, 1)}): más detractores que promotores, "
                                      "lo que representa un riesgo de pérdida en ese segmento.")
        tk = s.ticket.max() - s.ticket.min()
        if tk < 1:
            res.limitaciones.append(f"Las diferencias de ticket entre segmentos son pequeñas ({_u(tk, 2)}); la elección se apoya "
                                    "sobre todo en satisfacción y participación.")
        res.recomendaciones += [
            f"Programa de captación para el segmento {o.Segmento} (convenios, pedidos programados, referidos de clientes promotores).",
            f"Plan de fidelización para {lider.Segmento} enfocado en aumentar la frecuencia de compra.",
            f"Investigar con encuestas las causas de insatisfacción de {bajo.Segmento} antes de invertir en promociones para ese segmento."]
        res.criterio = ("Promedio de posiciones en: NPS (mayor es mejor), ticket promedio (mayor es mejor), participación "
                        "actual en ventas (menor = más espacio para crecer)" + (" y variación de ventas vs período anterior."
                                                                               if "var_ventas" in s else "."))
        res.limitaciones.append("El NPS y el segmento provienen del maestro de clientes; las métricas de compra, de la base de ventas.")
        res.tabla = s[["Segmento", "ventas", "participacion", "clientes", "ticket", "frec", "nps", "score"]
                      + (["var_ventas"] if "var_ventas" in s else [])].round(2)
        return res

    def _ciudades(self) -> Respuesta:
        c = self._var("Ciudad")
        if len(c) < 2:
            return Respuesta("Ciudades", limitaciones=["Seleccione más de una ciudad para comparar."])
        for k in ["ventas", "utilidad", "margen", "ticket"]:
            c[f"r_{k}"] = c[k].rank(ascending=True)
        crit = ["r_ventas", "r_utilidad", "r_margen", "r_ticket"]
        if "var_ventas" in c:
            c["r_var"] = c.var_ventas.rank(ascending=True)
            crit.append("r_var")
        c["score"] = c[crit].mean(axis=1)
        c = c.sort_values("score")
        w = c.iloc[0]
        res = Respuesta("Ciudad que necesita atención comercial")
        for x in c.itertuples():
            t = (f"**{x.Ciudad}**: ventas {_u(x.ventas)}, utilidad {_u(x.utilidad)}, margen {_p(x.margen)}, ticket {_u(x.ticket, 2)}, "
                 f"{_p(x.pct_desc)} de transacciones con descuento")
            if "var_ventas" in c:
                t += f", variación de ventas {x.var_ventas:+.1f}%, margen {0.0 if abs(x.var_margen_pp) < 0.05 else x.var_margen_pp:+.1f} p.p."
            res.hechos.append(t + ".")
        res.interpretacion.append(f"**{w.Ciudad}** ocupa la última posición combinada en ventas, utilidad, margen y ticket"
                                  + (" y crecimiento." if "var_ventas" in c else "."))
        otros = c[c.Ciudad != w.Ciudad].pct_desc.mean()
        if w.pct_desc - otros > 10:
            res.interpretacion.append(f"En {w.Ciudad} el {_p(w.pct_desc)} de las transacciones tuvo descuento frente a {_p(otros)} en "
                                      "el resto: el mayor uso de descuentos coincide con un margen menor"
                                      + (" y no evitó una caída de ventas mayor." if "var_ventas" in c and w.var_ventas < c.var_ventas.mean() else "."))
            res.recomendaciones.append(f"Revisar la política de descuentos de {w.Ciudad}: limitar su frecuencia y evaluar su efecto mes a mes.")
        if "TiempoEntregaMin" in self.df:
            dl = self.df[(self.df.Canal == "Delivery") & (self.df.TiempoEntregaMin > 0)]
            if len(dl):
                te = dl.groupby("Ciudad").TiempoEntregaMin.mean()
                resto = te.drop(w.Ciudad, errors="ignore").mean()
                if w.Ciudad in te and te[w.Ciudad] > resto * 1.2:
                    res.hechos.append(f"Tiempo medio de entrega a domicilio: {w.Ciudad} {_n(te[w.Ciudad], 1)} min vs {_n(resto, 1)} min en el resto.")
                    res.interpretacion.append(f"{w.Ciudad} también presenta tiempos de entrega claramente mayores; la experiencia de servicio "
                                              "es una posible explicación adicional a validar con la operación.")
                    res.recomendaciones.append(f"Auditar la logística de reparto de {w.Ciudad} y fijar una meta de tiempo de entrega.")
        res.recomendaciones += [f"Plan comercial específico para {w.Ciudad} con metas mensuales de ventas y margen por sucursal.",
                                f"Comparar precios y mezcla de productos de {w.Ciudad} con la ciudad de mejor desempeño ({c.iloc[-1].Ciudad})."]
        res.criterio = "Promedio de posiciones (1 = peor) en ventas, utilidad, margen, ticket" + (" y variación de ventas." if "var_ventas" in c else ".")
        res.tabla = c[["Ciudad", "ventas", "utilidad", "margen", "ticket", "pct_desc"] + (["var_ventas"] if "var_ventas" in c else [])].round(2)
        return res

    def _ticket(self) -> Respuesta:
        df = self.df
        res = Respuesta("Cómo mejorar el ticket promedio")
        t = self.tot["ticket"]
        q = df.Cantidad.value_counts(normalize=True).sort_index() * 100
        cat = kpis.por(df, "Categoria", orden="ticket")
        cq = df.groupby("Cantidad").VentaNeta.mean()
        sd, cd = df[~df.ConDescuento], df[df.ConDescuento]
        res.hechos.append(f"Ticket promedio actual: {_u(t, 2)} con {_n(self.tot['transacciones'])} transacciones.")
        res.hechos.append("Distribución de unidades por transacción: " + ", ".join(f"{int(k)} u. = {_p(v)}" for k, v in q.items()) + ".")
        res.hechos.append("Ticket por categoría: " + ", ".join(f"{r.Categoria} {_u(r.ticket, 2)}" for r in cat.itertuples()) + ".")
        res.hechos.append("Ticket según unidades: " + ", ".join(f"{int(k)} u. {_u(v, 2)}" for k, v in cq.items()) + ".")
        if len(cd) and len(sd):
            res.hechos.append(f"Ticket sin descuento {_u(kpis.resumen(sd)['ticket'], 2)} vs con descuento {_u(kpis.resumen(cd)['ticket'], 2)}.")
        tk_s = kpis.por(df, "Sucursal", orden="ticket")
        if len(tk_s) > 1:
            res.hechos.append(f"Rango por sucursal: {tk_s.iloc[-1].Sucursal} {_u(tk_s.iloc[-1].ticket, 2)} – {tk_s.iloc[0].Sucursal} {_u(tk_s.iloc[0].ticket, 2)}.")
        p1 = q.get(1, 0)
        res.interpretacion.append("En esta base cada transacción registra un solo producto; el ticket sube si aumenta la cantidad "
                                  "por transacción o si la mezcla se desplaza hacia productos de mayor precio.")
        if p1 > 25:
            sim = t + (cq.get(2, t) - cq.get(1, t)) * 0.10 * p1 / 100 if 1 in cq and 2 in cq else np.nan
            res.interpretacion.append(f"{_p(p1)} de las transacciones son de 1 unidad. Escenario ilustrativo (no un resultado): si 10% "
                                      f"de ellas pasaran a 2 unidades, el ticket teórico sería ≈ {_u(sim, 2)}.")
        res.recomendaciones += [
            "Ofrecer precio por segunda unidad o combos de 2 pizzas para transacciones de 1 unidad.",
            f"Promover la categoría de mayor ticket ({cat.iloc[0].Categoria}) en canales digitales y en caja.",
            "Sustituir descuentos generales por beneficios condicionados a un monto mínimo de compra.",
            "Fijar metas de ticket por sucursal y seguimiento mensual."]
        res.criterio = "Ticket = Σ VentaNeta ÷ nº de VentaID únicos; desgloses con la misma fórmula."
        res.limitaciones.append("No hay información de pedidos con varios productos (canasta), por lo que no se puede medir venta cruzada real.")
        return res

    def _descuentos(self) -> Respuesta:
        df = self.df
        res = Respuesta("Efecto de los descuentos")
        g = kpis.por(df, "DescuentoPct", orden=None).sort_values("DescuentoPct")
        res.hechos.append(f"Transacciones con descuento: {_p(df.ConDescuento.mean() * 100)}; monto descontado: {_u(self.tot['descuento'])} "
                          f"({_p(self.tot['descuento'] / (self.tot['ventas'] + self.tot['descuento']) * 100)} de la venta bruta).")
        res.hechos.append("Margen según nivel de descuento: " + ", ".join(f"{int(r.DescuentoPct)}% → {_p(r.margen)} ({_n(r.transacciones)} tx)" for r in g.itertuples()) + ".")
        c = self._var("Ciudad").sort_values("pct_desc", ascending=False)
        res.hechos.append("Uso de descuentos por ciudad: " + ", ".join(f"{r.Ciudad} {_p(r.pct_desc)}" for r in c.itertuples()) + ".")
        if "var_ventas" in c:
            res.hechos.append("Variación de ventas por ciudad vs período anterior: " + ", ".join(f"{r.Ciudad} {r.var_ventas:+.1f}%" for r in c.itertuples()) + ".")
        anual = df.groupby("Año").ConDescuento.mean().mul(100)
        if len(anual) > 1:
            res.hechos.append("Transacciones con descuento por año: " + ", ".join(f"{int(a)} {_p(v)}" for a, v in anual.items()) + ".")
        res.interpretacion.append("A mayor descuento, menor margen: cada punto de descuento reduce directamente la utilidad por transacción.")
        if "var_ventas" in c and len(c) > 1:
            top = c.iloc[0]
            if top.pct_desc - c.pct_desc.iloc[1:].mean() > 10 and top.var_ventas <= c.var_ventas.mean():
                res.interpretacion.append(f"{top.Ciudad}, la ciudad con más descuentos, no muestra un mejor comportamiento de ventas: "
                                          "los datos no evidencian que los descuentos hayan estimulado la demanda (correlación, no causalidad).")
        res.recomendaciones += ["Definir un tope de descuento y de porcentaje de transacciones con descuento por sucursal.",
                                "Medir cada promoción con grupo de control (sucursal o período comparable) antes de extenderla.",
                                "Orientar descuentos a productos de margen alto y a recuperar clientes inactivos, no de forma general."]
        res.criterio = "Comparación del margen ponderado por nivel de descuento y del uso de descuentos por ciudad."
        res.tabla = g[["DescuentoPct", "transacciones", "ventas", "utilidad", "margen", "ticket"]].round(2)
        return res

    def _rentabilidad(self) -> Respuesta:
        df = self.df
        res = Respuesta("Acciones para incrementar la rentabilidad")
        cat = kpis.por(df, "Categoria", orden="margen")
        sd, cd = df[~df.ConDescuento], df[df.ConDescuento]
        pr = kpis.por(df, "ProductoNombre", orden="margen")
        res.hechos.append(f"Margen bruto: {_p(self.tot['margen'])}; utilidad {_u(self.tot['utilidad'])} sobre ventas {_u(self.tot['ventas'])}.")
        if len(sd) and len(cd):
            res.hechos.append(f"Margen sin descuento {_p(kpis.resumen(sd)['margen'])} vs con descuento {_p(kpis.resumen(cd)['margen'])}; "
                              f"descuentos otorgados {_u(self.tot['descuento'])}.")
        res.hechos.append("Margen por categoría: " + ", ".join(f"{r.Categoria} {_p(r.margen)} ({_p(r.participacion)} de ventas)" for r in cat.itertuples()) + ".")
        res.hechos.append(f"Productos de menor margen: {', '.join(f'{r.ProductoNombre} {_p(r.margen)}' for r in pr.tail(3).itertuples())}.")
        if self.prev is not None:
            p = kpis.resumen(self.prev)
            res.hechos.append(f"Margen del período anterior: {_p(p['margen'])} ({self.tot['margen'] - p['margen']:+.1f} p.p.).")
        sin_desc_util = kpis.resumen(sd)["margen"] if len(sd) else np.nan
        if len(cd):
            pot = cd.VentaNeta.sum() * (sin_desc_util - kpis.resumen(cd)["margen"]) / 100
            res.interpretacion.append(f"Si las ventas con descuento tuvieran el margen de las ventas sin descuento, la utilidad sería "
                                      f"≈ {_u(pot)} mayor (escenario ilustrativo, asume igual volumen).")
        res.interpretacion.append(f"{cat.iloc[0].Categoria} tiene el mayor margen ({_p(cat.iloc[0].margen)}) pero solo {_p(cat.iloc[0].participacion)} "
                                  "de las ventas: aumentar su peso mejora el margen global.")
        res.recomendaciones += ["Controlar la política de descuentos (topes y medición de efecto).",
                                f"Impulsar la venta de {cat.iloc[0].Categoria.lower()} como complemento de las pizzas.",
                                "Revisar precio o costo de los productos de menor margen.",
                                "Incorporar margen y utilidad —no solo ventas— en las metas de las sucursales."]
        res.criterio = "Margen ponderado = Σ UtilidadBruta ÷ Σ VentaNeta; comparación por descuento, categoría y producto."
        res.limitaciones.append("Solo se analiza utilidad bruta; la base no tiene gastos operativos ni de marketing.")
        return res

    def _tendencia(self) -> Respuesta:
        res = Respuesta("Tendencia de las ventas")
        pend, m = self._tendencia_interna()
        res.hechos.append(f"Ventas del período {self.per}: {_u(self.tot['ventas'])} en {len(m)} meses "
                          f"(promedio mensual {_u(self.tot['ventas'] / max(1, len(m)))}).")
        if len(m):
            mx, mn = m.loc[m.ventas.idxmax()], m.loc[m.ventas.idxmin()]
            res.hechos.append(f"Mes más alto: {mx.Periodo:%m/%Y} ({_u(mx.ventas)}); más bajo: {mn.Periodo:%m/%Y} ({_u(mn.ventas)}).")
        if self.prev is not None:
            p = kpis.resumen(self.prev)
            res.hechos.append(f"Frente al período anterior ({self.per_prev}): ventas {kpis.variacion(self.tot['ventas'], p['ventas']):+.1f}%, "
                              f"transacciones {kpis.variacion(self.tot['transacciones'], p['transacciones']):+.1f}%, "
                              f"ticket {kpis.variacion(self.tot['ticket'], p['ticket']):+.1f}%, margen {self.tot['margen'] - p['margen']:+.1f} p.p.")
        anual = kpis.por(self.df, "Año", orden=None).sort_values("Año")
        if len(anual) > 1:
            a0, a1 = anual.iloc[-2], anual.iloc[-1]
            res.hechos.append(f"{int(a1['Año'])} vs {int(a0['Año'])}: ventas {kpis.variacion(a1.ventas, a0.ventas):+.1f}%, "
                              f"transacciones {kpis.variacion(a1.transacciones, a0.transacciones):+.1f}%, ticket {kpis.variacion(a1.ticket, a0.ticket):+.1f}%.")
        if not pd.isna(pend):
            res.hechos.append(f"Pendiente de la tendencia lineal mensual: {pend:+.2f}% del promedio mensual por mes.")
            if pend < -0.5:
                res.interpretacion.append("La tendencia es decreciente. Al comparar transacciones y ticket se observa si la caída viene "
                                          "de menos compras (tráfico) o de menor valor por compra.")
            elif pend > 0.5:
                res.interpretacion.append("La tendencia es creciente en el período seleccionado.")
            else:
                res.interpretacion.append("Las ventas se mantienen estables en el período seleccionado.")
        if self.prev is not None:
            p = kpis.resumen(self.prev)
            vt, vk = kpis.variacion(self.tot["transacciones"], p["transacciones"]), kpis.variacion(self.tot["ticket"], p["ticket"])
            if vt < -5 and abs(vk) < 3:
                res.interpretacion.append("La variación se explica principalmente por el número de transacciones, no por el ticket: "
                                          "el foco debe estar en tráfico y frecuencia de compra.")
        res.recomendaciones += ["Establecer un tablero mensual de seguimiento de transacciones por sucursal con alertas de caída.",
                                "Activar campañas de frecuencia (programa de lealtad) en los meses de menor venta.",
                                "Analizar con la operación las causas de la variación, ya que la base no registra factores externos."]
        res.criterio = "Suma mensual de VentaNeta; tendencia por regresión lineal simple sobre los meses del período."
        res.limitaciones.append("La base no contiene variables externas (competencia, clima, precios de mercado); las causas deben validarse.")
        res.tabla = m[["Periodo", "ventas", "utilidad", "margen", "transacciones", "ticket"]].assign(
            Periodo=lambda x: x.Periodo.dt.strftime("%Y-%m")).round(2) if len(m) else None
        return res

    def _recuperacion(self) -> Respuesta:
        cl = kpis.clientes_desde_ventas(self.df, self.corte)
        res = Respuesta("Clientes a recuperar")
        inact = cl[cl.dias_sin_comprar > 90]
        mitad = self.df.Fecha.min() + (self.df.Fecha.max() - self.df.Fecha.min()) / 2
        g1 = self.df[self.df.Fecha < mitad].groupby("ClienteID").VentaNeta.sum()
        g2 = self.df[self.df.Fecha >= mitad].groupby("ClienteID").VentaNeta.sum()
        cl["cambio"] = (cl.ClienteID.map(g2).fillna(0) / cl.ClienteID.map(g1) - 1) * 100
        caen = cl[cl.cambio <= -50]
        res.hechos.append(f"Clientes compradores: {_n(len(cl))}; sin compras en más de 90 días al {self.corte:%d/%m/%Y}: {_n(len(inact))}.")
        res.hechos.append(f"Clientes cuyo gasto cayó 50% o más entre la primera y la segunda mitad del período: {_n(len(caen))} "
                          f"(gasto previo {_u(cl.ClienteID.map(g1)[caen.index].sum() if len(caen) else 0)}).")
        if "ClienteActivo" in cl:
            no = (cl.ClienteActivo == "No").sum()
            res.hechos.append(f"Clientes marcados «No activo» en el maestro: {_n(no)}; de ellos con compras en los últimos 90 días: "
                              f"{_n(((cl.ClienteActivo == 'No') & (cl.dias_sin_comprar <= 90)).sum())}.")
            mot = cl[cl.ClienteActivo == "No"].MotivoPerdida.value_counts()
            if len(mot):
                res.hechos.append("Motivos de pérdida registrados en el maestro: " + ", ".join(f"{k} ({v})" for k, v in mot.items()) + ".")
        res.interpretacion.append("La inactividad se mide con las compras reales. El indicador «ClienteActivo» del maestro no coincide "
                                  "con la base de ventas, por lo que se usa solo como referencia.")
        res.recomendaciones += ["Contactar primero a los clientes con mayor gasto previo cuyo consumo cayó (lista en Análisis de clientes).",
                                "Ofrecer incentivos de regreso personalizados y medir la tasa de recompra en 60 días.",
                                "Depurar el maestro de clientes para que el estado de actividad se actualice con las ventas."]
        res.criterio = "Inactivo: más de 90 días sin compras respecto a la última fecha de la base. Caída: gasto 2.ª mitad ≤ 50% de la 1.ª."
        res.limitaciones.append("Los motivos de pérdida se muestran como están en el maestro; el motor no infiere motivos.")
        return res

    def _dim_simple(self, dim: str, titulo: str, nombre: str = "") -> Respuesta:
        g = self._var(dim).sort_values("ventas", ascending=False)
        res = Respuesta(titulo)
        for r in g.itertuples():
            t = f"**{getattr(r, dim)}**: ventas {_u(r.ventas)} ({_p(r.participacion)}), margen {_p(r.margen)}, ticket {_u(r.ticket, 2)}"
            if "var_ventas" in g:
                t += f", variación {r.var_ventas:+.1f}%"
            res.hechos.append(t + ".")
        rango = g.participacion.max() - g.participacion.min()
        if rango < 3:
            res.interpretacion.append(f"La distribución es muy homogénea (diferencia máxima de participación {rango:.1f} p.p.): "
                                      f"no hay {nombre or dim.lower()} claramente superior en los datos.")
            res.recomendaciones.append("Mantener la oferta actual y concentrar la inversión comercial en otras palancas (descuentos, mezcla, segmentos).")
        else:
            res.interpretacion.append(f"{getattr(g.iloc[0], dim)} concentra la mayor participación.")
            res.recomendaciones.append(f"Fortalecer {getattr(g.iloc[0], dim)} y revisar la experiencia en {getattr(g.iloc[-1], dim)}.")
        res.criterio = f"Indicadores agregados por {dim}."
        return res

    def _canales(self) -> Respuesta:
        return self._dim_simple("Canal", "Desempeño por canal de venta", "un canal")

    def _pagos(self) -> Respuesta:
        return self._dim_simple("FormaPago", "Desempeño por forma de pago", "una forma de pago")

    def _categorias(self) -> Respuesta:
        return self._dim_simple("Categoria", "Desempeño por categoría de producto", "una categoría")

    def _tiempos(self) -> Respuesta:
        d = self.df[(self.df.Canal == "Delivery") & (self.df.get("TiempoEntregaMin", pd.Series(dtype=float)) > 0)] \
            if "TiempoEntregaMin" in self.df else pd.DataFrame()
        if d.empty:
            return Respuesta("Tiempos de entrega", limitaciones=["No hay registros de entregas a domicilio con tiempo informado en el filtro actual."])
        res = Respuesta("Tiempos de entrega (canal Delivery)")
        s = d.groupby("Sucursal").TiempoEntregaMin.agg(["mean", lambda x: (x > 45).mean() * 100]).rename(
            columns={"mean": "prom", "<lambda_0>": "pct45"}).sort_values("prom")
        res.hechos.append(f"Tiempo medio de entrega: {_n(d.TiempoEntregaMin.mean(), 1)} min; entregas de más de 45 min: {_p((d.TiempoEntregaMin > 45).mean() * 100)}.")
        res.hechos.append("Por sucursal: " + ", ".join(f"{k} {_n(v.prom, 1)} min" for k, v in s.iterrows()) + ".")
        res.interpretacion.append("En los canales Restaurante y Pickup el tiempo de entrega registrado es 0 porque no aplica; no se incluye en el promedio.")
        res.recomendaciones.append(f"Revisar la logística de {s.index[-1]} (mayor tiempo medio) y fijar una meta de entregas en menos de 45 minutos.")
        res.criterio = "Promedio de TiempoEntregaMin en transacciones Delivery con tiempo > 0."
        return res

    def _resumen(self) -> Respuesta:
        res = Respuesta("Principales hallazgos del período seleccionado")
        t = self._tendencia()
        res.hechos += t.hechos[:3]
        for f in (self._ciudades, self._sucursales, self._segmentos, self._descuentos, self._tiempos):
            try:
                r = f()
                res.hechos += r.hechos[:1]
                res.interpretacion += r.interpretacion[:1]
                res.recomendaciones += r.recomendaciones[:1]
            except Exception:  # noqa: BLE001
                continue
        res.criterio = "Síntesis de las reglas de tendencia, ciudades, sucursales, segmentos y descuentos."
        res.limitaciones.append("Para el detalle de cada tema, formule la pregunta específica.")
        return res

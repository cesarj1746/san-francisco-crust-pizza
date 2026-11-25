from __future__ import annotations

import pandas as pd
import streamlit as st

from sfcp import ui
from sfcp.asistente.motor import DESCRIPCION, NOMBRE, PREGUNTAS_SUGERIDAS, MotorReglas
from sfcp.asistente.proveedores import PROVEEDOR_ACTIVO
from vistas._comun import cabecera, contexto


def _mostrar(resp) -> None:
    st.markdown(PROVEEDOR_ACTIVO.redactar("", resp))
    if resp.tabla is not None and len(resp.tabla):
        with st.expander("Ver tabla de respaldo"):
            st.dataframe(resp.tabla, hide_index=True, width="stretch")


def render() -> None:
    ctx = contexto()
    cabecera("🧭 ASISTENTE INTELIGENTE DE DECISIONES COMERCIALES", ctx)
    st.markdown(f"<span class='sf-badge'>⚙️ {NOMBRE}</span><span class='sf-badge'>Sin internet</span>"
                "<span class='sf-badge'>Sin modelos generativos</span><span class='sf-badge'>Usa los filtros activos</span>",
                unsafe_allow_html=True)
    ui.nota(DESCRIPCION + " Las recomendaciones deben ser analizadas críticamente por el equipo antes de "
            "incorporarlas a sus conclusiones.")
    if ui.sin_datos(ctx.df):
        return
    motor = MotorReglas(ctx.df, ctx.prev, ctx.fecha_corte, periodo_txt=f"{ctx.f['inicio']:%d/%m/%Y}–{ctx.f['fin']:%d/%m/%Y}",
                        periodo_prev_txt=ctx.periodo_prev.texto() if ctx.periodo_prev else "",
                        filtros_txt=_filtros_txt(ctx.f))
    hist = st.session_state.setdefault("chat", [])

    st.markdown("**Preguntas sugeridas**")
    cols = st.columns(4)
    pendiente = None
    for i, q in enumerate(PREGUNTAS_SUGERIDAS):
        if cols[i % 4].button(q, key=f"sug_{i}", width="stretch"):
            pendiente = q
    c1, c2 = st.columns([1, 5])
    if c1.button("🗑️ Limpiar conversación"):
        st.session_state["chat"] = []
        st.rerun()
    escrita = st.chat_input("Escriba su pregunta comercial…")
    pregunta = escrita or pendiente
    if pregunta:
        hist.append({"q": pregunta, "f": _filtros_txt(ctx.f) or "sin filtros",
                     "per": f"{ctx.f['inicio']:%d/%m/%Y}–{ctx.f['fin']:%d/%m/%Y}"})

    for i, h in enumerate(hist):
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(h["q"])
            st.caption(f"Período {h['per']} · {h['f']}")
        with st.chat_message("assistant", avatar="🧭"):
            if "resp" in h:
                st.markdown(h["resp"])
                if h.get("tabla") is not None:
                    with st.expander("Ver tabla de respaldo"):
                        st.dataframe(h["tabla"], hide_index=True, width="stretch")
            else:
                r = motor.responder(h["q"])
                h["resp"] = PROVEEDOR_ACTIVO.redactar(h["q"], r)
                h["tabla"] = r.tabla
                _mostrar(r)
    if not hist:
        st.info("Elija una pregunta sugerida o escriba la suya. Ejemplos: «¿Qué sucursal tiene peor desempeño?», "
                "«¿Cómo afectan los descuentos?», «¿Qué segmento conviene impulsar?».")


def _filtros_txt(f: dict) -> str:
    partes = []
    for k, n in [("ciudad", "ciudad"), ("sucursal", "sucursal"), ("segmento", "segmento"), ("producto_etq", "producto")]:
        if f.get(k):
            partes.append(f"{n}: {', '.join(f[k][:3])}{'…' if len(f[k]) > 3 else ''}")
    return "; ".join(partes)


_ = pd

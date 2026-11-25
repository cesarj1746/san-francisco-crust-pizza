from __future__ import annotations

import streamlit as st

from sfcp import config, storage, ui
from vistas._comun import cabecera


def render() -> None:
    cabecera("🪪 Identificación del equipo")
    ui.aviso_nube()
    r = config.rutas()
    eq = storage.leer_equipo(r)
    st.markdown("Complete estos datos una sola vez. Se mostrarán en el encabezado de todas las secciones "
                "y se guardan en la carpeta de configuración (`config/equipo.json`).")
    with st.form("form_equipo"):
        c1, c2 = st.columns(2)
        numero = c1.text_input("Número de equipo", eq.get("numero_equipo", ""))
        fecha = c2.text_input("Fecha de entrega", eq.get("fecha_entrega", ""), placeholder="dd/mm/aaaa")
        integrantes = st.text_area("Integrantes (uno por línea)", "\n".join(eq.get("integrantes", [])), height=150)
        c1, c2 = st.columns(2)
        programa = c1.text_input("Programa", eq.get("programa", ""))
        asignatura = c2.text_input("Asignatura", eq.get("asignatura", ""))
        profesor = c1.text_input("Profesor/a", eq.get("profesor", ""))
        univ = c2.text_input("Universidad", eq.get("universidad", ""))
        if st.form_submit_button("💾 Guardar identificación", type="primary"):
            storage.guardar_equipo(r, {
                "numero_equipo": numero.strip(), "fecha_entrega": fecha.strip(),
                "integrantes": [x.strip() for x in integrantes.splitlines() if x.strip()],
                "programa": programa.strip(), "asignatura": asignatura.strip(),
                "profesor": profesor.strip(), "universidad": univ.strip()})
            st.success("Identificación guardada.")
            st.rerun()
    eq = storage.leer_equipo(r)
    if eq.get("numero_equipo") or eq.get("integrantes"):
        ui.seccion("Vista previa")
        st.markdown(f"**Equipo:** {eq.get('numero_equipo') or '—'}  \n"
                    f"**Integrantes:** {', '.join(eq.get('integrantes') or []) or '—'}  \n"
                    f"**Programa:** {eq.get('programa') or '—'}  \n**Asignatura:** {eq.get('asignatura') or '—'}  \n"
                    f"**Profesor/a:** {eq.get('profesor') or '—'}  \n**Universidad:** {eq.get('universidad') or '—'}  \n"
                    f"**Fecha de entrega:** {eq.get('fecha_entrega') or '—'}")

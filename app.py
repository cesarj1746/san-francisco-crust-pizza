"""San Francisco Crust Pizza — Sistema Inteligente de Información y Decisiones Comerciales.

Punto de entrada de Streamlit:  streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from sfcp import repo, storage, ui  # noqa: E402
from sfcp.config import APP_TITLE, APP_VERSION, rutas  # noqa: E402

st.set_page_config(page_title="San Francisco Crust Pizza · Decisiones Comerciales",
                   page_icon="🍕", layout="wide", initial_sidebar_state="expanded")
ui.estilos()

from vistas import (administracion, asistente, clientes, dashboard, equipo,  # noqa: E402
                    productos, sucursales, ventas)

paginas = [
    st.Page(dashboard.render, title="Dashboard ejecutivo", icon="📊", url_path="dashboard", default=True),
    st.Page(ventas.render, title="Análisis de ventas", icon="📈", url_path="ventas"),
    st.Page(productos.render, title="Análisis de productos", icon="🍕", url_path="productos"),
    st.Page(clientes.render, title="Análisis de clientes", icon="👥", url_path="clientes"),
    st.Page(sucursales.render, title="Análisis de sucursales", icon="🏪", url_path="sucursales"),
    st.Page(asistente.render, title="Asistente comercial", icon="🧭", url_path="asistente"),
    st.Page(administracion.render, title="Administración de bases", icon="🗄️", url_path="administracion"),
    st.Page(equipo.render, title="Identificación del equipo", icon="🪪", url_path="equipo"),
]
nav = st.navigation(paginas, position="sidebar")

try:
    datos = repo.obtener()
except Exception as e:  # noqa: BLE001
    storage.get_logger().exception("Error al cargar datos")
    ui.encabezado()
    st.error(f"No fue posible cargar las bases de datos: {e}")
    st.info("Vaya a «Administración de bases» para cargar o restaurar los archivos.")
    if nav.title in ("Administración de bases", "Identificación del equipo"):
        nav.run()
    st.stop()

st.session_state["_datos"] = datos
st.session_state["_filtros"] = ui.filtros_sidebar(datos.modelo, datos.productos)
st.sidebar.markdown("---")
st.sidebar.caption(f"{APP_TITLE} · v{APP_VERSION}\n\nDatos en: {rutas().root}")
nav.run()

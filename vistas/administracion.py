from __future__ import annotations

import io
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from sfcp import config, data, repo, storage, ui, validator
from sfcp.schema import ESQUEMAS, NOMBRES
from vistas._comun import cabecera

DERIVADAS = ["Periodo", "Año", "Mes", "Trimestre"]


def _a_xlsx(df: pd.DataFrame, tipo: str) -> bytes:
    req, opc, _ = ESQUEMAS[tipo]
    cols = [c for c in req + opc if c in df.columns]
    if tipo == "ventas":
        cols = [c for c in cols if c not in DERIVADAS]
        cols = cols[:2] + ["Año", "Mes", "Trimestre"] + cols[2:]
        df = df.assign(Año=df.Fecha.dt.year, Mes=df.Fecha.dt.month, Trimestre=df.Fecha.dt.quarter)
    extra = [c for c in df.columns if c not in cols and c not in DERIVADAS
             and c not in ("ProductoNombre", "Etiqueta")]
    buf = io.BytesIO()
    df[cols + extra].to_excel(buf, index=False, sheet_name="Sheet")
    return buf.getvalue()


def _mostrar_resultado(res: validator.Resultado) -> None:
    if res.errores:
        st.error("❌ El archivo NO fue aceptado. La base vigente no se modificó.")
        for e in res.errores:
            st.markdown(f"- 🔴 {e}")
    else:
        st.success("✅ Validación superada.")
    for a in res.advertencias:
        st.markdown(f"- 🟡 {a}")
    if res.info:
        info = {k: (v.strftime("%d/%m/%Y") if isinstance(v, pd.Timestamp) else
                    (f"${v:,.2f}" if isinstance(v, float) else v)) for k, v in res.info.items()}
        st.json(info, expanded=False)


def _flujo_carga(tipo: str, d) -> None:
    r = config.rutas()
    up = st.file_uploader(f"Seleccione el archivo de {NOMBRES[tipo].lower()} (.xlsx o .csv)",
                          type=["xlsx", "xls", "csv"], key=f"up_{tipo}")
    modo = "Sustituir"
    if tipo == "ventas":
        modo = st.radio("Modo de carga", ["Sustituir", "Agregar"], horizontal=True, key="modo_ventas",
                        captions=["Reemplaza toda la base de ventas vigente por el nuevo archivo.",
                                  "Añade las ventas nuevas a la base vigente (los VentaID no pueden repetirse)."])
    if up is None:
        return
    contenido = up.getvalue()
    try:
        bruto = data.leer_tabla(contenido, up.name)
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo leer el archivo: {e}")
        storage.registrar(r, "validacion", tipo, up.name, None, "RECHAZADO", f"Archivo ilegible: {e}")
        return
    if tipo == "ventas":
        if modo == "Agregar":
            vig = data.leer_tabla(r.archivo("ventas"))
            combinado = pd.concat([data.normalizar_columnas(vig, "ventas"),
                                   data.normalizar_columnas(bruto, "ventas")], ignore_index=True)
            res = validator.validar_ventas(combinado, d.clientes, d.productos)
        else:
            res = validator.validar_ventas(bruto, d.clientes, d.productos)
    elif tipo == "clientes":
        res = validator.validar_clientes(bruto, d.ventas)
    else:
        res = validator.validar_productos(bruto, d.ventas)
    st.markdown(f"**Vista previa** ({len(bruto):,} filas × {len(bruto.columns)} columnas)")
    st.dataframe(bruto.head(10), width="stretch", hide_index=True)
    _mostrar_resultado(res)
    clave = f"{tipo}_{up.name}_{len(contenido)}_{modo}"
    if not res.ok:
        if st.session_state.get("_rech") != clave:
            storage.registrar(r, "validacion", tipo, up.name, len(bruto), "RECHAZADO",
                              " | ".join(res.errores))
            st.session_state["_rech"] = clave
        return
    accion = "Agregar a la base de ventas" if modo == "Agregar" else f"Reemplazar {NOMBRES[tipo].lower()} vigente"
    if st.button(f"💾 {accion}", type="primary", key=f"btn_{tipo}"):
        if modo == "Agregar" or not up.name.lower().endswith(".xlsx"):
            binario = _a_xlsx(res.df, tipo)
        else:
            binario = contenido
        det = f"Modo: {modo}. " + " ".join(res.advertencias)[:300]
        respaldo = storage.guardar_archivo(r, tipo, binario, up.name, len(res.df), det)
        repo.invalidar()
        st.session_state["_msg_admin"] = (f"✅ {NOMBRES[tipo]} actualizada con {len(res.df):,} filas. "
                                          f"Respaldo de la versión anterior: {respaldo.name if respaldo else '—'}. "
                                          "Todos los indicadores y gráficos ya usan la nueva información.")
        st.rerun()


def render() -> None:
    cabecera("🗄️ Administración de bases de datos")
    ui.aviso_nube()
    if msg := st.session_state.pop("_msg_admin", None):
        st.success(msg)
    r = config.rutas()
    d = st.session_state.get("_datos")
    tabs = st.tabs(["Estado actual", "Cargar ventas", "Actualizar maestros", "Historial y errores",
                    "Respaldos", "Ubicación de datos"])
    with tabs[0]:
        filas = []
        for t, (interno, original) in config.ARCHIVOS.items():
            p = r.archivo(t)
            if p.exists():
                s = p.stat()
                df = {"ventas": d.ventas, "clientes": d.clientes, "productos": d.productos}[t] if d else None
                extra = ""
                if t == "ventas" and df is not None:
                    extra = f"{df.Fecha.min():%d/%m/%Y} – {df.Fecha.max():%d/%m/%Y}"
                filas.append({"Base": NOMBRES[t], "Archivo": interno, "Archivo original": original,
                              "Filas": len(df) if df is not None else None,
                              "Período": extra, "Última actualización": datetime.fromtimestamp(s.st_mtime),
                              "Tamaño (KB)": round(s.st_size / 1024, 1), "Ruta": str(p)})
            else:
                filas.append({"Base": NOMBRES[t], "Archivo": interno, "Archivo original": original,
                              "Filas": None, "Período": "NO ENCONTRADO", "Ruta": str(p)})
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                     column_config={"Última actualización": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")})
        if config.IS_WINDOWS and not config.is_cloud() and st.button("📂 Abrir carpeta de datos"):
            os.startfile(str(r.data))  # type: ignore[attr-defined]
        ui.nota("Para actualizar la información no es necesario modificar la aplicación: cargue el nuevo "
                "archivo en las pestañas siguientes. Antes de cada reemplazo se crea un respaldo automático.")
    with tabs[1]:
        st.markdown("El archivo debe tener las mismas columnas que la base original de ventas: "
                    + ", ".join(f"`{c}`" for c in ESQUEMAS["ventas"][0]) + ". Opcionales: "
                    + ", ".join(f"`{c}`" for c in ESQUEMAS["ventas"][1]) + ".")
        if d:
            _flujo_carga("ventas", d)
    with tabs[2]:
        st.markdown("Actualice primero los maestros si la nueva base de ventas incluye clientes o productos nuevos.")
        sub = st.radio("Maestro", ["clientes", "productos"], horizontal=True,
                       format_func=lambda x: NOMBRES[x], key="maestro_sel")
        st.markdown("Columnas obligatorias: " + ", ".join(f"`{c}`" for c in ESQUEMAS[sub][0]))
        if d:
            _flujo_carga(sub, d)
    with tabs[3]:
        h = storage.leer_historial(r)
        if h:
            hd = pd.DataFrame(h)
            solo_err = st.checkbox("Mostrar solo validaciones rechazadas")
            if solo_err:
                hd = hd[hd.resultado == "RECHAZADO"]
            st.dataframe(hd, hide_index=True, width="stretch", height=420)
        else:
            st.info("Aún no hay movimientos registrados.")
    with tabs[4]:
        resp = storage.listar_respaldos(r)
        if not resp:
            st.info("No hay respaldos todavía. Se crean automáticamente antes de cada reemplazo.")
        else:
            rd = pd.DataFrame(resp)
            st.dataframe(rd[["tipo", "archivo", "fecha", "tamano_kb"]].rename(columns={
                "tipo": "Base", "archivo": "Respaldo", "fecha": "Fecha", "tamano_kb": "Tamaño (KB)"}),
                hide_index=True, width="stretch",
                column_config={"Fecha": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss")})
            tipo_r = st.selectbox("Base a recuperar", list(config.ARCHIVOS), format_func=lambda t: NOMBRES[t],
                                  key="rest_tipo")
            opciones = {f"{x['archivo']} ({x['fecha']:%d/%m/%Y %H:%M})": x for x in resp if x["tipo"] == tipo_r}
            if not opciones:
                st.info("No hay respaldos de esta base.")
                return
            elegido = st.selectbox("Respaldo a recuperar (el más reciente aparece primero)", list(opciones))
            x = opciones[elegido]
            st.warning(f"Se reemplazará la base vigente de **{NOMBRES[x['tipo']]}** por «{x['archivo']}». "
                       "La versión vigente se respaldará antes.")
            if st.checkbox("Confirmo que deseo restaurar este respaldo", key="conf_rest"):
                if st.button("♻️ Restaurar respaldo", type="primary"):
                    try:
                        dfp = data.leer_tabla(x["ruta"])
                        vref = d.ventas if d and x["tipo"] != "ventas" else None
                        if x["tipo"] == "ventas":
                            res = validator.validar_ventas(dfp, d.clientes if d else None, d.productos if d else None)
                        elif x["tipo"] == "clientes":
                            res = validator.validar_clientes(dfp, vref)
                        else:
                            res = validator.validar_productos(dfp, vref)
                        if not res.ok:
                            _mostrar_resultado(res)
                        else:
                            storage.restaurar(r, x["tipo"], x["ruta"])
                            repo.invalidar()
                            st.session_state["_msg_admin"] = f"✅ Respaldo restaurado: {x['archivo']}"
                            st.session_state.pop("conf_rest", None)
                            st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"No se pudo restaurar: {e}")
    with tabs[5]:
        st.markdown(f"**Ubicación actual:** `{r.root}`")
        st.code("\n".join(str(c) for c in r.carpetas()), language=None)
        if config.is_cloud():
            st.info("En la versión pública el almacenamiento lo define el servidor.")
        else:
            nueva = st.text_input("Nueva ubicación de almacenamiento", placeholder=r"D:\Datos\SanFranciscoCrustPizza")
            copiar = st.checkbox("Copiar las bases, respaldos y configuración actuales a la nueva ubicación", value=True)
            if st.button("Cambiar ubicación") and nueva:
                try:
                    destino = config.Rutas(Path(nueva))
                    if not config.is_writable(destino.root):
                        raise PermissionError("No hay permisos de escritura en esa carpeta.")
                    if copiar:
                        storage.migrar(r, destino)
                    config.set_root(destino.root)
                    storage.initialize(destino)
                    storage.registrar(destino, "ubicacion", "config", str(destino.root), None, "OK",
                                      f"Antes: {r.root}")
                    repo.invalidar()
                    st.success(f"Ubicación cambiada a {destino.root}.")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"No se pudo cambiar la ubicación: {e}")
            if os.environ.get("SFCP_HOME"):
                st.caption("La variable de entorno SFCP_HOME tiene prioridad sobre esta configuración.")


_ = (subprocess, sys)

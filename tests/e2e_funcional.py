"""Prueba funcional de extremo a extremo con un navegador real (Playwright + Chrome).

Uso:  python tests/e2e_funcional.py <url> <carpeta_evidencias> <carpeta_archivos_prueba>
Requiere la aplicación en ejecución. Genera capturas y un registro JSON de resultados.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL, EVID, ARCH = sys.argv[1].rstrip("/"), Path(sys.argv[2]), Path(sys.argv[3])
EVID.mkdir(parents=True, exist_ok=True)
resultados = []


def paso(nombre, ok, detalle=""):
    resultados.append({"prueba": nombre, "resultado": "OK" if ok else "FALLA", "detalle": detalle})
    print(("✔" if ok else "✘"), nombre, detalle)


def esperar(pg, extra=800):
    pg.wait_for_timeout(600)
    try:
        pg.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=90000)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(extra)


def tarjeta(pg, titulo):
    t = pg.locator(".sf-card").filter(has_text=re.compile(rf"^{titulo}", re.I)).first
    return t.locator(".v").inner_text()


def elegir(pg, etiqueta, opcion, multi=False):
    pg.locator("[data-testid='stSidebar']").get_by_role("combobox", name=etiqueta).click()
    pg.wait_for_timeout(400)
    if multi:
        pg.keyboard.type(opcion.split(" · ")[-1])
        pg.wait_for_timeout(400)
    pg.get_by_role("option", name=opcion, exact=True).click()
    if multi:
        pg.keyboard.press("Escape")
    esperar(pg)


def opciones(pg, etiqueta):
    pg.locator("[data-testid='stSidebar']").get_by_role("combobox", name=etiqueta).click()
    pg.wait_for_timeout(500)
    ops = [o for o in pg.get_by_role("option").all_inner_texts() if o != "Select all"]
    pg.keyboard.press("Escape")
    return ops


def ir(pg, ruta):
    pg.goto(f"{URL}/{ruta}", wait_until="domcontentloaded")
    esperar(pg, 1500)


def captura(pg, nombre):
    pg.screenshot(path=str(EVID / f"{nombre}.png"), full_page=True)


def errores(pg):
    return pg.locator("[data-testid='stException']").count()


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1500, "height": 1400})
    t0 = time.time()
    ir(pg, "")
    paso("Inicio de la aplicación y carga del dashboard", tarjeta(pg, "Ventas totales") == "$1,357,882",
         f"Ventas totales mostradas: {tarjeta(pg, 'Ventas totales')} (tiempo {time.time() - t0:.1f}s)")
    vals = {k: tarjeta(pg, k) for k in ["Ventas totales", "Utilidad bruta", "Margen bruto", "Ticket promedio",
                                        "Clientes", "Transacciones"]}
    paso("Seis indicadores visibles", vals == {"Ventas totales": "$1,357,882", "Utilidad bruta": "$813,714",
                                                "Margen bruto": "59.9%", "Ticket promedio": "$29.58",
                                                "Clientes": "1,000", "Transacciones": "45,900"}, json.dumps(vals, ensure_ascii=False))
    try:
        pg.wait_for_function("document.querySelectorAll('[data-testid=stPlotlyChart]').length >= 5", timeout=60000)
    except Exception:  # noqa: BLE001
        pass
    n_graf = pg.locator("[data-testid='stPlotlyChart']").count()
    paso("Gráficos del dashboard renderizados", n_graf >= 5, f"{n_graf} gráficos")
    captura(pg, "01_dashboard_inicial")

    elegir(pg, "Fecha", "Año 2025")
    v25 = tarjeta(pg, "Ventas totales")
    delta = pg.locator(".sf-card").first.locator(".d").inner_text()
    paso("Filtro de fecha (Año 2025) y variación vs 2024", v25 == "$574,105" and "-26.8%" in delta, f"{v25} · {delta}")
    captura(pg, "02_filtro_anio_2025")

    elegir(pg, "Ciudad", "Dallas", multi=True)
    ops = opciones(pg, "Sucursal")
    paso("Coherencia ciudad → sucursal", sorted(ops) == ["Dallas Downtown", "Dallas North"], ", ".join(ops))
    vd = tarjeta(pg, "Ventas totales")
    paso("Filtro combinado año + ciudad", vd == "$132,795", vd)
    elegir(pg, "Segmento de cliente", "Corporativo", multi=True)
    elegir(pg, "Producto", "P013 · Mexicana M", multi=True)
    paso("Filtros de segmento y producto aplicados", errores(pg) == 0, f"Ventas: {tarjeta(pg, 'Ventas totales')}")
    captura(pg, "03_filtros_combinados")
    pg.locator(".sf-header").first.click()  # cierra cualquier lista desplegable abierta
    pg.wait_for_timeout(500)
    pg.get_by_role("button", name=re.compile("Limpiar filtros")).click()
    esperar(pg)
    paso("Botón limpiar filtros", tarjeta(pg, "Ventas totales") == "$1,357,882", tarjeta(pg, "Ventas totales"))

    for ruta, nombre in [("ventas", "Análisis de ventas"), ("productos", "Análisis de productos"),
                         ("clientes", "Análisis de clientes"), ("sucursales", "Análisis de sucursales")]:
        ir(pg, ruta)
        g = pg.locator("[data-testid='stPlotlyChart']").count()
        paso(f"Sección {nombre} sin errores", errores(pg) == 0 and g > 0, f"{g} gráficos")
        captura(pg, f"04_{ruta}")
    ir(pg, "sucursales")
    paso("Mejor/peor sucursal (multicriterio)", pg.get_by_text("Austin South").count() > 0 and
         pg.get_by_text("Dallas Downtown").count() > 0, "Austin South / Dallas Downtown")

    ir(pg, "asistente")
    pg.get_by_role("button", name="¿Cuál es la sucursal con mejor desempeño?").click()
    esperar(pg, 1500)
    txt = pg.locator("[data-testid='stChatMessage']").last.inner_text()
    paso("Asistente responde con cifras verificables", "Austin South" in txt and "$174,510" in txt and "Criterio" in txt,
         txt[:160].replace("\n", " "))
    pg.get_by_test_id("stChatInputTextArea").fill("¿Qué ciudad necesita atención comercial?")
    pg.keyboard.press("Enter")
    esperar(pg, 1500)
    txt = pg.locator("[data-testid='stChatMessage']").last.inner_text()
    paso("Asistente: pregunta escrita libremente", "Dallas" in txt, txt[:120].replace("\n", " "))
    captura(pg, "05_asistente")

    ir(pg, "equipo")
    pg.get_by_label("Número de equipo").fill("99")
    pg.get_by_label("Integrantes (uno por línea)").fill("Integrante de prueba A\nIntegrante de prueba B")
    pg.get_by_role("button", name=re.compile("Guardar identificación")).click()
    esperar(pg, 1200)
    paso("Identificación del equipo guardada y visible en encabezado",
         pg.locator(".sf-header").first.inner_text().find("Equipo 99") >= 0, pg.locator(".sf-header").first.inner_text().replace("\n", " ")[-80:])

    # --- Administración: archivo inválido ----------------------------------------
    ir(pg, "administracion")
    pg.get_by_role("tab", name="Cargar ventas").click()
    pg.locator("[data-testid='stFileUploaderDropzoneInput']").first.set_input_files(str(ARCH / "ventas_invalida.xlsx"))
    esperar(pg, 2000)
    rech = pg.get_by_text("El archivo NO fue aceptado").count() > 0
    paso("Validación rechaza archivo con errores", rech, "Mensaje de rechazo mostrado")
    captura(pg, "06_validacion_rechazo")
    ir(pg, "")
    paso("Base vigente intacta tras rechazo", tarjeta(pg, "Ventas totales") == "$1,357,882", tarjeta(pg, "Ventas totales"))

    # --- Administración: reemplazo válido ----------------------------------------
    ir(pg, "administracion")
    pg.get_by_role("tab", name="Cargar ventas").click()
    pg.locator("[data-testid='stFileUploaderDropzoneInput']").first.set_input_files(str(ARCH / "ventas_solo_2025.xlsx"))
    esperar(pg, 2500)
    pg.get_by_role("button", name=re.compile("Reemplazar")).click()
    esperar(pg, 3000)
    ok_msg = pg.get_by_text("Todos los indicadores y gráficos ya usan la nueva información").count() > 0
    captura(pg, "07_reemplazo_ventas")
    ir(pg, "")
    v = tarjeta(pg, "Ventas totales")
    paso("Reemplazo de la base de ventas y actualización automática", ok_msg and v == "$574,105", v)
    captura(pg, "08_dashboard_tras_reemplazo")

    # --- Respaldos y restauración -------------------------------------------------
    ir(pg, "administracion")
    pg.get_by_role("tab", name="Respaldos").click()
    esperar(pg)
    paso("Respaldo automático creado", pg.get_by_text(re.compile(r"_ventas\.xlsx")).count() > 0, "")
    pg.get_by_role("tab", name="Respaldos").click()
    pg.get_by_text("Confirmo que deseo restaurar este respaldo").click()
    esperar(pg)
    pg.get_by_role("button", name=re.compile("Restaurar respaldo")).click()
    esperar(pg, 3000)
    captura(pg, "09_restauracion")
    ir(pg, "")
    v = tarjeta(pg, "Ventas totales")
    paso("Recuperación de respaldo anterior", v == "$1,357,882", v)
    ir(pg, "administracion")
    pg.get_by_role("tab", name="Historial y errores").click()
    esperar(pg)
    captura(pg, "10_historial")
    paso("Historial de cargas registrado", errores(pg) == 0, "")
    b.close()

(EVID / "resultados_e2e.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
fallas = [r for r in resultados if r["resultado"] != "OK"]
print(f"\n{len(resultados) - len(fallas)}/{len(resultados)} pruebas OK")
sys.exit(1 if fallas else 0)

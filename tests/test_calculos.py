"""Pruebas de datos: la aplicación (sfcp.kpis) se compara contra cálculos
independientes hechos directamente con openpyxl + Python puro (sin pandas ni
módulos de la aplicación)."""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfcp import data, kpis  # noqa: E402

SEM = RAIZ / "datos_iniciales"


def _filas(nombre):
    wb = openpyxl.load_workbook(SEM / nombre, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    cab = next(it)
    return [dict(zip(cab, r)) for r in it]


@pytest.fixture(scope="module")
def crudo():
    return _filas("ventas.xlsx"), _filas("clientes.xlsx"), _filas("productos.xlsx")


@pytest.fixture(scope="module")
def modelo():
    v = data.preparar_ventas(data.leer_tabla(SEM / "ventas.xlsx"))
    c = data.preparar_clientes(data.leer_tabla(SEM / "clientes.xlsx"))
    p = data.preparar_productos(data.leer_tabla(SEM / "productos.xlsx"))
    return data.construir_modelo(v, c, p)


def _indep(filas):
    vn = sum(r["VentaNeta"] for r in filas)
    ub = sum(r["UtilidadBruta"] for r in filas)
    tx = len({r["VentaID"] for r in filas})
    return {"ventas": vn, "utilidad": ub, "margen": ub / vn * 100, "ticket": vn / tx,
            "clientes": len({r["ClienteID"] for r in filas}), "transacciones": tx,
            "unidades": sum(r["Cantidad"] for r in filas)}


def _cmp(app, ind):
    for k, v in ind.items():
        assert app[k] == pytest.approx(v, rel=1e-9, abs=1e-6), k


def test_kpis_globales(crudo, modelo):
    _cmp(kpis.resumen(modelo), _indep(crudo[0]))


def test_cifras_de_referencia(modelo):
    a = kpis.resumen(modelo)
    assert round(a["ventas"], 2) == 1357881.66
    assert round(a["utilidad"], 2) == 813713.76
    assert a["transacciones"] == 45900 and a["clientes"] == 1000


def test_margen_ponderado_no_promedio_simple(modelo):
    simple = (modelo.UtilidadBruta / modelo.VentaNeta).mean() * 100
    pond = kpis.resumen(modelo)["margen"]
    assert pond == pytest.approx(modelo.UtilidadBruta.sum() / modelo.VentaNeta.sum() * 100)
    assert abs(simple - pond) > 1e-6  # demuestra que son distintos


@pytest.mark.parametrize("anio", [2024, 2025])
def test_filtro_anio(crudo, modelo, anio):
    filas = [r for r in crudo[0] if r["Fecha"].year == anio]
    _cmp(kpis.resumen(modelo[modelo.Año == anio]), _indep(filas))


def test_filtros_combinados(crudo, modelo):
    seg = {r["ClienteID"]: r["Segmento"] for r in crudo[1]}
    ini, fin = datetime(2025, 3, 1), datetime(2025, 8, 31)
    filas = [r for r in crudo[0] if r["Ciudad"] in ("Dallas", "Austin") and seg[r["ClienteID"]] == "Familiar"
             and r["ProductoID"] in ("P001", "P013", "P031") and ini <= r["Fecha"] <= fin]
    f = {"inicio": pd.Timestamp(ini), "fin": pd.Timestamp(fin), "ciudad": ["Dallas", "Austin"], "sucursal": [],
         "segmento": ["Familiar"], "producto": ["P001", "P013", "P031"]}
    from sfcp.ui import aplicar
    _cmp(kpis.resumen(aplicar(modelo, f)), _indep(filas))


def test_por_sucursal_suma_total_sin_duplicar(crudo, modelo):
    g = kpis.por(modelo, "Sucursal")
    assert g.ventas.sum() == pytest.approx(sum(r["VentaNeta"] for r in crudo[0]))
    assert g.transacciones.sum() == 45900          # cada venta en una sola sucursal
    ind = defaultdict(float)
    for r in crudo[0]:
        ind[r["Sucursal"]] += r["VentaNeta"]
    for s in g.itertuples():
        assert s.ventas == pytest.approx(ind[s.Sucursal])


def test_union_no_duplica_filas(crudo, modelo):
    assert len(modelo) == len(crudo[0])


def test_por_producto_y_segmento(crudo, modelo):
    seg = {r["ClienteID"]: r["Segmento"] for r in crudo[1]}
    ind = defaultdict(lambda: [0.0, 0.0, set()])
    for r in crudo[0]:
        x = ind[seg[r["ClienteID"]]]
        x[0] += r["VentaNeta"]; x[1] += r["UtilidadBruta"]; x[2].add(r["ClienteID"])
    for s in kpis.por(modelo, "Segmento").itertuples():
        assert s.ventas == pytest.approx(ind[s.Segmento][0])
        assert s.margen == pytest.approx(ind[s.Segmento][1] / ind[s.Segmento][0] * 100)
        assert s.clientes == len(ind[s.Segmento][2])
    u = defaultdict(int)
    for r in crudo[0]:
        u[r["ProductoID"]] += r["Cantidad"]
    for s in kpis.por(modelo, "ProductoID").itertuples():
        assert s.unidades == u[s.ProductoID]


def test_periodo_anterior():
    pa = kpis.periodo_anterior(pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31"), pd.Timestamp("2024-01-01"))
    assert (pa.inicio, pa.fin) == (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"))
    assert kpis.periodo_anterior(pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-28"), pd.Timestamp("2024-01-01")) is None
    pa = kpis.periodo_anterior(pd.Timestamp("2025-03-10"), pd.Timestamp("2025-03-19"), pd.Timestamp("2024-01-01"))
    assert (pa.inicio, pa.fin) == (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-03-09"))


def test_clientes_desde_ventas(crudo, modelo):
    cl = kpis.clientes_desde_ventas(modelo, modelo.Fecha.max())
    n = defaultdict(int)
    for r in crudo[0]:
        n[r["ClienteID"]] += 1
    assert dict(zip(cl.ClienteID, cl.compras)) == dict(n)


def test_nps():
    assert kpis.nps(pd.Series([10, 9, 8, 7, 6, 0])) == pytest.approx((2 / 6 - 2 / 6) * 100)
    assert pd.isna(kpis.nps(pd.Series([], dtype=float)))

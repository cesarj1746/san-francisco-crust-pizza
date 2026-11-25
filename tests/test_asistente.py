"""El asistente debe: reconocer intenciones, usar cifras iguales a las del
dashboard, respetar filtros y reconocer cuando no hay datos suficientes."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfcp import data, kpis  # noqa: E402
from sfcp.asistente.motor import PREGUNTAS_SUGERIDAS, MotorReglas  # noqa: E402


@pytest.fixture(scope="module")
def m():
    s = RAIZ / "datos_iniciales"
    v = data.preparar_ventas(data.leer_tabla(s / "ventas.xlsx"))
    c = data.preparar_clientes(data.leer_tabla(s / "clientes.xlsx"))
    p = data.preparar_productos(data.leer_tabla(s / "productos.xlsx"))
    return data.construir_modelo(v, c, p)


ESPERADO = {
    "¿Cuál es la sucursal con mejor desempeño?": "sucursales",
    "¿Qué productos generan mayor utilidad?": "productos_utilidad",
    "¿Qué segmento representa una oportunidad de crecimiento?": "segmentos",
    "¿Qué ciudad necesita atención comercial?": "ciudades",
    "¿Qué productos deberían revisarse?": "productos_revisar",
    "¿Cómo mejorar el ticket promedio?": "ticket",
    "¿Qué acciones pueden incrementar la rentabilidad?": "rentabilidad",
    "¿Cuáles son los principales hallazgos?": "resumen",
    "¿Cómo están afectando los descuentos?": "descuentos",
    "¿Cuál es la tendencia de las ventas?": "tendencia",
    "¿Qué clientes debemos recuperar?": "recuperacion",
    "¿Qué canal de venta funciona mejor?": "canales",
}


@pytest.mark.parametrize("q", PREGUNTAS_SUGERIDAS)
def test_intenciones_y_sin_errores(m, q):
    mo = MotorReglas(m[m.Año == 2025], m[m.Año == 2024], m.Fecha.max())
    r = mo.responder(q)
    assert r.intencion == ESPERADO[q]
    assert r.hechos and r.criterio


def test_cifras_coinciden_con_dashboard(m):
    df = m[m.Año == 2025]
    r = MotorReglas(df, m[m.Año == 2024], m.Fecha.max()).responder("¿Cuál es la sucursal con mejor desempeño?")
    rk = kpis.ranking_sucursales(df, m[m.Año == 2024])
    assert rk.iloc[0].Sucursal in r.hechos[0]
    assert f"${rk.iloc[0].ventas:,.0f}" in r.hechos[0]


def test_respeta_filtros(m):
    df = m[m.Ciudad == "Houston"]
    r = MotorReglas(df, None, m.Fecha.max()).responder("mejor sucursal")
    texto = " ".join(r.hechos)
    assert "Houston" in texto and "Dallas" not in texto


def test_reconoce_datos_insuficientes(m):
    r = MotorReglas(m[m.Sucursal == "SA North"], None, m.Fecha.max()).responder("¿Cuál es la mejor sucursal?")
    assert r.limitaciones and not r.hechos
    r = MotorReglas(m.iloc[0:0], None, m.Fecha.max()).responder("ventas")
    assert "Sin datos" in r.titulo


def test_pregunta_no_reconocida(m):
    r = MotorReglas(m, None, m.Fecha.max()).responder("¿Quién ganó el partido?")
    assert r.intencion == "" and "No identifiqué" in r.titulo


def test_no_se_presenta_como_generativo():
    from sfcp.asistente import motor
    assert "reglas" in motor.NOMBRE.lower() or "sin modelos generativos" in motor.DESCRIPCION.lower()
    _ = pd

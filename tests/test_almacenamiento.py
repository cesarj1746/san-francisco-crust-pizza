"""Pruebas de carpetas, validación, respaldos y restauración (sin interfaz)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfcp import config, data, storage, validator  # noqa: E402


@pytest.fixture()
def rutas(tmp_path, monkeypatch):
    monkeypatch.setenv("SFCP_HOME", str(tmp_path / "SFCP"))
    r = config.rutas()
    storage.initialize(r)
    return r


@pytest.fixture(scope="module")
def bases():
    s = RAIZ / "datos_iniciales"
    return (data.leer_tabla(s / "ventas.xlsx"), data.leer_tabla(s / "clientes.xlsx"),
            data.leer_tabla(s / "productos.xlsx"))


def test_crea_estructura(rutas):
    for c in rutas.carpetas():
        assert c.is_dir(), c
    for t in ("ventas", "clientes", "productos"):
        assert rutas.archivo(t).exists()
    originales = list((rutas.respaldos / "originales").glob("*.xlsx"))
    assert {p.name for p in originales} == {v[1] for v in config.ARCHIVOS.values()}


def test_inicializar_no_sobrescribe(rutas):
    p = rutas.archivo("ventas")
    p.write_bytes(b"x")
    storage.initialize(rutas)
    assert p.read_bytes() == b"x"


def test_bases_originales_validas(bases):
    v, c, p = bases
    assert validator.validar_ventas(v, c, p).ok
    assert validator.validar_clientes(c, v).ok
    assert validator.validar_productos(p, v).ok


@pytest.mark.parametrize("dano,mensaje", [
    (lambda d: d.drop(columns=["VentaNeta"]), "Faltan columnas"),
    (lambda d: pd.concat([d, d.head(3)]), "duplicad"),
    (lambda d: d.assign(Fecha=d.Fecha.astype(str).where(d.index > 2, "no-es-fecha")), "fechas no válidas"),
    (lambda d: d.assign(ClienteID=d.ClienteID.where(d.index > 0, "C99999")), "no existen en el maestro de clientes"),
    (lambda d: d.assign(ProductoID=d.ProductoID.where(d.index > 0, "P999")), "no existen en el maestro de productos"),
    (lambda d: d.assign(Cantidad=d.Cantidad.astype(object).where(d.index > 0, "tres")), "no numéricos"),
    (lambda d: d.assign(VentaID=d.VentaID.where(d.index > 0, None)), "sin VentaID"),
])
def test_validacion_rechaza(bases, dano, mensaje):
    v, c, p = bases
    res = validator.validar_ventas(dano(v.copy()), c, p)
    assert not res.ok
    assert any(mensaje in e for e in res.errores), res.errores


def test_maestro_que_rompe_relaciones(bases):
    v, c, p = bases
    assert not validator.validar_clientes(c.iloc[10:], v).ok
    assert not validator.validar_productos(p.iloc[1:], v).ok


def test_reemplazo_respaldo_y_restauracion(rutas, bases):
    v, c, p = bases
    original = rutas.archivo("ventas").read_bytes()
    nueva = v[pd.to_datetime(v.Fecha).dt.year == 2025]
    buf = io.BytesIO()
    nueva.to_excel(buf, index=False)
    res = validator.validar_ventas(nueva, c, p)
    assert res.ok
    respaldo = storage.guardar_archivo(rutas, "ventas", buf.getvalue(), "ventas_2025.xlsx", len(nueva))
    assert respaldo.exists() and respaldo.read_bytes() == original
    assert len(data.leer_tabla(rutas.archivo("ventas"))) == len(nueva)
    storage.restaurar(rutas, "ventas", str(respaldo))
    assert rutas.archivo("ventas").read_bytes() == original
    h = storage.leer_historial(rutas)
    acciones = [x["accion"] for x in h]
    assert "carga" in acciones and "restauracion" in acciones and acciones.count("respaldo") >= 2
    assert len(storage.listar_respaldos(rutas, "ventas")) >= 3  # 2 respaldos + original


def test_equipo(rutas):
    storage.guardar_equipo(rutas, {"numero_equipo": "7", "integrantes": ["Ana", "Luis"]})
    e = storage.leer_equipo(rutas)
    assert e["numero_equipo"] == "7" and e["integrantes"] == ["Ana", "Luis"]


def test_cambio_de_ubicacion(rutas, tmp_path, monkeypatch):
    monkeypatch.delenv("SFCP_HOME")
    monkeypatch.setattr(config, "pointer_file", lambda: tmp_path / "ptr.json")
    destino = config.Rutas(tmp_path / "otra")
    storage.migrar(rutas, destino)
    config.set_root(destino.root)
    assert config.get_root() == destino.root
    assert destino.archivo("ventas").exists()

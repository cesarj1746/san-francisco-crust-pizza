"""Interfaz para conectar en una segunda etapa un modelo generativo (API o local)
sin modificar el dashboard ni el motor de reglas.

Diseño:
    pregunta ──► MotorReglas (calcula HECHOS verificables con kpis.py)
                    │
                    ├─► Respuesta estructurada (lo que se usa hoy)
                    └─► ProveedorRedaccion.redactar(pregunta, respuesta)   (futuro, opcional)

El proveedor generativo NUNCA calcula cifras: recibe los hechos ya calculados y
solo los redacta. Así se conserva la trazabilidad de cada número.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProveedorRedaccion(ABC):
    nombre: str = "base"

    @abstractmethod
    def disponible(self) -> bool: ...

    @abstractmethod
    def redactar(self, pregunta: str, respuesta) -> str:
        """Devuelve un texto redactado a partir de una Respuesta del motor de reglas."""


class SinProveedor(ProveedorRedaccion):
    """Proveedor por defecto de la versión 1: no usa ningún modelo generativo."""
    nombre = "ninguno (solo motor local de reglas)"

    def disponible(self) -> bool:
        return False

    def redactar(self, pregunta: str, respuesta) -> str:
        return respuesta.markdown()


# Ejemplo de extensión futura (no activo):
#
# class ProveedorAPI(ProveedorRedaccion):
#     nombre = "modelo generativo vía API"
#     def __init__(self, clave_api: str, modelo: str): ...
#     def disponible(self): return bool(self.clave_api)
#     def redactar(self, pregunta, respuesta):
#         prompt = ("Redacta en español, sin añadir cifras nuevas, esta respuesta: "
#                   + respuesta.markdown())
#         return llamar_api(prompt)
#
# class ProveedorLocal(ProveedorRedaccion):   # p. ej. Ollama en http://localhost:11434
#     ...

PROVEEDOR_ACTIVO: ProveedorRedaccion = SinProveedor()

# San Francisco Crust Pizza — Sistema Inteligente de Información y Decisiones Comerciales

Aplicación web desarrollada en Python con Streamlit para la Dirección General de San Francisco Crust Pizza. Es la actividad 1 de la asignatura Sistemas de Información para la Toma de Decisiones Comerciales (UNIR).

**Aplicación publicada:** https://sf-crust-pizza-abv.streamlit.app/

## Funcionalidades

- Dashboard ejecutivo con 6 indicadores: ventas, utilidad bruta, margen bruto, ticket promedio, clientes y transacciones.
- Análisis de ventas, productos, clientes y sucursales con gráficos interactivos.
- Filtros globales por fecha, ciudad, sucursal, segmento de cliente y producto.
- Administración de bases: carga de una nueva base de ventas o de los maestros, con validación, respaldo automático y restauración.
- Asistente de decisiones comerciales basado en reglas, que responde con cifras verificables.
- Identificación del equipo, que se muestra en el encabezado.

## Estructura del código

```
app.py                    Punto de entrada (navegación y filtros globales)
sfcp/
  config.py               Rutas y configuración
  storage.py              Carpetas, respaldos, restauración, historial, identificación del equipo
  schema.py               Estructura esperada de las tres bases
  data.py                 Lectura, normalización y modelo integrado ventas + maestros
  validator.py            Validaciones antes de aceptar un archivo
  kpis.py                 Fórmulas oficiales (única fuente de cálculo)
  repo.py                 Caché de datos (se recarga cuando cambia un archivo)
  ui.py                   Estilos, tarjetas de indicadores, gráficos y filtros
  asistente/motor.py      Motor de reglas del asistente comercial
  asistente/proveedores.py  Interfaz para conectar un modelo generativo en el futuro
vistas/                   Una página por sección
datos_iniciales/          Bases de la empresa: ventas.xlsx, clientes.xlsx y productos.xlsx
.streamlit/config.toml    Tema visual
tests/                    Pruebas de cálculo, validación, respaldos y asistente
docs/                     Guía de publicación en Streamlit Community Cloud
```

## Cómo se publica

El código está en este repositorio de GitHub. Streamlit Community Cloud (plan gratuito) lo toma de la rama `main`, instala `requirements.txt` y ejecuta `app.py`. Cada cambio que se sube a `main` vuelve a publicar la aplicación automáticamente. Los detalles están en `docs/PUBLICACION_STREAMLIT_CLOUD.md`.

## Ejecutar en una computadora (desarrollo)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q tests
```

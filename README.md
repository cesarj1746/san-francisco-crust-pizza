# San Francisco Crust Pizza — Sistema Inteligente de Información y Decisiones Comerciales

Aplicación web local en Python y Streamlit para la Dirección General de San Francisco Crust Pizza. Incluye:

- un dashboard ejecutivo;
- análisis de ventas, productos, clientes y sucursales;
- filtros globales;
- administración de bases con validación, respaldos y restauración;
- un motor local de recomendaciones comerciales basado en reglas.

## Estructura del código

```
app.py                   Punto de entrada de Streamlit (navegación y filtros globales)
launcher.py              Lanzador de escritorio (SanFranciscoCrustPizza.exe)
sfcp/
  config.py              Rutas y configuración (código separado de los datos)
  storage.py             Carpetas, respaldos, restauración, historial, identificación del equipo
  schema.py              Estructura esperada de las tres bases
  data.py                Lectura y normalización, y modelo integrado ventas + maestros
  validator.py           Validaciones antes de aceptar un archivo
  kpis.py                Fórmulas oficiales (única fuente de cálculo)
  repo.py                Caché de datos: se recarga cuando cambia un archivo
  ui.py                  Estilos, tarjetas KPI, gráficos Plotly y filtros
  asistente/motor.py     Motor local de reglas (sin IA generativa)
  asistente/proveedores.py  Interfaz para conectar un modelo generativo en el futuro
vistas/                  Una página por sección (dashboard, ventas, productos, clientes,
                         sucursales, asistente, administración, equipo)
datos_iniciales/         Bases originales de la empresa (se copian al primer arranque)
tests/                   Pruebas de cálculo, almacenamiento, asistente y prueba funcional e2e
SanFranciscoCrustPizza.spec  Configuración de PyInstaller (modo onedir)
instalador.nsi           Script del instalador de Windows (NSIS)
```

## Ejecutar en modo desarrollo

```bash
pip install -r requirements.txt
streamlit run app.py
```

La carpeta de datos se resuelve en este orden:

1. La variable `SFCP_HOME`, si está definida.
2. La ubicación elegida en la app.
3. Si no hay ninguna de las dos, la ubicación predeterminada: `C:\SanFranciscoCrustPizza` en Windows (o `%LOCALAPPDATA%\SanFranciscoCrustPizza\datos` si no hay permisos), y `./almacenamiento` en servidor.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q tests          # 43 pruebas: cálculos, validación, respaldos, asistente
streamlit run app.py &                              # y luego:
python tests/e2e_funcional.py http://localhost:8501 evidencias archivos_prueba
```

## Compilar el ejecutable de Windows

Consulte `docs/COMPILACION_WINDOWS.md`.

## Publicación futura en internet

Consulte `docs/PUBLICACION_STREAMLIT_CLOUD.md`.

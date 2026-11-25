# Compilación del ejecutable de Windows

## Opción A: en una PC con Windows 10/11 (recomendada para recompilar)

1. Instale Python 3.13 de 64 bits desde python.org y marque «Add Python to PATH».
2. Abra una terminal en la carpeta del código fuente y ejecute:

   ```bat
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt pyinstaller
   pyinstaller --noconfirm SanFranciscoCrustPizza.spec
   ```

3. El resultado queda en `dist\SanFranciscoCrustPizza\`. Esa carpeta completa es la aplicación portable: contiene `SanFranciscoCrustPizza.exe`, `_internal\` (el runtime de Python y las dependencias), `datos_iniciales\` y la configuración.
4. Instalador (opcional): instale NSIS (nsis.sourceforge.io) y ejecute
   `makensis instalador.nsi`. Esto genera `SanFranciscoCrustPizza_Instalador.exe`.

## Opción B: como se compiló la versión entregada

La versión 1.0.0 se compiló en un entorno Linux, sin una PC Windows, de la siguiente manera:

1. **Runtime de Python:** se descargó CPython 3.13.18 para Windows (win-64) desde el repositorio conda-forge.
2. **Dependencias:** se instalaron las ruedas `win_amd64` oficiales de PyPI de streamlit 1.67.0, pandas 3.0.5, numpy 2.5.3, plotly 7.1.0, openpyxl 3.1.5, python-calamine y PyInstaller 6.22.3.
3. **Compilación:** se ejecutó PyInstaller dentro de **Wine 9.0**, la capa de compatibilidad de Windows para Linux, con el mismo archivo `.spec`.
4. **Instalador:** se generó con NSIS 3 (`makensis`) desde Linux.
5. **Prueba:** el paquete se probó en Wine. La app arrancó, creó las carpetas, levantó el servidor en localhost, respondió en `/_stcore/health`, mostró el dashboard y se detuvo con `--detener`.

La prueba en Wine **no sustituye** la prueba en una PC Windows real. Siga el protocolo de `05_PRUEBAS/Protocolo_prueba_portabilidad.md`.

## Parámetros del lanzador

| Comando | Acción |
|---|---|
| `SanFranciscoCrustPizza.exe` | Inicia la app, abre el navegador y muestra la ventana de control |
| `SanFranciscoCrustPizza.exe --detener` | Cierra una instancia en ejecución |
| `SanFranciscoCrustPizza.exe --servidor 8501` | Uso interno: servidor Streamlit |

Variables opcionales:

- `SFCP_HOME`: carpeta de datos.
- `SFCP_NO_BROWSER=1`: no abre el navegador (útil para pruebas).

## Notas técnicas de la compilación en Wine (opción B)

- Para que PyInstaller incluyera tkinter, la compilación se ejecutó con `TCL_LIBRARY` y `TK_LIBRARY` apuntando a `Library\lib\tcl8.6` y `Library\lib\tk8.6` del runtime.
- Wine 9.0 no implementa algunas funciones de la UCRT, como `ucrtbase.crealf`, que usa NumPy. Para las pruebas se usó la `ucrtbase.dll` nativa de Microsoft, que Windows 10 y 11 ya incluyen.
- Wine tampoco implementa `CopyFile2`; por eso la aplicación copia los archivos con `shutil.copyfile` + `copystat`.
- El servidor usa el bucle de eventos *Selector* de asyncio, configurable en `config\config.json` (`"bucle_eventos": "selector" | "proactor"`).

# Publicación en internet (Streamlit Community Cloud, plan gratuito)

La versión local no necesita internet. La publicación pública es una copia de la misma aplicación, desplegada desde GitHub. El profesor exige el enlace público para la evaluación.

## Requisitos (todos gratuitos)

- Una cuenta de GitHub y un repositorio **público** con este código fuente.
- Una cuenta de Streamlit Community Cloud (share.streamlit.io). Se inicia sesión con la misma cuenta de GitHub.

## Pasos

1. **Subir el código al repositorio.** Suba el contenido de `04_CODIGO_FUENTE` a la raíz del repositorio: `app.py`, `requirements.txt`, `sfcp/`, `vistas/`, `datos_iniciales/`, `.streamlit/`, `recursos/`.
2. **Abrir el asistente de despliegue.** Entre en share.streamlit.io, elija «Create app» y luego «Deploy a public app from GitHub».
3. **Configurar la app.** Elija:
   - el repositorio;
   - la rama `main`;
   - el archivo principal `app.py`;
   - una URL personalizada si lo desea, por ejemplo `sf-crust-pizza`.
4. **Elegir la versión de Python.** En «Advanced settings» seleccione Python 3.13 o 3.12. No hacen falta secretos.
5. **Desplegar.** Pulse «Deploy». Al terminar obtendrá un enlace `https://<nombre>.streamlit.app`, que es el **enlace público** para la entrega.

## Diferencias entre la versión local y la versión pública

| Aspecto | Local (Windows) | Pública (Streamlit Cloud) |
|---|---|---|
| Carpeta de datos | `C:\SanFranciscoCrustPizza\` o la que elija el usuario | `almacenamiento/` dentro del servidor (detección automática) |
| Persistencia de cargas | Permanente | **Temporal:** las cargas y respaldos se pierden cuando el servidor se reinicia o se reactiva tras un período sin uso |
| Bases iniciales | `datos_iniciales/` | `datos_iniciales/` del repositorio |
| Dirección | `http://localhost:8501` (solo en esa PC) | `https://<nombre>.streamlit.app` (accesible por cualquier persona) |
| Identificación del equipo | `config/equipo.json` | Debe volver a llenarse tras un reinicio, o guardarse en `datos_iniciales/` (ver abajo) |

`localhost` **no es un enlace público**: solo funciona en la computadora donde se ejecuta la app.

## Cómo dejar fijos los datos en la versión pública

- **Bases de datos:** para cambiar las bases de forma permanente, reemplace los archivos de `datos_iniciales/` en GitHub con los mismos nombres (`ventas.xlsx`, `clientes.xlsx`, `productos.xlsx`). Streamlit Cloud vuelve a desplegar la app automáticamente.
- **Identificación del equipo:** se puede publicar de forma permanente añadiendo el archivo `datos_iniciales/equipo.json`, con el mismo formato que `config/equipo.json`. El código lo copia al primer arranque.

## Migración futura a almacenamiento persistente

El acceso a los archivos está concentrado en `sfcp/config.py` (rutas) y `sfcp/storage.py` (lectura, escritura, respaldos e historial). Para usar almacenamiento persistente en la nube, por ejemplo Google Drive, S3 o una base de datos, se reemplazan solo esas funciones (`guardar_archivo`, `respaldar`, `restaurar`, `listar_respaldos`, `registrar`). El dashboard, los cálculos y el asistente no cambian.

Componentes que requerirán configuración adicional en esa etapa:

1. Credenciales del servicio de almacenamiento, guardadas en `st.secrets`, nunca en el código.
2. Autenticación de usuarios, si la información no debe ser pública. El plan gratuito permite apps privadas limitadas.
3. Revisión del tamaño de los archivos. El límite de carga actual es de 200 MB.

## Prueba realizada antes de publicar

La aplicación se ejecutó en modo servidor (Linux, como Streamlit Cloud) con `SFCP_CLOUD=1`. En ese modo creó su almacenamiento dentro de la carpeta del código y mostró el aviso de almacenamiento temporal.

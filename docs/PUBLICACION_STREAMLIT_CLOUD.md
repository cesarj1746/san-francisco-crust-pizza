# Publicación en Streamlit Community Cloud (plan gratuito)

**Aplicación publicada:** https://sf-crust-pizza-abv.streamlit.app/
**Repositorio:** https://github.com/cesarj1746/san-francisco-crust-pizza

## Cómo se publicó

1. **Repositorio:** se creó en GitHub un repositorio público vacío, `cesarj1746/san-francisco-crust-pizza`.
2. **Código:** se subió a la rama `main` el código fuente, con `app.py`, `requirements.txt`, `sfcp/`, `vistas/`, `datos_iniciales/` y `.streamlit/`.
3. **Inicio de sesión:** en share.streamlit.io se inició sesión con la cuenta de GitHub.
4. **Despliegue:** se eligió «Create app» → «Deploy a public app from GitHub», con el repositorio `cesarj1746/san-francisco-crust-pizza`, la rama `main` y el archivo `app.py`.
5. **Instalación:** Streamlit instaló las dependencias de `requirements.txt` y publicó la aplicación en `https://sf-crust-pizza-abv.streamlit.app/`.

## Cómo se actualiza

- **Cambios de código:** cada cambio que se sube a la rama `main` del repositorio vuelve a publicar la aplicación automáticamente.
- **Gestión:** la aplicación se administra desde share.streamlit.io, con el botón «Manage app» o el menú «⋮». Desde ahí se puede reiniciar (Reboot) y ver los registros.

## Dónde se guardan las bases

| Acción | Efecto |
|---|---|
| Cargar una base en «Administración de bases» | Se aplica de inmediato a todos los indicadores y crea un respaldo. Se conserva mientras el servidor esté activo |
| El servidor se reinicia o se reactiva tras días sin uso | La aplicación vuelve a las bases de `datos_iniciales/` del repositorio |
| Subir un archivo a `datos_iniciales/` en GitHub con el mismo nombre (`ventas.xlsx`, `clientes.xlsx` o `productos.xlsx`) | Cambio permanente: Streamlit vuelve a publicar la aplicación con esa base |

**Para fijar la identificación del equipo** en la versión publicada, se puede subir `datos_iniciales/equipo.json` con este formato:

```json
{"numero_equipo": "5", "integrantes": ["Nombre 1", "Nombre 2"], "programa": "Maestría en Dirección Comercial y Ventas",
 "asignatura": "Sistemas de Información para la Toma de Decisiones Comerciales", "profesor": "", "universidad": "UNIR", "fecha_entrega": ""}
```

## Plan gratuito

- La aplicación es pública: se abre con el enlace, sin pedir inicio de sesión.
- Si pasa varios días sin visitas, se suspende. Al abrirla aparece un botón para reactivarla («Yes, get this app back up!» o «Wake up»), y vuelve en uno o dos minutos. Conviene abrirla el día anterior a la evaluación.

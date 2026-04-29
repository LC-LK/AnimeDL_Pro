# Guía de Mantenimiento - AnimeDL

Esta guía describe la nueva arquitectura modular de AnimeDL, las dependencias entre componentes y cómo realizar el mantenimiento del sistema.

## 1. Estructura de Directorios

La aplicación se ha organizado siguiendo una arquitectura de capas:

```text
src/
├── config/             # Gestión de configuración y constantes
│   └── manager.py      # Carga/guardado de config.json y User-Agents
├── core/               # Lógica de negocio (Core Business Logic)
│   ├── downloader.py   # Gestión de descargas fragmentadas y reintentos
│   └── scraper.py      # Extracción de metadatos y enlaces de JkAnime
├── img/                # Recursos visuales (Iconos .png, .ico)
├── ui/                 # Interfaz de Usuario (Flet)
│   ├── components/     # Componentes UI reutilizables
│   │   ├── activity_log.py
│   │   ├── download_tab.py
│   │   └── library_tab.py
│   ├── app.py          # Controlador principal de la UI e integración
│   └── styles.py       # Constantes de diseño (colores, temas)
├── utils/              # Utilidades generales
│   ├── browser.py      # Gestión de Playwright y navegadores
│   └── helpers.py      # Funciones auxiliares (rutas, lazy loading)
└── main.py             # Punto de entrada de la aplicación
tests/                  # Pruebas unitarias
└── ...
```

## 2. Diagrama de Dependencias (Conceptual)

```mermaid
graph TD
    Main[main.py] --> App[ui/app.py]
    App --> Tabs[ui/components/*]
    App --> Scraper[core/scraper.py]
    App --> Downloader[core/downloader.py]
    App --> Config[config/manager.py]
    Scraper --> Browser[utils/browser.py]
    Downloader --> Config
    Browser --> Helpers[utils/helpers.py]
```

## 3. Principios de Diseño Aplicados

- **SOLID (Single Responsibility)**: Cada clase tiene una única responsabilidad. `Downloader` solo descarga, `Scraper` solo extrae datos, `AnimeDownloaderApp` coordina la UI.
- **Lazy Loading**: Los módulos pesados como `playwright` y `aiohttp` se cargan solo cuando son necesarios para mejorar el tiempo de arranque.
- **Inyección de Dependencias**: Los servicios (Scraper, Downloader) reciben la configuración y otros recursos necesarios en su constructor.
- **Asincronía**: Toda la red y operaciones de I/O son asíncronas (`async/await`) para evitar bloquear la interfaz.

## 4. Guía de Mantenimiento

### Actualización de Scrapers
Si JkAnime cambia su estructura HTML, los cambios deben realizarse principalmente en `src/core/scraper.py`.

### Modificación de la UI
Para añadir nuevas pestañas o modificar las existentes, edite los archivos en `src/ui/components/` y regístrelos en `src/ui/app.py`.

### Ejecución de Tests
Para validar que los cambios no rompan la funcionalidad existente, ejecute:
```bash
py -m unittest discover tests -v
```
*(Nota: Use `py` en Windows o `python` según su configuración de sistema).*

### Gestión de Configuración y UI
- **Lógica**: La configuración persistente se almacena en `config.json`. Si se añaden nuevas opciones, asegúrese de actualizar los valores por defecto en `src/config/manager.py`.
- **Recursos**: Los iconos y logos deben colocarse en `src/img/`. La aplicación utiliza `assets_dir` en `main.py` para resolver estas rutas.
- **Visual**: Las constantes de diseño, dimensiones de ventana y la versión del programa se centralizan en `src/ui/styles.py`.

### Compilación y Build
El archivo `build_exe.py` automatiza la creación del ejecutable.
- **Limpieza**: Antes de compilar, el script elimina automáticamente `__pycache__`, carpetas `build/dist` y archivos `.spec` para asegurar una compilación limpia.
- **Metadatos**: La información de versión se extrae de `version_info.txt`.

### Responsividad
Al modificar componentes en `src/ui/components/`, asegúrese de probar la interfaz en dimensiones reducidas (ej. 400x200), utilizando el parámetro `wrap=True` en filas y ajustando los valores de `ft.ResponsiveRow`.


# AnimeDL Pro 🚀

**AnimeDL Pro** es una aplicación de escritorio moderna y ligera diseñada para gestionar tu colección de anime y descargar capítulos de forma automatizada desde JkAnime. Construida con Python y Flet, ofrece una interfaz fluida, responsiva y profesional.

![Versión](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![License](https://img.shields.io/badge/license-MIT-important.svg)

## ✨ Características

- 📱 **Interfaz Moderna**: UI profesional basada en Flet con soporte para temas oscuros.
- ⚡ **Descargas Fragmentadas**: Sistema de descarga robusto con soporte para pausa, reanudación y reintentos automáticos.
- 🔍 **Buscador Integrado**: Encuentra y añade animes a tu biblioteca directamente desde la app.
- 📚 **Biblioteca Personalizada**: Gestiona tus series seguidas, con vistas de lista o cuadrícula responsiva.
- 🛠️ **Arquitectura Modular**: Código limpio siguiendo principios SOLID y Lazy Loading para un rendimiento óptimo.
- 🧪 **Suite de Tests**: Pruebas unitarias integradas para asegurar la estabilidad del core.

## 🚀 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   cd "Descarga Anime"
   ```

2. **Crear un entorno virtual (Recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instalar navegadores de Playwright:**
   ```bash
   playwright install chromium
   ```

## 💻 Uso

Para iniciar la aplicación, simplemente ejecuta:

```bash
python src/main.py
```

## 🛠️ Desarrollo y Mantenimiento

Para más detalles sobre la arquitectura del proyecto, diagramas de dependencias y guías de mantenimiento, consulta el archivo [Mantenimiento.md](src/Mantenimiento.md).

### Ejecutar Tests
```bash
py -m unittest discover tests -v
```

## 📦 Compilación (EXE)

Si deseas generar un ejecutable para Windows, puedes usar el script de construcción incluido:

```bash
python build_exe.py
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---
Desarrollado con ❤️ para la comunidad de anime.

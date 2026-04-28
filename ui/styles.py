"""
Módulo de Estilos y Constantes Visuales.
Define la paleta de colores, dimensiones de ventana y estilos reutilizables para Flet.
"""
import flet as ft

# Paleta de Colores Profesional (Slate/Blue Theme)
BG_COLOR = "#0f172a"          # Slate 950 (Fondo muy oscuro)
SURFACE_COLOR = "#1e293b"     # Slate 800 (Superficies)
ACCENT_COLOR = "#3b82f6"      # Blue 500 (Acentos)
SUCCESS_COLOR = "#10b981"     # Emerald 500
ERROR_COLOR = "#ef4444"       # Red 500
TEXT_PRIMARY = "#f8fafc"      # Slate 50
TEXT_SECONDARY = "#94a3b8"    # Slate 400

# Colores Semánticos para Retrocompatibilidad
PRIMARY_COLOR = ACCENT_COLOR
SECONDARY_COLOR = SURFACE_COLOR
LOG_BG_COLOR = "#0b1120"        # Un poco más oscuro que BG_COLOR

# Estilos de Componentes Reutilizables
TEXT_FIELD_STYLE = {
    "border": ft.InputBorder.UNDERLINE,
    "height": 50,
    "text_size": 14,
    "label_style": ft.TextStyle(size=12, color=TEXT_SECONDARY),
    "focused_border_color": ACCENT_COLOR,
    "border_color": SURFACE_COLOR,
    "cursor_color": ACCENT_COLOR,
    "bgcolor": "transparent"
}

# Configuración Inicial de la Ventana
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
WINDOW_TITLE = "AnimeDL Pro"
APP_VERSION = "1.0"

# Colores Categorizados para Logs (WCAG 2.1 Contrast > 4.5:1)
LOG_COLORS = {
    "error": "#FF4444",      # Rojo brillante (Accesible sobre fondo oscuro)
    "warning": "#FFA500",    # Naranja/Amarillo
    "info": "#47A1F5",       # Azul claro optimizado
    "debug": "#4CAF50",      # Verde
    "critical": "#D166FF",   # Púrpura claro
    "timestamp": "#94A3B8"   # Slate 400
}

# Estilos de Botones Modernos
BUTTON_STYLE = {
    "style": ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
    )
}

# Estilos de Contenedores
MAIN_CONTAINER_STYLE = {
    "padding": ft.padding.all(24),
    "border_radius": 16,
    "bgcolor": SURFACE_COLOR,
}

# Estilos de Cards
CARD_STYLE = {
    "elevation": 0,
    "margin": 0,
}

# Estilos Dinámicos de Checkbox
CHECKBOX_FILL_COLOR = {
    ft.ControlState.SELECTED: SUCCESS_COLOR,
    ft.ControlState.HOVERED: "#059669",
}

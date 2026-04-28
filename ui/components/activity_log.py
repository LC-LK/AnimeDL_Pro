"""
Componente de Log de Actividad Simplificado.
Proporciona un área visual para mostrar mensajes categorizados con timestamp.
"""
import flet as ft
from datetime import datetime
from ui.styles import LOG_BG_COLOR, TEXT_PRIMARY, LOG_COLORS

class ActivityLog(ft.Container):
    """
    Control de interfaz de usuario simplificado para la visualización de logs.
    """
    def __init__(self):
        super().__init__()
        self.log_view = ft.ListView(
            expand=True,
            spacing=5,
            padding=15,
            auto_scroll=True
        )
        
        self.content = self.log_view
        self.bgcolor = LOG_BG_COLOR
        self.border_radius = 12
        self.border = ft.border.all(1, ft.Colors.WHITE10)
        self.expand = True

    def add_message(self, message, type="info"):
        """Añade un mensaje con estilo, timestamp y categoría."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        color = LOG_COLORS.get(type, TEXT_PRIMARY)
        
        self.log_view.controls.append(
            ft.Text(
                spans=[
                    ft.TextSpan(f"[{timestamp}] ", ft.TextStyle(color=LOG_COLORS["timestamp"], size=11, weight=ft.FontWeight.W_300)),
                    ft.TextSpan(f"[{type.upper()}] ", ft.TextStyle(color=color, size=11, weight=ft.FontWeight.BOLD)),
                    ft.TextSpan(message, ft.TextStyle(color=TEXT_PRIMARY, size=13)),
                ]
            )
        )
        self.update()

"""
Componente de la Pestaña de Descargas.
Define la interfaz para ingresar URLs, seleccionar carpetas y controlar el proceso de descarga.
"""
import flet as ft
import os
from ui.styles import TEXT_FIELD_STYLE, BUTTON_STYLE, ACCENT_COLOR, SURFACE_COLOR, SUCCESS_COLOR, ERROR_COLOR

class DownloadTab(ft.Column):
    """
    Vista modular para la gestión de descargas activas.
    """
    def __init__(self, on_start, on_stop, on_pause, on_restart, on_dir_picker, on_url_change):
        super().__init__()
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_pause = on_pause
        self.on_restart = on_restart
        self.on_dir_picker = on_dir_picker
        self.on_url_change = on_url_change
        
        self.setup_controls()
        
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Inputs Section
                    ft.Container(
                        content=ft.Column([
                            ft.ResponsiveRow([
                                ft.Column([self.url_input], col={"sm": 12, "md": 8}),
                                ft.Column([self.alias_input], col={"sm": 12, "md": 4}),
                            ], spacing=10),
                            ft.ResponsiveRow([
                                ft.Column([self.dir_input], col={"sm": 10, "md": 11}),
                                ft.Column([self.dir_btn], col={"sm": 2, "md": 1}, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ], spacing=10),
                        padding=ft.padding.only(bottom=10)
                    ),
                    
                    # Actions Section (Compacta)
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                self.start_btn,
                                self.stop_btn,
                            ], spacing=10),
                            ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                            ft.Row([
                                self.pause_btn,
                                self.restart_btn,
                            ], spacing=5),
                        ], alignment=ft.MainAxisAlignment.START, spacing=20),
                        padding=ft.padding.symmetric(vertical=10)
                    ),

                    # Progress Section
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                self.status_text,
                                self.progress_info,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            self.progress_bar,
                        ], spacing=10),
                        padding=20,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.WHITE10)
                    ),
                ], spacing=10),
                padding=20,
            )
        ]
        self.spacing = 0
        self.expand = False

    def setup_controls(self):
        self.url_input = ft.TextField(
            label="URL de JkAnime",
            hint_text="https://jkanime.net/...",
            on_change=self.on_url_change,
            **TEXT_FIELD_STYLE
        )
        self.alias_input = ft.TextField(
            label="Alias",
            hint_text="Ej: One Piece",
            **TEXT_FIELD_STYLE
        )
        self.dir_input = ft.TextField(
            label="Carpeta de Destino",
            read_only=True,
            **TEXT_FIELD_STYLE
        )
        self.dir_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            icon_color=ACCENT_COLOR,
            on_click=self.on_dir_picker,
            tooltip="Cambiar carpeta"
        )
        self.start_btn = ft.FilledButton(
            "Iniciar", 
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(
                bgcolor=ACCENT_COLOR,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self.on_start,
        )
        self.stop_btn = ft.OutlinedButton(
            "Detener", 
            icon=ft.Icons.STOP_ROUNDED,
            style=ft.ButtonStyle(
                color=ERROR_COLOR,
                side={"": ft.BorderSide(1, ERROR_COLOR)},
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            disabled=True, 
            on_click=self.on_stop,
        )
        self.pause_btn = ft.IconButton(
            icon=ft.Icons.PAUSE_ROUNDED,
            icon_color=ACCENT_COLOR,
            disabled=True, 
            on_click=self.on_pause,
            tooltip="Pausar/Reanudar"
        )
        self.restart_btn = ft.IconButton(
            icon=ft.Icons.RESTART_ALT_ROUNDED,
            icon_color=ACCENT_COLOR,
            disabled=True, 
            on_click=self.on_restart,
            tooltip="Reiniciar capítulo"
        )
        self.status_text = ft.Text("Listo para descargar", size=14, weight=ft.FontWeight.W_500, color=ACCENT_COLOR)
        self.progress_bar = ft.ProgressBar(value=0, height=8, color=ACCENT_COLOR, bgcolor=ft.Colors.WHITE10, border_radius=4)
        self.progress_info = ft.Text("Esperando acción...", size=12, color=ft.Colors.WHITE70)

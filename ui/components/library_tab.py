"""
Componente de la Pestaña de Biblioteca.
Maneja la visualización de los animes seguidos, búsqueda, filtrado y actualizaciones.
"""
import flet as ft
from ui.styles import ACCENT_COLOR, SURFACE_COLOR, TEXT_FIELD_STYLE, CHECKBOX_FILL_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS_COLOR, ERROR_COLOR

class LibraryTab(ft.Column):
    """
    Vista modular para la gestión de la colección de anime.
    """
    def __init__(self, on_search, on_check_updates, on_delete, on_toggle_view, on_grid_size, on_prev, on_next):
        super().__init__()
        self.on_search = on_search
        self.on_check_updates = on_check_updates
        self.on_delete = on_delete
        self.on_toggle_view = on_toggle_view
        self.on_grid_size = on_grid_size
        self.on_prev = on_prev
        self.on_next = on_next
        
        self.setup_controls()
        
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Toolbar Section
                    ft.Container(
                        content=ft.ResponsiveRow([
                            ft.Column([self.search_field], col={"sm": 12, "md": 4, "lg": 5}),
                            ft.Column([
                                ft.Row([
                                    self.check_updates_btn, 
                                    self.delete_btn,
                                ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True)
                            ], col={"sm": 6, "md": 4, "lg": 4}),
                            ft.Column([
                                ft.Row([
                                    self.view_toggle,
                                ], alignment=ft.MainAxisAlignment.END, wrap=True)
                            ], col={"sm": 6, "md": 4, "lg": 3}),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=ft.padding.only(bottom=10)
                    ),
                    
                    # Content Area
                    ft.Container(
                        content=self.library_container,
                        expand=True,
                        border_radius=16,
                        bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
                        border=ft.border.all(1, ft.Colors.WHITE10),
                        padding=10
                    ),
                    
                    # Pagination Section
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                self.prev_btn,
                                self.page_indicator,
                                self.next_btn
                            ], spacing=20),
                            self.grid_size_slider
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.symmetric(vertical=10)
                    )
                ], spacing=0, expand=True),
                expand=True,
                padding=20
            )
        ]
        self.spacing = 0
        self.expand = True

    def setup_controls(self):
        self.search_field = ft.TextField(
            label="Buscar en tu biblioteca",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            on_change=self.on_search,
            **TEXT_FIELD_STYLE
        )
        self.check_updates_btn = ft.FilledButton(
            "Actualizar",
            icon=ft.Icons.REFRESH_ROUNDED,
            on_click=self.on_check_updates,
            style=ft.ButtonStyle(
                bgcolor=SUCCESS_COLOR,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        )
        self.delete_btn = ft.OutlinedButton(
            "Eliminar",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            on_click=self.on_delete,
            style=ft.ButtonStyle(
                color=ERROR_COLOR,
                side={"": ft.BorderSide(1, ERROR_COLOR)},
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        )
        self.view_toggle = ft.SegmentedButton(
            allow_multiple_selection=False,
            on_change=self.on_toggle_view,
            segments=[
                ft.Segment(value="list", icon=ft.Icon(ft.Icons.LIST_ROUNDED, size=16)),
                ft.Segment(value="grid", icon=ft.Icon(ft.Icons.GRID_VIEW_ROUNDED, size=16)),
            ],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=2),
            )
        )
        self.grid_size_slider = ft.Slider(
            min=120, max=250,
            on_change=self.on_grid_size,
            width=150,
            active_color=ACCENT_COLOR,
            inactive_color=ft.Colors.WHITE10,
            label="{value}px"
        )
        self.library_list = ft.ListView(expand=True, spacing=12, padding=10)
        self.library_grid = ft.GridView(
            expand=True, 
            child_aspect_ratio=0.7,
            spacing=15, 
            run_spacing=15, 
            padding=10,
            max_extent=150
        )
        self.library_container = ft.Container(content=self.library_list, expand=True)
        self.prev_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT_ROUNDED, 
            icon_color=TEXT_SECONDARY,
            on_click=self.on_prev
        )
        self.next_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT_ROUNDED, 
            icon_color=TEXT_SECONDARY,
            on_click=self.on_next
        )
        self.page_indicator = ft.Text("Página 1", size=14, weight=ft.FontWeight.W_500, color=TEXT_PRIMARY)

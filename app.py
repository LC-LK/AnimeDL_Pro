"""
Módulo Principal de la Interfaz de Usuario.
Contiene la lógica de orquestación de la aplicación AnimeDL, integrando componentes UI y servicios core.
"""
import flet as ft
import asyncio
import os
import re
import time
import random
from datetime import datetime

from config.manager import load_config, save_config, USER_AGENTS
from utils.helpers import lazy_import_network, resource_path
from utils.browser import get_browser_instance

from .styles import BG_COLOR, SURFACE_COLOR, ACCENT_COLOR, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, CHECKBOX_FILL_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, APP_VERSION
from .components.activity_log import ActivityLog
from .components.download_tab import DownloadTab
from .components.library_tab import LibraryTab

# Expresiones regulares pre-compiladas para optimizar el rendimiento
RE_CHAPTER_URL = re.compile(r'/(\d+)/?$')
RE_CLEAN_TITLE = re.compile(r' Sub Español.*')
RE_EPISODE_NUM = re.compile(r'(\d+)$')
RE_BASE_NAME = re.compile(r'\s*\d+$')
RE_INVALID_CHARS = re.compile(r'[\\/*?:"<>|]')

class AnimeDownloaderApp:
    """
    Controlador principal de la aplicación.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page_config()
        self.init_state()
        self.setup_ui()

    def setup_page_config(self):
        self.page.title = WINDOW_TITLE
        
        # Dimensiones iniciales y mínimas
        self.page.window_width = WINDOW_WIDTH
        self.page.window_height = WINDOW_HEIGHT
        self.page.window_min_width = WINDOW_WIDTH
        self.page.window_min_height = WINDOW_HEIGHT
        
        # Soporte para versiones más recientes de Flet
        if hasattr(self.page, "window"):
            self.page.window.width = WINDOW_WIDTH
            self.page.window.height = WINDOW_HEIGHT
            self.page.window.min_width = WINDOW_WIDTH
            self.page.window.min_height = WINDOW_HEIGHT

        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.bgcolor = BG_COLOR
        self.page.theme = ft.Theme(font_family="Segoe UI, Tahoma, Geneva, Verdana, sans-serif")
        self.page.update()

    def init_state(self):
        """Inicializa el estado interno, controladores de eventos y servicios core."""
        self.config = load_config()
        self.is_paused = asyncio.Event()
        self.is_paused.set()
        self.stop_requested = False
        self.current_task = None
        self.total_downloaded_session = 0
        self.total_size_mb_session = 0.0
        self.session_start_time = None
        self.current_chapter_info = ""
        
        # Estado de la Biblioteca
        self.library_search = ""
        self.library_page = 0
        self.selected_animes = set()
        self.view_mode = self.config.get("settings", {}).get("view_mode", "list")
        
        # Validar grid_size para evitar AssertionError con el Slider (min 120, max 250)
        saved_grid_size = self.config.get("settings", {}).get("grid_size", 150)
        self.grid_size = max(120, min(250, saved_grid_size))
        
        # Inicializar herramientas (Downloader se carga de forma diferida al usarse)
        self._downloader = None
        
        # Diálogos y Pickers
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_result)
        self.page.overlay.append(self.dir_picker)
        
        self.setup_dialogs()

    @property
    def downloader(self):
        """Property para cargar el Downloader solo cuando sea necesario."""
        if self._downloader is None:
            from core.downloader import Downloader
            self._downloader = Downloader(self)
        return self._downloader

    def setup_dialogs(self):
        """Prepara los diálogos modales de confirmación y actualización."""
        self.delete_dialog = ft.AlertDialog(
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text("¿Estás seguro de que deseas eliminar los animes seleccionados?"),
            actions=[
                ft.TextButton("Eliminar", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=self.delete_selected_animes),
                ft.TextButton("Cancelar", on_click=lambda _: self.close_delete_dialog()),
            ],
        )
        self.page.overlay.append(self.delete_dialog)
        
        self.pending_updates = []
        self.updates_list = ft.ListView(height=150, spacing=5)
        self.update_dialog = ft.AlertDialog(
            title=ft.Text("¡Nuevos capítulos detectados!"),
            content=ft.Column([
                ft.Text("Se han encontrado capítulos nuevos para tus animes:"),
                self.updates_list
            ], tight=True),
            actions=[
                ft.TextButton("Descargar todo", on_click=self.accept_all_updates),
                ft.TextButton("Ignorar", on_click=self.close_update_dialog),
            ],
        )
        self.page.overlay.append(self.update_dialog)

    def setup_ui(self):
        self.activity_log = ActivityLog()
        
        self.download_tab_view = DownloadTab(
            on_start=self.start_process,
            on_stop=self.stop_process,
            on_pause=self.toggle_pause,
            on_restart=self.restart_current,
            on_dir_picker=lambda _: self.dir_picker.get_directory_path(),
            on_url_change=self.on_url_change
        )
        
        self.library_tab_view = LibraryTab(
            on_search=self.on_library_search_change,
            on_check_updates=self.check_selected_updates,
            on_delete=lambda _: self.show_delete_dialog(),
            on_toggle_view=self.toggle_view_mode,
            on_grid_size=self.on_grid_size_change,
            on_prev=self.prev_library_page,
            on_next=self.next_library_page
        )
        
        self.download_tab_view.dir_input.value = self.config.get("settings", {}).get("default_dir", os.getcwd())
        self.library_tab_view.grid_size_slider.value = self.grid_size
        self.library_tab_view.library_grid.max_extent = self.grid_size
        self.library_tab_view.view_toggle.selected = {self.view_mode}
        self.library_tab_view.grid_size_slider.visible = self.view_mode == "grid"
        
        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Descargas", icon=ft.Icons.DOWNLOAD_ROUNDED, content=self.build_downloads_layout()),
                ft.Tab(text="Biblioteca", icon=ft.Icons.BOOKMARK_ROUNDED, content=self.library_tab_view),
            ],
            expand=True,
            animation_duration=300,
            divider_color=ft.Colors.TRANSPARENT,
            indicator_color=ACCENT_COLOR,
            label_color=TEXT_PRIMARY,
            unselected_label_color=TEXT_SECONDARY,
        )

        # Layout Principal Elegante
        self.page.add(
            ft.Container(
                content=ft.Column([
                    # Header Moderno
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=24, color=ACCENT_COLOR),
                                ft.Text("AnimeDL", size=22, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Container(
                                    content=ft.Text("PRO", size=10, weight=ft.FontWeight.BOLD, color=ACCENT_COLOR),
                                    bgcolor=ft.Colors.with_opacity(0.1, ACCENT_COLOR),
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4
                                ),
                            ], spacing=10),
                            ft.Row([
                                ft.Text(f"v{APP_VERSION}", size=12, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                                ft.IconButton(ft.Icons.SETTINGS_ROUNDED, icon_color=TEXT_SECONDARY, icon_size=20),
                            ], spacing=10),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.only(top=25, left=30, right=30, bottom=15),
                    ),
                    # Tabs Area
                    ft.Container(
                        content=self.tabs,
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=20)
                    )
                ], spacing=0, expand=True),
                expand=True,
                bgcolor=BG_COLOR
            )
        )
        
        self.update_library_list()
        
        if self.config.get("settings", {}).get("auto_check", True):
            self.page.run_task(self.auto_check_updates)
            
        # Forzar una última actualización para asegurar dimensiones
        self.page.update()
            
        # Forzar una última actualización para asegurar dimensiones
        self.page.update()

    def build_downloads_layout(self):
        return ft.Container(
            content=ft.Column([
                self.download_tab_view,
                ft.Text("Log de Actividad:", size=14, weight="bold"),
                ft.Container(content=self.activity_log, expand=True)
            ], spacing=15, expand=True),
            padding=ft.padding.only(top=20),
            expand=True
        )

    # --- Handlers ---
    def log(self, message, type="info"):
        self.activity_log.add_message(message, type)

    def on_dir_result(self, e):
        if e.path:
            self.download_tab_view.dir_input.value = e.path
            self.config["settings"]["default_dir"] = e.path
            save_config(self.config)
            self.page.update()

    def on_url_change(self, e):
        url = self.download_tab_view.url_input.value.strip()
        anime_data, _ = self._find_anime_by_url(url)
        
        if anime_data:
            self.download_tab_view.alias_input.value = anime_data.get("alias", "")
            saved_path = anime_data.get("download_path")
            if saved_path and os.path.exists(saved_path):
                self.download_tab_view.dir_input.value = saved_path
            self.page.update()

    def _find_anime_by_url(self, url):
        """Helper para encontrar datos de anime en la configuración basándose en una URL."""
        if not url:
            return None, ""
            
        search_url = url.rstrip("/")
        anime_data = None
        matched_base_url = ""
        
        following = self.config.get("following", {})
        for b_url, data in following.items():
            norm_b_url = b_url.rstrip("/")
            if search_url.startswith(norm_b_url):
                if not matched_base_url or len(b_url) > len(matched_base_url):
                    matched_base_url = b_url
                    anime_data = data
        return anime_data, matched_base_url

    # --- Biblioteca Logic ---
    def toggle_view_mode(self, e):
        self.view_mode = list(e.control.selected)[0]
        self.config["settings"]["view_mode"] = self.view_mode
        self.library_tab_view.grid_size_slider.visible = self.view_mode == "grid"
        save_config(self.config)
        self.update_library_list()

    def on_grid_size_change(self, e):
        self.grid_size = e.control.value
        self.library_tab_view.library_grid.max_extent = self.grid_size
        self.config["settings"]["grid_size"] = self.grid_size
        save_config(self.config)
        self.page.update()

    def on_library_search_change(self, e):
        self.library_search = e.control.value.lower()
        self.library_page = 0
        self.update_library_list()

    def prev_library_page(self, e):
        if self.library_page > 0:
            self.library_page -= 1
            self.update_library_list()

    def next_library_page(self, e):
        self.library_page += 1
        self.update_library_list()

    def update_library_list(self):
        self.library_tab_view.library_list.controls.clear()
        self.library_tab_view.library_grid.controls.clear()
        
        is_grid = self.view_mode == "grid"
        self.library_tab_view.library_container.content = (
            self.library_tab_view.library_grid if is_grid else self.library_tab_view.library_list
        )

        search_query = self.library_search
        following = self.config.get("following", {})
        
        animes = [
            (url, data) for url, data in following.items()
            if search_query in data.get("alias", "").lower() or search_query in url.lower()
        ]
        
        animes.sort(key=lambda x: x[1].get("date", ""), reverse=True)
        
        items_per_page = 24 if is_grid else 20
        total_items = len(animes)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        start_idx = self.library_page * items_per_page
        page_items = animes[start_idx : start_idx + items_per_page]
        
        self.library_tab_view.page_indicator.value = f"Página {self.library_page + 1} de {max(1, total_pages)}"
        self.library_tab_view.prev_btn.disabled = self.library_page == 0
        self.library_tab_view.next_btn.disabled = self.library_page >= total_pages - 1
        
        for base_url, data in page_items:
            self.add_anime_to_view(base_url, data)
        
        self.page.update()

    def add_anime_to_view(self, base_url, data):
        last_date = data.get("date", "Sin fecha")
        last_cap = data.get("last_chapter", "?")
        alias = data.get("alias", "Sin nombre")
        thumb_url = data.get("thumbnail", "https://jkanime.net/assets/images/no-poster.jpg")
        has_next = data.get("has_next", True)
        
        is_recent = False
        if last_date != "Sin fecha":
            try:
                dt = datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S")
                is_recent = (datetime.now() - dt).days < 1
            except (ValueError, TypeError):
                pass

        if has_next:
            try:
                next_cap = int(last_cap) + 1
            except (ValueError, TypeError):
                next_cap = "?"
            status_text = f"Nuevo capitulo disponible | Cap {next_cap}"
            status_color = ft.Colors.GREEN_400
        else:
            status_color = ft.Colors.GREEN_400 if is_recent else ft.Colors.BLUE_400
            status_text = "Descargado recientemente" if is_recent else "Al día"
            if not has_next:
                status_text = "Sin capítulos nuevos"
                status_color = ft.Colors.ORANGE_400

        if self.view_mode == "list":
            card = self.build_list_card(base_url, alias, last_cap, last_date, thumb_url, status_color, status_text, has_next, data)
            self.library_tab_view.library_list.controls.append(card)
        else:
            card = self.build_grid_card(base_url, alias, last_cap, thumb_url, status_color, status_text, has_next, data)
            self.library_tab_view.library_grid.controls.append(card)

    def build_list_card(self, base_url, alias, last_cap, last_date, thumb_url, status_color, status_text, has_next, data):
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Checkbox(
                        value=base_url in self.selected_animes,
                        on_change=lambda e, url=base_url: self.on_anime_select(e, url),
                        fill_color=CHECKBOX_FILL_COLOR,
                        check_color=ft.Colors.WHITE
                    ),
                    ft.Image(src=thumb_url, width=60, height=80, fit=ft.ImageFit.COVER, border_radius=5),
                    ft.Column([
                        ft.Text(alias, size=16, weight="bold", width=300, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Icon(ft.Icons.CIRCLE, size=10, color=status_color),
                            ft.Text(f" {status_text}" if has_next else f" {status_text} | Cap {last_cap}", size=12, color=status_color),
                        ]),
                        ft.Text(f"Última descarga: {last_date}", size=10, color="grey"),
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.PLAY_CIRCLE_FILL,
                        icon_color="blue" if has_next else "grey",
                        disabled=not has_next,
                        on_click=lambda e, url=data.get("last_url"): self.load_to_downloads(url, next_chapter=True)
                    )
                ], alignment=ft.MainAxisAlignment.START),
                padding=10
            )
        )

    def build_grid_card(self, base_url, alias, last_cap, thumb_url, status_color, status_text, has_next, data):
        return ft.Card(
            content=ft.Container(
                content=ft.Stack([
                    ft.Column([
                        ft.Container(
                            content=ft.Image(
                                src=thumb_url, 
                                fit=ft.ImageFit.COVER, 
                                border_radius=8,
                                repeat=ft.ImageRepeat.NO_REPEAT,
                            ),
                            expand=True,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(alias, size=12, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, color=TEXT_PRIMARY),
                                ft.Text(status_text if has_next else f"{status_text} | Cap {last_cap}", size=11, color=status_color, weight=ft.FontWeight.W_500),
                            ], spacing=2),
                            padding=ft.padding.only(left=8, right=8, bottom=10, top=5)
                        )
                    ], spacing=0),
                    ft.Container(
                        content=ft.Checkbox(
                             value=base_url in self.selected_animes,
                             on_change=lambda e, url=base_url: self.on_anime_select(e, url),
                             fill_color=CHECKBOX_FILL_COLOR,
                             check_color=ft.Colors.WHITE,
                             scale=1.2
                         ),
                        top=5, left=5, bgcolor=ft.Colors.BLACK54, border_radius=5, padding=2
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.PLAY_CIRCLE_FILL,
                            icon_color="blue" if has_next else "grey",
                            icon_size=30,
                            disabled=not has_next,
                            on_click=lambda e, url=data.get("last_url"): self.load_to_downloads(url, next_chapter=True),
                            bgcolor=ft.Colors.BLACK54
                        ),
                        top=0, right=0
                    )
                ]),
                padding=0
            )
        )

    def on_anime_select(self, e, url):
        if e.control.value:
            self.selected_animes.add(url)
        else:
            self.selected_animes.discard(url)

    def show_delete_dialog(self):
        if not self.selected_animes:
            self.page.snack_bar = ft.SnackBar(ft.Text("No hay animes seleccionados."))
            self.page.snack_bar.open = True
            self.page.update()
            return
        self.delete_dialog.open = True
        self.page.update()

    def close_delete_dialog(self):
        self.delete_dialog.open = False
        self.page.update()

    def delete_selected_animes(self, e):
        count = 0
        for url in list(self.selected_animes):
            if url in self.config.get("following", {}):
                del self.config["following"][url]
                count += 1
        
        if count > 0:
            save_config(self.config)
            self.selected_animes.clear()
            self.update_library_list()
            self.log(f"[-] Se eliminaron {count} animes.", type="warning")
        
        self.delete_dialog.open = False
        self.page.update()

    def load_to_downloads(self, url, next_chapter=False):
        if not url: return
        
        anime_data, matched_base_url = self._find_anime_by_url(url)

        if anime_data and not anime_data.get("has_next", True):
            self.log(f"  [!] No hay capítulos nuevos disponibles.", type="warning")
            return

        if next_chapter:
            match = RE_CHAPTER_URL.search(url)
            if match:
                current_ep = int(match.group(1))
                new_url = RE_CHAPTER_URL.sub(f"/{current_ep + 1}/", url)
                self.download_tab_view.url_input.value = new_url
            elif anime_data and "last_chapter" in anime_data:
                try:
                    next_ep = int(anime_data["last_chapter"]) + 1
                    self.download_tab_view.url_input.value = f"{matched_base_url}{next_ep}/"
                except (ValueError, TypeError):
                    self.download_tab_view.url_input.value = url
            else:
                self.download_tab_view.url_input.value = url
        else:
            self.download_tab_view.url_input.value = url

        if anime_data:
            self.download_tab_view.alias_input.value = anime_data.get("alias", "")
            saved_path = anime_data.get("download_path")
            if saved_path and os.path.exists(saved_path):
                self.download_tab_view.dir_input.value = saved_path
        
        self.tabs.selected_index = 0
        self.page.update()
        self.log(f"[*] Cargado: {self.download_tab_view.alias_input.value or 'Sin nombre'}", type="info")

    async def check_selected_updates(self, e):
        if not self.selected_animes:
            return
        
        self.library_tab_view.check_updates_btn.disabled = True
        self.library_tab_view.check_updates_btn.text = "Buscando..."
        self.page.update()

        async_playwright, _ = lazy_import_network()
        from core.scraper import AnimeScraper
        
        async with async_playwright() as p:
            browser = await get_browser_instance(p)
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            scraper = AnimeScraper(context)
            
            semaphore = asyncio.Semaphore(5)
            updates_found = []
            
            async def check_anime(base_url):
                async with semaphore:
                    data = self.config["following"].get(base_url)
                    if not data: return
                    
                    page = await context.new_page()
                    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_())
                    try:
                        await page.goto(data.get("last_url"), wait_until="domcontentloaded", timeout=15000)
                        next_url = await scraper.get_next_url(page)
                        thumb = await scraper.get_anime_info(page)
                        if thumb: self.config["following"][base_url]["thumbnail"] = thumb
                        self.config["following"][base_url]["has_next"] = next_url is not None
                        save_config(self.config)
                        if next_url: updates_found.append((data.get("alias", base_url), next_url))
                    except Exception as ex:
                        self.log(f"Error revisando {base_url}: {str(ex)}", type="error")
                    finally:
                        await page.close()

            await asyncio.gather(*[check_anime(url) for url in list(self.selected_animes)])
            await browser.close()

        self.library_tab_view.check_updates_btn.disabled = False
        self.library_tab_view.check_updates_btn.text = "Actualizar"
        self.show_updates_dialog(updates_found)
        self.update_library_list()

    def show_updates_dialog(self, updates):
        if not updates:
            self.page.snack_bar = ft.SnackBar(ft.Text("No hay nuevos episodios."))
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        self.pending_updates = []
        self.updates_list.controls.clear()
        for alias, next_url in updates:
            ep = re.findall(r'(\d+)/$', next_url)
            ep = ep[0] if ep else "?"
            base_url = re.sub(r'\d+/$', '', next_url)
            self.pending_updates.append((base_url, next_url, alias, ep))
            self.updates_list.controls.append(ft.Text(f"• {alias} - Cap {ep}", size=14))
        
        self.update_dialog.open = True
        self.page.update()

    async def auto_check_updates(self):
        if not self.config["following"]: return
        
        self.log(f"[*] Verificando actualizaciones automáticas...", type="info")
        async_playwright, _ = lazy_import_network()
        from core.scraper import AnimeScraper
        
        initial_count = len(self.pending_updates)
        async with async_playwright() as p:
            try:
                browser = await get_browser_instance(p)
                context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
                scraper = AnimeScraper(context)
                semaphore = asyncio.Semaphore(5)
                
                async def check_anime(base_url, data):
                    async with semaphore:
                        last_url = data.get("last_url")
                        if not last_url: return
                        page = await context.new_page()
                        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_())
                        try:
                            await page.goto(last_url, wait_until="domcontentloaded", timeout=20000)
                            next_url = await scraper.get_next_url(page)
                            thumb = await scraper.get_anime_info(page)
                            if thumb: self.config["following"][base_url]["thumbnail"] = thumb
                            self.config["following"][base_url]["has_next"] = next_url is not None
                            save_config(self.config)
                            if next_url:
                                ep = re.findall(r'/(\d+)/$', next_url)
                                ep = ep[0] if ep else "?"
                                self.pending_updates.append((base_url, next_url, data.get("alias", "Anime"), ep))
                                self.updates_list.controls.append(ft.Text(f"• {data.get('alias')}: Cap {ep}", size=14, color="blue"))
                        except: pass
                        finally: await page.close()

                await asyncio.gather(*[check_anime(url, data) for url, data in self.config["following"].items()])
                await browser.close()
                
                new_updates = len(self.pending_updates) - initial_count
                if new_updates > 0:
                    self.log(f"[+] Se encontraron {new_updates} nuevos capítulos.", type="success")
                    self.update_dialog.open = True
                    self.page.update()
                else:
                    self.log(f"[-] No se encontraron capítulos nuevos.", type="info")
            except Exception as e:
                self.log(f"Error en actualización automática: {str(e)}", type="error")

    async def close_update_dialog(self, e):
        self.update_dialog.open = False
        self.page.update()

    async def accept_all_updates(self, e):
        self.update_dialog.open = False
        self.stop_requested = False
        self.page.update()
        
        updates = list(self.pending_updates)
        self.pending_updates.clear()
        
        for base_url, next_url, alias, ep in updates:
            if self.stop_requested: break
            
            self.download_tab_view.url_input.value = next_url
            self.download_tab_view.alias_input.value = alias
            self.page.update()
            
            await self.start_process(None)
            if self.current_task: 
                await self.current_task

    # --- Descarga Logic ---
    async def toggle_pause(self, e):
        if self.is_paused.is_set():
            self.is_paused.clear()
            self.download_tab_view.pause_btn.icon = ft.Icons.PLAY_ARROW
            self.log("[-] Descarga pausada.")
        else:
            self.is_paused.set()
            self.download_tab_view.pause_btn.icon = ft.Icons.PAUSE
            self.log("[+] Descarga reanudada.")
        self.page.update()

    async def stop_process(self, e):
        self.stop_requested = True
        self.is_paused.set()
        self.log("[!] Detención solicitada...")

    async def restart_current(self, e):
        self.log("[!] Reiniciando capítulo actual...")

    async def start_process(self, e):
        self.current_task = None
        self.log("[*] Cargando servicios de red...", type="info")
        lazy_import_network()
        
        url = self.download_tab_view.url_input.value.strip()
        if not url: return

        self.download_tab_view.start_btn.disabled = True
        self.download_tab_view.stop_btn.disabled = False
        self.download_tab_view.pause_btn.disabled = False
        self.download_tab_view.restart_btn.disabled = False
        self.stop_requested = False
        
        # Inicializar estadísticas de sesión
        self.session_start_time = time.time()
        self.total_downloaded_session = 0
        self.chapters_downloaded_count = 0
        
        self.page.update()

        self.current_task = asyncio.create_task(self.main_loop(url))

    async def main_loop(self, start_url):
        async_playwright, _ = lazy_import_network()
        from core.scraper import AnimeScraper
        
        async with async_playwright() as p:
            try:
                browser = await get_browser_instance(p)
                context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
                scraper = AnimeScraper(context)
                await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_())

                current_url = start_url
                while current_url and not self.stop_requested:
                    self.log(f"[*] Navegando a: {current_url}", type="info")
                    page = await context.new_page()
                    try:
                        await page.goto(current_url, wait_until="domcontentloaded")
                        title = await page.title()
                        clean_name = RE_CLEAN_TITLE.sub('', title).replace("— JkAnime", "").strip()
                        ep_match = RE_EPISODE_NUM.findall(clean_name)
                        ep_number = ep_match[0] if ep_match else ""
                        base_anime_name = RE_BASE_NAME.sub('', clean_name).strip() or clean_name
                        
                        self.current_chapter_info = f"Cap {ep_number}"
                        self.download_tab_view.status_text.value = f"Estado: Procesando {clean_name}"
                        self.page.update()
                        
                        self.log(f"[*] Analizando página para {clean_name}...", type="info")
                        next_url = await scraper.get_next_url(page)
                        servers = await scraper.get_server_links(page)
                        thumb_url = await scraper.get_anime_info(page)
                        
                        if "Mediafire" in servers:
                            mf_url = servers["Mediafire"]
                            self.log(f"[*] Servidor MediaFire encontrado, obteniendo enlace directo...", type="info")
                            direct_link, ext = await scraper.get_mediafire_direct_link(mf_url)
                            
                            if direct_link:
                                alias = self.download_tab_view.alias_input.value.strip()
                                base_dir = self.download_tab_view.dir_input.value or os.getcwd()
                                anime_folder = alias or base_anime_name
                                download_dir = os.path.join(base_dir, RE_INVALID_CHARS.sub("", anime_folder))
                                os.makedirs(download_dir, exist_ok=True)

                                filename = f"{alias or base_anime_name} - {ep_number}{ext}"
                                final_path = os.path.join(download_dir, RE_INVALID_CHARS.sub("", filename))
                                
                                self.log(f"[*] Iniciando descarga de: {filename}", type="info")
                                _, aiohttp = lazy_import_network()
                                async with aiohttp.ClientSession(headers={'User-Agent': random.choice(USER_AGENTS)}) as session:
                                    res = await self.downloader.download_chunked(
                                        session, direct_link, final_path, self.update_progress
                                    )
                                    if res:
                                        file_size = os.path.getsize(final_path)
                                        self.total_downloaded_session += file_size
                                        self.chapters_downloaded_count += 1
                                        
                                        self.log(f"[+] Descargado: {filename} ({file_size / (1024*1024):.1f} MB)", type="success")
                                        # Actualizar config
                                        base_url = re.sub(r'\d+/$', '', current_url)
                                        self.config["following"][base_url] = {
                                            "last_chapter": int(ep_number) if ep_number.isdigit() else 0,
                                            "last_url": current_url,
                                            "alias": alias or base_anime_name,
                                            "thumbnail": thumb_url or self.config["following"].get(base_url, {}).get("thumbnail"),
                                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "has_next": next_url is not None,
                                            "download_path": base_dir
                                        }
                                        save_config(self.config)
                                        self.update_library_list()
                                    else:
                                        self.log(f"[!] Falló la descarga de: {filename}", type="error")
                                        if os.path.exists(final_path): os.remove(final_path)
                            else:
                                self.log(f"[!] No se pudo obtener el enlace directo de MediaFire.", type="error")
                        else:
                            self.log(f"[!] No se encontró el servidor MediaFire para este capítulo.", type="warning")

                        current_url = next_url
                        if not current_url:
                            self.log("[*] No hay más capítulos disponibles.", type="info")
                    except Exception as e:
                        self.log(f"Error: {str(e)}", type="error")
                        break
                    finally:
                        await page.close()
            finally:
                # Mostrar resumen final
                if self.chapters_downloaded_count > 0:
                    end_time = time.time()
                    total_time = end_time - self.session_start_time
                    avg_speed = (self.total_downloaded_session / (1024 * 1024)) / total_time if total_time > 0 else 0
                    
                    self.log("="*40, type="info")
                    self.log("       RESUMEN DE DESCARGAS", type="info")
                    self.log("="*40, type="info")
                    self.log(f"• Capítulos descargados: {self.chapters_downloaded_count}", type="info")
                    self.log(f"• Tamaño total: {self.total_downloaded_session / (1024 * 1024):.2f} MB", type="info")
                    self.log(f"• Tiempo total: {total_time:.1f} segundos", type="info")
                    self.log(f"• Velocidad media: {avg_speed:.2f} MB/s", type="info")
                    self.log("="*40, type="info")

                self.download_tab_view.start_btn.disabled = False
                self.download_tab_view.stop_btn.disabled = True
                self.download_tab_view.pause_btn.disabled = True
                self.download_tab_view.restart_btn.disabled = True
                self.download_tab_view.status_text.value = "Estado: Finalizado"
                self.page.update()

    async def update_progress(self, progress, downloaded, total, speed):
        self.download_tab_view.progress_bar.value = progress
        self.download_tab_view.progress_info.value = f"{progress:.1%} | {downloaded/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB | {speed:.2f} MB/s"
        self.download_tab_view.status_text.value = f"Estado: Descargando {self.current_chapter_info} ({progress:.1%})"
        self.page.update()

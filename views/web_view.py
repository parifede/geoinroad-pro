from typing import Awaitable, Callable

import flet as ft
import flet_webview as fwv

from app_config import ROUTE_WEBVIEW, BRAND_ACCENT, BRAND_DARK
from app_state import AppState

_ACCENT = BRAND_ACCENT
_BG = BRAND_DARK


def build_web_view(
    *,
    page: ft.Page,
    state: AppState,
    login_url: str,
    on_open_dashboard: Callable[[], Awaitable[None]],
    on_open_external_login: Callable[[], Awaitable[None]],
    on_reload_login_page: Callable[[], Awaitable[None]],
    on_refresh_webview: Callable[[], Awaitable[None]],
    on_request_work_stats: Callable[[], Awaitable[None]],
    on_report_bug: Callable[[], Awaitable[None]],
    on_logout: Callable[[], Awaitable[None]],
    on_open_vault: Callable[[], Awaitable[None]],
    on_page_started: Callable[[ft.ControlEvent], None],
    on_page_ended: Callable[[ft.ControlEvent], None],
    on_progress: Callable[[ft.ControlEvent], None],
    on_url_change: Callable[[ft.ControlEvent], None],
    on_web_resource_error: Callable[[ft.ControlEvent], None],
    on_console_message: Callable[[object], None],
) -> ft.View:
    page.drawer = None

    if state.supports_embedded_webview(page):
        webview_stack = ft.Stack(
            expand=True,
            controls=[
                ft.Container(
                    top=0,
                    left=0,
                    right=0,
                    height=6,
                    bgcolor=_ACCENT,
                ),
                fwv.WebView(
                    ref=state.webview_ref,
                    expand=True,
                    url=state.last_loaded_url or login_url,
                    bgcolor=ft.Colors.WHITE,
                    on_page_started=on_page_started,
                    on_page_ended=on_page_ended,
                    on_progress=on_progress,
                    on_url_change=on_url_change,
                    on_web_resource_error=on_web_resource_error,
                    on_console_message=on_console_message,
                ),
                ft.Container(
                    top=0,
                    left=0,
                    right=0,
                    height=6,
                    content=ft.ProgressBar(
                        ref=state.web_progress_ref,
                        value=state.web_progress / 100 if state.web_progress else None,
                        color=_ACCENT,
                        bgcolor=ft.Colors.TRANSPARENT,
                    ),
                ),
                _build_quick_menu(
                    page=page,
                    on_refresh_webview=on_refresh_webview,
                    on_request_work_stats=on_request_work_stats,
                    on_report_bug=on_report_bug,
                    on_logout=on_logout,
                ),
            ],
        )
        outer_body = ft.Container(
            expand=True,
            bgcolor=_ACCENT,
            content=ft.SafeArea(
                expand=True,
                avoid_intrusions_bottom=False,
                content=webview_stack,
            ),
        )
    else:
        outer_body = ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                bgcolor=_BG,
                padding=32,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=24,
                    controls=[
                        ft.Image(src="download.png", width=140, fit="contain"),
                        ft.Text(
                            "WebView non disponibile su questa piattaforma.",
                            size=18,
                            weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER,
                            color=ft.Colors.WHITE,
                        ),
                        ft.FilledButton(
                            "Apri nel browser",
                            icon=ft.Icons.OPEN_IN_BROWSER,
                            on_click=lambda _: page.run_task(on_open_external_login),
                            style=ft.ButtonStyle(
                                bgcolor=_ACCENT,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=14),
                            ),
                        ),
                    ],
                ),
            ),
        )

    return ft.View(
        route=ROUTE_WEBVIEW,
        can_pop=False,
        bgcolor=_BG,
        padding=0,
        controls=[outer_body],
    )


def _build_quick_menu(
    *,
    page: ft.Page,
    on_refresh_webview: Callable[[], Awaitable[None]],
    on_request_work_stats: Callable[[], Awaitable[None]],
    on_report_bug: Callable[[], Awaitable[None]],
    on_logout: Callable[[], Awaitable[None]],
) -> ft.Control:
    scrim = ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.WHITE),
        visible=False,
    )
    menu_icon = ft.Icon(ft.Icons.MENU, color=ft.Colors.WHITE, size=26)
    panel = ft.Column(
        left=16,
        bottom=144,
        spacing=8,
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    def set_open(opened: bool) -> None:
        scrim.visible = opened
        panel.visible = opened
        menu_icon.name = ft.Icons.CLOSE if opened else ft.Icons.MENU
        menu_icon.size = 34 if opened else 26
        page.update()

    def run_action(callback: Callable[[], Awaitable[None]]) -> None:
        set_open(False)
        page.run_task(callback)

    def action_button(
        icon: str,
        label: str,
        callback: Callable[[], Awaitable[None]],
        width: int,
    ) -> ft.Control:
        available_width = (page.width or 430) - 32
        button_width = min(width, available_width)
        return ft.Container(
            width=button_width,
            height=54,
            border_radius=999,
            bgcolor="#3F3F3F",
            padding=ft.padding.symmetric(horizontal=16),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=18,
                color=ft.Colors.with_opacity(0.22, ft.Colors.BLACK),
                offset=ft.Offset(0, 8),
            ),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                    ft.Text(
                        label,
                        color=ft.Colors.WHITE,
                        size=15,
                        weight=ft.FontWeight.W_700,
                        no_wrap=True,
                    ),
                ],
            ),
            on_click=lambda _: run_action(callback),
        )

    scrim.on_click = lambda _: set_open(False)
    panel.controls.extend(
        [
            action_button(ft.Icons.REFRESH, "Ricarica", on_refresh_webview, 224),
            action_button(
                ft.Icons.CALENDAR_MONTH,
                "Statistiche lavoro",
                on_request_work_stats,
                224,
            ),
            action_button(ft.Icons.ERROR_OUTLINE, "Segnala bug", on_report_bug, 224),
            action_button(ft.Icons.LOGOUT, "Log out", on_logout, 224),
        ]
    )

    return ft.Stack(
        left=0,
        top=0,
        right=0,
        bottom=0,
        controls=[
            scrim,
            panel,
            ft.Container(
                left=16,
                bottom=56,
                width=64,
                height=64,
                border_radius=18,
                bgcolor="#1A1A1A",
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=18,
                    color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                    offset=ft.Offset(0, 6),
                ),
                alignment=ft.Alignment(0, 0),
                content=menu_icon,
                on_click=lambda _: set_open(not panel.visible),
            ),
        ],
    )

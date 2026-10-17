from typing import Awaitable, Callable

import flet as ft

from app_config import ROUTE_REPORT, BRAND_ACCENT, BRAND_DARK, BRAND_SURFACE
from app_state import AppState

_ACCENT = BRAND_ACCENT
_BG = BRAND_DARK
_SURFACE = BRAND_SURFACE
_CARD = "#FFFFFF"
_TEXT = "#1A1A1A"
_MUTED = "#86868B"
_DIVIDER = "#E5E5EA"

_SHADOW = ft.BoxShadow(
    spread_radius=0,
    blur_radius=10,
    color="#12000000",
    offset=ft.Offset(0, 2),
)


def build_report_view(
    *,
    page: ft.Page,
    state: AppState,
    on_back_to_diary: Callable[[], Awaitable[None]],
    on_send_whatsapp: Callable[[], Awaitable[None]],
    on_copy_report: Callable[[], Awaitable[None]],
    on_copy_report_id: Callable[[], Awaitable[None]],
    on_copy_saved_report: Callable[[str], Awaitable[None]],
) -> ft.View:
    return ft.View(
        route=ROUTE_REPORT,
        can_pop=False,
        bgcolor=_SURFACE,
        padding=0,
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        _header(page, on_back_to_diary),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                                spacing=0,
                                controls=[
                                    ft.Container(height=20),
                                    _report_id_card(page, state, on_copy_report_id),
                                    ft.Container(height=16),
                                    _details_card(state),
                                    ft.Container(height=16),
                                    _actions_card(page, state, on_send_whatsapp, on_copy_report),
                                    ft.Container(height=16),
                                    _saved_reports_card(page, state, on_copy_saved_report),
                                    ft.Container(height=40),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


def _header(page: ft.Page, on_back_to_diary: Callable[[], Awaitable[None]]) -> ft.Control:
    return ft.Container(
        bgcolor=_BG,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.WHITE,
                    icon_size=20,
                    tooltip="Torna al diario",
                    on_click=lambda _: page.run_task(on_back_to_diary),
                ),
                ft.Text(
                    "Report problema",
                    size=18,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.WHITE,
                ),
                ft.Container(width=48),
            ],
        ),
    )


def _report_id_card(
    page: ft.Page,
    state: AppState,
    on_copy_report_id: Callable[[], Awaitable[None]],
) -> ft.Control:
    report_id = state.last_report_id or "—"
    captured_at = str(state.last_report.get("captured_at", ""))[:19].replace("T", " ")
    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text(
                    "Codice problema",
                    size=12,
                    color=_MUTED,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            report_id,
                            size=24,
                            weight=ft.FontWeight.W_800,
                            color=_ACCENT,
                            selectable=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            icon_color=_ACCENT,
                            icon_size=20,
                            tooltip="Copia codice",
                            on_click=lambda _: page.run_task(on_copy_report_id),
                        ),
                    ],
                ),
                ft.Text(
                    f"Generato il {captured_at} UTC" if captured_at else "",
                    size=11,
                    color=_MUTED,
                    visible=bool(captured_at),
                ),
                ft.Text(
                    "Comunica questo codice quando segnali il problema: "
                    "il report completo resta salvato sul dispositivo.",
                    size=12,
                    color=_MUTED,
                ),
                ft.Text(
                    ref=state.report_status_ref,
                    value="",
                    size=12,
                    color=ft.Colors.GREEN_700,
                    weight=ft.FontWeight.W_600,
                ),
            ],
        ),
    )


def _details_card(state: AppState) -> ft.Control:
    report = state.last_report or {}
    details = [
        ("Schermata", str(report.get("route", "") or "n/d")),
        ("Ultima pagina", str(report.get("last_loaded_url", "") or "n/d")),
        ("Stato web", str(report.get("web_status", "") or "n/d")),
        ("Console JS", str(report.get("last_console_message", "") or "n/d")[:160]),
        ("Account", str(report.get("account_id", "") or "n/d")),
    ]
    rows = [
        ft.Column(
            spacing=2,
            controls=[
                ft.Text(label, size=11, color=_MUTED, weight=ft.FontWeight.W_600),
                ft.Text(
                    value,
                    size=13,
                    color=_TEXT,
                    selectable=True,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
        )
        for label, value in details
    ]
    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Dettagli diagnostici", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                ft.Divider(color=_DIVIDER, height=1),
                *rows,
            ],
        ),
    )


def _actions_card(
    page: ft.Page,
    state: AppState,
    on_send_whatsapp: Callable[[], Awaitable[None]],
    on_copy_report: Callable[[], Awaitable[None]],
) -> ft.Control:
    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.FilledButton(
                    "Invia su WhatsApp",
                    icon=ft.Icons.SEND,
                    on_click=lambda _: page.run_task(on_send_whatsapp),
                    style=ft.ButtonStyle(
                        bgcolor=_ACCENT,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.padding.symmetric(horizontal=20, vertical=16),
                    ),
                ),
                ft.OutlinedButton(
                    "Copia report completo",
                    icon=ft.Icons.COPY_ALL,
                    on_click=lambda _: page.run_task(on_copy_report),
                    style=ft.ButtonStyle(
                        color=_TEXT,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.padding.symmetric(horizontal=20, vertical=16),
                    ),
                ),
            ],
        ),
    )


def _saved_reports_card(
    page: ft.Page,
    state: AppState,
    on_copy_saved_report: Callable[[str], Awaitable[None]],
) -> ft.Control:
    entries = state.saved_reports or []
    if not entries:
        body: list[ft.Control] = [
            ft.Text("Nessun report salvato sul dispositivo.", size=13, color=_MUTED),
        ]
    else:
        body = [
            ft.Container(
                padding=ft.padding.symmetric(vertical=8),
                border=ft.border.only(bottom=ft.BorderSide(1, _DIVIDER)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(
                                    entry.get("report_id", ""),
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=_TEXT,
                                    selectable=True,
                                ),
                                ft.Text(
                                    str(entry.get("captured_at", ""))[:19].replace("T", " "),
                                    size=11,
                                    color=_MUTED,
                                ),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            icon_color=_MUTED,
                            icon_size=18,
                            tooltip="Copia questo report",
                            on_click=lambda _, p=entry.get("path", ""): page.run_task(
                                on_copy_saved_report, p
                            ),
                        ),
                    ],
                ),
            )
            for entry in entries
        ]
    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("Report recenti", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                ft.Divider(color=_DIVIDER, height=1),
                *body,
            ],
        ),
    )

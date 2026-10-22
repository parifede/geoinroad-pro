from typing import Awaitable, Callable

import flet as ft

from app_config import ROUTE_LOCK, BRAND_ACCENT, BRAND_DARK
from app_state import AppState

_BG = BRAND_DARK
_CARD = "#242424"
_BORDER = "#333333"
_ACCENT = BRAND_ACCENT
_TEXT_MUTED = "#888888"


def build_lock_screen(
    *,
    page: ft.Page,
    state: AppState,
    on_save_credentials: Callable[[], Awaitable[None]],
    on_unlock: Callable[[], Awaitable[None]],
    on_clear_credentials: Callable[[], Awaitable[None]],
) -> ft.View:
    is_light = getattr(page, "platform_brightness", None) == ft.Brightness.LIGHT
    bg = "#F5F5F7" if is_light else _BG
    card = "#FFFFFF" if is_light else _CARD
    border = "#D8D8DC" if is_light else _BORDER
    text = "#1A1A1A" if is_light else ft.Colors.WHITE
    muted = "#6E6E73" if is_light else _TEXT_MUTED

    return ft.View(
        route=ROUTE_LOCK,
        can_pop=False,
        bgcolor=bg,
        padding=0,
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=32, vertical=0),
                    content=ft.Column(
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            ft.Container(height=48),
                            ft.Image(
                                src="download.png",
                                width=160,
                                fit="contain",
                            ),
                            ft.Container(height=48),
                            ft.Container(
                                content=ft.Column(
                                    spacing=6,
                                    controls=[
                                        ft.Text(
                                            "Accedi",
                                            size=32,
                                            weight=ft.FontWeight.W_700,
                                            color=text,
                                        ),
                                        ft.Text(
                                            "Le credenziali vengono salvate in modo sicuro sul dispositivo.",
                                            size=13,
                                            color=muted,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(height=32),
                            # AutofillGroup consente ad Android di proporre
                            # le credenziali salvate nel telefono.
                            ft.AutofillGroup(
                                content=ft.Column(
                                    spacing=14,
                                    controls=[
                                        ft.TextField(
                                            ref=state.username_field_ref,
                                            label="Username",
                                            value=state.cached_username,
                                            autofill_hints=[
                                                ft.AutofillHint.USERNAME,
                                                ft.AutofillHint.EMAIL,
                                            ],
                                            prefix_icon=ft.Icons.PERSON_OUTLINE,
                                            bgcolor=card,
                                            border_color=border,
                                            focused_border_color=_ACCENT,
                                            color=text,
                                            label_style=ft.TextStyle(color=muted),
                                            cursor_color=_ACCENT,
                                        ),
                                        ft.TextField(
                                            ref=state.password_field_ref,
                                            label="Password",
                                            password=True,
                                            can_reveal_password=True,
                                            autofill_hints=[
                                                ft.AutofillHint.PASSWORD,
                                            ],
                                            prefix_icon=ft.Icons.LOCK_OUTLINE,
                                            bgcolor=card,
                                            border_color=border,
                                            focused_border_color=_ACCENT,
                                            color=text,
                                            label_style=ft.TextStyle(color=muted),
                                            cursor_color=_ACCENT,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(height=10),
                            ft.Text(
                                ref=state.lock_status_ref,
                                value=state.lock_message,
                                size=13,
                                color=muted,
                            ),
                            ft.Container(height=24),
                            ft.Row(
                                controls=[
                                    ft.FilledButton(
                                        "Salva ed Entra",
                                        expand=True,
                                        icon=ft.Icons.ARROW_FORWARD,
                                        on_click=lambda _: page.run_task(on_save_credentials),
                                        style=ft.ButtonStyle(
                                            bgcolor=_ACCENT,
                                            color=ft.Colors.WHITE,
                                            shape=ft.RoundedRectangleBorder(radius=14),
                                            padding=ft.padding.symmetric(vertical=18),
                                        ),
                                    ),
                                ],
                            ),
                            *(
                                [
                                    ft.Container(height=12),
                                    ft.Row(
                                        controls=[
                                            ft.OutlinedButton(
                                                "Sblocca con impronta",
                                                expand=True,
                                                icon=ft.Icons.FINGERPRINT,
                                                on_click=lambda _: page.run_task(on_unlock),
                                                style=ft.ButtonStyle(
                                                    color=_ACCENT,
                                                    side=ft.BorderSide(1, _ACCENT),
                                                    shape=ft.RoundedRectangleBorder(radius=14),
                                                    padding=ft.padding.symmetric(vertical=18),
                                                ),
                                            ),
                                        ],
                                    ),
                                ]
                                if state.gate_locked and state.credentials_available
                                else []
                            ),
                            ft.Container(height=20),
                            ft.TextButton(
                                "Rimuovi credenziali salvate",
                                style=ft.ButtonStyle(color=muted),
                                on_click=lambda _: page.run_task(on_clear_credentials),
                            ),
                            ft.Container(height=32),
                        ],
                    ),
                ),
            ),
        ],
    )

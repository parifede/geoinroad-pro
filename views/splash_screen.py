import asyncio

import flet as ft

from app_config import BRAND_ACCENT, BRAND_DARK, ROUTE_SPLASH


async def _pulse_logo(page: ft.Page, logo_frame: ft.Container) -> None:
    await asyncio.sleep(0.1)
    grow = True
    while getattr(page, "route", None) == ROUTE_SPLASH:
        logo_frame.scale = 1.06 if grow else 0.96
        logo_frame.opacity = 0.94 if grow else 1
        try:
            logo_frame.update()
        except Exception:
            return
        grow = not grow
        await asyncio.sleep(0.72)


def build_splash_view(page: ft.Page) -> ft.View:
    # Sempre scura, come la splash nativa di avvio: un'unica schermata
    # d'ingresso coerente, indipendente dal tema del telefono.
    bg = BRAND_DARK
    muted = "#A1A1A6"
    logo_frame = ft.Container(
        width=180,
        height=180,
        alignment=ft.Alignment(0, 0),
        animate_scale=ft.Animation(720, ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(720, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Image(
            src="splash_mark_dark.png",
            fit=ft.BoxFit.CONTAIN,
            error_content=ft.Image(
                src="icon.png",
                fit=ft.BoxFit.CONTAIN,
            ),
        ),
    )
    if hasattr(page, "run_task"):
        page.run_task(_pulse_logo, page, logo_frame)

    return ft.View(
        route=ROUTE_SPLASH,
        can_pop=False,
        bgcolor=bg,
        padding=0,
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    bgcolor=bg,
                    padding=ft.Padding.symmetric(horizontal=32),
                    content=ft.Column(
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=24,
                        controls=[
                            logo_frame,
                            ft.ProgressRing(
                                width=30,
                                height=30,
                                stroke_width=3,
                                color=BRAND_ACCENT,
                            ),
                            ft.Text(
                                "Caricamento",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=muted,
                            ),
                        ],
                    ),
                ),
            )
        ],
    )

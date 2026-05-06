import asyncio
from pathlib import Path

import flet as ft
import flet_webview as fwv

from app_config import BRAND_ACCENT, BRAND_DARK, ROUTE_SPLASH

_ANIMATED_SPLASH_HTML: str | None = None


def _animated_splash_html() -> str | None:
    global _ANIMATED_SPLASH_HTML
    if _ANIMATED_SPLASH_HTML is not None:
        return _ANIMATED_SPLASH_HTML

    for candidate in (
        Path("assets/geo-in-road-splash-animated.svg"),
        Path("geo-in-road-splash-animated.svg"),
    ):
        if candidate.exists():
            svg = candidate.read_text(encoding="utf-8")
            _ANIMATED_SPLASH_HTML = (
                "<!doctype html><html><head><meta name='viewport' "
                "content='width=device-width,initial-scale=1'>"
                "<style>html,body{margin:0;width:100%;height:100%;"
                "overflow:hidden;background:transparent;display:flex;"
                "align-items:center;justify-content:center}"
                "body>svg{width:100%;height:100%;max-width:100%;"
                "max-height:100%;object-fit:contain}</style>"
                "</head><body>"
                f"{svg}"
                "</body></html>"
            )
            return _ANIMATED_SPLASH_HTML

    return None


async def _load_animated_splash(
    page: ft.Page, webview_ref: ft.Ref[fwv.WebView], html: str
) -> None:
    for _ in range(12):
        if getattr(page, "route", None) != ROUTE_SPLASH:
            return
        if webview_ref.current:
            try:
                await webview_ref.current.load_html(html)
            except Exception:
                return
            return
        await asyncio.sleep(0.05)


async def _pulse_logo(page: ft.Page, logo_frame: ft.Container) -> None:
    await asyncio.sleep(0.1)
    grow = True
    while getattr(page, "route", None) == ROUTE_SPLASH:
        logo_frame.scale = 1.04 if grow else 0.985
        logo_frame.opacity = 0.96 if grow else 1
        try:
            logo_frame.update()
        except Exception:
            return
        grow = not grow
        await asyncio.sleep(0.72)


def build_splash_view(page: ft.Page) -> ft.View:
    is_light = getattr(page, "platform_brightness", None) == ft.Brightness.LIGHT
    bg = "#FFFFFF" if is_light else BRAND_DARK
    muted = "#6E6E73" if is_light else "#A1A1A6"
    frame_bg = "#FFFFFF" if is_light else "#F7F7F7"
    animated_html = _animated_splash_html()
    webview_ref = ft.Ref[fwv.WebView]()
    logo_content = ft.Image(
        src="splash.png",
        fit=ft.BoxFit.CONTAIN,
        error_content=ft.Image(
            src="download.png",
            fit=ft.BoxFit.CONTAIN,
        ),
    )
    logo_frame = ft.Container(
        width=320,
        height=160,
        alignment=ft.Alignment(0, 0),
        bgcolor=frame_bg,
        animate_scale=ft.Animation(720, ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(720, ft.AnimationCurve.EASE_IN_OUT),
        content=(
            fwv.WebView(
                ref=webview_ref,
                url="about:blank",
                bgcolor=ft.Colors.TRANSPARENT,
                expand=True,
            )
            if animated_html
            else logo_content
        ),
    )
    if hasattr(page, "run_task"):
        if animated_html:
            page.run_task(_load_animated_splash, page, webview_ref, animated_html)
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

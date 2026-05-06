import unittest
import struct
from pathlib import Path
from types import SimpleNamespace

import flet as ft
import flet_webview as fwv

from app_config import ROUTE_SPLASH
from views.splash_screen import build_splash_view


class DummyPage(SimpleNamespace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = []

    def run_task(self, func, *args):
        self.tasks.append((func, args))


class SplashScreenTest(unittest.TestCase):
    def test_splash_screen_keeps_logo_inside_fixed_frame(self):
        page = DummyPage(platform_brightness=None)

        view = build_splash_view(page)
        root = view.controls[0].content.content
        logo_frame = root.controls[0]

        self.assertEqual(view.route, ROUTE_SPLASH)
        self.assertEqual(logo_frame.width, 320)
        self.assertEqual(logo_frame.height, 160)
        self.assertIsNotNone(logo_frame.animate_scale)
        self.assertIsNotNone(logo_frame.animate_opacity)

    def test_splash_screen_uses_uploaded_animated_svg(self):
        page = DummyPage(
            platform=ft.PagePlatform.ANDROID,
            platform_brightness=None,
            web=False,
        )

        view = build_splash_view(page)
        root = view.controls[0].content.content
        logo_frame = root.controls[0]

        self.assertIsInstance(logo_frame.content, fwv.WebView)
        self.assertEqual(logo_frame.content.url, "about:blank")
        self.assertEqual(page.tasks[0][0].__name__, "_load_animated_splash")
        self.assertIn("Geo in Road animated loading logo", page.tasks[0][1][2])
        self.assertEqual(page.tasks[1][0].__name__, "_pulse_logo")

    def test_native_splash_and_launcher_sources_are_square(self):
        root = Path(__file__).resolve().parent.parent

        for relative in ("assets/splash.png", "assets/icon.png", "assets/icon_android.png"):
            width, height = _png_size(root / relative)
            self.assertEqual(width, height, relative)


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")
    return struct.unpack(">II", header[16:24])


if __name__ == "__main__":
    unittest.main()

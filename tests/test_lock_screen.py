import unittest

import flet as ft

from app_state import AppState
from views.lock_screen import build_lock_screen


class _DummyPage:
    def run_task(self, func):
        return func


async def _noop():
    return None


class LockScreenTest(unittest.TestCase):
    def test_build_lock_screen_uses_supported_icons(self):
        view = build_lock_screen(
            page=_DummyPage(),
            state=AppState(),
            on_save_credentials=_noop,
            on_unlock=_noop,
            on_clear_credentials=_noop,
        )

        self.assertIsInstance(view, ft.View)


if __name__ == "__main__":
    unittest.main()

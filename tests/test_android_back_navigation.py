import re
import unittest
from pathlib import Path


class AndroidBackNavigationTest(unittest.TestCase):
    def test_system_back_pop_is_disabled_on_app_views(self):
        for path in (
            "views/lock_screen.py",
            "views/web_view.py",
            "views/dashboard.py",
            "views/splash_screen.py",
            "views/report_screen.py",
        ):
            source = Path(path).read_text(encoding="utf-8")
            self.assertIn("can_pop=False", source, path)

    def test_back_from_unlocked_diary_does_not_return_to_login(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def view_pop\(e: ft\.ViewPopEvent\) -> None:\n(?P<body>.*?)(?=\n    page\.on_route_change)",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("state.session_unlocked and popped_route == ROUTE_WEBVIEW", body)
        self.assertIn("await go_to(ROUTE_WEBVIEW)", body)
        self.assertIn("state.session_unlocked and popped_route == ROUTE_DASHBOARD", body)


if __name__ == "__main__":
    unittest.main()

import re
import unittest
from pathlib import Path


class StatsButtonTest(unittest.TestCase):
    def test_stats_button_scrapes_only_when_webview_is_live_then_opens_dashboard(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def request_work_stats\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("page.route == ROUTE_WEBVIEW", body)
        self.assertIn("state.webview_ref.current is not None", body)
        self.assertIn("run_javascript", body)
        self.assertIn("collectStats({background:false})", body)
        self.assertIn("return 'missing'", body)
        self.assertIn("Bridge statistiche non pronto", body)
        self.assertIn("await open_dashboard_fast()", body)

    def test_dashboard_opens_over_live_webview_so_scraping_can_finish(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"def show_overlay_over_live_webview\(route: str, build_overlay\) -> bool:\n"
            r"(?P<body>.*?)(?=\n    def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("view.route == ROUTE_WEBVIEW", body)
        self.assertIn("page.views.append(", body)

        dashboard_match = re.search(
            r"def show_dashboard_over_live_webview\(\) -> bool:\n(?P<body>.*?)(?=\n    def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(dashboard_match)
        self.assertIn("show_overlay_over_live_webview(", dashboard_match.group("body"))
        self.assertIn("build_dashboard_view", dashboard_match.group("body"))

    def test_dashboard_back_and_period_changes_preserve_live_webview_stack(self):
        source = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("def reveal_live_webview() -> bool:", source)
        self.assertIn("if page.route == ROUTE_DASHBOARD and show_dashboard_over_live_webview()", source)
        self.assertIn("if reveal_live_webview():\n            return", source)

    def test_background_stats_start_on_driver_url_change(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"def on_url_change\(e: ft\.ControlEvent\) -> None:\n(?P<body>.*?)(?=\n    def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("state.session_unlocked", body)
        self.assertIn('"/login" not in', body)
        self.assertIn("page.run_task(start_background_stats_sync)", body)

    def test_background_stats_sets_guard_before_waiting(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def start_background_stats_sync\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertLess(
            body.index("state.background_stats_started = True"),
            body.index("await asyncio.sleep"),
        )
        self.assertIn("return 'missing'", body)
        self.assertIn("state.background_stats_started = False", body)

    def test_foreground_quick_stats_payload_opens_dashboard_without_persisting(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def persist_scraped_stats\(payload: dict\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("is_quick_response", body)
        self.assertIn("if is_quick_response and not is_background", body)
        quick_branch = body[
            body.index("if is_quick_response and not is_background") :
            body.index("if not payload or not payload.get")
        ]
        self.assertIn("return", quick_branch)
        self.assertIn("await open_dashboard_fast()", quick_branch)
        self.assertNotIn("save_snapshot", quick_branch)
        self.assertNotIn("go_to(ROUTE_DASHBOARD)", quick_branch)

    def test_full_foreground_stats_refresh_preserves_live_webview_stack(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def persist_scraped_stats\(payload: dict\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        final_branch = body[body.rindex("else:") :]
        self.assertIn("show_dashboard_over_live_webview()", final_branch)
        self.assertIn("await go_to(ROUTE_DASHBOARD)", final_branch)


if __name__ == "__main__":
    unittest.main()

import re
import unittest
from pathlib import Path


class StatsButtonTest(unittest.TestCase):
    def test_stats_collection_works_from_dashboard_overlay_too(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def request_work_stats\(from_date: str = \"\", to_date: str = \"\"\) -> None:\n"
            r"(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        # La WebView vive anche sotto la dashboard in overlay: la raccolta
        # non deve piu' dipendere da page.route == ROUTE_WEBVIEW.
        self.assertIn("webview_is_live()", body)
        self.assertNotIn("page.route == ROUTE_WEBVIEW", body)
        self.assertIn("run_javascript", body)
        self.assertIn("collectStats({options_json})", body)
        self.assertIn('options["from"] = from_date', body)
        self.assertIn("return 'missing'", body)
        self.assertIn("Bridge statistiche non pronto", body)
        self.assertIn("await open_dashboard_fast()", body)

    def test_period_navigation_syncs_missing_periods_from_portal(self):
        source = Path("main.py").read_text(encoding="utf-8")

        # Il tasto sync ricarica il periodo visualizzato...
        self.assertIn("on_refresh_stats=sync_dashboard_period,", source)
        sync_match = re.search(
            r"async def sync_dashboard_period\(\) -> None:\n(?P<body>.*?)(?=\n    def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(sync_match)
        self.assertIn("_period_bounds", sync_match.group("body"))
        self.assertIn(
            "await request_work_stats(start.isoformat(), end.isoformat())",
            sync_match.group("body"),
        )
        self.assertIn("Sincronizzazione", sync_match.group("body"))

        # ...e navigare su un periodo vuoto la avvia da sola, una volta sola.
        empty_match = re.search(
            r"def maybe_sync_empty_period\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(empty_match)
        self.assertIn("state.synced_periods", empty_match.group("body"))
        self.assertIn("page.run_task(sync_dashboard_period)", empty_match.group("body"))
        self.assertIn("maybe_sync_empty_period()", source)

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

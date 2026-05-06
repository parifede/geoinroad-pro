import re
import unittest
from pathlib import Path


class CredentialsFlowTest(unittest.TestCase):
    def test_initialize_app_shows_login_without_waiting_for_timelog_refresh(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def initialize_app\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("await asyncio.sleep(0.4)", body)
        self.assertNotIn("timelog_repository.initialize", body)
        self.assertNotIn("await refresh_timelog_data()", body)
        self.assertIn("page.run_task(ensure_timelog_repository)", body)
        self.assertIn("page.run_task(refresh_timelog_data)", body)

    def test_save_credentials_enters_webview_before_background_vault_write(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def save_credentials\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("page.run_task(save_credentials_in_background", body)
        self.assertIn("await go_to(ROUTE_WEBVIEW)", body)
        self.assertLess(
            body.index("page.run_task(save_credentials_in_background"),
            body.index("await go_to(ROUTE_WEBVIEW)"),
        )
        self.assertNotIn("await credential_store.save_credentials", body)


if __name__ == "__main__":
    unittest.main()

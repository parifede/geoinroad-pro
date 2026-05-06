import re
import unittest
from pathlib import Path


class LogoutBehaviorTest(unittest.TestCase):
    def test_logout_clears_credentials_and_account_log(self):
        source = Path("main.py").read_text(encoding="utf-8")
        match = re.search(
            r"async def logout\(\) -> None:\n(?P<body>.*?)(?=\n    async def )",
            source,
            flags=re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn("credential_store.clear_credentials", body)
        self.assertIn("clear_account_data", body)
        self.assertIn("await go_to(ROUTE_LOCK)", body)


if __name__ == "__main__":
    unittest.main()

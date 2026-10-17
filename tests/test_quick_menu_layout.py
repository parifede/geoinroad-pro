import unittest
from pathlib import Path


class QuickMenuLayoutTest(unittest.TestCase):
    def test_menu_button_keeps_clearance_from_virtual_navigation_bar(self):
        source = Path("views/web_view.py").read_text(encoding="utf-8")
        self.assertIn("bottom=56", source)
        self.assertIn("bottom=144", source)
        self.assertNotIn("bottom=24", source)

    def test_menu_offers_credentials_shortcut_for_password_changes(self):
        source = Path("views/web_view.py").read_text(encoding="utf-8")
        self.assertIn('"Credenziali", on_open_vault', source)


if __name__ == "__main__":
    unittest.main()

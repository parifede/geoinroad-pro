import unittest

from services.bug_report import build_whatsapp_report_url, normalize_whatsapp_number
from app_config import BUG_REPORT_WHATSAPP_NUMBER


class BugReportTest(unittest.TestCase):
    def test_normalize_whatsapp_number_keeps_international_digits(self):
        self.assertEqual(normalize_whatsapp_number("+39 333 123 4567"), "393331234567")

    def test_build_whatsapp_report_url_prefills_encoded_report(self):
        url = build_whatsapp_report_url("+39 333 123 4567", "Errore stats\nOre: 0")

        self.assertEqual(
            url,
            "https://wa.me/393331234567?text=Errore%20stats%0AOre%3A%200",
        )

    def test_build_whatsapp_report_url_is_empty_without_number(self):
        self.assertEqual(build_whatsapp_report_url("", "Report"), "")

    def test_configured_company_whatsapp_number_builds_valid_link(self):
        url = build_whatsapp_report_url(BUG_REPORT_WHATSAPP_NUMBER, "Report")

        self.assertEqual(url, "https://wa.me/393346867229?text=Report")


if __name__ == "__main__":
    unittest.main()

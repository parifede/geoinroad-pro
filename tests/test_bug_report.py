import json
import re
import shutil
import unittest
from pathlib import Path

from services.bug_report import (
    build_report_id,
    build_report_text,
    build_whatsapp_report_url,
    list_saved_reports,
    normalize_whatsapp_number,
    save_report,
)
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

    def test_report_id_is_deterministic_and_well_formed(self):
        report = {
            "captured_at": "2026-05-06T21:52:00+00:00",
            "route": "/diario",
            "web_status": "Errore WebView: timeout",
        }

        report_id = build_report_id(report)

        self.assertRegex(report_id, r"^GIR-260506-[0-9A-F]{6}$")
        self.assertEqual(report_id, build_report_id(report))
        self.assertEqual(report_id, build_report_id({**report, "report_id": report_id}))
        self.assertNotEqual(
            report_id,
            build_report_id({**report, "web_status": "altro errore"}),
        )

    def test_report_text_starts_with_report_id(self):
        report = {"captured_at": "2026-05-06T21:52:00+00:00", "route": "/diario"}
        report["report_id"] = build_report_id(report)

        text = build_report_text(report)

        first_line, _, body = text.partition("\n")
        self.assertEqual(first_line, f"Report {report['report_id']}")
        self.assertEqual(json.loads(body)["route"], "/diario")

    def test_save_and_list_reports_roundtrip_newest_first(self):
        base_dir = Path.cwd() / "tmp-test" / "bug_reports_roundtrip"
        shutil.rmtree(base_dir, ignore_errors=True)

        older = {"captured_at": "2026-05-05T08:00:00+00:00", "route": "/diario"}
        newer = {"captured_at": "2026-05-06T08:00:00+00:00", "route": "/statistiche"}
        save_report(base_dir, older)
        newer_path = save_report(base_dir, newer)

        entries = list_saved_reports(base_dir)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["captured_at"], "2026-05-06T08:00:00+00:00")
        self.assertEqual(entries[0]["path"], str(newer_path))
        self.assertTrue(entries[0]["report_id"].startswith("GIR-260506-"))
        saved = json.loads(newer_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["report_id"], entries[0]["report_id"])

        shutil.rmtree(base_dir, ignore_errors=True)

    def test_list_reports_is_empty_for_missing_directory(self):
        self.assertEqual(
            list_saved_reports(Path.cwd() / "tmp-test" / "missing_reports_dir"),
            [],
        )


if __name__ == "__main__":
    unittest.main()

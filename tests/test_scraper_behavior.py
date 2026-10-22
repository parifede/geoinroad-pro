import json
import shutil
import subprocess
import unittest
from pathlib import Path

_HARNESS = Path(__file__).resolve().parent / "js" / "scraper_harness.js"


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class ScraperBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = subprocess.run(
            ["node", str(_HARNESS)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        cls.results = json.loads(output)

    def test_page_date_comes_from_the_page_not_the_url(self):
        # Il portale ignora ?date= e mostra oggi: il turno resta su oggi
        # invece di finire sul giorno chiesto nell'URL.
        self.assertEqual(self.results["shown_date_wins"], ["2026-10-22"])
        self.assertEqual(self.results["current_page_rows"], ["2026-10-22"])

    def test_rows_are_dropped_when_the_page_date_cannot_be_verified(self):
        self.assertEqual(self.results["unverified_date_rows"], 0)

    def test_day_types_are_learned_only_from_past_days(self):
        # Il sabato futuro mostra la presenza pianificata (W): non deve
        # insegnare che activity 6 (riposo) significa "presente".
        self.assertEqual(self.results["learned"], 1)
        self.assertEqual(self.results["map_keys"], ["a:9"])

    def test_api_absences_use_learned_markers(self):
        rows = {row[0]: row[1:] for row in self.results["api_rows"]}
        # Ferie imparate dal calendario: sigla FA e 8 ore pagate.
        self.assertEqual(
            rows["2026-08-10"],
            ["FA", "8.00", "geoinroad_api/employees/driver_calendar-default"],
        )
        # Activity mai vista: riposo generico, nessuna ora.
        self.assertEqual(rows["2026-08-11"][:2], ["R", "0"])
        self.assertEqual(rows["2026-08-12"][1], "8.83")
        # Assenze future non ancora definitive: ignorate.
        self.assertNotIn("2026-10-25", rows)

    def test_default_hours_are_counted_once_per_day(self):
        self.assertEqual(self.results["default_rows_per_day"], 1)


if __name__ == "__main__":
    unittest.main()

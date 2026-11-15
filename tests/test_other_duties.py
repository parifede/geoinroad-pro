import tempfile
import unittest
from pathlib import Path

from services.timelog_repository import TimelogRepository


class OtherDutiesDayTest(unittest.TestCase):
    """AA "altri adempimenti": giornata rosa, ore solo se il portale le da'."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = TimelogRepository()
        self.repo.db_path = Path(self._tmp.name) / "aa.sqlite3"
        self.repo._ensure_schema()

    def tearDown(self):
        self._tmp.cleanup()

    def test_aa_days_are_typed_with_or_without_hours(self):
        self.repo._save_snapshot_sync(
            self.repo.db_path,
            {
                "captured_at": "2026-09-30T10:00:00+00:00",
                "sync_range": {"from": "2026-09-01", "to": "2026-09-30"},
                "rows": [
                    # Con orario dal portale: ore pagate e giornata AA.
                    {"label": "Turno 08:00-15:00", "value": "7.00", "date": "2026-09-01",
                     "status": "Altri adempimenti", "work_marker": "AA"},
                    {"label": "Turno 08:00-15:00", "value": "7.00", "date": "2026-09-01",
                     "source": "geoinroad_api/planner/route"},
                    # Senza orario: nessuna ora inventata.
                    {"label": "MAR 2 Altri adempimenti (HPI7)", "value": "0",
                     "date": "2026-09-02", "status": "Altri adempimenti", "work_marker": "AA"},
                ],
            },
            account_id="acc",
        )
        daily = self.repo._fetch_period_daily_totals_sync(
            self.repo.db_path, account_id="acc", period="week", anchor_date="2026-09-01"
        )
        by_day = {item["day"]: item for item in daily}

        self.assertEqual(by_day["2026-09-01"]["status"], "adempimenti")
        self.assertAlmostEqual(by_day["2026-09-01"]["total_value"], 7.0)
        self.assertEqual(by_day["2026-09-02"]["status"], "adempimenti")
        self.assertEqual(by_day["2026-09-02"]["total_value"], 0)


if __name__ == "__main__":
    unittest.main()

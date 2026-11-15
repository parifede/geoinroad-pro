import tempfile
import unittest
from datetime import date
from pathlib import Path

from services.history_sync import (
    EMPTY_MONTHS_TO_STOP,
    HISTORY_COMPLETE,
    HISTORY_PAUSED,
    HISTORY_STOPPED,
    run_history,
    MONTH_DONE,
    MONTH_EMPTY,
    history_is_complete,
    month_bounds,
    next_history_month,
    payload_is_complete,
    payload_is_empty,
)
from services.timelog_repository import TimelogRepository

_TODAY = date(2026, 11, 15)


class HistoryPlanTest(unittest.TestCase):
    def test_starts_from_the_previous_month(self):
        # Il mese in corso lo aggiorna gia' la sincronizzazione normale.
        self.assertEqual(next_history_month(_TODAY, {}), "2026-10")

    def test_goes_back_across_years_skipping_done_months(self):
        months = {f"2026-{m:02d}": MONTH_DONE for m in range(1, 11)}
        self.assertEqual(next_history_month(_TODAY, months), "2025-12")

    def test_stops_after_a_full_empty_year(self):
        months = {"2026-10": MONTH_DONE, "2026-09": MONTH_DONE}
        key_year, key_month = 2026, 8
        for _ in range(EMPTY_MONTHS_TO_STOP):
            months[f"{key_year}-{key_month:02d}"] = MONTH_EMPTY
            key_month -= 1
            if key_month == 0:
                key_year, key_month = key_year - 1, 12
        self.assertIsNone(next_history_month(_TODAY, months))
        self.assertTrue(history_is_complete(_TODAY, months))

    def test_a_short_gap_does_not_stop_the_history(self):
        # Es. una lunga assenza: pochi mesi vuoti non bastano a fermarsi.
        months = {"2026-10": MONTH_EMPTY, "2026-09": MONTH_EMPTY, "2026-08": MONTH_DONE}
        self.assertEqual(next_history_month(_TODAY, months), "2026-07")

    def test_a_new_month_makes_the_previous_one_due(self):
        months = {"2026-10": MONTH_DONE}
        self.assertEqual(next_history_month(date(2026, 12, 1), months), "2026-11")

    def test_month_bounds(self):
        self.assertEqual(
            month_bounds("2024-02"), (date(2024, 2, 1), date(2024, 2, 29))
        )
        self.assertEqual(
            month_bounds("2025-12"), (date(2025, 12, 1), date(2025, 12, 31))
        )

    def test_payload_classification(self):
        self.assertFalse(payload_is_complete({"rows": []}))
        self.assertTrue(payload_is_complete({"sync_range": {"from": "a", "to": "b"}}))
        rest_only = {"rows": [{"value": "0", "work_marker": "R"}, {"value": "0"}]}
        self.assertTrue(payload_is_empty(rest_only))
        self.assertFalse(payload_is_empty({"rows": [{"value": "8.00", "work_marker": "S"}]}))
        # Malattia senza ore: il mese non e' vuoto, si lavorava gia'.
        self.assertFalse(payload_is_empty({"rows": [{"value": "0", "work_marker": "M"}]}))


_COMPLETE = {"sync_range": {"from": "x", "to": "y"}}
_WORKED = {**_COMPLETE, "rows": [{"value": "8.00", "work_marker": "S"}]}


class _FakePortal:
    """Portale finto: mesi lavorati fino a una data, poi vuoti."""

    def __init__(self, first_worked_month: str, failing=()) -> None:
        self.first_worked_month = first_worked_month
        self.failing = list(failing)
        self.saved = {}
        self.requested = []
        self.statuses = []
        self.active = True

    async def fetch_months(self):
        return dict(self.saved)

    async def collect_month(self, month):
        self.requested.append(month)
        if self.failing and self.failing[0] == month:
            self.failing.pop(0)
            return {}
        return _WORKED if month >= self.first_worked_month else _COMPLETE

    async def mark_month(self, month, status):
        self.saved[month] = status

    def is_active(self):
        return self.active

    async def sleep(self, _seconds):
        return None

    async def run(self, today=_TODAY):
        return await run_history(
            today=lambda: today,
            fetch_months=self.fetch_months,
            collect_month=self.collect_month,
            mark_month=self.mark_month,
            is_active=self.is_active,
            set_status=self.statuses.append,
            sleep=self.sleep,
        )


class HistoryRunTest(unittest.IsolatedAsyncioTestCase):
    async def test_downloads_newest_first_and_stops_after_an_empty_year(self):
        portal = _FakePortal(first_worked_month="2026-03")

        self.assertEqual(await portal.run(), HISTORY_COMPLETE)

        # Da ottobre 2026 indietro fino a marzo, poi 12 mesi vuoti e stop.
        self.assertEqual(portal.requested[0], "2026-10")
        self.assertEqual(portal.requested[7], "2026-03")
        self.assertEqual(len(portal.requested), 8 + EMPTY_MONTHS_TO_STOP)
        self.assertEqual(portal.requested[-1], "2025-03")
        self.assertEqual(portal.saved["2026-03"], MONTH_DONE)
        self.assertEqual(portal.saved["2026-02"], MONTH_EMPTY)
        self.assertEqual(portal.statuses[0], "Storico: scarico ottobre 2026...")
        self.assertEqual(portal.statuses[-1], "")

    async def test_finished_history_never_touches_the_portal_again(self):
        portal = _FakePortal(first_worked_month="2026-03")
        await portal.run()
        portal.requested.clear()

        # Riavvio: stessi mesi in SQLite, nessuna richiesta.
        self.assertEqual(await portal.run(), HISTORY_COMPLETE)
        self.assertEqual(portal.requested, [])

    async def test_resumes_where_it_stopped(self):
        portal = _FakePortal(first_worked_month="2020-01")
        calls = {"n": 0}

        def stop_after_three():
            calls["n"] += 1
            return calls["n"] <= 3

        portal.is_active = stop_after_three
        self.assertEqual(await portal.run(), HISTORY_STOPPED)
        done_before = set(portal.saved)

        portal.is_active = lambda: True
        portal.requested.clear()
        portal.first_worked_month = "2026-09"
        await portal.run()

        # Ottobre era finito e segnato; settembre era a meta' quando l'app
        # si e' fermata, quindi si riparte proprio da settembre.
        self.assertEqual(done_before, {"2026-10"})
        self.assertFalse(done_before & set(portal.requested))
        self.assertEqual(portal.requested[0], "2026-09")

    async def test_a_failed_month_is_retried_then_paused_without_marking(self):
        portal = _FakePortal(first_worked_month="2026-01", failing=["2026-10", "2026-10"])

        self.assertEqual(await portal.run(), HISTORY_PAUSED)

        self.assertEqual(portal.requested, ["2026-10", "2026-10"])
        self.assertEqual(portal.saved, {})
        self.assertIn("pausa", portal.statuses[-1])

    async def test_a_single_failure_is_retried(self):
        portal = _FakePortal(first_worked_month="2026-09", failing=["2026-10"])

        self.assertEqual(await portal.run(), HISTORY_COMPLETE)

        self.assertEqual(portal.requested[:2], ["2026-10", "2026-10"])
        self.assertEqual(portal.saved["2026-10"], MONTH_DONE)


class HistoryRepositoryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "history.sqlite3"

    def tearDown(self):
        self._tmp.cleanup()

    def _repo(self) -> TimelogRepository:
        repo = TimelogRepository()
        repo.db_path = self.db_path
        repo._ensure_schema()
        return repo

    def test_history_survives_a_restart(self):
        repo = self._repo()
        repo._mark_history_month_sync(self.db_path, "acc", "2026-10", MONTH_DONE)
        repo._mark_history_month_sync(self.db_path, "acc", "2026-09", MONTH_EMPTY)

        reopened = self._repo()
        self.assertEqual(
            reopened._fetch_history_months_sync(self.db_path, "acc"),
            {"2026-10": MONTH_DONE, "2026-09": MONTH_EMPTY},
        )

    def test_history_is_per_account_and_cleared_at_logout(self):
        repo = self._repo()
        repo._mark_history_month_sync(self.db_path, "acc", "2026-10", MONTH_DONE)
        repo._mark_history_month_sync(self.db_path, "other", "2026-10", MONTH_DONE)

        repo._clear_account_data_sync(self.db_path, "acc")

        self.assertEqual(repo._fetch_history_months_sync(self.db_path, "acc"), {})
        self.assertEqual(
            repo._fetch_history_months_sync(self.db_path, "other"),
            {"2026-10": MONTH_DONE},
        )


if __name__ == "__main__":
    unittest.main()

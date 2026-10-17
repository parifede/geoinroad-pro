import json
import os
import time
import unittest
from pathlib import Path

from services.timelog_repository import TimelogRepository


class TimelogRepositoryTest(unittest.TestCase):
    def test_save_and_read_snapshot(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_timelogs_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        payload = {
            "captured_at": "2026-05-01T10:00:00+00:00",
            "url": "https://example.test",
            "rows": [
                {"label": "ore", "value": "7.5", "raw": "ore 7.5"},
                {"label": "straordinari", "value": "1.25", "raw": "straordinari 1.25"},
            ],
        }

        repo._save_snapshot_sync(repo.db_path, payload)
        summary = repo._fetch_summary_sync(repo.db_path)
        recent = repo._fetch_recent_entries_sync(repo.db_path, 10)
        daily = repo._fetch_daily_totals_sync(repo.db_path, 7)

        self.assertEqual(summary["total_entries"], 2)
        self.assertAlmostEqual(summary["total_value"], 8.75)
        self.assertEqual(len(recent), 2)
        self.assertEqual(len(daily), 1)
        self.assertAlmostEqual(daily[0]["total_value"], 8.75)

    def test_account_snapshot_updates_same_work_day_and_writes_json_log(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_account_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        log_dir = test_dir / "account_logs"
        if log_dir.exists():
            for child in log_dir.iterdir():
                child.unlink()
        repo._ensure_schema()

        first_payload = {
            "captured_at": "2026-05-04T07:00:00+00:00",
            "url": "https://geoinroad.dimetior.com/diary",
            "rows": [
                {
                    "label": "Turno 06:25-15:30",
                    "value": "9.08",
                    "raw": "DATA: 04/05/2026 Turno 06:25 - 15:30",
                    "date": "2026-05-04",
                }
            ],
        }
        second_payload = {
            "captured_at": "2026-05-11T08:00:00+00:00",
            "url": "https://geoinroad.dimetior.com/diary",
            "rows": [
                {
                    "label": "Turno 06:25-15:40",
                    "value": "9.25",
                    "raw": "DATA: 04/05/2026 Turno 06:25 - 15:40 aggiornato",
                    "date": "2026-05-04",
                }
            ],
        }

        account_id = repo.account_id_for_username("rewq3798@gmail.com")
        repo._save_snapshot_sync(repo.db_path, first_payload, account_id=account_id)
        repo._save_snapshot_sync(repo.db_path, second_payload, account_id=account_id)

        summary = repo._fetch_summary_sync(repo.db_path, account_id=account_id)
        recent = repo._fetch_recent_entries_sync(repo.db_path, 10, account_id=account_id)
        log_path = repo.account_log_path(account_id)

        self.assertEqual(summary["total_entries"], 1)
        self.assertAlmostEqual(summary["total_value"], 9.25)
        self.assertEqual(recent[0]["label"], "Turno 06:25-15:40")
        self.assertEqual(recent[0]["work_date"], "2026-05-04")
        self.assertTrue(log_path.exists())
        self.assertIn('"account_id"', log_path.read_text(encoding="utf-8"))

    def test_zero_rows_do_not_affect_summaries_or_daily_totals(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_zero_rows_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        payload = {
            "captured_at": "2026-05-05T08:00:00+00:00",
            "url": "https://geoinroad.dimetior.com/diary",
            "rows": [
                {"label": "Presente no route", "value": "0", "raw": "W", "date": "2026-05-05"},
                {"label": "Turno 06:25-15:40", "value": "9.25", "raw": "turno", "date": "2026-05-04"},
            ],
        }

        repo._save_snapshot_sync(repo.db_path, payload)

        summary = repo._fetch_summary_sync(repo.db_path)
        recent = repo._fetch_recent_entries_sync(repo.db_path, 10)
        daily = repo._fetch_daily_totals_sync(repo.db_path, 14)

        self.assertEqual(summary["total_entries"], 1)
        self.assertAlmostEqual(summary["total_value"], 9.25)
        self.assertEqual(len(recent), 1)
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["day"], "2026-05-04")

    def test_empty_snapshot_still_writes_account_debug_log(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_empty_snapshot_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        account_id = "zero@example.test"
        payload = {
            "captured_at": "2026-05-06T10:00:00+00:00",
            "url": "https://geoinroad.dimetior.com/driver",
            "rows": [],
            "debug": {"reason": "no rows found"},
        }

        repo._save_snapshot_sync(repo.db_path, payload, account_id=account_id)

        log_path = repo.account_log_path(account_id)
        self.assertTrue(log_path.exists())
        data = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual(data["account_id"], account_id)
        self.assertEqual(data["latest_payload"]["debug"]["reason"], "no rows found")
        self.assertEqual(data["entries"], [])

    def test_fetch_period_totals_filters_by_day_site_week_month_and_year(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_period_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()
        account_id = "acct_test"

        payload = {
            "captured_at": "2026-05-11T08:00:00+00:00",
            "url": "https://example.test",
            "rows": [
                {"label": "oggi", "value": "8", "raw": "oggi", "date": "2026-05-04"},
                {"label": "settimana", "value": "7", "raw": "settimana", "date": "2026-05-06"},
                {"label": "domenica inclusa", "value": "3", "raw": "domenica", "date": "2026-05-03"},
                {"label": "mese", "value": "6", "raw": "mese", "date": "2026-04-20"},
                {"label": "anno", "value": "5", "raw": "anno", "date": "2026-01-15"},
                {"label": "domenica successiva esclusa", "value": "9", "raw": "domenica", "date": "2026-05-10"},
                {"label": "vecchio", "value": "4", "raw": "vecchio", "date": "2025-12-31"},
            ],
        }
        repo._save_snapshot_sync(repo.db_path, payload, account_id=account_id)

        self.assertAlmostEqual(
            repo._fetch_period_summary_sync(
                repo.db_path, account_id=account_id, period="day", anchor_date="2026-05-04"
            )["total_value"],
            8,
        )
        self.assertAlmostEqual(
            repo._fetch_period_summary_sync(
                repo.db_path, account_id=account_id, period="week", anchor_date="2026-05-04"
            )["total_value"],
            18,
        )
        self.assertAlmostEqual(
            repo._fetch_period_summary_sync(
                repo.db_path, account_id=account_id, period="month", anchor_date="2026-05-04"
            )["total_value"],
            27,
        )
        self.assertAlmostEqual(
            repo._fetch_period_summary_sync(
                repo.db_path, account_id=account_id, period="year", anchor_date="2026-05-04"
            )["total_value"],
            38,
        )

    def test_fetch_month_daily_totals_returns_every_day_in_calendar_month(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_month_days_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()
        account_id = "acct_test"

        payload = {
            "captured_at": "2026-05-04T08:00:00+00:00",
            "url": "https://example.test",
            "rows": [
                {"label": "aprile", "value": "7", "raw": "aprile", "date": "2026-04-30"},
                {"label": "maggio", "value": "8", "raw": "maggio", "date": "2026-05-04"},
                {"label": "giugno", "value": "9", "raw": "giugno", "date": "2026-06-01"},
            ],
        }
        repo._save_snapshot_sync(repo.db_path, payload, account_id=account_id)

        daily = repo._fetch_month_daily_totals_sync(
            repo.db_path,
            account_id=account_id,
            anchor_date="2026-05-04",
        )

        self.assertEqual(len(daily), 31)
        self.assertEqual(daily[0]["day"], "2026-05-01")
        self.assertEqual(daily[-1]["day"], "2026-05-31")
        self.assertAlmostEqual(daily[3]["total_value"], 8)
        self.assertEqual(daily[0]["entries"], 0)

    def test_fetch_period_daily_totals_matches_selected_day_and_site_week(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_period_days_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()
        account_id = "acct_test"
        repo._save_snapshot_sync(
            repo.db_path,
            {
                "captured_at": "2026-05-09T08:00:00+00:00",
                "url": "https://geoinroad.dimetior.com/driver/calendar",
                "rows": [
                    {"label": "Domenica", "value": 1, "date": "2026-05-03"},
                    {"label": "Mercoledi", "value": 8.5, "date": "2026-05-06"},
                    {"label": "Sabato", "value": 7, "date": "2026-05-09"},
                    {"label": "Fuori settimana", "value": 9, "date": "2026-05-10"},
                ],
            },
            account_id=account_id,
        )

        day = repo._fetch_period_daily_totals_sync(
            repo.db_path,
            account_id=account_id,
            period="day",
            anchor_date="2026-05-06",
        )
        week = repo._fetch_period_daily_totals_sync(
            repo.db_path,
            account_id=account_id,
            period="week",
            anchor_date="2026-05-06",
        )

        self.assertEqual([item["day"] for item in day], ["2026-05-06"])
        self.assertEqual(day[0]["total_value"], 8.5)
        self.assertEqual(week[0]["day"], "2026-05-03")
        self.assertEqual(week[-1]["day"], "2026-05-09")
        self.assertEqual(
            [item["total_value"] for item in week],
            [1.0, 0.0, 0.0, 8.5, 0.0, 0.0, 7.0],
        )

    def test_day_states_are_saved_and_returned_with_daily_totals(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_day_states_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()
        account_id = "acct_states"

        repo._save_snapshot_sync(
            repo.db_path,
            {
                "captured_at": "2026-05-08T10:00:00+00:00",
                "url": "https://example.test/driver/calendar",
                "rows": [
                    {"label": "Turno 06:00-14:00", "value": 8, "date": "2026-05-04"},
                    {"label": "MAR 5 Libero (ROMA)", "value": 0, "date": "2026-05-05",
                     "status": "Libero", "work_marker": "R"},
                    {"label": "MER 6 Ferie (ROMA)", "value": 0, "date": "2026-05-06",
                     "status": "Ferie", "work_marker": "R"},
                    {"label": "GIO 7 Presente no route (ROMA)", "value": 0,
                     "date": "2026-05-07", "status": "Presente no route",
                     "work_marker": "W"},
                    {"label": "VEN 8 Congedo straord. (ROMA)", "value": 0,
                     "date": "2026-05-08", "status": "Congedo straord.",
                     "work_marker": "R"},
                ],
            },
            account_id=account_id,
        )

        daily = repo._fetch_period_daily_totals_sync(
            repo.db_path,
            account_id=account_id,
            period="week",
            anchor_date="2026-05-06",
        )
        status_by_day = {item["day"]: item["status"] for item in daily}

        self.assertEqual(status_by_day["2026-05-04"], "lavorato")
        self.assertEqual(status_by_day["2026-05-05"], "riposo")
        self.assertEqual(status_by_day["2026-05-06"], "ferie")
        self.assertEqual(status_by_day["2026-05-07"], "lavorato")
        self.assertEqual(status_by_day["2026-05-08"], "assenza")
        self.assertEqual(status_by_day["2026-05-09"], "")

        repo._clear_account_data_sync(repo.db_path, account_id)
        with repo._connect(repo.db_path) as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM day_states WHERE account_id = ?",
                (account_id,),
            ).fetchone()[0]
        self.assertEqual(remaining, 0)

    def test_one_time_cleanup_removes_legacy_keyword_and_implausible_rows(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_cleanup_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        with repo._connect(repo.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO timelogs (
                    account_id, entry_key, captured_at, work_date,
                    source_url, label, value, raw, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}')
                """,
                [
                    ("acct", "2026-05-06|turno 06:00-14:00", "2026-05-06T10:00:00+00:00",
                     "2026-05-06", "u", "Turno 06:00-14:00", 8.0, ""),
                    ("acct", "2026-05-06|totale", "2026-05-06T10:00:00+00:00",
                     "2026-05-06", "u", "Totale", 173.0, ""),
                    ("acct", "2026-05-07|ore", "2026-05-07T10:00:00+00:00",
                     "2026-05-07", "u", "ore", 8.5, ""),
                    ("acct", "2026-05-08|dato strano", "2026-05-08T10:00:00+00:00",
                     "2026-05-08", "u", "dato strano", 99.0, ""),
                ],
            )
            # Simula un database pre-migrazione.
            conn.execute("DELETE FROM app_meta WHERE key = 'cleanup_legacy_rows'")
            conn.commit()

        repo._ensure_schema()

        with repo._connect(repo.db_path) as conn:
            labels = {
                row[0]
                for row in conn.execute(
                    "SELECT label FROM timelogs WHERE account_id = 'acct'"
                ).fetchall()
            }
            flag = conn.execute(
                "SELECT value FROM app_meta WHERE key = 'cleanup_legacy_rows'"
            ).fetchone()

        self.assertEqual(labels, {"Turno 06:00-14:00"})
        self.assertEqual(flag[0], "done")

        # La pulizia e' una tantum: nuove righe keyword plausibili sopravvivono.
        with repo._connect(repo.db_path) as conn:
            conn.execute(
                """
                INSERT INTO timelogs (
                    account_id, entry_key, captured_at, work_date,
                    source_url, label, value, raw, payload
                )
                VALUES ('acct', '2026-05-09|ore', '2026-05-09T10:00:00+00:00',
                        '2026-05-09', 'u', 'ore', 8.0, '', '{}')
                """
            )
            conn.commit()
        repo._ensure_schema()
        with repo._connect(repo.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM timelogs WHERE account_id = 'acct'"
            ).fetchone()[0]
        self.assertEqual(count, 2)

    @unittest.skipUnless(hasattr(time, "tzset"), "richiede time.tzset (Unix)")
    def test_capture_day_uses_device_timezone_not_utc(self):
        original_tz = os.environ.get("TZ")
        os.environ["TZ"] = "Europe/Rome"
        time.tzset()
        try:
            # 22:30 UTC = 00:30 del giorno dopo a Roma (ora legale):
            # il giorno di cattura deve essere quello locale.
            parsed = TimelogRepository._parse_date("2026-05-06T22:30:00+00:00")
            self.assertEqual(parsed.isoformat(), "2026-05-07")
            # Una data secca resta invariata.
            parsed_plain = TimelogRepository._parse_date("2026-05-06")
            self.assertEqual(parsed_plain.isoformat(), "2026-05-06")
        finally:
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()

    def test_saved_rows_store_slim_per_row_payload(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_slim_payload_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        repo._save_snapshot_sync(
            repo.db_path,
            {
                "captured_at": "2026-05-06T10:00:00+00:00",
                "url": "https://example.test",
                "debug": {"text_sample": "x" * 600},
                "rows": [
                    {"label": "Turno 06:00-10:00", "value": 4, "date": "2026-05-06"},
                    {"label": "Turno 14:00-18:00", "value": 4, "date": "2026-05-06"},
                ],
            },
            account_id="acct_slim",
        )

        with repo._connect(repo.db_path) as conn:
            stored = conn.execute(
                "SELECT payload FROM timelogs WHERE account_id = ?",
                ("acct_slim",),
            ).fetchall()

        self.assertEqual(len(stored), 2)
        for (raw_payload,) in stored:
            data = json.loads(raw_payload)
            self.assertNotIn("rows", data)
            self.assertNotIn("debug", data)
            self.assertIn(data["label"], {"Turno 06:00-10:00", "Turno 14:00-18:00"})

    def test_future_planned_rows_after_capture_day_are_ignored(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_future_rows_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()
        account_id = "acct_test"

        repo._save_snapshot_sync(
            repo.db_path,
            {
                "captured_at": "2026-05-06T21:52:00+00:00",
                "url": "https://geoinroad.dimetior.com/driver/calendar",
                "rows": [
                    {"label": "Turno 06:25-15:15", "value": 8.83, "date": "2026-05-06"},
                    {"label": "Turno pianificato", "value": 8.83, "date": "2026-05-07"},
                    {"label": "Turno pianificato", "value": 8.83, "date": "2026-05-08"},
                    {"label": "Turno pianificato", "value": 8.83, "date": "2026-05-09"},
                ],
            },
            account_id=account_id,
        )

        summary = repo._fetch_period_summary_sync(
            repo.db_path,
            account_id=account_id,
            period="month",
            anchor_date="2026-05-06",
        )
        daily = repo._fetch_period_daily_totals_sync(
            repo.db_path,
            account_id=account_id,
            period="month",
            anchor_date="2026-05-06",
        )

        self.assertEqual(summary["total_entries"], 1)
        self.assertAlmostEqual(summary["total_value"], 8.83)
        values_by_day = {item["day"]: item["total_value"] for item in daily}
        self.assertAlmostEqual(values_by_day["2026-05-06"], 8.83)
        self.assertEqual(values_by_day["2026-05-07"], 0.0)
        self.assertEqual(values_by_day["2026-05-08"], 0.0)
        self.assertEqual(values_by_day["2026-05-09"], 0.0)

    def test_clear_account_data_removes_database_rows_and_json_log_only_for_account(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_clear_account_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()
        repo._ensure_schema()

        target_account = "acct_target"
        other_account = "acct_other"
        payload = {
            "captured_at": "2026-05-06T08:00:00+00:00",
            "url": "https://example.test",
            "rows": [{"label": "Turno", "value": 8, "date": "2026-05-06"}],
        }
        repo._save_snapshot_sync(repo.db_path, payload, account_id=target_account)
        repo._save_snapshot_sync(repo.db_path, payload, account_id=other_account)

        target_log = repo.account_log_path(target_account)
        other_log = repo.account_log_path(other_account)
        self.assertTrue(target_log.exists())
        self.assertTrue(other_log.exists())

        repo._clear_account_data_sync(repo.db_path, target_account)

        self.assertEqual(
            repo._fetch_summary_sync(repo.db_path, account_id=target_account)["total_entries"],
            0,
        )
        self.assertEqual(
            repo._fetch_summary_sync(repo.db_path, account_id=other_account)["total_entries"],
            1,
        )
        self.assertFalse(target_log.exists())
        self.assertTrue(other_log.exists())

    def test_schema_migration_deduplicates_old_entry_keys_before_unique_index(self):
        repo = TimelogRepository()
        test_dir = Path.cwd() / "tmp-test"
        test_dir.mkdir(parents=True, exist_ok=True)
        repo.db_path = test_dir / "geoinroad_pro_duplicate_migration_test.sqlite3"
        if repo.db_path.exists():
            repo.db_path.unlink()

        with repo._connect(repo.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE timelogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL DEFAULT 'default',
                    entry_key TEXT NOT NULL DEFAULT '',
                    captured_at TEXT NOT NULL,
                    work_date TEXT,
                    source_url TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value REAL NOT NULL,
                    raw TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.executemany(
                """
                INSERT INTO timelogs (
                    account_id, entry_key, captured_at, work_date, source_url, label, value, raw, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "acct_test",
                        "",
                        "2026-05-04T07:00:00+00:00",
                        "2026-05-04",
                        "https://example.test",
                        "Turno 06:25-15:40",
                        9.0,
                        "old",
                        "{}",
                    ),
                    (
                        "acct_test",
                        "",
                        "2026-05-04T08:00:00+00:00",
                        "2026-05-04",
                        "https://example.test",
                        "Turno 06:25-15:40",
                        9.25,
                        "new",
                        "{}",
                    ),
                ],
            )

        repo._ensure_schema()

        with repo._connect(repo.db_path) as conn:
            rows = conn.execute(
                "SELECT entry_key, value, raw FROM timelogs WHERE account_id = ?",
                ("acct_test",),
            ).fetchall()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "2026-05-04|turno 06:25-15:40")
        self.assertAlmostEqual(rows[0][1], 9.25)
        self.assertEqual(rows[0][2], "new")


if __name__ == "__main__":
    unittest.main()

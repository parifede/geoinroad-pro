import asyncio
import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import flet as ft


class TimelogRepository:
    def __init__(self) -> None:
        self.db_path: Path | None = None

    async def initialize(
        self,
        *,
        page: ft.Page,
        storage_paths: ft.StoragePaths,
    ) -> Path:
        if page.web:
            base_dir = Path.cwd() / "data"
        else:
            try:
                base_dir = Path(await storage_paths.get_application_documents_directory())
            except Exception:
                base_dir = Path.cwd() / "data"

        base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = base_dir / "geoinroad_pro.sqlite3"
        await asyncio.to_thread(self._ensure_schema)
        return self.db_path

    async def save_snapshot(self, payload: dict, *, account_id: str = "default") -> None:
        db_path = self._require_db_path()
        await asyncio.to_thread(
            self._save_snapshot_sync,
            db_path,
            payload,
            account_id=account_id,
        )

    async def fetch_summary(self, *, account_id: str = "default") -> dict:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_summary_sync,
            db_path,
            account_id=account_id,
        )

    async def fetch_recent_entries(
        self,
        limit: int = 10,
        *,
        account_id: str = "default",
    ) -> list[dict]:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_recent_entries_sync,
            db_path,
            limit,
            account_id=account_id,
        )

    async def fetch_daily_totals(
        self,
        days: int = 7,
        *,
        account_id: str = "default",
    ) -> list[dict]:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_daily_totals_sync,
            db_path,
            days,
            account_id=account_id,
        )

    async def fetch_month_daily_totals(
        self,
        *,
        account_id: str = "default",
        anchor_date: str | None = None,
    ) -> list[dict]:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_month_daily_totals_sync,
            db_path,
            account_id=account_id,
            anchor_date=anchor_date,
        )

    async def fetch_period_daily_totals(
        self,
        *,
        account_id: str = "default",
        period: str = "week",
        anchor_date: str | None = None,
    ) -> list[dict]:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_period_daily_totals_sync,
            db_path,
            account_id=account_id,
            period=period,
            anchor_date=anchor_date,
        )

    async def fetch_period_summary(
        self,
        *,
        account_id: str = "default",
        period: str = "week",
        anchor_date: str | None = None,
    ) -> dict:
        db_path = self._require_db_path()
        return await asyncio.to_thread(
            self._fetch_period_summary_sync,
            db_path,
            account_id=account_id,
            period=period,
            anchor_date=anchor_date,
        )

    async def clear_account_data(self, *, account_id: str = "default") -> None:
        db_path = self._require_db_path()
        await asyncio.to_thread(
            self._clear_account_data_sync,
            db_path,
            account_id,
        )

    def _require_db_path(self) -> Path:
        if self.db_path is None:
            raise RuntimeError("Database path is not initialized.")
        return self.db_path

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        return sqlite3.connect(db_path)

    def _ensure_schema(self) -> None:
        db_path = self._require_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS timelogs (
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
            self._ensure_column(conn, "account_id", "TEXT NOT NULL DEFAULT 'default'")
            self._ensure_column(conn, "entry_key", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "work_date", "TEXT")
            self._backfill_entry_keys(conn)
            self._dedupe_entry_keys(conn)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timelogs_captured_at
                ON timelogs(captured_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timelogs_account_work_date
                ON timelogs(account_id, work_date)
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_timelogs_account_entry_key
                ON timelogs(account_id, entry_key)
                """
            )
            conn.commit()

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        column_name: str,
        definition: str,
    ) -> None:
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(timelogs)").fetchall()
        }
        if column_name not in existing:
            conn.execute(f"ALTER TABLE timelogs ADD COLUMN {column_name} {definition}")

    def _backfill_entry_keys(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            UPDATE timelogs
            SET account_id = 'default'
            WHERE account_id IS NULL OR trim(account_id) = ''
            """
        )
        conn.execute(
            """
            UPDATE timelogs
            SET entry_key = COALESCE(work_date, substr(captured_at, 1, 10), captured_at)
                || '|'
                || lower(trim(label))
            WHERE entry_key IS NULL OR trim(entry_key) = ''
            """
        )

    def _dedupe_entry_keys(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM timelogs
            WHERE id NOT IN (
                SELECT id
                FROM (
                    SELECT id
                    FROM timelogs AS latest
                    WHERE latest.id = (
                        SELECT candidate.id
                        FROM timelogs AS candidate
                        WHERE candidate.account_id = latest.account_id
                          AND candidate.entry_key = latest.entry_key
                        ORDER BY candidate.captured_at DESC, candidate.id DESC
                        LIMIT 1
                    )
                )
            )
            """
        )

    def _save_snapshot_sync(
        self,
        db_path: Path,
        payload: dict,
        *,
        account_id: str = "default",
    ) -> None:
        captured_at = payload.get("captured_at") or datetime.now(timezone.utc).isoformat()
        capture_day = max(
            self._parse_date(str(captured_at)) or date.today(),
            date.today(),
        )
        rows = [
            row for row in (payload.get("rows", []) or [])
            if self._coerce_value(row.get("value")) > 0
            and self._row_work_date(row, captured_at) <= capture_day.isoformat()
        ]
        normalized_account_id = account_id or "default"
        with self._connect(db_path) as conn:
            conn.execute(
                """
                DELETE FROM timelogs
                WHERE account_id = ?
                  AND value > 0
                  AND COALESCE(work_date, substr(captured_at, 1, 10)) > ?
                """,
                (normalized_account_id, capture_day.isoformat()),
            )
            conn.commit()
        if not rows:
            self._write_account_log(db_path, normalized_account_id, payload)
            return

        source_url = payload.get("url", "")
        serialized_payload = json.dumps(payload, ensure_ascii=False)
        positive_dates = sorted(
            {self._row_work_date(row, captured_at) for row in rows}
        )

        with self._connect(db_path) as conn:
            if positive_dates:
                placeholders = ",".join("?" for _ in positive_dates)
                conn.execute(
                    f"""
                    DELETE FROM timelogs
                    WHERE account_id = ?
                      AND value > 0
                      AND work_date IN ({placeholders})
                    """,
                    [normalized_account_id, *positive_dates],
                )
            conn.executemany(
                """
                INSERT INTO timelogs (
                    account_id, entry_key, captured_at, work_date, source_url, label, value, raw, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, entry_key)
                DO UPDATE SET
                    captured_at = excluded.captured_at,
                    work_date = excluded.work_date,
                    source_url = excluded.source_url,
                    value = excluded.value,
                    raw = excluded.raw,
                    payload = excluded.payload
                """,
                [
                    self._row_insert_values(
                        row=row,
                        account_id=normalized_account_id,
                        captured_at=captured_at,
                        source_url=source_url,
                        serialized_payload=serialized_payload,
                    )
                    for row in rows
                ],
            )
            conn.commit()
        self._write_account_log(db_path, normalized_account_id, payload)

    def _fetch_summary_sync(
        self,
        db_path: Path,
        *,
        account_id: str = "default",
    ) -> dict:
        with self._connect(db_path) as conn:
            total_entries = conn.execute(
                "SELECT COUNT(*) FROM timelogs WHERE account_id = ? AND value > 0",
                (account_id,),
            ).fetchone()[0]
            total_value = conn.execute(
                "SELECT COALESCE(SUM(value), 0) FROM timelogs WHERE account_id = ? AND value > 0",
                (account_id,),
            ).fetchone()[0]
            latest_capture = conn.execute(
                "SELECT MAX(captured_at) FROM timelogs WHERE account_id = ? AND value > 0",
                (account_id,),
            ).fetchone()[0]
            average_value = conn.execute(
                "SELECT COALESCE(AVG(value), 0) FROM timelogs WHERE account_id = ? AND value > 0",
                (account_id,),
            ).fetchone()[0]

        return {
            "total_entries": int(total_entries or 0),
            "total_value": float(total_value or 0),
            "latest_capture": latest_capture,
            "average_value": float(average_value or 0),
        }

    def _fetch_recent_entries_sync(
        self,
        db_path: Path,
        limit: int,
        *,
        account_id: str = "default",
    ) -> list[dict]:
        with self._connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT captured_at, work_date, source_url, label, value, raw
                FROM timelogs
                WHERE account_id = ?
                  AND value > 0
                ORDER BY captured_at DESC, id DESC
                LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()

        return [
            {
                "captured_at": row[0],
                "work_date": row[1],
                "source_url": row[2],
                "label": row[3],
                "value": float(row[4]),
                "raw": row[5],
            }
            for row in rows
        ]

    def _fetch_daily_totals_sync(
        self,
        db_path: Path,
        days: int,
        *,
        account_id: str = "default",
    ) -> list[dict]:
        with self._connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(work_date, substr(captured_at, 1, 10)) AS day,
                       COALESCE(SUM(value), 0) AS total_value,
                       COUNT(*) AS entries
                FROM timelogs
                WHERE account_id = ?
                  AND value > 0
                GROUP BY day
                ORDER BY day DESC
                LIMIT ?
                """,
                (account_id, days),
            ).fetchall()

        rows = list(reversed(rows))
        return [
            {
                "day": row[0],
                "total_value": float(row[1] or 0),
                "entries": int(row[2] or 0),
            }
            for row in rows
        ]

    def _fetch_month_daily_totals_sync(
        self,
        db_path: Path,
        *,
        account_id: str = "default",
        anchor_date: str | None = None,
    ) -> list[dict]:
        return self._fetch_period_daily_totals_sync(
            db_path,
            account_id=account_id,
            period="month",
            anchor_date=anchor_date,
        )

    def _fetch_period_daily_totals_sync(
        self,
        db_path: Path,
        *,
        account_id: str = "default",
        period: str = "week",
        anchor_date: str | None = None,
    ) -> list[dict]:
        start, end = self._period_bounds("month", anchor_date)
        if period != "month":
            start, end = self._period_bounds(period, anchor_date)
        with self._connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(work_date, substr(captured_at, 1, 10)) AS day,
                       COALESCE(SUM(value), 0) AS total_value,
                       COUNT(*) AS entries
                FROM timelogs
                WHERE account_id = ?
                  AND value > 0
                  AND COALESCE(work_date, substr(captured_at, 1, 10)) >= ?
                  AND COALESCE(work_date, substr(captured_at, 1, 10)) <= ?
                GROUP BY day
                """,
                (account_id, start.isoformat(), end.isoformat()),
            ).fetchall()

        values_by_day = {
            row[0]: {"total_value": float(row[1] or 0), "entries": int(row[2] or 0)}
            for row in rows
        }
        result = []
        current = start
        while current <= end:
            day_key = current.isoformat()
            values = values_by_day.get(day_key, {"total_value": 0.0, "entries": 0})
            result.append(
                {
                    "day": day_key,
                    "total_value": values["total_value"],
                    "entries": values["entries"],
                }
            )
            current += timedelta(days=1)
        return result

    def _fetch_period_summary_sync(
        self,
        db_path: Path,
        *,
        account_id: str = "default",
        period: str = "week",
        anchor_date: str | None = None,
    ) -> dict:
        start, end = self._period_bounds(period, anchor_date)
        with self._connect(db_path) as conn:
            total_entries, total_value, average_value = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(value), 0), COALESCE(AVG(value), 0)
                FROM timelogs
                WHERE account_id = ?
                  AND value > 0
                  AND COALESCE(work_date, substr(captured_at, 1, 10)) >= ?
                  AND COALESCE(work_date, substr(captured_at, 1, 10)) <= ?
                """,
                (account_id, start.isoformat(), end.isoformat()),
            ).fetchone()

        return {
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_entries": int(total_entries or 0),
            "total_value": float(total_value or 0),
            "average_value": float(average_value or 0),
        }

    @staticmethod
    def _coerce_value(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _row_insert_values(
        self,
        *,
        row: dict,
        account_id: str,
        captured_at: str,
        source_url: str,
        serialized_payload: str,
    ) -> tuple:
        work_date = self._row_work_date(row, captured_at)
        label = str(row.get("label", "dato"))
        return (
            account_id,
            self._entry_key(work_date, label),
            captured_at,
            work_date,
            source_url,
            label,
            self._coerce_value(row.get("value")),
            str(row.get("raw", ""))[:500],
            serialized_payload,
        )

    @staticmethod
    def _entry_key(work_date: str, label: str) -> str:
        return f"{work_date}|{label.strip().lower()}"

    @staticmethod
    def account_id_for_username(username: str) -> str:
        normalized = (username or "default").strip().lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"acct_{digest}"

    def account_log_path(self, account_id: str) -> Path:
        db_path = self._require_db_path()
        safe_account = "".join(
            char if char.isalnum() or char in ("_", "-") else "_"
            for char in (account_id or "default")
        )
        return db_path.parent / "account_logs" / f"{safe_account}.json"

    def _clear_account_data_sync(self, db_path: Path, account_id: str) -> None:
        normalized_account_id = account_id or "default"
        with self._connect(db_path) as conn:
            conn.execute(
                "DELETE FROM timelogs WHERE account_id = ?",
                (normalized_account_id,),
            )
            conn.commit()

        log_path = self.account_log_path(normalized_account_id)
        if log_path.exists():
            log_path.unlink()

    def _write_account_log(
        self,
        db_path: Path,
        account_id: str,
        latest_payload: dict,
    ) -> None:
        entries = self._fetch_recent_entries_sync(
            db_path,
            limit=5000,
            account_id=account_id,
        )
        totals = self._fetch_summary_sync(db_path, account_id=account_id)
        data = {
            "account_id": account_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "summary": totals,
            "latest_payload": latest_payload,
            "entries": entries,
        }
        path = self.account_log_path(account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _row_work_date(row: dict, captured_at: str) -> str:
        raw_date = row.get("date") or row.get("work_date")
        if raw_date:
            parsed = TimelogRepository._parse_date(str(raw_date))
            if parsed is not None:
                return parsed.isoformat()
        return captured_at[:10]

    @staticmethod
    def _period_bounds(period: str, anchor_date: str | None) -> tuple[date, date]:
        anchor = TimelogRepository._parse_date(anchor_date or "") or date.today()
        if period == "day":
            return anchor, anchor
        if period == "month":
            start = anchor.replace(day=1)
            if anchor.month == 12:
                end = anchor.replace(year=anchor.year + 1, month=1, day=1)
            else:
                end = anchor.replace(month=anchor.month + 1, day=1)
            return start, end - timedelta(days=1)
        if period == "year":
            return date(anchor.year, 1, 1), date(anchor.year, 12, 31)

        start = anchor - timedelta(days=(anchor.weekday() + 1) % 7)
        return start, start + timedelta(days=6)

    @staticmethod
    def _parse_date(value: str) -> date | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value[:10], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

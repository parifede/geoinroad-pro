import unittest

import flet as ft

from app_state import AppState
from views.dashboard import _chart_title, _fmt_h, build_dashboard_view


class _DummyPage:
    def run_task(self, func, *args):
        return func


async def _noop(*args):
    return None


class DashboardTest(unittest.TestCase):
    def test_dashboard_handles_non_numeric_scraped_values(self):
        state = AppState()
        state.scraped_stats = {
            "rows": [
                {"label": "Turno sporco", "value": "n/d", "raw": "n/d"},
                {"label": "Turno buono", "value": "8.5", "raw": "8.5"},
            ]
        }
        state.timelog_daily_totals = [
            {"day": "2026-05-05", "total_value": "n/d", "entries": 1}
        ]
        state.timelog_recent_entries = [
            {"label": "Voce sporca", "value": "n/d", "work_date": "2026-05-05"}
        ]

        view = build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
        )

        self.assertIsInstance(view, ft.View)

    def test_dashboard_period_filter_removes_year_report(self):
        state = AppState()

        view = build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
        )

        labels = _collect_text_values(view)
        self.assertIn("Giorno", labels)
        self.assertIn("Week", labels)
        self.assertIn("Mese", labels)
        self.assertNotIn("Anno", labels)

    def test_month_chart_title_names_current_month(self):
        self.assertEqual(_chart_title("month", "2026-05-05"), "Mese maggio")

    def test_day_cells_mark_rest_and_vacation_days(self):
        state = AppState()
        state.dashboard_period = "week"
        state.timelog_daily_totals = [
            {"day": "2026-05-04", "total_value": 8, "entries": 1, "status": "lavorato"},
            {"day": "2026-05-05", "total_value": 0, "entries": 0, "status": "riposo"},
            {"day": "2026-05-06", "total_value": 0, "entries": 0, "status": "ferie"},
            {"day": "2026-05-07", "total_value": 0, "entries": 0, "status": ""},
        ]

        labels = _collect_text_values(
            build_dashboard_view(
                page=_DummyPage(),
                state=state,
                on_back_to_diary=_noop,
                on_period_change=_noop,
                on_shift_period=_noop,
                on_reset_period=_noop,
            )
        )

        self.assertIn("Riposo", labels)
        self.assertIn("Ferie", labels)
        self.assertIn("0 h", labels)

    def test_period_navigation_shows_anchored_range(self):
        state = AppState()
        state.dashboard_period = "month"
        state.dashboard_anchor = "2026-05-05"
        state.timelog_period_summary = {
            "period": "month",
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
        }

        view = build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
            on_shift_period=_noop,
            on_reset_period=_noop,
        )

        labels = _collect_text_values(view)
        self.assertIn("Maggio 2026", labels)

    def test_period_navigation_week_range_label(self):
        state = AppState()
        state.dashboard_period = "week"
        state.timelog_period_summary = {
            "period": "week",
            "start_date": "2026-05-03",
            "end_date": "2026-05-09",
        }

        labels = _collect_text_values(
            build_dashboard_view(
                page=_DummyPage(),
                state=state,
                on_back_to_diary=_noop,
                on_period_change=_noop,
                on_shift_period=_noop,
                on_reset_period=_noop,
            )
        )
        self.assertIn("03/05 – 09/05", labels)

    def test_month_chart_shows_all_calendar_days_without_year_filter(self):
        state = AppState()
        state.dashboard_period = "month"
        state.timelog_daily_totals = [
            {"day": f"2026-05-{day:02d}", "total_value": 0, "entries": 0}
            for day in range(1, 32)
        ]

        view = build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
        )

        labels = _collect_text_values(view)
        self.assertIn("Mese maggio", labels)
        self.assertIn("01", labels)
        self.assertIn("31", labels)
        self.assertNotIn("Anno", labels)

    def test_dashboard_does_not_render_recent_activity_section(self):
        state = AppState()
        state.timelog_recent_entries = [
            {"label": "Turno 06:25-15:15", "value": 8.83, "work_date": "2026-05-06"}
        ]

        view = build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
        )

        labels = _collect_text_values(view)
        self.assertNotIn("Attività recenti", labels)
        self.assertNotIn("AttivitÃ\xa0 recenti", labels)

    def test_hours_are_displayed_as_base_60_time_not_decimal_hundredths(self):
        self.assertEqual(_fmt_h(8.83), "8 h 50 m")
        self.assertEqual(_fmt_h(44.15), "44 h 9 m")
        self.assertEqual(_fmt_h(9.0), "9 h")
        self.assertEqual(_fmt_h(0), "0 h")


def _collect_text_values(control):
    values = []
    if isinstance(control, ft.Text):
        values.append(control.value)
    nested = []
    if hasattr(control, "controls") and control.controls:
        nested.extend(control.controls)
    if hasattr(control, "content") and control.content:
        nested.append(control.content)
    for child in nested:
        values.extend(_collect_text_values(child))
    return values


if __name__ == "__main__":
    unittest.main()

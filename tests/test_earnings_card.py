import unittest

import flet as ft

from app_state import AppState
from services.earnings import DISCLAIMER, EarningsSettings
from views.dashboard import build_dashboard_view, build_earnings_dialog


class _DummyPage:
    def run_task(self, func, *args):
        return func

    def update(self):
        return None

    def pop_dialog(self):
        return None


async def _noop(*args):
    return None


def _texts(control) -> list[str]:
    values = []
    if isinstance(control, str):
        return [control]
    if isinstance(control, ft.Text):
        values.append(control.value)
    nested = []
    if getattr(control, "controls", None):
        nested.extend(control.controls)
    if getattr(control, "content", None):
        nested.append(control.content)
    if getattr(control, "actions", None):
        nested.extend(control.actions)
    for child in nested:
        values.extend(_texts(child))
    return values


def _november_state() -> AppState:
    state = AppState()
    state.dashboard_period = "month"
    state.timelog_daily_totals = [
        {"day": f"2026-11-{day:02d}", "total_value": 0, "entries": 0, "status": ""}
        for day in range(1, 31)
    ]
    state.timelog_daily_totals[2] = {
        "day": "2026-11-03", "total_value": 9.0, "entries": 1, "status": "lavorato"
    }
    state.timelog_daily_totals[3] = {
        "day": "2026-11-04", "total_value": 7.0, "entries": 1, "status": "adempimenti"
    }
    state.timelog_daily_totals[4] = {
        "day": "2026-11-05", "total_value": 0, "entries": 0, "status": "adempimenti"
    }
    return state


def _dashboard(state: AppState) -> list[str]:
    return _texts(
        build_dashboard_view(
            page=_DummyPage(),
            state=state,
            on_back_to_diary=_noop,
            on_period_change=_noop,
            on_edit_earnings=_noop,
        )
    )


class EarningsCardTest(unittest.TestCase):
    def test_without_settings_there_is_no_estimate_but_an_invite(self):
        texts = _dashboard(_november_state())

        self.assertIn("Stima del mese", texts)
        self.assertIn("Imposta", texts)
        self.assertTrue(any("paga oraria" in text for text in texts))
        self.assertNotIn("Totale lordo stimato", texts)
        self.assertNotIn(DISCLAIMER, texts)

    def test_with_settings_the_estimate_shows_with_its_disclaimer(self):
        state = _november_state()
        state.earnings_settings = EarningsSettings(10.0, 40.0, 15.0, 30.0)

        texts = _dashboard(state)

        self.assertIn("Totale lordo stimato", texts)
        # 16 ore ordinarie x 10 + 2 giorni di diaria x 30.
        self.assertIn("220,00 €", texts)
        self.assertIn(DISCLAIMER, texts)
        self.assertIn("Modifica", texts)
        self.assertTrue(any("da verificare" in text for text in texts))
        self.assertTrue(any("Soglia straordinari" in text and "168 h" in text for text in texts))

    def test_card_only_in_the_month_view(self):
        state = _november_state()
        state.dashboard_period = "week"
        state.timelog_daily_totals = state.timelog_daily_totals[:7]
        state.earnings_settings = EarningsSettings(10.0, 40.0)

        self.assertNotIn("Stima del mese", _dashboard(state))

    def test_aa_days_are_labelled_in_the_calendar(self):
        texts = _dashboard(_november_state())

        self.assertIn("AA", texts)
        self.assertTrue(any("Rosa: altri adempimenti" in text for text in texts))

    def test_dialog_prefills_saved_values(self):
        state = AppState()
        state.earnings_settings = EarningsSettings(12.5, 42.0, None, 30.0)

        dialog = build_earnings_dialog(page=_DummyPage(), state=state, on_save=_noop)

        fields = [c for c in dialog.content.controls if isinstance(c, ft.TextField)]
        self.assertEqual([field.value for field in fields], ["12,5", "", "30", "42"])


if __name__ == "__main__":
    unittest.main()

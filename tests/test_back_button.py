import unittest
from pathlib import Path

from app_state import AppState
from services.web_history import WebHistory
from views.back import back_handler
from views.dashboard import build_dashboard_view
from views.report_screen import build_report_view

_DRIVER = "https://geoinroad.dimetior.com/driver"
_CALENDAR = "https://geoinroad.dimetior.com/driver/calendar"
_LOGIN = "https://geoinroad.dimetior.com/login"


class WebHistoryTest(unittest.TestCase):
    def test_goes_back_to_the_previous_portal_page(self):
        history = WebHistory()
        history.visit(_DRIVER)
        history.visit(_CALENDAR)

        self.assertTrue(history.can_go_back())
        history.went_back()
        # Il WebView poi segnala di nuovo l'URL raggiunto: nessun doppione.
        history.visit(_DRIVER)
        self.assertFalse(history.can_go_back())

    def test_nothing_before_the_first_page(self):
        history = WebHistory()
        self.assertFalse(history.can_go_back())
        history.visit(_DRIVER)
        history.visit(_DRIVER)
        self.assertFalse(history.can_go_back())

    def test_never_back_to_the_login_page(self):
        history = WebHistory()
        history.visit(_LOGIN)
        history.visit(_DRIVER)

        self.assertFalse(history.can_go_back())

    def test_reset_on_logout(self):
        history = WebHistory()
        history.visit(_DRIVER)
        history.visit(_CALENDAR)
        history.reset()

        self.assertFalse(history.can_go_back())


class _View:
    def __init__(self) -> None:
        self.answers = []

    async def confirm_pop(self, should_pop):
        self.answers.append(should_pop)


class _Event:
    def __init__(self) -> None:
        self.control = _View()


class _DummyPage:
    def run_task(self, func, *args):
        return func


async def _noop(*args):
    return None


class BackHandlerTest(unittest.IsolatedAsyncioTestCase):
    async def test_view_stays_and_the_app_decides(self):
        calls = []

        async def back_to_diary():
            calls.append("diary")

        event = _Event()
        await back_handler(back_to_diary)(event)

        # Il sistema non chiude mai la vista (niente uscita dall'app).
        self.assertEqual(event.control.answers, [False])
        self.assertEqual(calls, ["diary"])

    async def test_without_action_back_does_nothing(self):
        event = _Event()
        await back_handler(None)(event)

        self.assertEqual(event.control.answers, [False])

    def test_statistics_and_report_go_back_to_the_diary(self):
        dashboard = build_dashboard_view(
            page=_DummyPage(),
            state=AppState(),
            on_back_to_diary=_noop,
            on_period_change=_noop,
        )
        report = build_report_view(
            page=_DummyPage(),
            state=AppState(),
            on_back_to_diary=_noop,
            on_send_whatsapp=_noop,
            on_copy_report=_noop,
            on_copy_report_id=_noop,
            on_copy_saved_report=_noop,
        )

        self.assertIsNotNone(dashboard.on_confirm_pop)
        self.assertIsNotNone(report.on_confirm_pop)

    def test_lock_screen_back_stays_blocked(self):
        source = Path("views/lock_screen.py").read_text(encoding="utf-8")
        self.assertIn("can_pop=False", source)
        self.assertNotIn("on_confirm_pop", source)

    def test_diary_back_uses_portal_history(self):
        source = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("on_back=webview_back", source)
        self.assertIn("state.web_history.visit(e.data)", source)
        self.assertIn("await webview.go_back()", source)


if __name__ == "__main__":
    unittest.main()

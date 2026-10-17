import unittest

import flet as ft

from app_state import AppState
from views.report_screen import build_report_view
from app_config import ROUTE_REPORT


class _DummyPage:
    def run_task(self, func, *args):
        return func


async def _noop(*args):
    return None


def _collect_text_values(control) -> list[str]:
    values = []
    stack = [control]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            if node:
                values.append(node)
            continue
        value = getattr(node, "value", None)
        if isinstance(value, str) and value:
            values.append(value)
        for attr in ("controls", "content"):
            child = getattr(node, attr, None)
            if child is None:
                continue
            if isinstance(child, (list, tuple)):
                stack.extend(child)
            else:
                stack.append(child)
    return values


def _build_view(state: AppState) -> ft.View:
    return build_report_view(
        page=_DummyPage(),
        state=state,
        on_back_to_diary=_noop,
        on_send_whatsapp=_noop,
        on_copy_report=_noop,
        on_copy_report_id=_noop,
        on_copy_saved_report=_noop,
    )


class ReportScreenTest(unittest.TestCase):
    def test_report_screen_shows_problem_code_and_details(self):
        state = AppState()
        state.last_report_id = "GIR-260506-AB12CD"
        state.last_report = {
            "report_id": "GIR-260506-AB12CD",
            "captured_at": "2026-05-06T21:52:00+00:00",
            "route": "/diario",
            "last_loaded_url": "https://geoinroad.dimetior.com/driver",
            "web_status": "Errore WebView: timeout",
        }

        view = _build_view(state)
        labels = _collect_text_values(view)

        self.assertEqual(view.route, ROUTE_REPORT)
        self.assertFalse(view.can_pop)
        self.assertIn("GIR-260506-AB12CD", labels)
        self.assertIn("Codice problema", labels)
        self.assertIn("https://geoinroad.dimetior.com/driver", labels)
        self.assertIn("Errore WebView: timeout", labels)
        self.assertIn("Invia su WhatsApp", labels)
        self.assertIn("Copia report completo", labels)

    def test_report_screen_lists_saved_reports(self):
        state = AppState()
        state.last_report_id = "GIR-260506-AB12CD"
        state.last_report = {"captured_at": "2026-05-06T21:52:00+00:00"}
        state.saved_reports = [
            {
                "report_id": "GIR-260505-FF00AA",
                "captured_at": "2026-05-05T08:00:00+00:00",
                "route": "/diario",
                "path": "/tmp/GIR-260505-FF00AA.json",
            }
        ]

        labels = _collect_text_values(_build_view(state))

        self.assertIn("Report recenti", labels)
        self.assertIn("GIR-260505-FF00AA", labels)

    def test_report_screen_handles_empty_state(self):
        view = _build_view(AppState())
        labels = _collect_text_values(view)

        self.assertIsInstance(view, ft.View)
        self.assertIn("Nessun report salvato sul dispositivo.", labels)


if __name__ == "__main__":
    unittest.main()

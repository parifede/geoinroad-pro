import unittest

from services.js_bridge import build_auto_login_script


class AutoLoginScriptTest(unittest.TestCase):
    def test_js_floating_menu_is_not_attached_and_stats_button_removed(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertNotIn("document.body.appendChild(btn)", script)
        self.assertNotIn("geoinroad-menu-panel", script)
        self.assertIn("GEOINROAD_APP::ACTION::", script)
        self.assertNotIn("Statistiche App", script)

    def test_work_stats_action_is_delegated_to_python_bridge(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("window.GeoinroadApp.collectStats", script)
        self.assertNotIn("window.GeoinroadApp.collectStats();", script)

    def test_autologin_submits_once_without_duplicate_native_submit(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("submitButton.click();", script)
        self.assertNotIn('dispatchEvent(new MouseEvent("click"', script)
        self.assertNotIn("form.requestSubmit(submitButton || undefined)", script)

    def test_autologin_runs_only_on_login_page_with_attempt_limit(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("loginPathPattern", script)
        self.assertIn("skipped_not_login_page", script)
        self.assertIn("autologin_max_attempts", script)
        self.assertIn("maxAttempts = 3", script)
        self.assertIn("__geoinroadAutologinRan", script)
        self.assertIn("scheduleAutoLogin();", script)

    def test_stats_scraper_normalizes_dash_variants_and_start_end_labels(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn(
            'replace(/[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212]/g, "-")',
            script,
        )
        self.assertIn("(?:Inizio|Start)", script)
        self.assertIn("(?:Fine|End)", script)
        self.assertIn("text_sample", script)
        self.assertIn("visible_text_count", script)
        self.assertIn("Presente no route", script)
        self.assertIn("Libero", script)
        self.assertIn("CALENDARIO", script)

    def test_calendar_scraper_accepts_geoinroad_rows_without_month(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("calendarDefaultMonth", script)
        self.assertIn("(?:\\s+([A-Za-z]{3}))?", script)
        self.assertIn('match[4].toUpperCase() !== "W"', script)

    def test_stats_scraper_fetches_calendar_and_work_days(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("collectExpandedStats", script)
        self.assertIn('credentials: "include"', script)
        self.assertIn("/driver/calendar", script)
        self.assertIn("?date=", script)
        self.assertIn('a[href*="/driver/route/"]', script)
        self.assertIn("sourceDateMatch", script)
        self.assertIn("fallbackDate", script)
        self.assertIn("loadRenderedStatsDocument", script)
        self.assertIn("contentDocument", script)
        self.assertIn("collectApiStats", script)
        self.assertIn("window.$nuxt", script)
        self.assertIn("/geoinroad_api/employees/driver_calendar", script)
        self.assertIn("/geoinroad_api/planner/route", script)
        self.assertIn("renderedDates", script)
        self.assertIn("rowPriority(row) <= 20", script)
        self.assertIn("renderedLimit = hasPositiveRows ? 20 : 28", script)

    def test_stats_merge_prefers_calendar_or_diary_turns_over_route_times(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("bestPositiveByDate", script)
        self.assertIn("compareRows(row, current) > 0", script)
        self.assertIn("planner\\/route", script)
        self.assertIn("driver_calendar", script)
        self.assertIn("timeRangeFromApiObject", script)
        self.assertIn('"startTime"', script)
        self.assertIn('"shift_end"', script)
        self.assertIn('source: "dom/driver-status"', script)


if __name__ == "__main__":
    unittest.main()

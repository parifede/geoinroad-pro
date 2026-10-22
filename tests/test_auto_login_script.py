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

    def test_stats_scraper_attributes_hours_to_correct_day(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        # La SPA puo' ignorare ?date=: vale la data mostrata dalla pagina,
        # e senza data visibile le righe giornaliere vengono scartate.
        self.assertIn("if (pageDate) return pageDate;", script)
        self.assertIn("const dayRowsAllowed = !(sourceDateMatch && !shownDate);", script)
        # Le pagine calendario non producono righe orario generiche (giorni diversi
        # finirebbero tutti sulla stessa data di fallback).
        self.assertIn("isCalendarUrl", script)
        self.assertIn("if (!isCalendarUrl && dayRowsAllowed) {", script)
        # Le righe keyword (es. "Totale 173") non possono diventare ore giornaliere.
        self.assertIn("plausibleHours", script)
        self.assertIn("numericValue <= 24", script)
        self.assertIn('/dom\\/keyword/i.test(source)) return 10;', script)
        # Le pause non vengono conteggiate come turni.
        self.assertIn("pausa|pause|break|riposo", script)

    def test_stats_scraper_uses_local_dates_not_utc(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("function localIsoDate(", script)
        self.assertNotIn("toISOString().slice(0, 10)", script)

    def test_stats_collection_accepts_a_custom_date_range(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        # La dashboard puo' chiedere un periodo passato: from/to arrivano
        # fino alle query API e alle pagine per-giorno da renderizzare.
        self.assertIn("collectExpandedStats(options)", script)
        self.assertIn("options.from && options.to", script)
        self.assertIn("async function collectApiStats(range)", script)
        self.assertIn("range || currentMonthDateRange()", script)
        self.assertIn("Math.min(2 * rangeDays, 62)", script)

    def test_stats_payload_stays_small_enough_for_console_bridge(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("text_sample: bodyText.slice(0, 600)", script)
        self.assertIn("expanded_fetches: fetches.slice(0, 40)", script)
        self.assertIn("expanded_fetch_count", script)

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

    def test_calendar_scraper_emits_rest_and_absence_days(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        # La sigla badge e' generica (1-2 maiuscole: S, W, A, M, I, F, FA,
        # GF, R, RC e future) e la dicitura di stato e' testo libero.
        self.assertIn("([A-Z]{1,2})", script)
        self.assertIn("[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'. ]{0,30}?", script)
        # I giorni non lavorati non vengono piu' scartati: portano la sigla.
        self.assertNotIn('match[4].toUpperCase() !== "W"', script)
        self.assertIn("work_marker: sigla", script)
        # Presenze senza orario, abortive e ferie valgono 8 ore pagate di
        # default; l'orario reale vince perche' il default ha priorita' minima.
        self.assertIn('/^(S|W|A|F|FA)$/.test(sigla)', script)
        self.assertIn('paidDefault ? "8.00" : "0"', script)
        self.assertIn('"dom/calendar-default"', script)
        self.assertIn("/-default/i.test(source)) return 5;", script)
        # Anche l'API calendario segnala i giorni non lavorati, tipizzati
        # con la mappa activity_id -> sigla imparata dal calendario; mai per
        # oggi o il futuro, dove lo stato non e' ancora definitivo.
        self.assertIn('(item.present ? "W" : "R")', script)
        self.assertIn("calendar_samples", script)
        self.assertIn("type_stats", script)
        self.assertIn("if (!item.present && day >= today) continue;", script)

    def test_calendar_year_follows_nearest_month_across_new_year(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("function yearForMonth(", script)
        self.assertIn("if (diff > 6) year -= 1;", script)
        self.assertIn("if (diff < -6) year += 1;", script)
        # L'anno non viene piu' pescato dal primo "20xx" trovato nella pagina.
        self.assertNotIn("bodyText.match(/\\b(20\\d{2})\\b/)", script)

    def test_stats_scraper_fetches_calendar_and_work_days(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("collectExpandedStats", script)
        self.assertIn("/driver/calendar", script)
        self.assertIn("?date=", script)
        self.assertIn("sourceDateMatch", script)
        self.assertIn("fallbackDate", script)
        self.assertIn("loadRenderedStatsDocument", script)
        self.assertIn("contentDocument", script)
        # La SPA si idrata dopo l'evento load: la foto della pagina
        # aspetta che il contenuto compaia, con budget di tempo totale.
        self.assertIn("renderedDocLooksReady", script)
        self.assertIn("renderBudgetMs", script)
        self.assertIn("collectApiStats", script)
        self.assertIn("window.$nuxt", script)
        self.assertIn("/geoinroad_api/employees/driver_calendar", script)
        self.assertIn("/geoinroad_api/planner/route", script)
        # Il calendario ignora ?date= e mostra sempre la settimana
        # corrente: le settimane passate si leggono premendo la freccia
        # indietro, e la mappa dei tipi giorno resta salvata nel browser.
        self.assertIn("renderCalendarWeeks", script)
        self.assertIn("findPreviousWeekControl", script)
        self.assertIn("geoinroad_pro_day_types_v1", script)
        self.assertIn("merged.sync_range = { from, to }", script)
        self.assertIn("monthForCalendarDay(", script)
        self.assertIn("headerEndMonth", script)

    def test_stats_merge_prefers_calendar_or_diary_turns_over_route_times(self):
        script = build_auto_login_script(username="user@example.test", password="secret")

        self.assertIn("bestPriorityByDate", script)
        self.assertIn("priority !== bestPriorityByDate.get(row.date)", script)
        # Un solo default da 8 ore per giorno, qualunque fonte lo proponga.
        self.assertIn('row.date + "|default"', script)
        self.assertIn("shiftKeys", script)
        self.assertIn("planner\\/route", script)
        self.assertIn("driver_calendar", script)
        self.assertIn("timeRangeFromApiObject", script)
        self.assertIn('"startTime"', script)
        self.assertIn('"shift_end"', script)
        self.assertIn('source: "dom/driver-status"', script)


if __name__ == "__main__":
    unittest.main()

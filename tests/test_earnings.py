import unittest
from datetime import date

from services.earnings import (
    DISCLAIMER,
    EarningsSettings,
    build_settings,
    estimate_month,
    format_euro,
    monthly_threshold,
    parse_amount,
    settings_from_json,
    settings_to_json,
    weekdays_in_month,
)

_NOVEMBER = date(2026, 11, 1)  # 21 giorni dal lunedi' al venerdi'


def _day(day: int, hours: float, status: str = "lavorato") -> dict:
    return {"day": f"2026-11-{day:02d}", "total_value": hours, "status": status}


class ParsingTest(unittest.TestCase):
    def test_amounts_accept_comma_dot_and_euro_sign(self):
        self.assertEqual(parse_amount("12,50"), 12.5)
        self.assertEqual(parse_amount("12.5"), 12.5)
        self.assertEqual(parse_amount("€ 1.234,56"), 1234.56)
        self.assertIsNone(parse_amount(""))
        self.assertIsNone(parse_amount("abc"))
        self.assertIsNone(parse_amount("0"))
        self.assertIsNone(parse_amount("-3"))

    def test_rate_and_weekly_hours_are_required(self):
        settings, error = build_settings(hourly_rate="", weekly_hours="40")
        self.assertIsNone(settings)
        self.assertIn("paga oraria", error)
        settings, error = build_settings(hourly_rate="12", weekly_hours="")
        self.assertIsNone(settings)
        self.assertIn("ore settimanali", error)
        settings, error = build_settings(hourly_rate="12", weekly_hours="200")
        self.assertIsNone(settings)

    def test_overtime_and_allowance_are_optional(self):
        settings, error = build_settings(hourly_rate="12,5", weekly_hours="42")
        self.assertEqual(error, "")
        self.assertEqual(settings, EarningsSettings(12.5, 42.0, None, None))
        settings, error = build_settings(
            hourly_rate="12,5", weekly_hours="42", overtime_rate="x"
        )
        self.assertIsNone(settings)

    def test_settings_round_trip(self):
        settings = EarningsSettings(12.5, 42.0, 16.25, 35.0)
        self.assertEqual(settings_from_json(settings_to_json(settings)), settings)
        self.assertIsNone(settings_from_json(None))
        self.assertIsNone(settings_from_json("{broken"))


class ThresholdTest(unittest.TestCase):
    def test_weekdays(self):
        self.assertEqual(weekdays_in_month(_NOVEMBER), 21)
        self.assertEqual(weekdays_in_month(date(2026, 12, 1)), 23)

    def test_threshold_matches_contract_hours(self):
        # 40 h/sett. -> 8 h per giorno feriale.
        self.assertEqual(monthly_threshold(EarningsSettings(10, 40), _NOVEMBER), 168)
        # 42 h/sett. su 22 giorni feriali: circa la 184esima ora.
        self.assertEqual(
            monthly_threshold(EarningsSettings(10, 42), date(2026, 10, 1)), 184.8
        )


class EstimateTest(unittest.TestCase):
    def test_hours_above_the_threshold_are_overtime(self):
        settings = EarningsSettings(10.0, 40.0, overtime_rate=15.0)
        # 21 giorni da 9 ore = 189 h, soglia 168: 21 h di straordinario.
        totals = [_day(day, 9.0) for day in range(1, 22)]

        estimate = estimate_month(totals, _NOVEMBER, settings)

        self.assertEqual(estimate["paid_hours"], 189)
        self.assertEqual(estimate["ordinary_hours"], 168)
        self.assertEqual(estimate["overtime_hours"], 21)
        self.assertEqual(estimate["ordinary_amount"], 1680)
        self.assertEqual(estimate["overtime_amount"], 315)
        self.assertEqual(estimate["gross_total"], 1995)

    def test_without_overtime_rate_the_ordinary_rate_is_used(self):
        settings = EarningsSettings(10.0, 40.0)
        totals = [_day(day, 9.0) for day in range(1, 22)]

        estimate = estimate_month(totals, _NOVEMBER, settings)

        self.assertTrue(estimate["overtime_rate_is_ordinary"])
        self.assertEqual(estimate["overtime_amount"], 210)

    def test_allowance_over_six_hours_but_never_on_vacation(self):
        settings = EarningsSettings(10.0, 40.0, daily_allowance=30.0)
        totals = [
            _day(2, 8.5),                  # normale: diaria
            _day(3, 6.0),                  # esattamente 6: no
            _day(4, 8.0, "abortive"),      # abortive 8 h: diaria
            _day(5, 8.0, "ferie"),         # ferie: mai
            _day(6, 7.0, "adempimenti"),   # AA oltre 6 h: diaria, da verificare
            _day(7, 0.0, "riposo"),
        ]

        estimate = estimate_month(totals, _NOVEMBER, settings)

        self.assertEqual(estimate["allowance_days"], 3)
        self.assertEqual(estimate["uncertain_allowance_days"], 1)
        self.assertEqual(estimate["allowance_amount"], 90)
        # Le ferie contano come ore ordinarie pagate.
        self.assertEqual(estimate["paid_hours"], 37.5)
        self.assertEqual(estimate["gross_total"], 375 + 90)

    def test_formatting(self):
        self.assertEqual(format_euro(1234.5), "1.234,50 €")
        self.assertEqual(format_euro(0), "0,00 €")
        self.assertEqual(DISCLAIMER, "Stima indicativa, non è la busta paga")


if __name__ == "__main__":
    unittest.main()

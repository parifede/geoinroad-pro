"""Stima lorda del mese, con le cifre che ogni utente inserisce da se'.

Non e' la busta paga: niente contributi, tasse o voci contrattuali, solo
ore pagate, straordinari oltre una soglia mensile e diaria.
"""

import calendar
import json
from dataclasses import asdict, dataclass
from datetime import date

from app_config import APP_NAMESPACE

DISCLAIMER = "Stima indicativa, non è la busta paga"

# Diaria: giornate con piu' di queste ore pagate, ferie escluse.
ALLOWANCE_MIN_HOURS = 6.0
_NO_ALLOWANCE_STATUSES = {"ferie"}
# Altri adempimenti: pagati in base all'orario, diaria da verificare.
UNCERTAIN_ALLOWANCE_STATUS = "adempimenti"

_MAX_WEEKLY_HOURS = 80.0


@dataclass(frozen=True)
class EarningsSettings:
    hourly_rate: float
    weekly_hours: float
    overtime_rate: float | None = None
    daily_allowance: float | None = None


def settings_key(account_id: str) -> str:
    return f"{APP_NAMESPACE}.earnings.{account_id or 'default'}"


def parse_amount(text, *, maximum: float | None = None) -> float | None:
    """'12,50', '12.5', '€ 12,50' -> 12.5. Vuoto o non valido -> None."""
    cleaned = str(text or "").replace("€", "").replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        # 1.234,56: il punto separa le migliaia.
        cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value <= 0 or (maximum is not None and value > maximum):
        return None
    return round(value, 2)


def build_settings(
    *,
    hourly_rate: str,
    weekly_hours: str,
    overtime_rate: str = "",
    daily_allowance: str = "",
) -> tuple[EarningsSettings | None, str]:
    """Valida i campi del modulo. Restituisce (impostazioni, errore)."""
    rate = parse_amount(hourly_rate)
    if rate is None:
        return None, "Inserisci la paga oraria (es. 12,50)."
    hours = parse_amount(weekly_hours, maximum=_MAX_WEEKLY_HOURS)
    if hours is None:
        return None, "Inserisci le ore settimanali da contratto (es. 40)."
    overtime = None
    if str(overtime_rate or "").strip():
        overtime = parse_amount(overtime_rate)
        if overtime is None:
            return None, "Paga straordinaria non valida."
    allowance = None
    if str(daily_allowance or "").strip():
        allowance = parse_amount(daily_allowance)
        if allowance is None:
            return None, "Diaria non valida."
    return EarningsSettings(rate, hours, overtime, allowance), ""


def settings_to_json(settings: EarningsSettings) -> str:
    return json.dumps(asdict(settings))


def settings_from_json(raw) -> EarningsSettings | None:
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else dict(raw)
        settings = EarningsSettings(
            hourly_rate=float(data["hourly_rate"]),
            weekly_hours=float(data["weekly_hours"]),
            overtime_rate=(
                float(data["overtime_rate"]) if data.get("overtime_rate") else None
            ),
            daily_allowance=(
                float(data["daily_allowance"]) if data.get("daily_allowance") else None
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if settings.hourly_rate <= 0 or settings.weekly_hours <= 0:
        return None
    return settings


def weekdays_in_month(month_start: date) -> int:
    days = calendar.monthrange(month_start.year, month_start.month)[1]
    return sum(
        1
        for day in range(1, days + 1)
        if date(month_start.year, month_start.month, day).weekday() < 5
    )


def monthly_threshold(settings: EarningsSettings, month_start: date) -> float:
    """Ore ordinarie del mese: ore settimanali / 5 x giorni lun-ven."""
    return round(settings.weekly_hours / 5 * weekdays_in_month(month_start), 2)


def _hours(item: dict) -> float:
    try:
        return max(0.0, float(item.get("total_value") or 0))
    except (TypeError, ValueError):
        return 0.0


def estimate_month(
    daily_totals: list[dict],
    month_start: date,
    settings: EarningsSettings,
) -> dict:
    paid_hours = round(sum(_hours(item) for item in daily_totals), 2)
    threshold = monthly_threshold(settings, month_start)
    ordinary_hours = min(paid_hours, threshold)
    overtime_hours = round(max(0.0, paid_hours - threshold), 2)
    overtime_rate = settings.overtime_rate or settings.hourly_rate

    allowance_days = 0
    uncertain_allowance_days = 0
    for item in daily_totals:
        status = str(item.get("status") or "")
        if _hours(item) <= ALLOWANCE_MIN_HOURS or status in _NO_ALLOWANCE_STATUSES:
            continue
        allowance_days += 1
        if status == UNCERTAIN_ALLOWANCE_STATUS:
            uncertain_allowance_days += 1
    allowance_rate = settings.daily_allowance or 0.0

    ordinary_amount = round(ordinary_hours * settings.hourly_rate, 2)
    overtime_amount = round(overtime_hours * overtime_rate, 2)
    allowance_amount = round(allowance_days * allowance_rate, 2)
    return {
        "paid_hours": paid_hours,
        "threshold_hours": threshold,
        "weekdays": weekdays_in_month(month_start),
        "ordinary_hours": ordinary_hours,
        "ordinary_amount": ordinary_amount,
        "overtime_hours": overtime_hours,
        "overtime_rate": overtime_rate,
        "overtime_rate_is_ordinary": settings.overtime_rate is None,
        "overtime_amount": overtime_amount,
        "allowance_days": allowance_days,
        "uncertain_allowance_days": uncertain_allowance_days,
        "allowance_rate": allowance_rate,
        "allowance_amount": allowance_amount,
        "gross_total": round(ordinary_amount + overtime_amount + allowance_amount, 2),
    }


def format_euro(value: float) -> str:
    """1234.5 -> '1.234,50 €'."""
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def format_number(value: float) -> str:
    """12.5 -> '12,5'; 40.0 -> '40'."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")

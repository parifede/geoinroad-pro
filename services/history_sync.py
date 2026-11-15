"""Scaricamento dello storico, un mese alla volta dal piu' recente.

Funzioni pure: decidono quale mese scaricare e quando fermarsi. Lo stato
(mesi gia' fatti) vive in SQLite, cosi' dopo un riavvio si riparte da
dove ci si era fermati e i mesi passati non si riscaricano piu'.
"""

from datetime import date, timedelta

MONTH_DONE = "done"
MONTH_EMPTY = "empty"

# Un anno intero senza nulla: prima di li' non si lavorava ancora.
EMPTY_MONTHS_TO_STOP = 12
# Tetto di sicurezza se il portale restituisse sempre qualcosa.
MAX_YEARS_BACK = 15

# Sigle che non dicono nulla sul lavoro (riposo): un mese fatto solo di
# queste conta come vuoto.
_NEUTRAL_MARKERS = {"", "R", "RC"}


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def month_bounds(key: str) -> tuple[date, date]:
    year, month = (int(part) for part in key.split("-"))
    start = date(year, month, 1)
    next_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, next_start - timedelta(days=1)


def previous_month(key: str) -> str:
    start, _ = month_bounds(key)
    return month_key(start - timedelta(days=1))


def next_history_month(today: date, months: dict[str, str]) -> str | None:
    """Il prossimo mese passato da scaricare, o None se lo storico e' completo.

    Si parte dal mese precedente a quello corrente (il mese in corso lo
    aggiorna gia' la sincronizzazione normale) e si va indietro. I mesi gia'
    scaricati si saltano; dopo EMPTY_MONTHS_TO_STOP mesi vuoti di fila ci si
    ferma.
    """
    key = previous_month(month_key(today))
    empty_run = 0
    for _ in range(MAX_YEARS_BACK * 12):
        status = months.get(key)
        if status is None:
            return key
        empty_run = empty_run + 1 if status == MONTH_EMPTY else 0
        if empty_run >= EMPTY_MONTHS_TO_STOP:
            return None
        key = previous_month(key)
    return None


def history_is_complete(today: date, months: dict[str, str]) -> bool:
    return next_history_month(today, months) is None


def payload_is_complete(payload: dict) -> bool:
    """Il portale ha restituito il calendario del mese (non un errore)."""
    return bool((payload or {}).get("sync_range"))


def payload_is_empty(payload: dict) -> bool:
    """Nessuna ora pagata e nessuna giornata tipizzata oltre ai riposi."""
    for row in (payload or {}).get("rows") or []:
        try:
            value = float(str(row.get("value") or "0").replace(",", "."))
        except ValueError:
            value = 0.0
        if value > 0:
            return False
        if str(row.get("work_marker") or "").upper() not in _NEUTRAL_MARKERS:
            return False
    return True


def month_label(key: str) -> str:
    months = [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ]
    year, month = (int(part) for part in key.split("-"))
    return f"{months[month - 1]} {year}"


HISTORY_COMPLETE = "complete"
HISTORY_PAUSED = "paused"
HISTORY_STOPPED = "stopped"


async def run_history(
    *,
    today,
    fetch_months,
    collect_month,
    mark_month,
    is_active,
    set_status,
    sleep,
    pause_seconds: float = 2.0,
    retry_seconds: float = 10.0,
    max_failures: int = 2,
) -> str:
    """Scarica i mesi mancanti uno alla volta, dal piu' recente.

    Le dipendenze arrivano dall'app (WebView, SQLite, UI) cosi' il ciclo si
    prova senza telefono. Un mese si segna solo se il portale ha restituito
    il calendario completo; dopo max_failures errori di fila ci si ferma e
    si riprende alla prossima apertura. Restituisce il motivo dello stop.
    """
    failures = 0
    while is_active():
        month = next_history_month(today(), await fetch_months())
        if month is None:
            set_status("")
            return HISTORY_COMPLETE
        set_status(f"Storico: scarico {month_label(month)}...")
        payload = await collect_month(month)
        if not is_active():
            return HISTORY_STOPPED
        if not payload_is_complete(payload):
            failures += 1
            if failures >= max_failures:
                set_status("Storico in pausa: riprendo alla prossima apertura.")
                return HISTORY_PAUSED
            await sleep(retry_seconds)
            continue
        failures = 0
        await mark_month(month, MONTH_EMPTY if payload_is_empty(payload) else MONTH_DONE)
        await sleep(pause_seconds)
    return HISTORY_STOPPED

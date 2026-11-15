from datetime import date, datetime, timedelta
from typing import Awaitable, Callable

import flet as ft

from app_config import ROUTE_DASHBOARD, BRAND_ACCENT, BRAND_DARK, BRAND_SURFACE
from app_state import AppState
from services.earnings import (
    DISCLAIMER,
    estimate_month,
    format_euro,
    format_number,
)

_ACCENT = BRAND_ACCENT
_BG = BRAND_DARK
_SURFACE = BRAND_SURFACE
_CARD = "#FFFFFF"
_TEXT = "#1A1A1A"
_MUTED = "#86868B"
_DIVIDER = "#E5E5EA"

_SHADOW = ft.BoxShadow(
    spread_radius=0,
    blur_radius=10,
    color="#12000000",
    offset=ft.Offset(0, 2),
)


def build_dashboard_view(
    *,
    page: ft.Page,
    state: AppState,
    on_back_to_diary: Callable[[], Awaitable[None]],
    on_period_change: Callable[[str], Awaitable[None]],
    on_shift_period: Callable[[int], Awaitable[None]] | None = None,
    on_reset_period: Callable[[], Awaitable[None]] | None = None,
    on_refresh_stats: Callable[[], Awaitable[None]] | None = None,
    on_edit_earnings: Callable[[], Awaitable[None]] | None = None,
) -> ft.View:
    return ft.View(
        route=ROUTE_DASHBOARD,
        can_pop=False,
        bgcolor=_SURFACE,
        padding=0,
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        _header(page, on_back_to_diary, on_refresh_stats),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                                spacing=0,
                                controls=[
                                    ft.Container(height=20),
                                    _period_filter(page, state, on_period_change),
                                    ft.Container(height=10),
                                    _period_nav(page, state, on_shift_period, on_reset_period),
                                    _sync_status(state),
                                    ft.Container(height=10),
                                    _metrics_row(state),
                                    ft.Container(height=16),
                                    _chart_card(state.timelog_daily_totals, state.dashboard_period),
                                    *(
                                        [
                                            ft.Container(height=16),
                                            _earnings_card(page, state, on_edit_earnings),
                                        ]
                                        if state.dashboard_period == "month"
                                        else []
                                    ),
                                    ft.Container(height=40),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


def _header(
    page: ft.Page,
    on_back_to_diary: Callable[[], Awaitable[None]],
    on_refresh_stats: Callable[[], Awaitable[None]] | None = None,
) -> ft.Control:
    return ft.Container(
        bgcolor=_BG,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.WHITE,
                    icon_size=20,
                    tooltip="Torna al diario",
                    on_click=lambda _: page.run_task(on_back_to_diary),
                ),
                ft.Text(
                    "Statistiche lavoro",
                    size=18,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.WHITE,
                ),
                ft.Row(
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.SYNC,
                            icon_color=ft.Colors.WHITE,
                            icon_size=20,
                            tooltip="Ricarica i dati dal portale",
                            on_click=lambda _: (
                                page.run_task(on_refresh_stats)
                                if on_refresh_stats is not None
                                else None
                            ),
                        ),
                        ft.Container(
                            width=56,
                            height=36,
                            content=ft.Image(src="download.png", fit="contain"),
                        ),
                    ],
                ),
            ],
        ),
    )


def _metrics_row(state: AppState) -> ft.Control:
    period = state.timelog_period_summary or state.timelog_summary
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16),
        content=ft.ResponsiveRow(
            spacing=12,
            run_spacing=12,
            controls=[
                _metric_card(
                    col=4,
                    icon=ft.Icons.LIST_ALT,
                    value=str(period.get("total_entries", 0)),
                    label="Timelog",
                ),
                _metric_card(
                    col=4,
                    icon=ft.Icons.ACCESS_TIME,
                    value=_fmt_h(period.get("total_value", 0)),
                    label="Totale ore",
                ),
                _metric_card(
                    col=4,
                    icon=ft.Icons.TRENDING_UP,
                    value=_fmt_h(period.get("average_value", 0)),
                    label="Media",
                ),
            ],
        ),
    )


def _period_filter(
    page: ft.Page,
    state: AppState,
    on_period_change: Callable[[str], Awaitable[None]],
) -> ft.Control:
    options = [
        ("day", "Giorno"),
        ("week", "Week"),
        ("month", "Mese"),
    ]
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16),
        content=ft.Row(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=9),
                    border_radius=999,
                    bgcolor=_ACCENT if state.dashboard_period == key else _CARD,
                    ink=True,
                    on_click=lambda _, p=key: page.run_task(on_period_change, p),
                    content=ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE if state.dashboard_period == key else _TEXT,
                    ),
                )
                for key, label in options
            ],
        ),
    )


def _period_nav(
    page: ft.Page,
    state: AppState,
    on_shift_period: Callable[[int], Awaitable[None]] | None,
    on_reset_period: Callable[[], Awaitable[None]] | None,
) -> ft.Control:
    is_anchored_elsewhere = bool(state.dashboard_anchor)
    label = ft.Text(
        _period_range_label(state),
        size=13,
        weight=ft.FontWeight.W_700,
        color=_ACCENT if is_anchored_elsewhere else _TEXT,
        text_align=ft.TextAlign.CENTER,
    )
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    icon_color=_TEXT,
                    tooltip="Periodo precedente",
                    on_click=lambda _: (
                        page.run_task(on_shift_period, -1)
                        if on_shift_period is not None
                        else None
                    ),
                ),
                ft.Container(
                    expand=True,
                    ink=True,
                    border_radius=10,
                    padding=ft.padding.symmetric(vertical=6),
                    tooltip="Tocca per tornare a oggi",
                    on_click=lambda _: (
                        page.run_task(on_reset_period)
                        if on_reset_period is not None
                        else None
                    ),
                    content=label,
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    icon_color=_TEXT,
                    tooltip="Periodo successivo",
                    on_click=lambda _: (
                        page.run_task(on_shift_period, 1)
                        if on_shift_period is not None
                        else None
                    ),
                ),
            ],
        ),
    )


def _sync_status(state: AppState) -> ft.Control:
    # La sincronizzazione chiesta dall'utente ha la precedenza sulla riga
    # dello storico che si scarica in background.
    message = state.dashboard_status or state.history_status
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=2),
        visible=bool(message),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ProgressRing(
                    width=12,
                    height=12,
                    stroke_width=2,
                    color=_ACCENT,
                    visible=bool(state.dashboard_status) or state.history_running,
                ),
                ft.Text(
                    message,
                    size=11,
                    color=_ACCENT,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
            ],
        ),
    )


def _period_range_label(state: AppState) -> str:
    summary = state.timelog_period_summary or {}
    start = str(summary.get("start_date", "") or "")
    end = str(summary.get("end_date", "") or "")
    period = state.dashboard_period
    if period == "month":
        if start:
            return f"{_month_name(start).capitalize()} {start[:4]}"
        return "Mese corrente"
    if period == "day":
        return _short_date(start) or "Oggi"
    if start and end:
        return f"{_short_date(start)} – {_short_date(end)}"
    return "Settimana corrente"


def _short_date(value: str) -> str:
    parsed = _parse_anchor_date(value)
    return parsed.strftime("%d/%m") if parsed else ""


def _metric_card(*, col: int, icon: str, value: str, label: str) -> ft.Control:
    return ft.Container(
        col=col,
        padding=16,
        bgcolor=_CARD,
        border_radius=18,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon, color=_ACCENT, size=20),
                ft.Text(
                    value,
                    size=22,
                    weight=ft.FontWeight.W_800,
                    color=_TEXT,
                ),
                ft.Text(
                    label,
                    size=11,
                    color=_MUTED,
                    max_lines=1,
                ),
            ],
        ),
    )


def _chart_card(daily_totals: list[dict], period: str) -> ft.Control:
    content: ft.Control
    if not daily_totals:
        content = ft.Text(
            "Nessun dato disponibile. Apri il menu rapido e scegli 'Statistiche lavoro'.",
            color=_MUTED,
            size=13,
        )
    else:
        content = (
            _month_grid(daily_totals)
            if period == "month"
            else _period_grid(daily_totals, period)
        )

    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Text(
                    _chart_title(
                        period,
                        daily_totals[0].get("day") if daily_totals else None,
                    ),
                    size=15,
                    weight=ft.FontWeight.W_700,
                    color=_TEXT,
                ),
                content,
                ft.Text(
                    "Verde: lavorato · Verde chiaro: abortive (8 h) · "
                    "Giallo: ferie (8 h) · Rosa: altri adempimenti · "
                    "Blu: riposo · Arancio: festivo · "
                    "Rosso: malattia/infortunio · Grigio: assenza",
                    size=10,
                    color=_MUTED,
                    visible=bool(daily_totals),
                ),
            ],
        ),
    )


def _bar_chart(daily_totals: list[dict]) -> ft.Control:
    max_val = max((_safe_float(d.get("total_value", 0)) for d in daily_totals), default=1) or 1
    bars = []
    for item in daily_totals:
        val = _safe_float(item.get("total_value", 0))
        bar_h = max(10, int((val / max_val) * 110))
        bars.append(
            ft.Container(
                expand=1,
                padding=ft.padding.symmetric(horizontal=3),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                    controls=[
                        ft.Container(
                            width=10,
                            height=bar_h,
                            bgcolor=_ACCENT,
                            border_radius=ft.border_radius.only(top_left=6, top_right=6),
                        ),
                        ft.Text(item.get("day", "")[5:], size=9, color=_MUTED),
                        ft.Text(
                            _fmt_h(val),
                            size=9,
                            weight=ft.FontWeight.W_600,
                            color=_TEXT,
                        ),
                    ],
                ),
            )
        )

    return ft.Container(
        height=170,
        content=ft.Row(
            spacing=0,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=bars,
        ),
    )


def _period_grid(daily_totals: list[dict], period: str) -> ft.Control:
    max_val = max((_safe_float(d.get("total_value", 0)) for d in daily_totals), default=1) or 1
    cells = [_month_day_cell(item, max_val) for item in daily_totals]
    if period == "day":
        return ft.Container(
            height=80,
            content=ft.Row(
                spacing=4,
                controls=[
                    ft.Container(width=58, content=cells[0]) if cells else ft.Container(width=58),
                ],
            ),
        )
    while len(cells) < 7:
        cells.append(ft.Container(expand=1))
    return ft.Container(
        height=58,
        content=ft.Row(
            spacing=4,
            controls=cells[:7],
        ),
    )


def _month_grid(daily_totals: list[dict]) -> ft.Control:
    max_val = max((_safe_float(d.get("total_value", 0)) for d in daily_totals), default=1) or 1
    rows = []
    for start in range(0, len(daily_totals), 7):
        week_items = daily_totals[start:start + 7]
        cells = [_month_day_cell(item, max_val) for item in week_items]
        while len(cells) < 7:
            cells.append(ft.Container(expand=1))
        rows.append(
            ft.Row(
                spacing=4,
                controls=cells,
            )
        )

    return ft.Container(
        height=285,
        content=ft.Column(
            spacing=6,
            controls=rows,
        ),
    )


# Colori allineati al calendario del portale Geoin ROAD:
# verde presenti, verde chiaro abortive, blu riposi, giallo ferie,
# arancio festivi, rosso malattia/infortunio, grigio altre assenze,
# rosa altri adempimenti (AA).
_WORKED_COLOR = "#388E3C"
_ABORTIVE_COLOR = "#81C784"
_DAY_STATUS_STYLES = {
    "adempimenti": ("AA", "#EC407A"),
    "riposo": ("Riposo", "#1E88E5"),
    "ferie": ("Ferie", "#FBC02D"),
    "permesso": ("Perm.", "#26A69A"),
    "malattia": ("Malat.", "#E53935"),
    "infortunio": ("Infort.", "#C62828"),
    "festivo": ("Festivo", "#FB8C00"),
    "assenza": ("Ass.", "#757575"),
}


def _month_day_cell(item: dict, max_val: float) -> ft.Control:
    val = _safe_float(item.get("total_value", 0))
    day_label = item.get("day", "")[-2:]
    status = str(item.get("status", "") or "")
    fill_ratio = (val / max_val) if max_val else 0
    status_style = _DAY_STATUS_STYLES.get(status) if val <= 0 else None

    if val > 0:
        if status == "abortive":
            bar_color = _ABORTIVE_COLOR
        elif status in ("ferie", "adempimenti"):
            bar_color = _DAY_STATUS_STYLES[status][1]
        else:
            bar_color = _WORKED_COLOR
        bar_opacity = max(0.25, fill_ratio)
        bottom_text = _fmt_h(val)
        bottom_color = _TEXT
        bottom_weight = ft.FontWeight.W_700
    elif status_style is not None:
        bar_color = status_style[1]
        bar_opacity = 1
        bottom_text = status_style[0]
        bottom_color = status_style[1]
        bottom_weight = ft.FontWeight.W_700
    else:
        bar_color = _DIVIDER
        bar_opacity = 1
        bottom_text = "0 h"
        bottom_color = _MUTED
        bottom_weight = ft.FontWeight.W_500

    return ft.Container(
        expand=1,
        height=52,
        bgcolor="#FAFAFB",
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=4, vertical=5),
        content=ft.Column(
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(day_label, size=10, color=_MUTED, weight=ft.FontWeight.W_700),
                ft.Container(
                    width=22,
                    height=5,
                    border_radius=999,
                    bgcolor=bar_color,
                    opacity=bar_opacity,
                ),
                ft.Text(
                    bottom_text,
                    size=9,
                    color=bottom_color,
                    weight=bottom_weight,
                    max_lines=1,
                ),
            ],
        ),
    )


def _earnings_line(label: str, amount: str, *, strong: bool = False) -> ft.Control:
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                label,
                size=15 if strong else 13,
                color=_TEXT,
                weight=ft.FontWeight.W_700 if strong else ft.FontWeight.W_500,
                expand=True,
            ),
            ft.Text(
                amount,
                size=22 if strong else 13,
                color=_ACCENT if strong else _TEXT,
                weight=ft.FontWeight.W_800 if strong else ft.FontWeight.W_600,
            ),
        ],
    )


def _earnings_card(
    page: ft.Page,
    state: AppState,
    on_edit_earnings: Callable[[], Awaitable[None]] | None,
) -> ft.Control:
    settings = state.earnings_settings
    daily_totals = state.timelog_daily_totals or []
    month_start = _parse_iso_date(daily_totals[0].get("day") if daily_totals else None)

    controls: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Stima del mese", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                ft.TextButton(
                    "Imposta" if settings is None else "Modifica",
                    style=ft.ButtonStyle(color=_ACCENT),
                    on_click=lambda _: (
                        page.run_task(on_edit_earnings)
                        if on_edit_earnings is not None
                        else None
                    ),
                ),
            ],
        )
    ]
    if settings is None or month_start is None:
        controls.append(
            ft.Text(
                "Inserisci la tua paga oraria e le ore settimanali da contratto "
                "per vedere quanto prendi questo mese. Le cifre restano solo "
                "sul telefono.",
                size=13,
                color=_MUTED,
            )
        )
    else:
        estimate = estimate_month(daily_totals, month_start, settings)
        overtime_label = (
            f"Straordinari {_fmt_h(estimate['overtime_hours'])} × "
            f"{format_euro(estimate['overtime_rate'])}"
        )
        if estimate["overtime_rate_is_ordinary"] and estimate["overtime_hours"] > 0:
            overtime_label += " (paga ordinaria: imposta quella straordinaria)"
        controls.extend(
            [
                _earnings_line(
                    f"Ore ordinarie {_fmt_h(estimate['ordinary_hours'])} × "
                    f"{format_euro(settings.hourly_rate)}",
                    format_euro(estimate["ordinary_amount"]),
                ),
                _earnings_line(overtime_label, format_euro(estimate["overtime_amount"])),
                _earnings_line(
                    f"Diaria {estimate['allowance_days']} giorni × "
                    f"{format_euro(estimate['allowance_rate'])}"
                    if settings.daily_allowance
                    else "Diaria non impostata",
                    format_euro(estimate["allowance_amount"]),
                ),
            ]
        )
        if estimate["uncertain_allowance_days"] and settings.daily_allowance:
            controls.append(
                ft.Text(
                    f"Di cui {estimate['uncertain_allowance_days']} con AA: "
                    "diaria da verificare.",
                    size=11,
                    color=_MUTED,
                )
            )
        controls.extend(
            [
                ft.Text(
                    f"Soglia straordinari del mese: {_fmt_h(estimate['threshold_hours'])} "
                    f"({format_number(settings.weekly_hours)} h/sett. × "
                    f"{estimate['weekdays']} giorni lun-ven)",
                    size=11,
                    color=_MUTED,
                ),
                ft.Divider(height=1, color=_DIVIDER),
                _earnings_line(
                    "Totale lordo stimato",
                    format_euro(estimate["gross_total"]),
                    strong=True,
                ),
                ft.Text(DISCLAIMER, size=12, color=_MUTED, italic=True),
            ]
        )

    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(spacing=8, controls=controls),
    )


def _parse_iso_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10]).replace(day=1)
    except ValueError:
        return None


def build_earnings_dialog(
    *,
    page: ft.Page,
    state: AppState,
    on_save: Callable[[dict], Awaitable[None]],
) -> ft.AlertDialog:
    settings = state.earnings_settings

    def field(label: str, value: float | None, hint: str) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=format_number(value) if value else "",
            hint_text=hint,
            keyboard_type=ft.KeyboardType.NUMBER,
            focused_border_color=_ACCENT,
            cursor_color=_ACCENT,
        )

    hourly = field("Paga oraria (€)", settings.hourly_rate if settings else None, "es. 12,50")
    overtime = field(
        "Paga oraria straordinaria (€, facoltativa)",
        settings.overtime_rate if settings else None,
        "la trovi in busta paga",
    )
    allowance = field(
        "Diaria giornaliera (€, facoltativa)",
        settings.daily_allowance if settings else None,
        "es. 30",
    )
    weekly = field(
        "Ore settimanali da contratto",
        settings.weekly_hours if settings else None,
        "es. 40",
    )
    error = ft.Text("", size=12, color=ft.Colors.RED_700, visible=False)

    def show_error(message: str) -> None:
        error.value = message
        error.visible = bool(message)
        page.update()

    async def save() -> None:
        await on_save(
            {
                "hourly_rate": hourly.value or "",
                "overtime_rate": overtime.value or "",
                "daily_allowance": allowance.value or "",
                "weekly_hours": weekly.value or "",
                "show_error": show_error,
            }
        )

    return ft.AlertDialog(
        modal=True,
        title=ft.Text("Stima del mese"),
        content=ft.Column(
            tight=True,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(
                    "Le cifre restano solo su questo telefono. Straordinari: le "
                    "ore oltre la soglia mensile (ore settimanali / 5 × giorni "
                    "dal lunedì al venerdì). Diaria: giorni con più di 6 ore, "
                    "ferie escluse.",
                    size=12,
                    color=_MUTED,
                ),
                hourly,
                overtime,
                allowance,
                weekly,
                error,
            ],
        ),
        actions=[
            ft.TextButton("Annulla", on_click=lambda _: page.pop_dialog()),
            ft.TextButton("Salva", on_click=lambda _: page.run_task(save)),
        ],
    )


def _stats_card(state: AppState) -> ft.Control:
    rows = state.scraped_stats.get("rows", []) if state.scraped_stats else []
    if not rows:
        debug = state.last_stats_debug or state.scraped_stats.get("debug", {}) if state.scraped_stats else {}
        debug_text = ""
        if debug:
            debug_text = (
                f"Diagnostica: testo {debug.get('text_length', 0)} caratteri, "
                f"orari {debug.get('time_range_count', 0)}, "
                f"inizio/fine {debug.get('start_count', 0)}/{debug.get('end_count', 0)}."
            )
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=16),
            padding=ft.padding.symmetric(horizontal=20, vertical=20),
            bgcolor=_CARD,
            border_radius=20,
            shadow=_SHADOW,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Ultima sessione", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                    ft.Text(
                        "Nessun dato. Apri il menu rapido e scegli 'Statistiche lavoro'.",
                        size=13,
                        color=_MUTED,
                    ),
                    ft.Text(
                        debug_text,
                        size=12,
                        color=_MUTED,
                        visible=bool(debug_text),
                    ),
                ],
            ),
        )

    items = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(
                    item.get("label", ""),
                    size=13,
                    color=_TEXT,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                ),
                ft.Text(
                    _fmt_val(item.get("value", 0)),
                    size=13,
                    color=_ACCENT,
                    weight=ft.FontWeight.W_700,
                ),
            ],
        )
        for item in rows[:12]
        if _safe_float(item.get("value", 0)) > 0
    ]

    if not items:
        items = [ft.Text("Solo etichette di percorso rilevate.", size=13, color=_MUTED)]

    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Ultima sessione", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                ft.Divider(color=_DIVIDER, height=1),
                *items,
            ],
        ),
    )


def _chart_title(period: str, anchor_date: str | None = None) -> str:
    return {
        "day": "Giorno selezionato",
        "week": _week_title(anchor_date),
        "month": f"Mese {_month_name(anchor_date)}",
    }.get(period, "Giorni rilevati")


def _week_title(anchor_date: str | None) -> str:
    parsed = _parse_anchor_date(anchor_date)
    if parsed is None:
        return "Settimana corrente"
    monday = parsed - timedelta(days=parsed.weekday())
    if monday <= date.today() <= monday + timedelta(days=6):
        return "Settimana corrente"
    return "Settimana"


def _month_name(anchor_date: str | None = None) -> str:
    months = [
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ]
    parsed = _parse_anchor_date(anchor_date) or date.today()
    return months[parsed.month - 1]


def _parse_anchor_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _entries_card(entries: list[dict]) -> ft.Control:
    if not entries:
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=16),
            padding=ft.padding.symmetric(horizontal=20, vertical=20),
            bgcolor=_CARD,
            border_radius=20,
            shadow=_SHADOW,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Attività recenti", size=15, weight=ft.FontWeight.W_700, color=_TEXT),
                    ft.Text("Nessuna voce nel database locale.", size=13, color=_MUTED),
                ],
            ),
        )

    rows = []
    for entry in entries:
        val = _safe_float(entry.get("value", 0))
        if val <= 0:
            continue
        date_str = entry.get("work_date") or entry.get("captured_at", "")[:10]
        rows.append(
            ft.Container(
                padding=ft.padding.symmetric(vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(1, _DIVIDER)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(
                                    entry.get("label", ""),
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=_TEXT,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(date_str, size=11, color=_MUTED),
                            ],
                        ),
                        ft.Text(
                            _fmt_h(val),
                            size=14,
                            weight=ft.FontWeight.W_700,
                            color=_ACCENT,
                        ),
                    ],
                ),
            )
        )

    if not rows:
        rows = [ft.Text("Solo etichette di percorso rilevate.", size=13, color=_MUTED)]

    return ft.Container(
        margin=ft.margin.symmetric(horizontal=16),
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        bgcolor=_CARD,
        border_radius=20,
        shadow=_SHADOW,
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Text(
                    "Attività recenti",
                    size=15,
                    weight=ft.FontWeight.W_700,
                    color=_TEXT,
                ),
                ft.Container(height=12),
                *rows,
            ],
        ),
    )


def _fmt_h(value) -> str:
    hours_decimal = max(0.0, _safe_float(value))
    total_minutes = int(round(hours_decimal * 60))
    hours, minutes = divmod(total_minutes, 60)
    if minutes:
        return f"{hours} h {minutes} m"
    return f"{hours} h"


def _fmt_val(value) -> str:
    v = _safe_float(value)
    return _fmt_h(v) if v > 0 else "—"


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

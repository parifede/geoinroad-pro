from datetime import date, datetime
from typing import Awaitable, Callable

import flet as ft

from app_config import ROUTE_DASHBOARD, BRAND_ACCENT, BRAND_DARK, BRAND_SURFACE
from app_state import AppState

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
                        _header(page, on_back_to_diary),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                                spacing=0,
                                controls=[
                                    ft.Container(height=20),
                                    _period_filter(page, state, on_period_change),
                                    ft.Container(height=16),
                                    _metrics_row(state),
                                    ft.Container(height=16),
                                    _chart_card(state.timelog_daily_totals, state.dashboard_period),
                                    ft.Container(height=40),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


def _header(page: ft.Page, on_back_to_diary: Callable[[], Awaitable[None]]) -> ft.Control:
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
                ft.Container(
                    width=72,
                    height=36,
                    content=ft.Image(src="download.png", fit="contain"),
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
                    _chart_title(period),
                    size=15,
                    weight=ft.FontWeight.W_700,
                    color=_TEXT,
                ),
                content,
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


def _month_day_cell(item: dict, max_val: float) -> ft.Control:
    val = _safe_float(item.get("total_value", 0))
    day_label = item.get("day", "")[-2:]
    fill_ratio = (val / max_val) if max_val else 0
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
                    bgcolor=_ACCENT if val > 0 else _DIVIDER,
                    opacity=max(0.25, fill_ratio) if val > 0 else 1,
                ),
                ft.Text(
                    _fmt_h(val) if val > 0 else "0 h",
                    size=9,
                    color=_TEXT if val > 0 else _MUTED,
                    weight=ft.FontWeight.W_700 if val > 0 else ft.FontWeight.W_500,
                    max_lines=1,
                ),
            ],
        ),
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
        "week": "Settimana Geoin ROAD",
        "month": f"Mese {_month_name(anchor_date)}",
    }.get(period, "Giorni rilevati")


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

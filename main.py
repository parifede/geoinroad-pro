import asyncio
import json
from datetime import date, datetime, timezone

import flet as ft

from app_config import (
    ACTION_PREFIX,
    APP_TITLE,
    BRAND_DARK,
    BUG_REPORT_WHATSAPP_NUMBER,
    ERROR_PREFIX,
    RELOAD_PREFIX,
    ROUTE_DASHBOARD,
    ROUTE_LOCK,
    ROUTE_SPLASH,
    ROUTE_WEBVIEW,
    STATS_PREFIX,
    STATUS_PREFIX,
)
from app_state import AppState
from services.credential_store import CredentialStore
from services.bug_report import build_whatsapp_report_url
from services.js_bridge import build_auto_login_script
from views.dashboard import build_dashboard_view
from views.lock_screen import build_lock_screen
from views.splash_screen import build_splash_view
from views.web_view import build_web_view


def main(page: ft.Page):
    state = AppState()
    credential_store = CredentialStore()
    preferences = ft.SharedPreferences()
    url_launcher = ft.UrlLauncher()
    timelog_init_task = None

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window.width = 430
    page.window.height = 880
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#1A1A1A"
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.PINK,
        scaffold_bgcolor="#1A1A1A",
    )

    def set_lock_status(message: str, color: str = ft.Colors.BLUE_GREY_700) -> None:
        state.lock_message = message
        if state.lock_status_ref.current is not None:
            state.lock_status_ref.current.value = message
            state.lock_status_ref.current.color = color
            page.update()

    def set_web_status(message: str) -> None:
        state.web_status = message
        if state.web_status_ref.current is not None:
            state.web_status_ref.current.value = message
            page.update()

    def set_web_progress(progress: int) -> None:
        state.web_progress = progress
        if state.web_progress_ref.current is not None:
            state.web_progress_ref.current.value = progress / 100 if progress else None
            page.update()

    async def go_to(route: str) -> None:
        page.route = route
        build_views()

    async def ensure_timelog_repository() -> None:
        nonlocal timelog_init_task
        if state.database_path:
            return
        if timelog_init_task is None:
            timelog_init_task = asyncio.create_task(
                state.timelog_repository.initialize(
                    page=page,
                    storage_paths=state.storage_paths,
                )
            )
        try:
            state.database_path = str(await timelog_init_task)
        except Exception:
            timelog_init_task = None
            raise

    async def initialize_app() -> None:
        await asyncio.sleep(0.4)
        state.credentials_available = await credential_store.has_saved_credentials(
            preferences
        )
        if state.credentials_available:
            try:
                username, password = await credential_store.load_credentials(
                    page=page,
                    storage=state.storage,
                    preferences=preferences,
                )
                state.session_unlocked = True
                state.cached_username = username
                state.cached_password = password
                state.account_id = state.timelog_repository.account_id_for_username(
                    username
                )
                await go_to(ROUTE_WEBVIEW)
                page.run_task(ensure_timelog_repository)
                page.run_task(refresh_timelog_data)
                return
            except Exception as exc:
                set_lock_status(
                    f"Accesso automatico non riuscito: {exc}",
                    ft.Colors.RED_700,
                )
        else:
            set_lock_status(
                "Inserisci le credenziali Dimetior e salvale nel vault protetto.",
                ft.Colors.BLUE_GREY_700,
            )
        build_views()
        page.run_task(ensure_timelog_repository)

    async def configure_webview() -> None:
        if not state.supports_embedded_webview(page):
            return
        if state.webview_ref.current is None:
            return
        if not page.web:
            await state.webview_ref.current.set_javascript_mode(
                state.javascript_mode_class.UNRESTRICTED
            )
        state.webview_ready = True
        set_web_status("WebView pronta. In attesa delle fasi di auto-login e scraping.")

    async def refresh_timelog_data() -> None:
        await ensure_timelog_repository()
        if not state.database_path:
            return
        today = date.today().isoformat()
        if state.dashboard_period == "year":
            state.dashboard_period = "month"
        state.timelog_summary = await state.timelog_repository.fetch_summary(
            account_id=state.account_id,
        )
        state.timelog_period_summary = await state.timelog_repository.fetch_period_summary(
            account_id=state.account_id,
            period=state.dashboard_period,
            anchor_date=today,
        )
        state.timelog_recent_entries = await state.timelog_repository.fetch_recent_entries(
            limit=10,
            account_id=state.account_id,
        )
        state.timelog_daily_totals = await state.timelog_repository.fetch_period_daily_totals(
            account_id=state.account_id,
            period=state.dashboard_period,
            anchor_date=today,
        )

    async def start_background_stats_sync() -> None:
        if state.background_stats_started:
            return
        if page.web or not state.supports_embedded_webview(page):
            return
        if state.webview_ref.current is None:
            return
        if "/login" in (state.last_loaded_url or ""):
            return
        state.background_stats_started = True
        set_web_status("Aggiornamento statistiche in background avviato.")
        await asyncio.sleep(1.0)
        try:
            result = await state.webview_ref.current.run_javascript(
                "(function(){"
                "if(!window.GeoinroadApp||!window.GeoinroadApp.collectStats){return 'missing';}"
                "window.GeoinroadApp.collectStats({background:true});"
                "return 'started';"
                "})()"
            )
            if "missing" in str(result):
                state.background_stats_started = False
                set_web_status("Scraping rimandato: bridge non ancora pronto.")
        except RuntimeError as exc:
            state.background_stats_started = False
            set_web_status(f"Aggiornamento statistiche rimandato: {exc}")

    async def inject_automation() -> None:
        if page.web:
            set_web_status(
                "Iniezione JS disponibile solo su target nativi supportati dalla WebView."
            )
            return
        if not state.supports_embedded_webview(page):
            return
        if state.webview_ref.current is None:
            return
        if not state.cached_username or not state.cached_password:
            set_web_status("Sblocco riuscito, ma le credenziali non sono disponibili in memoria.")
            return

        script = build_auto_login_script(
            username=state.cached_username,
            password=state.cached_password,
        )
        await state.webview_ref.current.run_javascript(script)
        state.autologin_injected = True
        set_web_status("Script JS iniettato: auto-login e menu rapido pronti.")
        page.run_task(start_background_stats_sync)

    def show_dashboard_over_live_webview() -> bool:
        if state.session_unlocked and any(
            view.route == ROUTE_WEBVIEW for view in page.views
        ):
            page.route = ROUTE_DASHBOARD
            page.drawer = None
            page.views = [
                view for view in page.views if view.route != ROUTE_DASHBOARD
            ]
            page.views.append(
                build_dashboard_view(
                    page=page,
                    state=state,
                    on_back_to_diary=back_to_diary,
                    on_period_change=set_dashboard_period,
                )
            )
            page.update()
            return True
        return False

    def reveal_live_webview() -> bool:
        if any(view.route == ROUTE_WEBVIEW for view in page.views):
            page.route = ROUTE_WEBVIEW
            page.views = [
                view for view in page.views if view.route != ROUTE_DASHBOARD
            ]
            page.update()
            return True
        return False

    async def open_dashboard() -> None:
        await refresh_timelog_data()
        if show_dashboard_over_live_webview():
            return
        await go_to(ROUTE_DASHBOARD)

    async def refresh_visible_dashboard() -> None:
        await refresh_timelog_data()
        if page.route == ROUTE_DASHBOARD:
            if show_dashboard_over_live_webview():
                return
            build_views()

    async def open_dashboard_fast() -> None:
        if show_dashboard_over_live_webview():
            page.run_task(refresh_visible_dashboard)
            return
        await open_dashboard()

    async def set_dashboard_period(period: str) -> None:
        if period == "year":
            period = "month"
        state.dashboard_period = period
        await refresh_timelog_data()
        if page.route == ROUTE_DASHBOARD and show_dashboard_over_live_webview():
            return
        build_views()

    async def back_to_diary() -> None:
        if reveal_live_webview():
            return
        await go_to(ROUTE_WEBVIEW)

    async def persist_scraped_stats(payload: dict) -> None:
        state.last_stats_debug = payload.get("debug", {}) if payload else {}
        is_background = bool((payload.get("debug") or {}).get("background_sync")) if payload else False
        is_quick_response = bool((payload.get("debug") or {}).get("quick_response")) if payload else False
        if is_quick_response and not is_background:
            set_web_status("Statistiche rapide ricevute, attendo il report completo.")
            state.scraped_stats = payload or {}
            await open_dashboard_fast()
            return
        if not payload or not payload.get("rows"):
            set_web_status("Nessun dato lavoro rilevato nella pagina corrente.")
            state.scraped_stats = payload or {}
            await refresh_timelog_data()
            if not is_background:
                await go_to(ROUTE_DASHBOARD)
            return
        payload = dict(payload)
        payload.setdefault("captured_at", datetime.now(timezone.utc).isoformat())
        try:
            await ensure_timelog_repository()
            await state.timelog_repository.save_snapshot(
                payload,
                account_id=state.account_id,
            )
            state.scraped_stats = payload
        except Exception as exc:
            state.scraped_stats = payload
            set_web_status(f"Statistiche lette, salvataggio locale non riuscito: {exc}")
        await refresh_timelog_data()
        if is_background:
            if page.route == ROUTE_DASHBOARD:
                build_views()
        else:
            if show_dashboard_over_live_webview():
                return
            await go_to(ROUTE_DASHBOARD)

    async def request_work_stats() -> None:
        if (
            page.route == ROUTE_WEBVIEW
            and not page.web
            and state.supports_embedded_webview(page)
            and state.webview_ref.current is not None
        ):
            try:
                set_web_status("Raccolta statistiche lavoro avviata dal menu.")
                result = await state.webview_ref.current.run_javascript(
                    "(function(){"
                    "if(!window.GeoinroadApp||!window.GeoinroadApp.collectStats){return 'missing';}"
                    "window.GeoinroadApp.collectStats({background:false});"
                    "return 'started';"
                    "})()"
                )
                if "missing" in str(result):
                    set_web_status("Bridge statistiche non pronto, apro i dati locali.")
            except RuntimeError as exc:
                set_web_status(f"WebView non disponibile, apro le statistiche locali: {exc}")
        await open_dashboard_fast()

    async def save_credentials_in_background(username: str, password: str) -> None:
        try:
            await credential_store.save_credentials(
                page=page,
                storage=state.storage,
                preferences=preferences,
                username=username,
                password=password,
            )
            state.credentials_available = True
        except Exception as exc:
            set_web_status(f"Accesso avviato, salvataggio locale non riuscito: {exc}")

    async def report_bug() -> None:
        report = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "route": page.route,
            "last_loaded_url": state.last_loaded_url,
            "last_console_message": state.last_console_message,
            "web_status": state.web_status,
            "last_stats_debug": state.last_stats_debug,
            "account_id": state.account_id,
            "database_path": state.database_path,
        }
        text = json.dumps(report, ensure_ascii=False, indent=2)
        whatsapp_url = build_whatsapp_report_url(BUG_REPORT_WHATSAPP_NUMBER, text)
        try:
            await page.clipboard.set(text)
            message = "Report copiato negli appunti. Incollalo nel ticket o in chat."
        except Exception:
            message = text
        if whatsapp_url:
            try:
                await url_launcher.launch_url(whatsapp_url)
                return
            except Exception:
                message = "Non riesco ad aprire WhatsApp. Report copiato negli appunti."
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Segnala bug"),
                content=ft.Text(message, selectable=True),
                actions=[
                    ft.TextButton("Chiudi", on_click=lambda _: page.pop_dialog()),
                ],
            )
        )

    async def save_credentials() -> None:
        username = (
            state.username_field_ref.current.value.strip()
            if state.username_field_ref.current is not None
            and state.username_field_ref.current.value
            else ""
        )
        password = (
            state.password_field_ref.current.value
            if state.password_field_ref.current is not None
            and state.password_field_ref.current.value
            else ""
        )

        if not username or not password:
            set_lock_status(
                "Username e password sono obbligatori prima del salvataggio.",
                ft.Colors.RED_700,
            )
            return

        state.credentials_available = True
        state.cached_username = username
        state.cached_password = password
        state.account_id = state.timelog_repository.account_id_for_username(username)
        state.session_unlocked = True
        if state.password_field_ref.current is not None:
            state.password_field_ref.current.value = ""
        set_lock_status(
            "Accesso in corso. Salvataggio protetto in background...",
            ft.Colors.GREEN_700,
        )
        page.run_task(save_credentials_in_background, username, password)
        await go_to(ROUTE_WEBVIEW)

    async def clear_credentials() -> None:
        account_to_clear = state.account_id
        try:
            await credential_store.clear_credentials(
                page=page,
                storage=state.storage,
                preferences=preferences,
            )
            await ensure_timelog_repository()
            await state.timelog_repository.clear_account_data(
                account_id=account_to_clear,
            )
        except RuntimeError as exc:
            set_lock_status(str(exc), ft.Colors.RED_700)
            return
        except Exception as exc:
            set_lock_status(
                f"Pulizia non riuscita: {exc}",
                ft.Colors.RED_700,
            )
            return

        state.credentials_available = False
        state.cached_username = ""
        state.cached_password = ""
        state.account_id = "default"
        state.session_unlocked = False
        state.background_stats_started = False
        if state.username_field_ref.current is not None:
            state.username_field_ref.current.value = ""
        if state.password_field_ref.current is not None:
            state.password_field_ref.current.value = ""
        set_lock_status(
            "Vault ripulito. Inserisci di nuovo le credenziali per continuare.",
            ft.Colors.BLUE_GREY_700,
        )
        build_views()

    async def unlock_app() -> None:
        if not state.credentials_available:
            set_lock_status(
                "Prima salva le credenziali nel vault protetto.",
                ft.Colors.RED_700,
            )
            return

        set_lock_status(
            "Richiesta di sblocco in corso...",
            ft.Colors.BLUE_700,
        )

        try:
            username, password = await credential_store.load_credentials(
                page=page,
                storage=state.storage,
                preferences=preferences,
            )
        except RuntimeError as exc:
            set_lock_status(str(exc), ft.Colors.RED_700)
            return
        except Exception as exc:
            set_lock_status(
                f"Sblocco non riuscito: {exc}",
                ft.Colors.RED_700,
            )
            return

        state.session_unlocked = True
        state.cached_username = username
        state.cached_password = password
        state.account_id = state.timelog_repository.account_id_for_username(username)
        set_lock_status(
            "App sbloccata. Accesso al diario abilitato.",
            ft.Colors.GREEN_700,
        )
        await go_to(ROUTE_WEBVIEW)

    async def logout() -> None:
        account_to_clear = state.account_id
        try:
            await credential_store.clear_credentials(
                page=page,
                storage=state.storage,
                preferences=preferences,
            )
            await ensure_timelog_repository()
            await state.timelog_repository.clear_account_data(
                account_id=account_to_clear,
            )
        except Exception as exc:
            set_web_status(f"Logout parziale: pulizia locale non riuscita: {exc}")
        state.credentials_available = False
        state.cached_username = ""
        state.cached_password = ""
        state.account_id = "default"
        state.session_unlocked = False
        state.background_stats_started = False
        await go_to(ROUTE_LOCK)

    async def open_vault() -> None:
        await go_to(ROUTE_LOCK)

    async def inject_ptr() -> None:
        if page.web or not state.supports_embedded_webview(page):
            return
        if state.webview_ref.current is None:
            return
        script = """
(function(){
  if(window._geoPtr)return;
  window._geoPtr=true;
  var sy=0;
  document.addEventListener('touchstart',function(e){sy=e.touches[0].pageY;},{passive:true});
  document.addEventListener('touchend',function(e){
    var atTop=window.scrollY===0||document.documentElement.scrollTop===0;
    if(atTop&&(e.changedTouches[0].pageY-sy)>80){console.log('GEOINROAD_APP::RELOAD::');}
  },{passive:true});
})();
"""
        await state.webview_ref.current.run_javascript(script)

    async def open_external_login() -> None:
        await url_launcher.launch_url(credential_store.login_url)

    async def reload_login_page() -> None:
        if state.webview_ref.current is None:
            return
        if page.web:
            state.webview_ref.current.url = credential_store.login_url
            page.update()
            return
        await state.webview_ref.current.load_request(credential_store.login_url)

    async def refresh_webview() -> None:
        if state.webview_ref.current is None:
            return
        if page.web:
            page.update()
            return
        await state.webview_ref.current.reload()

    def on_page_started(e: ft.ControlEvent) -> None:
        state.last_loaded_url = e.data or credential_store.login_url
        set_web_status(f"Caricamento in corso: {state.last_loaded_url}")
        set_web_progress(5)

    def on_page_ended(e: ft.ControlEvent) -> None:
        state.last_loaded_url = e.data or credential_store.login_url
        set_web_progress(100)
        page.run_task(configure_webview)
        page.run_task(inject_ptr)
        if state.session_unlocked:
            page.run_task(inject_automation)

    def on_web_error(e: ft.ControlEvent) -> None:
        set_web_status(f"Errore WebView: {e.data}")
        set_web_progress(0)

    def on_progress(e: ft.ControlEvent) -> None:
        try:
            set_web_progress(int(e.data))
        except (TypeError, ValueError):
            set_web_progress(0)

    def on_url_change(e: ft.ControlEvent) -> None:
        state.last_loaded_url = e.data or credential_store.login_url
        set_web_status(f"Pagina corrente: {state.last_loaded_url}")
        if state.session_unlocked and "/login" not in (state.last_loaded_url or ""):
            page.run_task(start_background_stats_sync)

    def on_console_message(e) -> None:
        state.last_console_message = getattr(e, "message", "")
        if not state.last_console_message:
            return

        if state.last_console_message.startswith(STATUS_PREFIX):
            payload_raw = state.last_console_message[len(STATUS_PREFIX) :]
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                set_web_status(f"Messaggio JS: {payload_raw}")
                return

            action = payload.get("action", "n/a")
            stage = payload.get("stage", "js")
            set_web_status(f"JS {stage}: {action}")
            return

        if state.last_console_message.startswith(STATS_PREFIX):
            payload_raw = state.last_console_message[len(STATS_PREFIX) :]
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                set_web_status("Dati statistici ricevuti ma non validi.")
                return

            row_count = len(payload.get("rows", []))
            set_web_status(f"Statistiche acquisite dalla pagina: {row_count} righe candidate.")
            page.run_task(persist_scraped_stats, payload)
            return

        if state.last_console_message.startswith(ACTION_PREFIX):
            payload_raw = state.last_console_message[len(ACTION_PREFIX) :]
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                return
            action = payload.get("action")
            if action == "reload":
                page.run_task(refresh_webview)
            elif action == "work_stats":
                set_web_status("Raccolta statistiche lavoro richiesta dal menu.")
                page.run_task(request_work_stats)
            elif action == "bug_report":
                page.run_task(report_bug)
            elif action == "logout":
                page.run_task(logout)
            return

        if state.last_console_message.startswith(RELOAD_PREFIX):
            page.run_task(refresh_webview)
            return

        if state.last_console_message.startswith(ERROR_PREFIX):
            payload_raw = state.last_console_message[len(ERROR_PREFIX) :]
            set_web_status(f"Errore JS: {payload_raw}")
            return

        set_web_status(f"Console JS: {state.last_console_message}")

    def _build_webview() -> ft.View:
        return build_web_view(
            page=page,
            state=state,
            login_url=credential_store.login_url,
            on_open_dashboard=open_dashboard,
            on_open_external_login=open_external_login,
            on_reload_login_page=reload_login_page,
            on_refresh_webview=refresh_webview,
            on_request_work_stats=request_work_stats,
            on_report_bug=report_bug,
            on_logout=logout,
            on_open_vault=open_vault,
            on_page_started=on_page_started,
            on_page_ended=on_page_ended,
            on_progress=on_progress,
            on_url_change=on_url_change,
            on_web_resource_error=on_web_error,
            on_console_message=on_console_message,
        )

    def build_views() -> None:
        if not page.route:
            page.route = ROUTE_LOCK

        requested_route = page.route
        if not state.session_unlocked and requested_route != ROUTE_LOCK:
            requested_route = ROUTE_LOCK
            page.route = ROUTE_LOCK

        page.drawer = None
        page.overlay.clear()
        page.views.clear()
        page.views.append(
            build_lock_screen(
                page=page,
                state=state,
                on_save_credentials=save_credentials,
                on_unlock=unlock_app,
                on_clear_credentials=clear_credentials,
            )
        )

        if requested_route == ROUTE_WEBVIEW:
            page.views.append(_build_webview())
            page.run_task(configure_webview)
        elif requested_route == ROUTE_DASHBOARD:
            page.views.append(
                build_dashboard_view(
                    page=page,
                    state=state,
                    on_back_to_diary=back_to_diary,
                    on_period_change=set_dashboard_period,
                )
            )
            page.drawer = None

        page.update()

    def show_splash() -> None:
        page.route = ROUTE_SPLASH
        page.drawer = None
        page.overlay.clear()
        page.views.clear()
        page.views.append(build_splash_view(page))
        page.update()

    def route_change(_: ft.RouteChangeEvent) -> None:
        build_views()

    def platform_brightness_change(_: ft.ControlEvent) -> None:
        build_views()

    async def view_pop(e: ft.ViewPopEvent) -> None:
        popped_route = e.view.route if e.view is not None else ""
        if state.session_unlocked and popped_route == ROUTE_DASHBOARD:
            if reveal_live_webview():
                return
            await go_to(ROUTE_WEBVIEW)
            return
        if state.session_unlocked and popped_route == ROUTE_WEBVIEW:
            await go_to(ROUTE_WEBVIEW)
            return
        if e.view is not None and e.view in page.views:
            page.views.remove(e.view)
        top_view = page.views[-1] if page.views else None
        await go_to(top_view.route if top_view is not None else ROUTE_LOCK)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.on_platform_brightness_change = platform_brightness_change

    show_splash()
    page.run_task(initialize_app)


ft.run(main)

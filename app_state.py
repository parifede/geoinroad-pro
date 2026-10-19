from dataclasses import dataclass, field

import flet as ft
import flet_secure_storage as fss
import flet_webview as fwv

from app_config import (
    ANDROID_PREFERENCES_PREFIX,
    ANDROID_SHARED_PREFERENCES_NAME,
    LOGIN_URL,
)
from services.timelog_repository import TimelogRepository


@dataclass
class AppState:
    storage: fss.SecureStorage = field(
        default_factory=lambda: fss.SecureStorage(
            android_options=fss.AndroidOptions(
                reset_on_error=True,
                migrate_on_algorithm_change=True,
                enforce_biometrics=False,
                key_cipher_algorithm=fss.KeyCipherAlgorithm.AES_GCM_NO_PADDING,
                storage_cipher_algorithm=fss.StorageCipherAlgorithm.AES_GCM_NO_PADDING,
                shared_preferences_name=ANDROID_SHARED_PREFERENCES_NAME,
                preferences_key_prefix=ANDROID_PREFERENCES_PREFIX,
                biometric_prompt_title="Sblocca Geoinroad Pro",
                biometric_prompt_subtitle="Usa biometria o credenziali dispositivo",
            ),
            ios_options=fss.IOSOptions(
                access_control_flags=[
                    fss.AccessControlFlag.BIOMETRY_ANY,
                    fss.AccessControlFlag.OR,
                    fss.AccessControlFlag.DEVICE_PASSCODE,
                ],
                accessibility=fss.KeychainAccessibility.FIRST_UNLOCK,
            ),
            macos_options=fss.MacOsOptions(
                access_control_flags=[
                    fss.AccessControlFlag.BIOMETRY_ANY,
                    fss.AccessControlFlag.OR,
                    fss.AccessControlFlag.DEVICE_PASSCODE,
                ],
                accessibility=fss.KeychainAccessibility.FIRST_UNLOCK,
            ),
        )
    )
    webview_ref: ft.Ref[fwv.WebView] = field(
        default_factory=lambda: ft.Ref[fwv.WebView]()
    )
    username_field_ref: ft.Ref[ft.TextField] = field(
        default_factory=lambda: ft.Ref[ft.TextField]()
    )
    password_field_ref: ft.Ref[ft.TextField] = field(
        default_factory=lambda: ft.Ref[ft.TextField]()
    )
    lock_status_ref: ft.Ref[ft.Text] = field(
        default_factory=lambda: ft.Ref[ft.Text]()
    )
    web_status_ref: ft.Ref[ft.Text] = field(
        default_factory=lambda: ft.Ref[ft.Text]()
    )
    web_progress_ref: ft.Ref[ft.ProgressBar] = field(
        default_factory=lambda: ft.Ref[ft.ProgressBar]()
    )
    report_status_ref: ft.Ref[ft.Text] = field(
        default_factory=lambda: ft.Ref[ft.Text]()
    )
    storage_paths: ft.StoragePaths = field(default_factory=lambda: ft.StoragePaths())
    timelog_repository: TimelogRepository = field(default_factory=TimelogRepository)
    session_unlocked: bool = False
    credentials_available: bool = False
    cached_username: str = ""
    cached_password: str = ""
    account_id: str = "default"
    lock_message: str = "Proteggi il diario con credenziali salvate e sblocco biometrico."
    web_status: str = "In attesa della WebView."
    web_progress: int = 0
    webview_ready: bool = False
    autologin_injected: bool = False
    login_failure_notified: bool = False
    background_stats_started: bool = False
    last_loaded_url: str = LOGIN_URL
    last_console_message: str = ""
    scraped_stats: dict = field(default_factory=dict)
    last_stats_debug: dict = field(default_factory=dict)
    last_report: dict = field(default_factory=dict)
    last_report_id: str = ""
    saved_reports: list[dict] = field(default_factory=list)
    timelog_summary: dict = field(default_factory=dict)
    timelog_period_summary: dict = field(default_factory=dict)
    timelog_recent_entries: list[dict] = field(default_factory=list)
    timelog_daily_totals: list[dict] = field(default_factory=list)
    dashboard_period: str = "week"
    dashboard_anchor: str = ""
    database_path: str = ""
    javascript_mode_class = fwv.JavaScriptMode

    @staticmethod
    def supports_embedded_webview(page: ft.Page) -> bool:
        return page.web or page.platform in (
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
            ft.PagePlatform.MACOS,
        )

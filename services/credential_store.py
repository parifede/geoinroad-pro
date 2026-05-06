import asyncio

import flet as ft
import flet_secure_storage as fss

from app_config import CREDENTIALS_READY_KEY, LOGIN_URL, PASSWORD_KEY, USERNAME_KEY

_STORAGE_TIMEOUT_SECONDS = 2


class CredentialStore:
    def __init__(self) -> None:
        self.login_url = LOGIN_URL

    @staticmethod
    def _ensure_supported(page: ft.Page) -> None:
        if page.web:
            raise RuntimeError(
                "Il vault protetto non e' configurato per il web. Usa un target mobile o desktop."
            )

    async def has_saved_credentials(self, preferences: ft.SharedPreferences) -> bool:
        saved = await preferences.get(CREDENTIALS_READY_KEY)
        return bool(saved)

    async def save_credentials(
        self,
        *,
        page: ft.Page,
        storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
        username: str,
        password: str,
    ) -> None:
        self._ensure_supported(page)
        await preferences.set(USERNAME_KEY, username)
        await preferences.set(PASSWORD_KEY, password)
        await preferences.set(CREDENTIALS_READY_KEY, True)
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    storage.set(USERNAME_KEY, username),
                    storage.set(PASSWORD_KEY, password),
                ),
                timeout=_STORAGE_TIMEOUT_SECONDS,
            )
        except Exception:
            pass

    async def load_credentials(
        self,
        *,
        page: ft.Page,
        storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str]:
        self._ensure_supported(page)
        username = await preferences.get(USERNAME_KEY)
        password = await preferences.get(PASSWORD_KEY)
        if username and password:
            return username, password
        try:
            username, password = await asyncio.wait_for(
                asyncio.gather(
                    storage.get(USERNAME_KEY),
                    storage.get(PASSWORD_KEY),
                ),
                timeout=_STORAGE_TIMEOUT_SECONDS,
            )
        except Exception:
            username = None
            password = None
        if not username or not password:
            username = await preferences.get(USERNAME_KEY)
            password = await preferences.get(PASSWORD_KEY)
        if not username or not password:
            raise RuntimeError(
                "Le credenziali protette non sono disponibili. Salvale di nuovo."
            )
        return username, password

    async def clear_credentials(
        self,
        *,
        page: ft.Page,
        storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> None:
        self._ensure_supported(page)
        await preferences.remove(USERNAME_KEY)
        await preferences.remove(PASSWORD_KEY)
        await preferences.remove(CREDENTIALS_READY_KEY)
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    storage.remove(USERNAME_KEY),
                    storage.remove(PASSWORD_KEY),
                ),
                timeout=_STORAGE_TIMEOUT_SECONDS,
            )
        except Exception:
            pass

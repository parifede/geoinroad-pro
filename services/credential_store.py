import asyncio

import flet as ft
import flet_secure_storage as fss

from app_config import CREDENTIALS_READY_KEY, LOGIN_URL, PASSWORD_KEY, USERNAME_KEY

# Il Keystore Android puo' essere lento alla prima apertura o mostrare un
# prompt biometrico: un timeout stretto faceva fallire il salvataggio e
# l'utente perdeva le credenziali a ogni riavvio.
_STORAGE_TIMEOUT_SECONDS = 8
_STORAGE_ATTEMPTS = 2


class CredentialStore:
    """Credenziali con password nel vault cifrato quando disponibile.

    La password vive nel SecureStorage (Keystore/Keychain). Nelle
    SharedPreferences restano username e flag di presenza. Se il vault
    non risponde dopo i tentativi, la password resta nelle preferences
    come fallback: perdere l'accesso a ogni riavvio e' peggio. Appena il
    vault torna disponibile, load_credentials migra e ripulisce.
    """

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

    @staticmethod
    async def _store_in_vault(
        storage: fss.SecureStorage,
        username: str,
        password: str,
    ) -> bool:
        for _ in range(_STORAGE_ATTEMPTS):
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        storage.set(USERNAME_KEY, username),
                        storage.set(PASSWORD_KEY, password),
                    ),
                    timeout=_STORAGE_TIMEOUT_SECONDS,
                )
                return True
            except Exception:
                continue
        return False

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
        secure_ok = await self._store_in_vault(storage, username, password)
        await preferences.set(USERNAME_KEY, username)
        if secure_ok:
            await preferences.remove(PASSWORD_KEY)
        else:
            await preferences.set(PASSWORD_KEY, password)
        await preferences.set(CREDENTIALS_READY_KEY, True)

    async def load_credentials(
        self,
        *,
        page: ft.Page,
        storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str]:
        self._ensure_supported(page)
        username = await preferences.get(USERNAME_KEY)
        password = None
        try:
            stored_username, password = await asyncio.wait_for(
                asyncio.gather(
                    storage.get(USERNAME_KEY),
                    storage.get(PASSWORD_KEY),
                ),
                timeout=_STORAGE_TIMEOUT_SECONDS,
            )
            username = username or stored_username
        except Exception:
            password = None

        legacy_password = await preferences.get(PASSWORD_KEY)
        if not password and legacy_password:
            password = legacy_password
            # Il fallback resta nelle preferences finche' il vault non
            # risponde: rimuoverlo prima bloccherebbe l'accesso al riavvio.
            if await self._store_in_vault(storage, username or "", password):
                await preferences.remove(PASSWORD_KEY)
        elif password and legacy_password:
            await preferences.remove(PASSWORD_KEY)

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

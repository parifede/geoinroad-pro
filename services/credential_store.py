import asyncio

import flet as ft
import flet_secure_storage as fss

from app_config import CREDENTIALS_READY_KEY, LOGIN_URL, PASSWORD_KEY, USERNAME_KEY

_STORAGE_TIMEOUT_SECONDS = 2


class CredentialStore:
    """Credenziali con password solo nel vault cifrato.

    La password vive esclusivamente nel SecureStorage (Keystore/Keychain).
    Nelle SharedPreferences restano solo username e flag di presenza.
    Le installazioni precedenti salvavano la password in chiaro nelle
    preferences: load_credentials la migra nel vault e la rimuove.
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
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    storage.set(USERNAME_KEY, username),
                    storage.set(PASSWORD_KEY, password),
                ),
                timeout=_STORAGE_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise RuntimeError(
                "Salvataggio nel vault protetto non riuscito. Riprova."
            ) from exc
        await preferences.set(USERNAME_KEY, username)
        await preferences.remove(PASSWORD_KEY)
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
            migrated = True
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        storage.set(USERNAME_KEY, username or ""),
                        storage.set(PASSWORD_KEY, password),
                    ),
                    timeout=_STORAGE_TIMEOUT_SECONDS,
                )
            except Exception:
                # Il vault non e' disponibile: la copia legacy resta l'unica
                # fonte, rimuoverla ora bloccherebbe l'accesso al riavvio.
                migrated = False
            if migrated:
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

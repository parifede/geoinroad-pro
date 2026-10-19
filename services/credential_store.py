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
    """Credenziali con le preferences come fonte affidabile.

    Su alcuni dispositivi il SecureStorage (Keystore) e' instabile: la
    scrittura sembra riuscire ma la lettura al riavvio fallisce o mostra
    prompt biometrici, e l'utente perde l'accesso. Le SharedPreferences
    (private dell'app, backup disabilitato) sono quindi la fonte di
    verita'; il vault cifrato resta una copia aggiuntiva best-effort,
    usata per recuperare le credenziali se le preferences si svuotano.
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

    @staticmethod
    async def _read_from_vault(
        storage: fss.SecureStorage,
    ) -> tuple[str | None, str | None]:
        for _ in range(_STORAGE_ATTEMPTS):
            try:
                return await asyncio.wait_for(
                    asyncio.gather(
                        storage.get(USERNAME_KEY),
                        storage.get(PASSWORD_KEY),
                    ),
                    timeout=_STORAGE_TIMEOUT_SECONDS,
                )
            except Exception:
                continue
        return None, None

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
        # Prima la fonte affidabile: qualunque cosa succeda dopo,
        # al riavvio le credenziali ci sono.
        await preferences.set(USERNAME_KEY, username)
        await preferences.set(PASSWORD_KEY, password)
        await preferences.set(CREDENTIALS_READY_KEY, True)
        await self._store_in_vault(storage, username, password)

    async def load_credentials(
        self,
        *,
        page: ft.Page,
        storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str]:
        self._ensure_supported(page)
        # Percorso veloce e affidabile: niente vault, niente prompt.
        username = await preferences.get(USERNAME_KEY)
        password = await preferences.get(PASSWORD_KEY)
        if username and password:
            return username, password

        # Recupero dalla copia nel vault (es. build precedenti che
        # salvavano solo li'); se riesce, ripristina le preferences
        # cosi' i prossimi avvii sono immediati.
        vault_username, vault_password = await self._read_from_vault(storage)
        username = username or vault_username
        password = password or vault_password
        if username and password:
            await preferences.set(USERNAME_KEY, username)
            await preferences.set(PASSWORD_KEY, password)
            await preferences.set(CREDENTIALS_READY_KEY, True)
            return username, password

        raise RuntimeError(
            "Le credenziali salvate non sono disponibili. Inseriscile di nuovo."
        )

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

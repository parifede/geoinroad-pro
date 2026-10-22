import asyncio

import flet as ft
import flet_secure_storage as fss

from app_config import (
    CREDENTIALS_READY_KEY,
    GATE_ENABLED_KEY,
    GATE_TOKEN_KEY,
    LOGIN_URL,
    PASSWORD_KEY,
    USERNAME_KEY,
)

# Il cancello biometrico aspetta l'interazione dell'utente col prompt.
_GATE_TIMEOUT_SECONDS = 90
_GATE_TOKEN_VALUE = "ok"


class CredentialStore:
    """Credenziali nelle preferences, cancello biometrico nel Keystore.

    Le SharedPreferences (private dell'app, backup disabilitato) sono la
    fonte di verita' delle credenziali. Il SecureStorage serve solo al
    cancello d'ingresso: il plugin nativo ha un'unica istanza per processo
    e la prima configurazione usata vince, quindi un secondo vault "senza
    biometria" aperto prima rendeva il cancello silenzioso (nessun prompt).
    Per questo l'app apre un solo SecureStorage, quello del cancello.
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
        preferences: ft.SharedPreferences,
        username: str,
        password: str,
    ) -> None:
        self._ensure_supported(page)
        await preferences.set(USERNAME_KEY, username)
        await preferences.set(PASSWORD_KEY, password)
        await preferences.set(CREDENTIALS_READY_KEY, True)

    async def load_credentials(
        self,
        *,
        page: ft.Page,
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str]:
        self._ensure_supported(page)
        username = await preferences.get(USERNAME_KEY)
        password = await preferences.get(PASSWORD_KEY)
        if username and password:
            return username, password
        raise RuntimeError(
            "Le credenziali salvate non sono disponibili. Inseriscile di nuovo."
        )

    async def gate_choice(self, preferences: ft.SharedPreferences) -> bool | None:
        """True/False se l'utente ha gia' scelto, None se non gli e' stato chiesto."""
        value = await preferences.get(GATE_ENABLED_KEY)
        if value is None:
            return None
        return bool(value)

    async def enroll_gate(
        self,
        *,
        page: ft.Page,
        gate_storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> tuple[bool, str]:
        """Attiva il cancello biometrico scrivendo il token protetto.

        La scrittura mostra il prompt biometrico/PIN di sistema. Il token
        viene riletto: solo se torna identico il cancello si considera
        attivo (un errore "assorbito" dal plugin non deve chiudere fuori
        l'utente al prossimo avvio).
        """
        if page.web:
            return False, "Lo sblocco biometrico e' disponibile solo sull'app Android."
        try:
            await asyncio.wait_for(
                gate_storage.set(GATE_TOKEN_KEY, _GATE_TOKEN_VALUE),
                timeout=_GATE_TIMEOUT_SECONDS,
            )
            value = await asyncio.wait_for(
                gate_storage.get(GATE_TOKEN_KEY),
                timeout=_GATE_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            return False, self._gate_error_message(exc)
        if value != _GATE_TOKEN_VALUE:
            return False, "Verifica non completata. Riprova dal menu."
        await preferences.set(GATE_ENABLED_KEY, True)
        return True, "Sblocco biometrico attivo: te lo chiedero' a ogni apertura."

    async def decline_gate(self, preferences: ft.SharedPreferences) -> None:
        await preferences.set(GATE_ENABLED_KEY, False)

    async def verify_gate(
        self,
        *,
        page: ft.Page,
        gate_storage: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> bool:
        """True se l'ingresso e' autorizzato.

        Con il cancello attivo, leggere il token richiede biometria o
        PIN di sistema: annullare o fallire la verifica nega l'accesso
        automatico (le credenziali restano al sicuro dove sono).
        """
        if page.web:
            return True
        if not await preferences.get(GATE_ENABLED_KEY):
            return True
        try:
            value = await asyncio.wait_for(
                gate_storage.get(GATE_TOKEN_KEY),
                timeout=_GATE_TIMEOUT_SECONDS,
            )
        except Exception:
            return False
        return value == _GATE_TOKEN_VALUE

    @staticmethod
    def _gate_error_message(exc: Exception) -> str:
        text = str(exc)
        if "BIOMETRIC_UNAVAILABLE" in text or "no PIN" in text or "enrolled" in text:
            return (
                "Nessuna impronta o blocco schermo sul telefono: impostali "
                "nelle impostazioni di Android e riprova dal menu."
            )
        return "Sblocco biometrico non attivato (verifica annullata)."

    async def clear_credentials(
        self,
        *,
        page: ft.Page,
        preferences: ft.SharedPreferences,
    ) -> None:
        self._ensure_supported(page)
        await preferences.remove(USERNAME_KEY)
        await preferences.remove(PASSWORD_KEY)
        await preferences.remove(CREDENTIALS_READY_KEY)
        # Al prossimo accesso la scelta sulla biometria viene riproposta.
        await preferences.remove(GATE_ENABLED_KEY)

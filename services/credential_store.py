import asyncio

import flet as ft
import flet_secure_storage as fss

from app_config import (
    CREDENTIALS_READY_KEY,
    LEGACY_GATE_ENABLED_KEY,
    LEGACY_GATE_TOKEN_KEY,
    LOGIN_URL,
    PASSWORD_KEY,
    USERNAME_KEY,
)

# La prima operazione sul vault in ogni processo aspetta l'utente davanti
# alla finestra di sistema (impronta o PIN).
_VAULT_TIMEOUT_SECONDS = 90


class VaultLockedError(RuntimeError):
    """Verifica con impronta/PIN annullata o non riuscita."""


class CredentialsMissingError(RuntimeError):
    """Il vault si apre ma non contiene le credenziali."""


class CredentialStore:
    """Credenziali nel vault protetto, mai in chiaro.

    L'app usa un solo SecureStorage (il plugin nativo ne serve uno per
    nome, e due configurazioni diverse avevano rotto il prompt). La chiave
    del vault richiede impronta o PIN sui telefoni con blocco schermo: la
    prima lettura di ogni avvio mostra la finestra di sistema, le letture
    successive dello stesso processo no. Sui telefoni senza blocco schermo
    il vault resta cifrato con una chiave del Keystore, senza finestra.

    Nelle preferences resta solo il flag "credenziali salvate", che non e'
    un segreto. Le installazioni fino alla 1.3 tenevano utente e password
    in chiaro nelle preferences: al primo sblocco vengono spostati nel
    vault e la copia in chiaro viene cancellata solo dopo averli riletti.
    """

    def __init__(self) -> None:
        self.login_url = LOGIN_URL
        # Diventa True alla prima operazione riuscita sul vault: da li' in
        # poi, nello stesso processo, il vault non chiede piu' impronta/PIN.
        self._vault_open = False

    @staticmethod
    def _ensure_supported(page: ft.Page) -> None:
        if page.web:
            raise RuntimeError(
                "Il vault protetto non e' configurato per il web. Usa un target mobile o desktop."
            )

    async def _vault_call(self, awaitable):
        try:
            result = await asyncio.wait_for(awaitable, timeout=_VAULT_TIMEOUT_SECONDS)
        except Exception as exc:
            raise VaultLockedError(
                "Verifica con impronta o PIN non riuscita."
            ) from exc
        self._vault_open = True
        return result

    async def has_saved_credentials(self, preferences: ft.SharedPreferences) -> bool:
        saved = await preferences.get(CREDENTIALS_READY_KEY)
        return bool(saved)

    async def save_credentials(
        self,
        *,
        page: ft.Page,
        vault: fss.SecureStorage,
        preferences: ft.SharedPreferences,
        username: str,
        password: str,
    ) -> None:
        """Scrive nel vault e conferma rileggendo.

        Solo se la rilettura coincide il flag viene acceso e l'eventuale
        copia in chiaro cancellata: un errore "assorbito" dal plugin non
        deve far perdere le credenziali.
        """
        self._ensure_supported(page)
        await self._vault_call(vault.set(USERNAME_KEY, username))
        await self._vault_call(vault.set(PASSWORD_KEY, password))
        stored_username = await self._vault_call(vault.get(USERNAME_KEY))
        stored_password = await self._vault_call(vault.get(PASSWORD_KEY))
        if stored_username != username or stored_password != password:
            raise RuntimeError("Salvataggio protetto non riuscito. Riprova.")
        await preferences.set(CREDENTIALS_READY_KEY, True)
        await self._drop_plaintext(preferences)

    async def load_credentials(
        self,
        *,
        page: ft.Page,
        vault: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str]:
        """Apre il vault (una finestra impronta/PIN) e legge le credenziali.

        Solleva VaultLockedError se la verifica viene annullata o fallisce:
        in quel caso nulla viene toccato e si puo' riprovare.
        """
        self._ensure_supported(page)
        legacy = await self._legacy_plaintext(preferences)
        if legacy is not None:
            username, password = legacy
            await self.save_credentials(
                page=page,
                vault=vault,
                preferences=preferences,
                username=username,
                password=password,
            )
            await self._drop_legacy_gate_token(vault)
            return username, password

        username = await self._vault_call(vault.get(USERNAME_KEY))
        password = await self._vault_call(vault.get(PASSWORD_KEY))
        if username and password:
            return username, password
        raise CredentialsMissingError(
            "Le credenziali salvate non sono disponibili. Inseriscile di nuovo."
        )

    async def clear_credentials(
        self,
        *,
        page: ft.Page,
        vault: fss.SecureStorage,
        preferences: ft.SharedPreferences,
    ) -> None:
        """Dimentica le credenziali senza mai chiedere impronta o PIN.

        Se il vault e' gia' aperto (logout dal menu) viene svuotato. Se e'
        chiuso (verifica annullata, schermata di accesso) non lo si apre:
        basta togliere il flag, la copia cifrata resta irraggiungibile e il
        prossimo salvataggio la sovrascrive.
        """
        self._ensure_supported(page)
        await preferences.remove(CREDENTIALS_READY_KEY)
        await self._drop_plaintext(preferences)
        if not self._vault_open:
            return
        for key in (USERNAME_KEY, PASSWORD_KEY, LEGACY_GATE_TOKEN_KEY):
            try:
                await self._vault_call(vault.remove(key))
            except VaultLockedError:
                break

    @staticmethod
    async def _legacy_plaintext(
        preferences: ft.SharedPreferences,
    ) -> tuple[str, str] | None:
        username = await preferences.get(USERNAME_KEY)
        password = await preferences.get(PASSWORD_KEY)
        if username and password:
            return str(username), str(password)
        return None

    @staticmethod
    async def _drop_plaintext(preferences: ft.SharedPreferences) -> None:
        await preferences.remove(USERNAME_KEY)
        await preferences.remove(PASSWORD_KEY)
        await preferences.remove(LEGACY_GATE_ENABLED_KEY)

    async def _drop_legacy_gate_token(self, vault: fss.SecureStorage) -> None:
        try:
            await self._vault_call(vault.remove(LEGACY_GATE_TOKEN_KEY))
        except VaultLockedError:
            pass

import tomllib
import unittest
from pathlib import Path

from app_config import (
    CREDENTIALS_READY_KEY,
    LEGACY_GATE_ENABLED_KEY,
    LEGACY_GATE_TOKEN_KEY,
    PASSWORD_KEY,
    USERNAME_KEY,
)
from services.credential_store import (
    CredentialStore,
    CredentialsMissingError,
    VaultLockedError,
)


class _Page:
    web = False


class _Preferences:
    def __init__(self) -> None:
        self.values = {}
        self.written_keys = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        self.written_keys.append(key)
        self.values[key] = value

    async def remove(self, key):
        self.values.pop(key, None)


class _Vault:
    """Vault finto: in memoria, come il SecureStorage gia' sbloccato."""

    def __init__(self) -> None:
        self.values = {}

    async def set(self, key, value):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def remove(self, key):
        self.values.pop(key, None)


class _LockedVault:
    """Impronta/PIN annullati: ogni operazione fallisce."""

    async def set(self, key, value):
        raise RuntimeError("Authentication cancelled")

    async def get(self, key):
        raise RuntimeError("Authentication cancelled")

    async def remove(self, key):
        raise RuntimeError("Authentication cancelled")


class _SwallowingVault(_Vault):
    """Plugin che "assorbe" l'errore: la scrittura riesce ma non salva nulla."""

    async def set(self, key, value):
        return "Data has been reset"


def _legacy_preferences() -> _Preferences:
    # Come le lascia la 1.3: credenziali in chiaro e scelta del cancello.
    preferences = _Preferences()
    preferences.values.update(
        {
            CREDENTIALS_READY_KEY: True,
            USERNAME_KEY: "driver",
            PASSWORD_KEY: "secret",
            LEGACY_GATE_ENABLED_KEY: True,
        }
    )
    return preferences


class CredentialStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_credentials_live_in_the_vault_only(self):
        store = CredentialStore()
        preferences = _Preferences()
        vault = _Vault()

        await store.save_credentials(
            page=_Page(),
            vault=vault,
            preferences=preferences,
            username="driver",
            password="secret",
        )

        self.assertEqual(vault.values[USERNAME_KEY], "driver")
        self.assertEqual(vault.values[PASSWORD_KEY], "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])
        # Nelle preferences non viene mai scritto nulla di segreto.
        self.assertEqual(preferences.written_keys, [CREDENTIALS_READY_KEY])
        self.assertTrue(await store.has_saved_credentials(preferences))
        self.assertEqual(
            await store.load_credentials(
                page=_Page(), vault=vault, preferences=preferences
            ),
            ("driver", "secret"),
        )

    async def test_legacy_plaintext_moves_to_the_vault_and_is_deleted(self):
        store = CredentialStore()
        preferences = _legacy_preferences()
        vault = _Vault()
        vault.values[LEGACY_GATE_TOKEN_KEY] = "ok"

        credentials = await store.load_credentials(
            page=_Page(), vault=vault, preferences=preferences
        )

        self.assertEqual(credentials, ("driver", "secret"))
        self.assertEqual(vault.values[USERNAME_KEY], "driver")
        self.assertEqual(vault.values[PASSWORD_KEY], "secret")
        self.assertNotIn(USERNAME_KEY, preferences.values)
        self.assertNotIn(PASSWORD_KEY, preferences.values)
        self.assertNotIn(LEGACY_GATE_ENABLED_KEY, preferences.values)
        self.assertNotIn(LEGACY_GATE_TOKEN_KEY, vault.values)
        # L'utente resta "con credenziali salvate": nessun nuovo login.
        self.assertTrue(await store.has_saved_credentials(preferences))
        self.assertEqual(
            await store.load_credentials(
                page=_Page(), vault=vault, preferences=preferences
            ),
            ("driver", "secret"),
        )

    async def test_cancelled_migration_keeps_the_old_copy(self):
        store = CredentialStore()
        preferences = _legacy_preferences()

        with self.assertRaises(VaultLockedError):
            await store.load_credentials(
                page=_Page(), vault=_LockedVault(), preferences=preferences
            )

        # Niente perso: al prossimo sblocco la migrazione riparte.
        self.assertEqual(preferences.values[USERNAME_KEY], "driver")
        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])

    async def test_migration_requires_the_vault_to_read_back(self):
        store = CredentialStore()
        preferences = _legacy_preferences()

        with self.assertRaises(RuntimeError):
            await store.load_credentials(
                page=_Page(), vault=_SwallowingVault(), preferences=preferences
            )

        self.assertEqual(preferences.values[USERNAME_KEY], "driver")
        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")

    async def test_locked_vault_raises_a_retryable_error(self):
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values[CREDENTIALS_READY_KEY] = True

        with self.assertRaises(VaultLockedError):
            await store.load_credentials(
                page=_Page(), vault=_LockedVault(), preferences=preferences
            )

    async def test_load_raises_when_the_vault_is_empty(self):
        # Es. chiave invalidata da una nuova impronta: il plugin svuota il
        # vault e bisogna reinserire la password.
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values[CREDENTIALS_READY_KEY] = True

        with self.assertRaises(CredentialsMissingError):
            await store.load_credentials(
                page=_Page(), vault=_Vault(), preferences=preferences
            )

    async def test_failed_save_writes_nothing(self):
        store = CredentialStore()
        preferences = _Preferences()

        with self.assertRaises(VaultLockedError):
            await store.save_credentials(
                page=_Page(),
                vault=_LockedVault(),
                preferences=preferences,
                username="driver",
                password="secret",
            )

        self.assertEqual(preferences.values, {})
        self.assertFalse(await store.has_saved_credentials(preferences))

    async def test_swallowed_save_is_not_reported_as_saved(self):
        store = CredentialStore()
        preferences = _Preferences()

        with self.assertRaises(RuntimeError):
            await store.save_credentials(
                page=_Page(),
                vault=_SwallowingVault(),
                preferences=preferences,
                username="driver",
                password="secret",
            )

        self.assertFalse(await store.has_saved_credentials(preferences))

    async def test_logout_empties_the_open_vault_and_preferences(self):
        store = CredentialStore()
        preferences = _Preferences()
        vault = _Vault()
        vault.values[LEGACY_GATE_TOKEN_KEY] = "ok"
        await store.save_credentials(
            page=_Page(),
            vault=vault,
            preferences=preferences,
            username="driver",
            password="secret",
        )

        await store.clear_credentials(page=_Page(), vault=vault, preferences=preferences)

        self.assertEqual(preferences.values, {})
        self.assertEqual(vault.values, {})

    async def test_remove_from_lock_screen_never_opens_the_vault(self):
        # Verifica annullata all'apertura: "Rimuovi credenziali" non deve
        # chiedere di nuovo impronta o PIN.
        store = CredentialStore()
        preferences = _legacy_preferences()
        with self.assertRaises(VaultLockedError):
            await store.load_credentials(
                page=_Page(), vault=_LockedVault(), preferences=preferences
            )

        class _UntouchableVault(_LockedVault):
            async def remove(self, key):
                raise AssertionError("il vault chiuso non va aperto")

        await store.clear_credentials(
            page=_Page(), vault=_UntouchableVault(), preferences=preferences
        )

        self.assertEqual(preferences.values, {})
        self.assertFalse(await store.has_saved_credentials(preferences))

    def test_app_opens_a_single_secure_storage(self):
        # Un secondo SecureStorage nello stesso processo aveva rotto il
        # prompt biometrico. enforce_biometrics=False: senza blocco schermo
        # il vault resta cifrato invece di diventare inutilizzabile.
        source = Path("app_state.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("fss.SecureStorage("), 1)
        self.assertIn("enforce_biometrics=False", source)

    def test_app_never_reads_credentials_from_preferences(self):
        source = Path("main.py").read_text(encoding="utf-8")
        self.assertNotIn("USERNAME_KEY", source)
        self.assertNotIn("PASSWORD_KEY", source)

    def test_native_plugin_is_pinned_to_a_working_release(self):
        with open("pyproject.toml", "rb") as handle:
            pyproject = tomllib.load(handle)
        overrides = pyproject["tool"]["flet"]["flutter"]["pubspec"]["dependency_overrides"]
        self.assertEqual(overrides["flutter_secure_storage"], "10.3.4")


if __name__ == "__main__":
    unittest.main()

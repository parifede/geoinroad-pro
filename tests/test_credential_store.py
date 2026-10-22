import tomllib
import unittest
from pathlib import Path

from app_config import (
    CREDENTIALS_READY_KEY,
    GATE_ENABLED_KEY,
    PASSWORD_KEY,
    USERNAME_KEY,
)
from services.credential_store import CredentialStore


class _Page:
    web = False


class _Preferences:
    def __init__(self) -> None:
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        self.values[key] = value

    async def remove(self, key):
        self.values.pop(key, None)


class _FailingStorage:
    async def set(self, key, value):
        raise RuntimeError("secure storage unavailable")

    async def get(self, key):
        raise RuntimeError("secure storage unavailable")

    async def remove(self, key):
        raise RuntimeError("secure storage unavailable")


class _RecordingStorage:
    def __init__(self) -> None:
        self.values = {}
        self.get_calls = 0

    async def set(self, key, value):
        self.values[key] = value

    async def get(self, key):
        self.get_calls += 1
        return self.values.get(key)

    async def remove(self, key):
        self.values.pop(key, None)


class _SwallowingStorage(_RecordingStorage):
    """Plugin che "assorbe" l'errore: la scrittura riesce ma non salva nulla."""

    async def set(self, key, value):
        return "Data has been reset"


class _NoLockScreenStorage(_FailingStorage):
    async def set(self, key, value):
        raise RuntimeError("BIOMETRIC_UNAVAILABLE: device has no PIN")


class CredentialStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_credentials_live_in_preferences(self):
        store = CredentialStore()
        preferences = _Preferences()

        await store.save_credentials(
            page=_Page(),
            preferences=preferences,
            username="driver",
            password="secret",
        )

        self.assertEqual(preferences.values[USERNAME_KEY], "driver")
        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])
        self.assertEqual(
            await store.load_credentials(page=_Page(), preferences=preferences),
            ("driver", "secret"),
        )

    async def test_load_raises_when_credentials_are_missing(self):
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values[CREDENTIALS_READY_KEY] = True

        with self.assertRaises(RuntimeError):
            await store.load_credentials(page=_Page(), preferences=preferences)

    async def test_clear_credentials_removes_values_and_gate_choice(self):
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values.update(
            {
                CREDENTIALS_READY_KEY: True,
                USERNAME_KEY: "driver",
                PASSWORD_KEY: "secret",
                GATE_ENABLED_KEY: True,
            }
        )

        await store.clear_credentials(page=_Page(), preferences=preferences)

        self.assertNotIn(CREDENTIALS_READY_KEY, preferences.values)
        self.assertNotIn(USERNAME_KEY, preferences.values)
        self.assertNotIn(PASSWORD_KEY, preferences.values)
        # Il prossimo accesso ripropone la scelta sulla biometria.
        self.assertIsNone(await store.gate_choice(preferences))

    async def test_gate_enrolls_and_blocks_when_verification_fails(self):
        store = CredentialStore()
        preferences = _Preferences()
        gate = _RecordingStorage()

        self.assertIsNone(await store.gate_choice(preferences))
        enabled, _ = await store.enroll_gate(
            page=_Page(), gate_storage=gate, preferences=preferences
        )
        self.assertTrue(enabled)
        self.assertTrue(await store.gate_choice(preferences))
        # Verifica riuscita: il token protetto e' leggibile.
        self.assertTrue(
            await store.verify_gate(
                page=_Page(), gate_storage=gate, preferences=preferences
            )
        )
        # Biometria annullata o fallita: ingresso negato.
        self.assertFalse(
            await store.verify_gate(
                page=_Page(), gate_storage=_FailingStorage(), preferences=preferences
            )
        )

    async def test_cancelled_enrollment_leaves_the_choice_open(self):
        store = CredentialStore()
        preferences = _Preferences()

        enabled, message = await store.enroll_gate(
            page=_Page(), gate_storage=_FailingStorage(), preferences=preferences
        )

        self.assertFalse(enabled)
        self.assertIn("annullata", message)
        self.assertIsNone(await store.gate_choice(preferences))
        # Cancello spento: l'app entra direttamente.
        self.assertTrue(
            await store.verify_gate(
                page=_Page(), gate_storage=_FailingStorage(), preferences=preferences
            )
        )

    async def test_enrollment_requires_the_token_to_read_back(self):
        # Un errore "assorbito" dal plugin non deve attivare il cancello,
        # altrimenti al prossimo avvio l'utente resterebbe chiuso fuori.
        store = CredentialStore()
        preferences = _Preferences()

        enabled, _ = await store.enroll_gate(
            page=_Page(), gate_storage=_SwallowingStorage(), preferences=preferences
        )

        self.assertFalse(enabled)
        self.assertIsNone(await store.gate_choice(preferences))

    async def test_enrollment_explains_a_missing_screen_lock(self):
        store = CredentialStore()
        enabled, message = await store.enroll_gate(
            page=_Page(), gate_storage=_NoLockScreenStorage(), preferences=_Preferences()
        )

        self.assertFalse(enabled)
        self.assertIn("blocco schermo", message)

    async def test_declined_gate_is_remembered(self):
        store = CredentialStore()
        preferences = _Preferences()

        await store.decline_gate(preferences)

        self.assertIs(await store.gate_choice(preferences), False)

    def test_app_opens_a_single_secure_storage(self):
        # Il plugin nativo ha un'istanza per processo: un secondo
        # SecureStorage ne prenderebbe la configurazione e il prompt
        # biometrico non comparirebbe piu'.
        source = Path("app_state.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("fss.SecureStorage("), 1)
        self.assertIn("enforce_biometrics=True", source)

    def test_native_plugin_is_pinned_to_a_working_release(self):
        with open("pyproject.toml", "rb") as handle:
            pyproject = tomllib.load(handle)
        overrides = pyproject["tool"]["flet"]["flutter"]["pubspec"]["dependency_overrides"]
        self.assertEqual(overrides["flutter_secure_storage"], "10.3.4")


if __name__ == "__main__":
    unittest.main()

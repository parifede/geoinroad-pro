import unittest

from app_config import (
    CREDENTIALS_READY_KEY,
    GATE_ENABLED_KEY,
    PASSWORD_KEY,
    USERNAME_KEY,
)
from services.credential_store import CredentialStore, _STORAGE_TIMEOUT_SECONDS


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


class CredentialStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_writes_reliable_copy_and_vault_copy(self):
        store = CredentialStore()
        preferences = _Preferences()
        storage = _RecordingStorage()

        await store.save_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
            username="driver",
            password="secret",
        )

        # Fonte affidabile: le preferences hanno sempre tutto.
        self.assertEqual(preferences.values[USERNAME_KEY], "driver")
        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])
        # Copia aggiuntiva nel vault.
        self.assertEqual(storage.values[PASSWORD_KEY], "secret")

    async def test_load_uses_fast_path_without_touching_the_vault(self):
        # Niente letture dal vault quando le preferences sono complete:
        # su alcuni dispositivi il vault e' lento o mostra prompt biometrici.
        store = CredentialStore()
        preferences = _Preferences()
        storage = _RecordingStorage()
        preferences.values.update(
            {
                CREDENTIALS_READY_KEY: True,
                USERNAME_KEY: "driver",
                PASSWORD_KEY: "secret",
            }
        )

        username, password = await store.load_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
        )

        self.assertEqual((username, password), ("driver", "secret"))
        self.assertEqual(storage.get_calls, 0)

    async def test_save_and_load_survive_a_broken_vault(self):
        store = CredentialStore()
        preferences = _Preferences()

        await store.save_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
            username="driver",
            password="secret",
        )
        username, password = await store.load_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
        )

        self.assertEqual((username, password), ("driver", "secret"))

    async def test_load_recovers_from_vault_and_restores_preferences(self):
        # Build precedenti salvavano solo nel vault: al primo avvio dopo
        # l'aggiornamento le credenziali vengono recuperate e ricopiate.
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values[CREDENTIALS_READY_KEY] = True
        storage = _RecordingStorage()
        storage.values[USERNAME_KEY] = "driver"
        storage.values[PASSWORD_KEY] = "secret"

        username, password = await store.load_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
        )

        self.assertEqual((username, password), ("driver", "secret"))
        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")
        self.assertEqual(preferences.values[USERNAME_KEY], "driver")

    async def test_load_raises_only_when_no_copy_exists(self):
        store = CredentialStore()
        preferences = _Preferences()

        with self.assertRaises(RuntimeError):
            await store.load_credentials(
                page=_Page(),
                storage=_RecordingStorage(),
                preferences=preferences,
            )

    async def test_clear_credentials_removes_fallback_values(self):
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values.update(
            {
                CREDENTIALS_READY_KEY: True,
                USERNAME_KEY: "driver",
                PASSWORD_KEY: "secret",
            }
        )

        await store.clear_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
        )

        self.assertNotIn(CREDENTIALS_READY_KEY, preferences.values)
        self.assertNotIn(USERNAME_KEY, preferences.values)
        self.assertNotIn(PASSWORD_KEY, preferences.values)

    async def test_gate_enrolls_and_blocks_when_verification_fails(self):
        store = CredentialStore()
        preferences = _Preferences()
        gate = _RecordingStorage()

        self.assertTrue(
            await store.enroll_gate(
                page=_Page(), gate_storage=gate, preferences=preferences
            )
        )
        self.assertTrue(preferences.values[GATE_ENABLED_KEY])
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

    async def test_gate_stays_disabled_when_enrollment_is_cancelled(self):
        store = CredentialStore()
        preferences = _Preferences()

        self.assertFalse(
            await store.enroll_gate(
                page=_Page(), gate_storage=_FailingStorage(), preferences=preferences
            )
        )
        self.assertFalse(preferences.values[GATE_ENABLED_KEY])
        # Cancello spento: l'app entra direttamente.
        self.assertTrue(
            await store.verify_gate(
                page=_Page(),
                gate_storage=_FailingStorage(),
                preferences=preferences,
            )
        )

    def test_secure_storage_timeout_tolerates_slow_keystore(self):
        self.assertGreaterEqual(_STORAGE_TIMEOUT_SECONDS, 5)
        self.assertLessEqual(_STORAGE_TIMEOUT_SECONDS, 15)


if __name__ == "__main__":
    unittest.main()

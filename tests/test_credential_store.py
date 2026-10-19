import unittest

from app_config import CREDENTIALS_READY_KEY, PASSWORD_KEY, USERNAME_KEY
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
    async def test_password_is_stored_only_in_secure_storage(self):
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

        self.assertEqual(storage.values[PASSWORD_KEY], "secret")
        self.assertNotIn(PASSWORD_KEY, preferences.values)
        self.assertEqual(preferences.values[USERNAME_KEY], "driver")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])

        username, password = await store.load_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
        )
        self.assertEqual((username, password), ("driver", "secret"))

    async def test_save_falls_back_to_preferences_when_vault_fails(self):
        # Perdere le credenziali a ogni riavvio e' peggio del fallback:
        # se il vault non risponde, l'accesso deve comunque sopravvivere.
        store = CredentialStore()
        preferences = _Preferences()

        await store.save_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
            username="driver",
            password="secret",
        )

        self.assertEqual(preferences.values[PASSWORD_KEY], "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])

        username, password = await store.load_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
        )
        self.assertEqual((username, password), ("driver", "secret"))

    async def test_load_migrates_legacy_plaintext_password_into_vault(self):
        store = CredentialStore()
        preferences = _Preferences()
        storage = _RecordingStorage()
        preferences.values.update(
            {
                CREDENTIALS_READY_KEY: True,
                USERNAME_KEY: "driver",
                PASSWORD_KEY: "legacy-secret",
            }
        )

        username, password = await store.load_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
        )

        self.assertEqual((username, password), ("driver", "legacy-secret"))
        self.assertEqual(storage.values[PASSWORD_KEY], "legacy-secret")
        self.assertNotIn(PASSWORD_KEY, preferences.values)

    async def test_legacy_password_is_kept_if_vault_is_unavailable(self):
        store = CredentialStore()
        preferences = _Preferences()
        preferences.values.update(
            {
                CREDENTIALS_READY_KEY: True,
                USERNAME_KEY: "driver",
                PASSWORD_KEY: "legacy-secret",
            }
        )

        username, password = await store.load_credentials(
            page=_Page(),
            storage=_FailingStorage(),
            preferences=preferences,
        )

        self.assertEqual((username, password), ("driver", "legacy-secret"))
        self.assertEqual(preferences.values[PASSWORD_KEY], "legacy-secret")

    async def test_load_scrubs_leftover_plaintext_when_vault_already_holds_password(self):
        store = CredentialStore()
        preferences = _Preferences()
        storage = _RecordingStorage()
        storage.values[PASSWORD_KEY] = "secret"
        storage.values[USERNAME_KEY] = "driver"
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
        self.assertNotIn(PASSWORD_KEY, preferences.values)

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

    def test_secure_storage_timeout_tolerates_slow_keystore(self):
        # Il Keystore puo' essere lento alla prima apertura: un timeout
        # troppo stretto faceva perdere le credenziali al riavvio.
        self.assertGreaterEqual(_STORAGE_TIMEOUT_SECONDS, 5)
        self.assertLessEqual(_STORAGE_TIMEOUT_SECONDS, 15)


if __name__ == "__main__":
    unittest.main()

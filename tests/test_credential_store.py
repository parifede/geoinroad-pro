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


class _CountingStorage:
    def __init__(self) -> None:
        self.get_calls = 0
        self.set_calls = 0

    async def set(self, key, value):
        self.set_calls += 1

    async def get(self, key):
        self.get_calls += 1
        return None

    async def remove(self, key):
        pass


class CredentialStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_and_load_fall_back_when_secure_storage_fails(self):
        store = CredentialStore()
        preferences = _Preferences()
        storage = _FailingStorage()

        await store.save_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
            username="driver",
            password="secret",
        )
        username, password = await store.load_credentials(
            page=_Page(),
            storage=storage,
            preferences=preferences,
        )

        self.assertEqual(username, "driver")
        self.assertEqual(password, "secret")
        self.assertTrue(preferences.values[CREDENTIALS_READY_KEY])

    async def test_load_credentials_uses_preferences_fast_path_before_secure_storage(self):
        store = CredentialStore()
        preferences = _Preferences()
        storage = _CountingStorage()
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

        self.assertEqual(username, "driver")
        self.assertEqual(password, "secret")
        self.assertEqual(storage.get_calls, 0)

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

    def test_secure_storage_timeout_stays_short_for_responsive_ui(self):
        self.assertLessEqual(_STORAGE_TIMEOUT_SECONDS, 2)


if __name__ == "__main__":
    unittest.main()

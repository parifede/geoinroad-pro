import tomllib
import unittest

from app_config import APP_VERSION


class VersionTest(unittest.TestCase):
    def test_app_version_matches_pyproject(self):
        # La splash e le segnalazioni mostrano APP_VERSION, la build usa
        # pyproject: devono coincidere, altrimenti l'app installata dice
        # una versione diversa dalla release (come la V1.3.1 che diceva 1.3.0).
        with open("pyproject.toml", "rb") as handle:
            pyproject = tomllib.load(handle)
        self.assertEqual(pyproject["project"]["version"], APP_VERSION)

    def test_version_is_1_4_0(self):
        self.assertEqual(APP_VERSION, "1.4.0")


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class FlutterSplashWrapperTest(unittest.TestCase):
    def test_boot_screen_uses_animated_lottie_startup_splash(self):
        source = Path("build/flutter/lib/main.dart").read_text(encoding="utf-8")

        self.assertIn("AnimatedStartupSplash(showProgress: true)", source)
        self.assertIn("SingleTickerProviderStateMixin", source)
        self.assertIn("Lottie.asset", source)
        self.assertIn("animate: true", source)
        self.assertIn("repeat: true", source)
        self.assertNotIn("'images/splash.png',\n              width: 180", source)

    def test_lottie_splash_does_not_overlay_static_logo(self):
        source = Path("build/flutter/lib/main.dart").read_text(encoding="utf-8")
        body = source.split("class GeoInRoadLottie", 1)[1].split("class BlankScreen", 1)[0]

        self.assertIn("Lottie.asset", body)
        self.assertNotIn("Image.asset", body)

    def test_flet_app_is_not_blocked_by_fixed_overlay_timer(self):
        source = Path("build/flutter/lib/main.dart").read_text(encoding="utf-8")
        factory = source.split("Widget buildFletAppWithStartupSplash()", 1)[1].split("Future prepareApp", 1)[0]

        self.assertIn("return FletApp(", factory)
        self.assertNotIn("return StartupSplash(", factory)
        self.assertNotIn("class StartupSplash", source)
        self.assertNotIn("return StartupSplash(", source)
        self.assertNotIn("Duration(seconds: 22)", source)


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path


def load_script_asset(filename: str) -> str:
    path = Path(__file__).resolve().parent.parent / "assets" / filename
    return path.read_text(encoding="utf-8")


def build_auto_login_script(*, username: str, password: str) -> str:
    template = load_script_asset("auto_login.js")
    return (
        template.replace("__USERNAME__", json.dumps(username))
        .replace("__PASSWORD__", json.dumps(password))
    )

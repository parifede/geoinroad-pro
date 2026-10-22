APP_TITLE = "Geoinroad Pro"
# Tenere allineata alla versione in pyproject.toml.
APP_VERSION = "1.3.0"
LOGIN_URL = "https://geoinroad.dimetior.com/login"

ROUTE_LOCK = "/"
ROUTE_SPLASH = "/splash"
ROUTE_WEBVIEW = "/diario"
ROUTE_DASHBOARD = "/statistiche"
ROUTE_REPORT = "/report"

APP_NAMESPACE = "geoinroad_pro"
CREDENTIALS_READY_KEY = f"{APP_NAMESPACE}.credentials_ready"
USERNAME_KEY = f"{APP_NAMESPACE}.username"
PASSWORD_KEY = f"{APP_NAMESPACE}.password"
GATE_TOKEN_KEY = f"{APP_NAMESPACE}.gate_token"
# v2: lo stato del cancello delle build con il plugin difettoso non vale
# piu' (poteva risultare attivo senza mai mostrare il prompt).
GATE_ENABLED_KEY = f"{APP_NAMESPACE}.gate_enabled_v2"
CONSOLE_PREFIX = "GEOINROAD_APP::"
STATS_PREFIX = f"{CONSOLE_PREFIX}STATS::"
STATUS_PREFIX = f"{CONSOLE_PREFIX}STATUS::"
ERROR_PREFIX = f"{CONSOLE_PREFIX}ERROR::"
ACTION_PREFIX = f"{CONSOLE_PREFIX}ACTION::"

GATE_SHARED_PREFERENCES_NAME = "geoinroad_pro_gate_v2"
GATE_PREFERENCES_PREFIX = "geoinroad_gate_v2"

RELOAD_PREFIX = f"{CONSOLE_PREFIX}RELOAD::"
BUG_REPORT_WHATSAPP_NUMBER = "393346867229"

BRAND_ACCENT = "#E8357A"
BRAND_DARK = "#1A1A1A"
BRAND_SURFACE = "#F5F5F7"

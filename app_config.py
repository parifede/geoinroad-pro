APP_TITLE = "Geoinroad Pro"
# Tenere allineata alla versione in pyproject.toml.
APP_VERSION = "1.4.0"
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
# Fino alla 1.3: token del cancello biometrico (nel vault) e scelta
# "cancello attivo" (nelle preferences). Servono solo per ripulirli.
LEGACY_GATE_TOKEN_KEY = f"{APP_NAMESPACE}.gate_token"
LEGACY_GATE_ENABLED_KEY = f"{APP_NAMESPACE}.gate_enabled_v2"
CONSOLE_PREFIX = "GEOINROAD_APP::"
STATS_PREFIX = f"{CONSOLE_PREFIX}STATS::"
STATUS_PREFIX = f"{CONSOLE_PREFIX}STATUS::"
ERROR_PREFIX = f"{CONSOLE_PREFIX}ERROR::"
ACTION_PREFIX = f"{CONSOLE_PREFIX}ACTION::"

# Nomi invariati rispetto al cancello della 1.3: e' lo stesso vault, cosi'
# chi lo aveva attivato riusa la chiave gia' creata.
VAULT_SHARED_PREFERENCES_NAME = "geoinroad_pro_gate_v2"
VAULT_PREFERENCES_PREFIX = "geoinroad_gate_v2"

RELOAD_PREFIX = f"{CONSOLE_PREFIX}RELOAD::"
BUG_REPORT_WHATSAPP_NUMBER = "393346867229"

BRAND_ACCENT = "#E8357A"
BRAND_DARK = "#1A1A1A"
BRAND_SURFACE = "#F5F5F7"

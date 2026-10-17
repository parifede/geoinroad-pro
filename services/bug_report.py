import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

REPORT_ID_PREFIX = "GIR"
REPORTS_DIR_NAME = "bug_reports"
MAX_SAVED_REPORTS = 50


def normalize_whatsapp_number(number: str) -> str:
    return "".join(ch for ch in str(number or "") if ch.isdigit())


def build_whatsapp_report_url(number: str, report_text: str) -> str:
    normalized = normalize_whatsapp_number(number)
    if not normalized:
        return ""
    return f"https://wa.me/{normalized}?text={quote(report_text)}"


def build_report_id(report: dict) -> str:
    content = {
        key: value for key, value in (report or {}).items() if key != "report_id"
    }
    digest = hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:6].upper()
    captured_at = str(content.get("captured_at", ""))
    try:
        day = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError:
        day = datetime.now(timezone.utc)
    return f"{REPORT_ID_PREFIX}-{day.strftime('%y%m%d')}-{digest}"


def build_report_text(report: dict) -> str:
    report_id = report.get("report_id") or build_report_id(report)
    body = json.dumps(report, ensure_ascii=False, indent=2)
    return f"Report {report_id}\n{body}"


def reports_dir(base_dir: Path) -> Path:
    return Path(base_dir) / REPORTS_DIR_NAME


def save_report(base_dir: Path, report: dict) -> Path:
    report = dict(report or {})
    report.setdefault("report_id", build_report_id(report))
    target_dir = reports_dir(base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(
        ch if ch.isalnum() or ch in ("_", "-") else "_"
        for ch in str(report["report_id"])
    )
    path = target_dir / f"{safe_id}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _prune_old_reports(target_dir)
    return path


def _prune_old_reports(target_dir: Path) -> None:
    files = sorted(
        target_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for stale in files[MAX_SAVED_REPORTS:]:
        try:
            stale.unlink()
        except OSError:
            pass


def list_saved_reports(base_dir: Path, limit: int = 10) -> list[dict]:
    target_dir = reports_dir(base_dir)
    if not target_dir.exists():
        return []
    entries = []
    for path in target_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        entries.append(
            {
                "report_id": str(data.get("report_id", path.stem)),
                "captured_at": str(data.get("captured_at", "")),
                "route": str(data.get("route", "")),
                "path": str(path),
            }
        )
    entries.sort(key=lambda item: item["captured_at"], reverse=True)
    return entries[:limit]

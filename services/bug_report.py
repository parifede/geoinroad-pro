from urllib.parse import quote


def normalize_whatsapp_number(number: str) -> str:
    return "".join(ch for ch in str(number or "") if ch.isdigit())


def build_whatsapp_report_url(number: str, report_text: str) -> str:
    normalized = normalize_whatsapp_number(number)
    if not normalized:
        return ""
    return f"https://wa.me/{normalized}?text={quote(report_text)}"

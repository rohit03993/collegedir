import re
from datetime import datetime

_BRAND = re.compile(r"Dekho\s*Campus", re.IGNORECASE)
_SCRIPT = re.compile(r"(?is)<script\b[^>]*>.*?</script>")
_STYLE = re.compile(r"(?is)<style\b[^>]*>.*?</style>")
_IFRAME = re.compile(r"(?is)<iframe\b[^>]*>.*?</iframe>")
_HANDLER = re.compile(r"""\son\w+\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_SCRIPT_LINK = re.compile(r"""\bhref\s*=\s*(['"])\s*javascript:[^'"]*\1""", re.IGNORECASE)
_REMOTE = re.compile(r"https?://[^\s\"'<>]*dekhocampus[^\s\"'<>]*", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_NBSP = re.compile(r"&nbsp;", re.IGNORECASE)
_EMPTY_DATE = {"not announced", "n/a", "na", "-", "tbd"}


def clean(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


def text_list(value):
    if not isinstance(value, list):
        return None
    items = []
    for item in value:
        text = clean(item) if isinstance(item, str) else None
        if text:
            items.append(text)
    return items or None


def positive_int(value):
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def money(amount):
    whole = str(int(round(float(amount))))
    if len(whole) <= 3:
        return whole
    last = whole[-3:]
    rest = whole[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    return ",".join(reversed(groups)) + "," + last


def fee_label(amount, fee_type, prefix_from=False):
    if amount is None or amount == "":
        return None
    try:
        number = float(amount)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    label = f"₹{money(number)}"
    kind = clean(fee_type)
    if kind:
        lowered = kind.lower()
        label = f"{label} {lowered}" if lowered.startswith("per ") else f"{label} per {lowered}"
    if prefix_from:
        label = f"From {label}"
    return label


def choose_fee(fees):
    positive = []
    fallback = None
    for fee in fees:
        group = clean(fee.get("course_group"))
        if group and fallback is None:
            fallback = group
        amount = fee.get("fee_amount")
        try:
            number = float(amount) if amount is not None and amount != "" else 0
        except (TypeError, ValueError):
            number = 0
        if number > 0:
            positive.append((number, fee))
    if not positive:
        return fallback, None
    positive.sort(key=lambda item: item[0])
    chosen = positive[0][1]
    label = fee_label(
        chosen.get("fee_amount"),
        chosen.get("fee_type"),
        prefix_from=len(positive) > 1,
    )
    return clean(chosen.get("course_group")) or fallback, label


def rating_value(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return round(number, 1)


def public_html(value):
    text = clean(value)
    if not text:
        return None
    text = _SCRIPT.sub("", text)
    text = _STYLE.sub("", text)
    text = _IFRAME.sub("", text)
    text = _HANDLER.sub("", text)
    text = _SCRIPT_LINK.sub('href="#"', text)
    text = _REMOTE.sub("", text)
    text = _BRAND.sub("Admission Setu", text)
    text = text.strip()
    visible = _NBSP.sub(" ", _TAGS.sub("", text)).strip()
    if not text or not visible:
        return None
    return text


def public_text(value):
    text = clean(value)
    if not text:
        return None
    text = _REMOTE.sub("", text)
    text = _BRAND.sub("Admission Setu", text).strip()
    return text or None


def named_label(value):
    text = clean(value)
    if not text or text.isdigit():
        return None
    return text


def shown_date(value):
    text = public_text(value)
    if not text or text.lower() in _EMPTY_DATE:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return f"{parsed.day} {parsed.strftime('%b')} {parsed.year}"

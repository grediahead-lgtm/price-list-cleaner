"""Small, predictable normalizers. Each returns (value, problem) so nothing is fixed silently."""
import re

_CURRENCY = re.compile(r"(грн\.?|uah|usd|eur|₴|\$|€|грн)", re.I)


def clean_text(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def parse_price(s):
    """'1 234,50 грн' -> (1234.5, None). Returns (None, reason) if it cannot be read."""
    t = clean_text(s)
    if not t:
        return None, "empty price"
    t = _CURRENCY.sub("", t).replace(" ", "")
    if re.search(r"[^\d.,\-]", t):
        return None, "not a number: %r" % s
    if "," in t and "." in t:  # the last separator is the decimal one
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        thousands = "." if dec == "," else ","
        t = t.replace(thousands, "").replace(dec, ".")
    elif "," in t:
        parts = t.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):  # 12,5 and 12,50 are decimals
            t = parts[0] + "." + parts[1]
        else:  # 1,234 and 1,234,567 are thousands separators
            t = t.replace(",", "")
    try:
        value = float(t)
    except ValueError:
        return None, "not a number: %r" % s
    if value < 0:
        return None, "negative price"
    return round(value, 2), None


_SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[xхXХ×*]\s*(\d+(?:[.,]\d+)?)(?:\s*[xхXХ×*]\s*(\d+(?:[.,]\d+)?))?")


def normalize_size(s):
    """'40 х 30 см' -> ('40x30', None); no size found -> ('', None)."""
    t = clean_text(s)
    if not t:
        return "", None
    m = _SIZE.search(t)
    if not m:
        return t, "size not in AxB format"
    parts = [p.replace(",", ".").rstrip("0").rstrip(".") if "." in p.replace(",", ".") else p for p in m.groups() if p]
    return "x".join(parts), None


def name_key(s):
    """Key for finding duplicate names: lowercase, letters and digits only, words sorted."""
    words = re.findall(r"[0-9a-zа-яіїєґ]+", clean_text(s).lower())
    return " ".join(sorted(words))

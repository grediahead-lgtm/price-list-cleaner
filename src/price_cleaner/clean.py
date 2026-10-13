import json

from .normalize import clean_text, name_key, normalize_size, parse_price

DEFAULT_MAP = {"sku": "sku", "name": "name", "price": "price", "size": "size", "stock": "stock"}
OUT_FIELDS = ["sku", "name", "price", "size", "stock"]


def clean_rows(rows, colmap=None):
    """Returns (clean_rows, issues). issues: list of dicts {row, level, code, message}."""
    cm = dict(DEFAULT_MAP)
    cm.update(colmap or {})
    issues, out = [], []
    if rows:
        missing = [v for k, v in cm.items() if k in ("name", "price") and v not in rows[0]]
        if missing:
            raise ValueError("columns not found in the file: %s. Found: %s" % (", ".join(missing), ", ".join(rows[0])))

    def issue(i, level, code, msg):
        issues.append({"row": i, "level": level, "code": code, "message": msg})

    seen_sku, seen_name = {}, {}
    for pos, r in enumerate(rows, start=2):  # row 1 is the header
        i = r.get("__row__") or pos
        sku = clean_text(r.get(cm["sku"]))
        name = clean_text(r.get(cm["name"]))
        price, perr = parse_price(r.get(cm["price"]))
        size, serr = normalize_size(r.get(cm["size"], ""))
        stock = clean_text(r.get(cm["stock"], ""))
        if not name:
            issue(i, "error", "empty_name", "product name is empty")
            continue
        if perr:
            issue(i, "error", "bad_price", perr)
        elif price == 0:
            issue(i, "warning", "zero_price", "price is 0")
        if serr:
            issue(i, "warning", "bad_size", serr)
        if sku:
            if sku in seen_sku:
                issue(i, "error", "duplicate_sku", "sku %r already on row %d" % (sku, seen_sku[sku]))
                continue
            seen_sku[sku] = i
        else:
            issue(i, "warning", "no_sku", "no sku")
        key = name_key(name) + "|" + size
        if key in seen_name:
            issue(i, "warning", "duplicate_name", "same name and size as row %d" % seen_name[key])
        else:
            seen_name[key] = i
        if perr:
            continue  # a row with an unreadable price is reported, not exported
        out.append({"sku": sku, "name": name, "price": "%.2f" % price if price is not None else "", "size": size, "stock": stock})
    return out, issues


def summary(total, clean, issues):
    by = {}
    for x in issues:
        by[x["code"]] = by.get(x["code"], 0) + 1
    return {"rows_in": total, "rows_out": len(clean), "issues": by}


def report_markdown(info, issues, limit=200):
    lines = ["# Price list report", "", "Rows in: %d. Rows exported: %d." % (info["rows_in"], info["rows_out"]), ""]
    if not issues:
        lines.append("No problems found.")
    else:
        lines += ["| code | count |", "|---|---|"] + ["| %s | %d |" % kv for kv in sorted(info["issues"].items())]
        lines += ["", "## Details (first %d)" % limit, "", "| row | level | message |", "|---|---|---|"]
        lines += ["| %d | %s | %s |" % (x["row"], x["level"], x["message"].replace("|", "/")) for x in issues[:limit]]
    return "\n".join(lines) + "\n"


def load_map(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

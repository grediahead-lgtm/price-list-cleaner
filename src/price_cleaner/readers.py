"""Read CSV and XLSX (standard library only) into a list of dict rows."""
import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET

ROW_KEY = "__row__"
MAX_UNPACKED = 200 * 1024 * 1024
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_csv(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = None
    for enc in ("utf-8-sig", "cp1251"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("cannot decode %s as UTF-8 or cp1251" % path)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    out = []
    for r in reader:
        d = dict(r)
        d[ROW_KEY] = reader.line_num  # last physical line of the record (matches the file even with multi-line cells)
        out.append(d)
    return out


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path, sheet=1):
    """First sheet by default. Values come back as strings (formulas: cached value)."""
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED:
            raise ValueError("xlsx unpacks to more than 200 MB; refusing")
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        name = "xl/worksheets/sheet%d.xml" % sheet
        if name not in z.namelist():
            raise ValueError("sheet %d not found" % sheet)
        root = ET.fromstring(z.read(name))
    rows = []
    for row in root.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            t = c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            elif v is None or v.text is None:
                continue
            elif t == "s":
                val = shared[int(v.text)]
            else:
                val = v.text
            cells[_col_index(c.get("r"))] = val
        if cells:
            width = max(cells) + 1
            rows.append((int(row.get("r") or len(rows) + 1), [cells.get(i, "") for i in range(width)]))
    if not rows:
        return []
    header = [h.strip() for h in rows[0][1]]
    out = []
    for rownum, r in rows[1:]:
        r = r + [""] * (len(header) - len(r))
        d = dict(zip(header, r))
        d[ROW_KEY] = rownum  # the row number as Excel shows it, blank rows included
        out.append(d)
    return out


def read_table(path):
    low = path.lower()
    if low.endswith(".xlsx"):
        return read_xlsx(path)
    if low.endswith((".csv", ".txt")):
        return read_csv(path)
    raise ValueError("supported files: .csv, .xlsx")

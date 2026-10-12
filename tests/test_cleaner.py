import json
import os
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from price_cleaner.__main__ import main  # noqa: E402
from price_cleaner.clean import clean_rows  # noqa: E402
from price_cleaner.normalize import name_key, normalize_size, parse_price  # noqa: E402
from price_cleaner.readers import read_csv, read_table, read_xlsx  # noqa: E402


class PriceTests(unittest.TestCase):
    def test_formats(self):
        cases = {"1 250,00 грн": 1250.0, "1250": 1250.0, "2 340,5": 2340.5, "1.234,56": 1234.56, "1,234.56": 1234.56,
                 "1,234": 1234.0, "12,5": 12.5, "99.9 UAH": 99.9, "₴ 300": 300.0, "0": 0.0}
        for text, want in cases.items():
            self.assertEqual(parse_price(text), (want, None), text)

    def test_bad_prices(self):
        for text in ("", "ціна за запитом", "-5", "12abc"):
            value, err = parse_price(text)
            self.assertIsNone(value, text)
            self.assertTrue(err, text)


class SizeTests(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(normalize_size("40 х 30 см"), ("40x30", None))  # Cyrillic х
        self.assertEqual(normalize_size("26×30x16,5"), ("26x30x16.5", None))
        self.assertEqual(normalize_size(""), ("", None))
        self.assertEqual(normalize_size("M")[1], "size not in AxB format")

    def test_name_key_ignores_order_case_punctuation(self):
        self.assertEqual(name_key('Лежак  Comfort, сірий'), name_key("сірий лежак comfort"))


class CleanTests(unittest.TestCase):
    def setUp(self):
        self.rows = read_csv(os.path.join(ROOT, "examples", "supplier.csv"))

    def test_example_file(self):
        clean, issues = clean_rows(self.rows)
        codes = sorted(x["code"] for x in issues)
        self.assertEqual(codes, ["bad_price", "bad_price", "bad_size", "duplicate_name", "duplicate_sku", "empty_name",
                                 "no_sku", "zero_price"])
        skus = [r["sku"] for r in clean]
        self.assertNotIn("A-104", skus)  # unreadable price is reported, not exported
        self.assertEqual(skus.count("A-102"), 1)  # the duplicate sku row is dropped
        self.assertEqual(clean[0]["price"], "1250.00")
        self.assertEqual(clean[0]["size"], "40x30")

    def test_row_numbers_match_the_file(self):
        _, issues = clean_rows(self.rows)
        dup = [x for x in issues if x["code"] == "duplicate_sku"][0]
        self.assertEqual(dup["row"], 5)  # header is row 1

    def test_missing_columns_are_named(self):
        with self.assertRaises(ValueError) as cm:
            clean_rows([{"a": "1"}])
        self.assertIn("name", str(cm.exception))

    def test_column_map(self):
        rows = [{"Назва": "Х", "Ціна": "10"}]
        clean, issues = clean_rows(rows, {"name": "Назва", "price": "Ціна"})
        self.assertEqual(clean[0]["price"], "10.00")


def make_xlsx(path, table):
    """Minimal .xlsx with shared strings for text and plain numbers."""
    strings, rows_xml = [], []
    for r, row in enumerate(table, start=1):
        cells = []
        for c, v in enumerate(row):
            ref = "ABCDEFGH"[c] + str(r)
            if isinstance(v, str):
                strings.append(v)
                cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, len(strings) - 1))
            else:
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, v))
        rows_xml.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, "".join(rows_xml)))
        z.writestr("xl/sharedStrings.xml", '<sst %s>%s</sst>' % (ns, "".join("<si><t>%s</t></si>" % s for s in strings)))


class ReaderTests(unittest.TestCase):
    def test_xlsx_with_empty_cell(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.xlsx")
            make_xlsx(p, [["sku", "name", "price"], ["A1", "Лежак", 99.5], ["A2", "Миска", 10]])
            rows = read_xlsx(p)
            self.assertEqual(rows[0], {"sku": "A1", "name": "Лежак", "price": "99.5"})
            self.assertEqual(len(read_table(p)), 2)

    def test_cp1251_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.csv")
            with open(p, "wb") as f:
                f.write("name;price\nМиска;10\n".encode("cp1251"))
            self.assertEqual(read_csv(p)[0]["name"], "Миска")

    def test_unsupported_extension(self):
        with self.assertRaises(ValueError):
            read_table("x.pdf")


class CliTests(unittest.TestCase):
    def test_cli_writes_files_and_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            code = main([os.path.join(ROOT, "examples", "supplier.csv"), "--out", d])
            self.assertEqual(code, 1)  # the example has errors
            for name in ("clean.csv", "report.md", "issues.json"):
                self.assertTrue(os.path.getsize(os.path.join(d, name)) > 0)
            with open(os.path.join(d, "issues.json"), encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)), 8)


if __name__ == "__main__":
    unittest.main()

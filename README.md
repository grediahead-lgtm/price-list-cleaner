# price-list-cleaner

Cleans a supplier price list (CSV or XLSX) before you import it into a shop: prices, sizes, duplicates, and a short report of everything that looked wrong. Python standard library only, no internet.

## What it does
- Reads `.csv` (UTF-8 or Windows-1251, comma/semicolon/tab) and `.xlsx` (first sheet).
- **Prices:** `1 250,00 грн`, `1.234,56`, `$ 300`, `12,5` become `1250.00`, `1234.56`, `300.00`, `12.50`. Rows with an unreadable or negative price are reported and **not exported**.
- **Sizes:** `40 х 30 см` (Cyrillic х), `26×30x16,5` become `40x30`, `26x30x16.5`. A size that is not in AxB form (for example `M`) is kept as written and reported as a warning.
- **Duplicates:** same SKU (the later row is dropped and reported); same name and size, ignoring case, punctuation and word order (reported as a warning, both rows stay).
- **Problems reported:** empty name, no SKU, price 0, bad price, bad size. Row numbers match the original file (header is row 1; in XLSX blank rows are counted, as Excel shows them).
- Writes three files: `clean.csv`, `report.md` (counts and a table) and `issues.json`. Exit code 1 if there is at least one error.

## Use
```bash
PYTHONPATH=src python3 -m price_cleaner examples/supplier.csv --out out
PYTHONPATH=src python3 -m price_cleaner my.xlsx --map columns.json --out out
```
Column names default to `sku, name, price, size, stock`. If your file uses other names, put them in a JSON file (see `examples/columns.example.json`). Missing required columns (`name`, `price`) are named in the error message.

Tests: `python3 -m unittest discover -s tests`.

## Limits (read this)
- A price with a single comma and three digits (`1,234`) is read as 1234 (thousands separator), and `1.234` as 1.234 (decimal). If your supplier uses the opposite convention, check `clean.csv` before importing.
- Currency is stripped, not converted. All prices are assumed to be in one currency.
- XLSX: first sheet only, no merged-cell or date handling; formula cells use the cached value.
- It finds duplicates by exact normalized name, not by similarity ("Bed grey" vs "Grey bed M" are different).

MIT license.

---

# price-list-cleaner (українською)

Очищає прайс постачальника (CSV або XLSX) перед імпортом у магазин: ціни, розміри, дублікати та короткий звіт про все підозріле. Лише стандартна бібліотека Python.

**Запуск:** `PYTHONPATH=src python3 -m price_cleaner examples/supplier.csv --out out`. Результат: `clean.csv`, `report.md`, `issues.json`. Рядки з нечитабельною ціною не експортуються, а потрапляють у звіт.

**Важливо:** коми й крапки в цінах визначаються за простими правилами (див. «Limits»); перевірте `clean.csv` перед імпортом. Валюти не конвертуються.

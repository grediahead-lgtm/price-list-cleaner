import argparse
import csv
import json
import os
import sys

from .clean import OUT_FIELDS, clean_rows, load_map, report_markdown, summary
from .readers import read_table


def main(argv=None):
    ap = argparse.ArgumentParser(prog="price_cleaner", description="Clean a supplier price list.")
    ap.add_argument("input", help=".csv or .xlsx")
    ap.add_argument("--out", default="out", help="output folder (default: out)")
    ap.add_argument("--map", help="JSON file mapping our fields to your column names")
    args = ap.parse_args(argv)
    rows = read_table(args.input)
    clean, issues = clean_rows(rows, load_map(args.map))
    info = summary(len(rows), clean, issues)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "clean.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(clean)
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as f:
        f.write(report_markdown(info, issues))
    with open(os.path.join(args.out, "issues.json"), "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False))
    return 1 if any(x["level"] == "error" for x in issues) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Ingest USAspending Advanced Search downloads (zips) into data/raw/usaspending/.

USAspending's API is the canonical source but the download is done by hand in the browser
(see README, "Getting the raw files"). This script copies the zips in, extracts only the
prime-transaction and prime-award-summary CSVs, and logs every file's size and SHA-256.

Usage:  python code/01_ingest.py path/to/download1.zip [path/to/download2.zip ...]
"""
import csv
import io
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from common import RAW, ROOT

URL = "https://www.usaspending.gov/search (Advanced Search: FY2008-FY2026, all financial assistance)"
WANT = ("PrimeTransactions", "PrimeAwardSummaries")


def listings_in(path: Path) -> str:
    """Assistance Listings actually present in a CSV, for the provenance note."""
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        col = next((c for c in ("cfda_number", "assistance_listing_number") if c in (r.fieldnames or [])), None)
        if not col:
            return "listings: n/a"
        return "listings: " + " + ".join(sorted({row[col] for row in r if row.get(col)}))


def log(path: Path, note: str):
    subprocess.run([sys.executable, str(ROOT / "code" / "provenance.py"), str(path), URL,
                    "--log", str(RAW / "PROVENANCE.txt"), "--note", note], check=True)


def main(zips):
    RAW.mkdir(parents=True, exist_ok=True)
    for z in map(Path, zips):
        dest = RAW / z.name
        if z.resolve() != dest.resolve():
            shutil.copy2(z, dest)
        log(dest, "browser download by author")
        with zipfile.ZipFile(dest) as zf:
            for m in zf.infolist():
                name = Path(m.filename).name           # flatten; never trust member paths
                if not name.lower().endswith(".csv") or not any(w in name for w in WANT):
                    continue
                target = RAW / name
                with zf.open(m) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                log(target, f"extracted from {dest.name}; {listings_in(target)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])

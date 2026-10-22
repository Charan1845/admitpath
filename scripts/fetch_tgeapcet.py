"""Download and parse the official TG EAPCET (formerly TS EAMCET) last rank statement into a CSV.

    python scripts/fetch_tgeapcet.py [--url ...] [--year 2025] [--phase final]

Source: https://tgeapcet.nic.in (links to https://tgeapcetd.nic.in/files/TGEAPCET_2025_FINALPHASE_LASTRANKS.pdf)
Telangana state engineering colleges (CBIT, VNR VJIET, BVRIT, Vasavi, MGIT, JNTUH and others) admit through
this counselling, not JoSAA. The PDF is a table: college, place, district, type, branch, and closing ranks per
category (OC, BC-A..E, SC-I..III, ST, EWS) for boys and girls.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pdfplumber
import requests

URL = "https://tgeapcetd.nic.in/files/TGEAPCET_2025_FINALPHASE_LASTRANKS.pdf"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "admitpath" / "data" / "tgeapcet_lastranks.csv"
CATS = ["OC", "BC_A", "BC_B", "BC_C", "BC_D", "BC_E", "SC_I", "SC_II", "SC_III", "ST", "EWS"]
RANK_COLS = [f"{c}_{g}" for c in CATS for g in ("BOYS", "GIRLS")]
FIELDS = ["year", "phase", "inst_code", "institute", "place", "district", "coed", "college_type", "branch_code",
          "branch", "affiliated"] + RANK_COLS


def one_line(text: str | None) -> str:
    return " ".join((text or "").split())


def parse(pdf_path: Path, year: int, phase: str) -> list[dict]:
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for cells in table:
                    if not cells or len(cells) != 31 or not cells[0] or "Inst" in cells[0]:
                        continue
                    cells = [one_line(c) for c in cells]
                    row = {"year": year, "phase": phase, "inst_code": cells[0], "institute": cells[1], "place": cells[2],
                           "district": cells[3], "coed": cells[4], "college_type": cells[5], "branch_code": cells[6],
                           "branch": cells[7], "affiliated": cells[30]}
                    for col, value in zip(RANK_COLS, cells[8:30]):
                        row[col] = value if re.fullmatch(r"\d+", value) else ""
                    rows.append(row)
    return rows


PHASES = [  # later phases override earlier ones; a branch filled early only appears in the early statements
    ("first", "https://tgeapcetd.nic.in/files/TGEAPCET_2025_LASTRANKS_FirstPhase.pdf"),
    ("second", "https://tgeapcetd.nic.in/files/TGEAPCET_2025_LASTRANKS_SecondPhase.pdf"),
    ("final", URL),
]


def download(url: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    pdf_path = RAW / Path(url).name
    if not pdf_path.exists():
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (AdmitPath; public last rank statement)"}, timeout=180)
        r.raise_for_status()
        pdf_path.write_bytes(r.content)
    return pdf_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    args = ap.parse_args()
    latest: dict[tuple[str, str], dict] = {}
    for phase, url in PHASES:
        rows = parse(download(url), args.year, phase)
        print(f"{phase}: {len(rows)} rows")
        for row in rows:
            latest[(row["inst_code"], row["branch_code"])] = row
    rows = sorted(latest.values(), key=lambda r: (r["inst_code"], r["branch_code"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} college-branches, {len({r['inst_code'] for r in rows})} colleges -> {OUT}")


if __name__ == "__main__":
    main()

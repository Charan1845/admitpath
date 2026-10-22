"""Download official JoSAA opening and closing ranks (final round) from the public archive.

    python scripts/fetch_josaa.py [--years 2023 2024 2025] [--out data/josaa_orcr.csv]

Source: https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx
The page is an ASP.NET form, so we walk it like a browser: year -> round -> institute type -> ALL -> ALL -> ALL.
One request per year and institute type, with a pause between them, to be gentle on the site.
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
P = "ctl00$ContentPlaceHolder1$"
TYPES = {"IIT": "IIT", "NIT": "NIT", "3IT": "IIIT", "CFI": "GFTI"}
FIELDS = ["year", "round", "inst_type", "institute", "program", "quota", "seat_type", "gender",
          "opening_rank", "closing_rank", "opening_prep", "closing_prep"]


def _parse(html: str):
    soup = BeautifulSoup(html, "html.parser")
    hidden = {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}
    selects = {s["name"]: [o.get("value") for o in s.select("option")] for s in soup.select("select")}
    return soup, hidden, selects


def _rank(text: str) -> tuple[int | None, bool]:
    """'1234' -> (1234, False); '56P' (preparatory-course rank) -> (56, True)."""
    m = re.fullmatch(r"\s*(\d+)\s*(P?)\s*", text or "")
    return (int(m.group(1)), bool(m.group(2))) if m else (None, False)


def fetch(session: requests.Session, year: int, type_code: str) -> list[dict]:
    def post(html, vals, target):
        _, hidden, _ = _parse(html)
        return session.post(URL, data={**hidden, **vals, "__EVENTTARGET": target, "__EVENTARGUMENT": ""}, timeout=120).text

    html = session.get(URL, timeout=60).text
    vals = {P + "ddlYear": str(year)}
    html = post(html, vals, P + "ddlYear")
    rounds = [r for r in _parse(html)[2][P + "ddlroundno"] if r and r.isdigit()]
    final = max(rounds, key=int)
    vals[P + "ddlroundno"] = final
    html = post(html, vals, P + "ddlroundno")
    vals[P + "ddlInstype"] = type_code
    html = post(html, vals, P + "ddlInstype")
    vals[P + "ddlInstitute"] = "ALL"
    html = post(html, vals, P + "ddlInstitute")
    vals[P + "ddlBranch"] = "ALL"
    html = post(html, vals, P + "ddlBranch")
    vals[P + "ddlSeatType"] = "ALL"
    _, hidden, _ = _parse(html)
    page = session.post(URL, data={**hidden, **vals, P + "btnSubmit": "Submit"}, timeout=300).text

    rows = []
    for tr in BeautifulSoup(page, "html.parser").select("table tr"):
        cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.select("td")]
        if len(cells) != 7:
            continue
        inst, prog, quota, seat, gender, o, c = cells
        (orank, oprep), (crank, cprep) = _rank(o), _rank(c)
        if crank is None:
            continue
        rows.append({"year": year, "round": int(final), "inst_type": TYPES[type_code], "institute": inst,
                     "program": prog, "quota": quota, "seat_type": seat, "gender": gender,
                     "opening_rank": orank, "closing_rank": crank, "opening_prep": int(oprep), "closing_prep": int(cprep)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "admitpath" / "data" / "josaa_orcr.csv"))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (AdmitPath; one-time download of public JoSAA cutoffs)"
    all_rows: list[dict] = []
    for year in args.years:
        for code, name in TYPES.items():
            for attempt in range(3):
                try:
                    rows = fetch(session, year, code)
                    break
                except requests.RequestException as exc:
                    print(f"  retry {year} {name}: {exc}")
                    time.sleep(5 * (attempt + 1))
            else:
                raise SystemExit(f"failed: {year} {name}")
            print(f"{year} {name}: {len(rows)} rows (round {rows[0]['round'] if rows else '?'})", flush=True)
            all_rows.extend(rows)
            time.sleep(2)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {len(all_rows)} rows to {out}")


if __name__ == "__main__":
    main()

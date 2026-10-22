"""Telangana state colleges (TG EAPCET counselling): official 2025 final-phase last ranks.

CBIT, VNR VJIET, BVRIT, Vasavi, MGIT, CVR, JNTUH and other Telangana colleges don't admit through JoSAA.
They fill convener seats through TG EAPCET counselling, by EAPCET rank, with Telangana categories
(OC, BC-A to BC-E, SC-I to SC-III, ST, EWS) and separate columns for boys (open to all) and girls.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .catalog import branch_matches, norm, words

DATA = Path(__file__).resolve().parent / "data" / "tgeapcet_lastranks.csv"
CATS = ["OC", "BC_A", "BC_B", "BC_C", "BC_D", "BC_E", "SC_I", "SC_II", "SC_III", "ST", "EWS"]
DISTRICTS = {"HYD": "Hyderabad", "RR": "Ranga Reddy", "MDL": "Medchal-Malkajgiri", "MED": "Medak", "SRD": "Sangareddy",
             "WGL": "Warangal", "HNK": "Hanumakonda", "KRM": "Karimnagar", "KMM": "Khammam", "NLG": "Nalgonda",
             "MBN": "Mahabubnagar", "NZB": "Nizamabad", "ADB": "Adilabad", "SDP": "Siddipet", "YBG": "Yadadri Bhuvanagiri",
             "SRP": "Suryapet", "JTL": "Jagtial", "PDL": "Peddapalli", "JGN": "Jangaon", "VKB": "Vikarabad",
             "MHB": "Mahabubabad", "KMR": "Kamareddy", "NGK": "Nagarkurnool", "WNP": "Wanaparthy", "SRC": "Rajanna Sircilla",
             "BDK": "Bhadradri Kothagudem", "MNC": "Mancherial", "NRM": "Nirmal", "JNG": "Jangaon"}
TYPES = {"PVT": "private", "UNIV": "university", "GOV": "government", "SF": "self-financing university"}
HYDERABAD_AREA = {"HYD", "RR", "MDL"}

# What people call these colleges -> words that pick the right one.
NICKNAMES = {
    "cbit": "chaitanya bharathi", "vnr": "v n r vignana jyothi", "vnrvjiet": "v n r vignana jyothi",
    "vjiet": "v n r vignana jyothi", "vnr vjiet": "v n r vignana jyothi", "vasavi": "vasavi", "mgit": "mahatma gandhi institute",
    "griet": "gokaraju rangaraju", "gokaraju": "gokaraju rangaraju", "cvr": "cvr", "mvsr": "maturi venkata",
    "kmit": "keshav memorial", "iare": "institute of aeronautical",
    "vardhaman": "vardhaman", "anurag": "anurag", "cmrit": "cmr institute of technology", "cmrcet": "cmr engg college",
    "mlrit": "marri laxman", "jntuh": "jntuh university college of engg sci and tech hyderabad", "jntu": "jntuh",
    "kits": "kakatiya institute", "matrusri": "matrusri", "methodist": "methodist", "stanley": "stanley",
    "vbit": "vignana bharathi", "geethanjali": "geethanjali", "malla reddy": "malla reddy", "mrec": "malla reddy college of engineering",
    "bvrit": "b v raju", "bv raju": "b v raju", "nalla malla": "nalla malla", "mahindra": "mahindra",
    "guru nanak": "guru nanak", "st martins": "st martins", "st. martin's": "st martins", "aurora": "aurora",
}


@dataclass
class TgBranch:
    code: str
    name: str
    ranks: dict[str, int]          # e.g. {"OC_BOYS": 2053, "OC_GIRLS": 2471, ...}

    @property
    def short(self) -> str:
        small = {"and", "of", "in", "for"}
        out = []
        for w in self.name.lower().split():
            if w in small:
                out.append(w)
            elif w.startswith("("):
                out.append("(" + w[1:].capitalize())
            else:
                out.append(w.capitalize())
        text = " ".join(out)
        for a in ("Ai", "Ml", "Iot", "Vlsi", "It"):
            text = re.sub(rf"\b{a}\b", a.upper(), text)
        return text


@dataclass
class TgCollege:
    code: str
    name: str
    place: str
    district: str
    coed: str
    kind: str
    affiliated: str
    branches: dict[str, TgBranch] = field(default_factory=dict)

    @property
    def short(self) -> str:
        keep = {"BVRIT", "CVR", "JNTUH", "CMR", "KU", "IARE", "MVSR", "KITS", "VNR", "B", "V", "N", "R", "TKR", "MLR", "SR", "NIT"}
        small = {"OF", "AND", "FOR", "THE", "IN"}
        out = []
        for w in self.name.replace("(AUTONOMOUS)", "").split():
            bare = w.strip("(),.-")
            if bare in keep:
                out.append(w)
            elif bare in small and out:
                out.append(w.lower())
            else:
                out.append(w.capitalize())
        return " ".join(out).strip(" ,")

    @property
    def where(self) -> str:
        district = DISTRICTS.get(self.district, self.district)
        return f"{self.place.title()}, {district}"

    @property
    def girls_only(self) -> bool:
        return self.coed.upper().startswith("GIRL")

    @property
    def autonomous(self) -> bool:
        return "AUTONOMOUS" in self.name.upper()


def _aliases(c: TgCollege) -> set[str]:
    out = {c.code.lower()}
    ws = [w for w in words(c.name) if w not in {"of", "and", "for", "the", "autonomous"}]
    out.add("".join(w[0] for w in ws))                     # acronym, e.g. cbit
    if c.name.upper().startswith("BVRIT") or "B V RAJU" in c.name.upper():
        out.add("bvrit")
    return out


@dataclass
class TgCatalog:
    colleges: dict[str, TgCollege]
    year: int

    def find(self, query: str) -> tuple[TgCollege | None, list[TgCollege], int]:
        """(best match, other colleges the same words could mean, strength 0-3). Strength 3 = a name or code matched."""
        q = norm(query)
        for k, v in sorted(NICKNAMES.items(), key=lambda kv: -len(kv[0])):
            q = re.sub(rf"\b{re.escape(k)}\b", f"{k} {v}", q)
        qw = set(words(q)) - {"college", "clg", "colleges", "in", "of", "and", "the", "engineering", "institute",
                              "technology", "which", "is", "better", "compare", "between", "vs", "or"}
        scored = []
        for c in self.colleges.values():
            cw = set(words(c.name)) | set(words(c.place))
            hits = len(qw & cw)
            alias = bool(qw & _aliases(c))
            if not hits and not alias:
                continue
            score = 3 + min(hits, 1) * 0.5 if alias else min(hits, 3) + (0.5 if hits >= len(qw) - 1 else 0)
            if {"hyderabad", "hyd"} & qw and c.district in HYDERABAD_AREA:
                score += 1                                    # "BVRIT in Hyderabad" -> the Bachupally campus
            if {"women", "girls", "ladies"} & qw and c.girls_only:
                score += 2
            scored.append((score, c))
        if not scored:
            return None, [], 0
        scored.sort(key=lambda x: -x[0])
        best_score, best = scored[0]
        others = [c for s, c in scored[1:] if s >= best_score - 1 and (_aliases(c) & _aliases(best) or s >= best_score)]
        strength = 3 if (qw & _aliases(best)) or best_score >= 3 else min(best_score, 2)
        return best, others[:2], strength

    def branches(self, college: TgCollege, branch: str | None) -> list[TgBranch]:
        items = list(college.branches.values())
        if not branch:
            return items
        found = [b for b in items if branch_matches(branch, b.name)]
        # Prefer the core branch over its specialisations ("CSE" before "CSE (Data Science)")
        found.sort(key=lambda b: ("(" in b.name, len(b.name)))
        return found


def load(path: Path = DATA) -> TgCatalog:
    colleges: dict[str, TgCollege] = {}
    year = 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            c = colleges.get(r["inst_code"])
            if c is None:
                c = colleges[r["inst_code"]] = TgCollege(r["inst_code"], r["institute"], r["place"], r["district"],
                                                         r["coed"], r["college_type"], r["affiliated"])
            ranks = {k: int(r[k]) for k in r if k.endswith(("_BOYS", "_GIRLS")) and r[k]}
            c.branches[r["branch_code"]] = TgBranch(r["branch_code"], r["branch"], ranks)
    return TgCatalog(colleges, year)


@lru_cache(maxsize=1)
def tg_catalog() -> TgCatalog:
    return load()


# ---------------- student categories and chances ----------------

def ts_category(text: str | None) -> str | None:
    if not text:
        return None
    t = re.sub(r"[\s\-]+", "_", text.strip().upper())
    t = {"GENERAL": "OC", "GEN": "OC", "OPEN": "OC", "OC": "OC", "SC": "SC_I", "BC": None}.get(t, t)
    m = re.fullmatch(r"BC_?([A-E])", t or "")
    if m:
        return f"BC_{m.group(1)}"
    m = re.fullmatch(r"SC_?(I{1,3}|[123])", t or "")
    if m:
        return "SC_" + {"1": "I", "2": "II", "3": "III"}.get(m.group(1), m.group(1))
    return t if t in CATS else None


def best_seat(branch: TgBranch, rank: int, category: str, female: bool) -> tuple[str, int] | None:
    """The column that gives the student the best chance: OC and their own category; boys columns are open to all,
    girls columns only to girls."""
    cols = []
    for cat in dict.fromkeys(["OC", category]):
        cols.append(f"{cat}_BOYS")
        if female:
            cols.append(f"{cat}_GIRLS")
    options = [(c, branch.ranks[c]) for c in cols if c in branch.ranks]
    if not options:
        return None
    return max(options, key=lambda x: x[1])                  # the highest closing rank is the easiest to get


def seat_words(col: str) -> str:
    cat, who = col.rsplit("_", 1)
    cat = {"OC": "OC (open)"}.get(cat, cat.replace("_", "-"))
    return f"{cat} {'girls' if who == 'GIRLS' else 'general'} seat"

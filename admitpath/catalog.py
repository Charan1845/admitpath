"""Official JoSAA cutoffs loaded into memory, plus matching of spoken institute and branch names.

Families say "NIT Warangal", "IIT B", "triple IT Allahabad" or "CSE", not the official names, so this
module turns everyday words into the exact institutes and programs in the data.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "josaa_orcr.csv"


def norm(text: str) -> str:
    text = text.lower().replace("&", " and ").replace("–", "-")
    text = re.sub(r"[^a-z0-9\-:, ]+", " ", text)
    return " ".join(text.split())


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", norm(text))


@dataclass
class Seat:
    year: int
    quota: str
    seat_type: str
    gender: str
    opening: int
    closing: int


@dataclass
class Program:
    institute: str
    name: str                      # official program name, e.g. "Computer Science and Engineering (4 Years, Bachelor of Technology)"
    seats: list[Seat] = field(default_factory=list)

    @property
    def short(self) -> str:
        return short_program(self.name)


@dataclass
class Institute:
    name: str
    kind: str                      # IIT, NIT, IIIT, GFTI
    aliases: list[str]
    programs: dict[str, Program] = field(default_factory=dict)

    @property
    def short(self) -> str:
        return self.aliases[0]


def short_program(name: str) -> str:
    """'Computer Science and Engineering (4 Years, Bachelor of Technology)' -> 'Computer Science and Engineering (B.Tech)'."""
    if re.search(r"\(\s*\d-year B\. ?Tech", name):           # "(4-year B. Tech / B. Tech (Hons.))"
        return re.split(r"\s*\(\s*\d-year B\. ?Tech", name)[0] + " (B.Tech)"
    m = re.match(r"(.*?)\s*\((\d) Years?, (.*)\)\s*$", name)
    if not m:
        return name
    base, years, degree = m.groups()
    tag = {"Bachelor of Technology": "B.Tech", "Bachelor of Architecture": "B.Arch", "Bachelor of Science": "B.Sc",
           "Bachelor of Planning": "B.Plan"}.get(degree, f"{years}-year {degree}")
    if "Dual Degree" in degree:
        tag = "Dual Degree"
    elif "Integrated" in degree:
        tag = f"{years}-year Integrated"
    return f"{base} ({tag})"


# ---------------- institute names ----------------

_TYPE_WORDS = {
    "IIT": "indian institute of technology",
    "NIT": "national institute of technology",
    "IIIT": "indian institute of information technology",
}
_FILLER = {"of", "and", "the", "institute", "technology", "national", "indian", "information", "university",
           "engineering", "science", "management", "design", "manufacturing", "college", "campus", "off"}


def _city_words(name: str) -> list[str]:
    """The distinctive words of an institute name: its city or state and any founder name."""
    return [w for w in words(name) if w not in _FILLER and not w.isdigit()]


def make_aliases(name: str, kind: str) -> list[str]:
    distinct = _city_words(name)
    place = " ".join(distinct[-2:]) if distinct else name
    low = norm(name)
    if kind == "NIT" and "national institute of technology" in low:
        tail = low.split("national institute of technology", 1)[1].strip(" ,")
        place = tail or place
    elif kind == "IIT" and "indian institute of technology" in low:
        place = low.split("indian institute of technology", 1)[1].strip(" ,")
    elif kind == "IIIT" and "information technology" in low:
        place = low.split("information technology", 1)[1].strip(" ,")
        place = re.sub(r"^(and management|design and manufacturing)\s*", "", place).strip(" ,")
    place = re.sub(r"\(?\biiit\b\)?", "", place)
    place = re.sub(r"[()]", "", place).strip(" ,")
    place = re.sub(r"\s*,\s*", ", ", place)
    label = {"IIT": "IIT", "NIT": "NIT", "IIIT": "IIIT"}.get(kind)
    pretty = place.title().replace("Bhu", "BHU").replace("Ism", "ISM")
    first = f"{label} {pretty}" if label and place else name
    if "shibpur" in low:
        first = "IIEST Shibpur"
    return [first, name]


# Everyday shorthand for institutes that people almost never call by the official name.
_NICKNAMES = {
    "iitb": "iit bombay", "iitd": "iit delhi", "iitm": "iit madras", "iitk": "iit kanpur", "iitkgp": "iit kharagpur",
    "iitr": "iit roorkee", "iitg": "iit guwahati", "iith": "iit hyderabad", "bhu": "iit bhu varanasi",
    "nitw": "nit warangal", "nitt": "nit tiruchirappalli", "nit trichy": "nit tiruchirappalli", "trichy": "tiruchirappalli",
    "nitk": "nit karnataka surathkal", "surathkal": "nit karnataka surathkal", "nitc": "nit calicut",
    "mnnit": "motilal nehru allahabad", "manit": "maulana azad bhopal", "mnit": "malaviya jaipur",
    "vnit": "visvesvaraya nagpur", "svnit": "sardar vallabhbhai surat", "nitr": "nit rourkela",
    "iiita": "iiit allahabad", "iiitm": "iiit gwalior", "iiitdm": "iiit design kancheepuram", "pec": "punjab engineering college",
    "bit mesra": "birla institute of technology mesra", "iiest": "iiest shibpur", "prayagraj": "allahabad",
    "bombay": "bombay", "mumbai": "bombay", "chennai": "madras", "trivandrum": "thiruvananthapuram", "kozhikode": "calicut",
    "kgp": "kharagpur", "nit ap": "nit andhra pradesh", "ism": "ism dhanbad", "iit dhanbad": "iit ism dhanbad",
    "nit uk": "nit uttarakhand",
}

# Well-known colleges that don't admit through JoSAA, so families get a clear answer instead of "not found".
NOT_IN_JOSAA = {
    "iiit hyderabad": "IIIT Hyderabad admits through its own process (UGEE and JEE Main-based direct admission), not JoSAA.",
    "iiith": "IIIT Hyderabad admits through its own process (UGEE and JEE Main-based direct admission), not JoSAA.",
    "iiit delhi": "IIIT Delhi admits through JAC Delhi counselling, not JoSAA.",
    "iiitd": "IIIT Delhi admits through JAC Delhi counselling, not JoSAA.",
    "iiit bangalore": "IIIT Bangalore admits through its own process, not JoSAA.",
    "iiitb": "IIIT Bangalore admits through its own process, not JoSAA.",
    "dtu": "DTU admits through JAC Delhi counselling, not JoSAA.",
    "delhi technological": "DTU admits through JAC Delhi counselling, not JoSAA.",
    "nsut": "NSUT admits through JAC Delhi counselling, not JoSAA.",
    "bits": "BITS Pilani admits through its own BITSAT exam, not JoSAA.",
    "vit": "VIT admits through its own VITEEE exam, not JoSAA.",
}


def not_in_josaa(query: str) -> str | None:
    q = _expand(query) if query else ""
    raw = norm(query or "")
    for key, msg in NOT_IN_JOSAA.items():
        if re.search(rf"\b{re.escape(key)}\b", raw) or re.search(rf"\b{re.escape(key)}\b", q):
            return msg
    return None


def _expand(query: str) -> str:
    q = norm(query)
    q = re.sub(r"\btriple i ?t\b|\btriple it\b|\bi i i t\b", "iiit", q)
    q = re.sub(r"\bi i t\b", "iit", q)
    q = re.sub(r"\bn i t\b", "nit", q)
    for k, v in sorted(_NICKNAMES.items(), key=lambda kv: -len(kv[0])):
        q = re.sub(rf"\b{re.escape(k)}\b", v, q)
    return q


@dataclass
class Catalog:
    institutes: dict[str, Institute]
    years: list[int]

    # ---- institutes ----
    def find_institute(self, query: str) -> Institute | None:
        matches = self.match_institutes(query, limit=1)
        return matches[0] if matches else None

    def match_institutes(self, query: str, limit: int = 3) -> list[Institute]:
        q = _expand(query)
        qwords = set(words(q))
        want = None
        for kind in ("IIIT", "IIT", "NIT"):
            if re.search(rf"\b{kind.lower()}s?\b", q):
                want = kind
                break
        q_distinct = qwords - _FILLER - {"iit", "nit", "iiit", "iits", "nits", "iiits"}
        scored = []
        for inst in self.institutes.values():
            if want and inst.kind != want:
                continue
            inst_words = set(words(inst.name)) | set(words(inst.aliases[0]))
            hits = len(q_distinct & inst_words)
            if q_distinct and not hits:
                continue
            ratio = max(SequenceMatcher(None, q, norm(a)).ratio() for a in inst.aliases)
            scored.append((hits * 2 + ratio, inst))
        scored.sort(key=lambda x: -x[0])
        return [i for _, i in scored[:limit]]

    # ---- programs ----
    def match_programs(self, inst: Institute, branch: str | None) -> list[Program]:
        latest = self.years[-1] if self.years else None
        # only programs still offered in the latest year
        progs = [p for p in inst.programs.values() if any(s.year == latest for s in p.seats)]
        if not branch:
            return progs
        return [p for p in progs if branch_matches(branch, p.name)]

    def all_programs(self, branch: str | None = None, kinds: set[str] | None = None) -> list[Program]:
        out = []
        for inst in self.institutes.values():
            if kinds and inst.kind not in kinds:
                continue
            out.extend(self.match_programs(inst, branch))
        return out

    def kind_of(self, program: Program) -> str:
        return self.institutes[program.institute].kind


# ---------------- branches ----------------

BRANCHES = {
    "computer science": ["computer science", "computer engineering"],
    "artificial intelligence": ["artificial intelligence", "data science", "machine learning", "data and computational"],
    "information technology": ["information technology"],
    "electronics": ["electronics and communication", "electronics and telecommunication", "electronics engineering",
                    "electronics and instrumentation", "vlsi", "microelectronics"],
    "electrical": ["electrical"],
    "mechanical": ["mechanical"],
    "civil": ["civil"],
    "chemical": ["chemical engineering"],
    "aerospace": ["aerospace", "aeronautical"],
    "mathematics and computing": ["mathematics and computing", "mathematics and data science"],
    "metallurgy": ["metallurg", "materials"],
    "biotechnology": ["biotechnology", "bio technology", "biological", "biomedical", "bioengineering"],
    "engineering physics": ["engineering physics"],
    "architecture": ["architecture"],
    "production": ["production", "industrial"],
    "mining": ["mining"],
}
BRANCH_ALIASES = {
    "cse": "computer science", "cs": "computer science", "comp sci": "computer science", "computers": "computer science",
    "computer": "computer science", "ai": "artificial intelligence", "aiml": "artificial intelligence",
    "ai ml": "artificial intelligence", "data science": "artificial intelligence", "ds": "artificial intelligence",
    "it": "information technology", "ece": "electronics", "ec": "electronics", "electronics and communication": "electronics",
    "eee": "electrical", "ee": "electrical", "mech": "mechanical", "me": "mechanical", "ce": "civil",
    "chem": "chemical", "aero": "aerospace", "mnc": "mathematics and computing", "math and computing": "mathematics and computing",
    "maths and computing": "mathematics and computing", "biotech": "biotechnology", "bio": "biotechnology",
    "meta": "metallurgy", "mme": "metallurgy", "ep": "engineering physics", "b arch": "architecture",
}


def branch_key(branch: str) -> str | None:
    b = norm(branch).replace("engineering", "").strip()
    if b in BRANCH_ALIASES:
        return BRANCH_ALIASES[b]
    for key in BRANCHES:
        if key in b or b in key:
            return key
    for key, pats in BRANCHES.items():
        if any(p in b for p in pats):
            return key
    return None


def branch_matches(branch: str, program_name: str) -> bool:
    key = branch_key(branch)
    low = program_name.lower()
    if key == "electronics" and "electrical and electronics" in low:
        return False                                  # EEE is an electrical branch, not ECE
    if key:
        return any(p in low for p in BRANCHES[key])
    return norm(branch) in norm(program_name)


# ---------------- loading ----------------

def load(path: Path = DATA) -> Catalog:
    institutes: dict[str, Institute] = {}
    years: set[int] = set()
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["closing_prep"] == "1" or not r["institute"]:
                continue                                   # preparatory-course ranks aren't comparable
            name = " ".join(r["institute"].split())
            inst = institutes.get(name)
            if inst is None:
                inst = institutes[name] = Institute(name=name, kind=r["inst_type"], aliases=make_aliases(name, r["inst_type"]))
            prog_name = " ".join(r["program"].split())
            prog = inst.programs.get(prog_name)
            if prog is None:
                prog = inst.programs[prog_name] = Program(institute=name, name=prog_name)
            year = int(r["year"])
            years.add(year)
            prog.seats.append(Seat(year, r["quota"], r["seat_type"], r["gender"],
                                   int(r["opening_rank"] or 0), int(r["closing_rank"])))
    return Catalog(institutes=institutes, years=sorted(years))


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return load()

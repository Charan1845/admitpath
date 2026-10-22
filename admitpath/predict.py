"""Safe / Target / Reach predictions from official JoSAA closing ranks.

For each program, we find every seat the student is eligible for (quota, category, gender), compare the
student's matching rank with that seat's past final-round closing ranks, and keep the best chance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from .catalog import Catalog, Institute, Program
from .home_states import HOME_STATE, SPECIAL_QUOTA

SAFE, TARGET, REACH = 0.85, 1.05, 1.25
TREND_CLIP = (0.85, 1.15)
CATEGORIES = ("OPEN", "EWS", "OBC-NCL", "SC", "ST")


@dataclass
class Student:
    name: str = "Student"
    main_rank: int | None = None            # JEE Main common rank list (CRL) rank
    main_category_rank: int | None = None   # JEE Main category rank (EWS, OBC-NCL, SC, ST)
    adv_rank: int | None = None             # JEE Advanced CRL rank (for IITs)
    adv_category_rank: int | None = None
    category: str = "OPEN"
    gender: str = "Male"                    # "Male" or "Female"
    home_state: str | None = None
    pwd: bool = False
    pwd_rank: int | None = None             # PwD rank (used for PwD seats, Main-based)

    @property
    def female(self) -> bool:
        return self.gender.lower().startswith("f")


@dataclass
class Option:
    institute: Institute
    program: Program
    quota: str
    seat_type: str
    gender: str
    rank_used: int
    rank_label: str
    closings: dict[int, int]
    expected: int
    ratio: float
    band: str
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.program.short} at {self.institute.short}"


def band_for(ratio: float) -> str:
    if ratio <= SAFE:
        return "Safe"
    if ratio <= TARGET:
        return "Target"
    if ratio <= REACH:
        return "Reach"
    return "Unlikely"


def expected_closing(closings: dict[int, int]) -> int:
    """Latest closing rank, nudged by the recent year-on-year trend (clipped so one odd year can't dominate)."""
    years = sorted(closings)
    latest = closings[years[-1]]
    ratios = [closings[b] / closings[a] for a, b in zip(years, years[1:]) if closings[a] > 0]
    if not ratios:
        return latest
    g = min(max(median(ratios), TREND_CLIP[0]), TREND_CLIP[1])
    return max(1, round(latest * g))


def _key(name: str) -> str:
    return " ".join(name.lower().replace("&", "and").split())


def quotas_for(inst: Institute, quotas_present: set[str], state: str | None) -> list[str]:
    """The quotas this student can use at this institute."""
    out = []
    if "AI" in quotas_present:
        out.append("AI")
    key = _key(inst.name)
    special = next((v for k, v in SPECIAL_QUOTA.items() if key.startswith(k)), {})
    for quota, states in special.items():
        if state in states and quota in quotas_present:
            out.append(quota)
            return out
    home = next((v for k, v in HOME_STATE.items() if key.startswith(k)), None)
    if home is not None and state in home and "HS" in quotas_present:
        out.append("HS")
    elif "OS" in quotas_present and not (home is not None and state in home):
        out.append("OS")
    return out


def _seat_ranks(student: Student, kind: str) -> list[tuple[str, int, str]]:
    """(seat type, rank to compare, how to describe that rank) the student can use."""
    iit = kind == "IIT"
    crl = student.adv_rank if iit else student.main_rank
    cat = student.adv_category_rank if iit else student.main_category_rank
    exam = "JEE Advanced" if iit else "JEE Main"
    out = []
    if crl:
        out.append(("OPEN", crl, f"{exam} rank {crl:,}"))
    if student.category != "OPEN" and cat:
        out.append((student.category, cat, f"{exam} {student.category} rank {cat:,}"))
    if student.pwd and student.pwd_rank and not iit:
        out.append(("OPEN (PwD)", student.pwd_rank, f"PwD rank {student.pwd_rank:,}"))
        if student.category != "OPEN":
            out.append((f"{student.category} (PwD)", student.pwd_rank, f"PwD rank {student.pwd_rank:,}"))
    return out


def evaluate(student: Student, inst: Institute, prog: Program) -> Option | None:
    """The student's best chance at one program, or None if they aren't eligible for any of its seats."""
    quotas = quotas_for(inst, {s.quota for s in prog.seats}, student.home_state)
    genders = {"Gender-Neutral"} | ({"Female-only (including Supernumerary)"} if student.female else set())
    best: Option | None = None
    for seat_type, rank, rank_label in _seat_ranks(student, inst.kind):
        for quota in quotas:
            for gender in genders:
                closings = {s.year: s.closing for s in prog.seats
                            if s.quota == quota and s.seat_type == seat_type and s.gender == gender}
                if not closings:
                    continue
                exp = expected_closing(closings)
                ratio = rank / exp
                if best is None or ratio < best.ratio:
                    best = Option(inst, prog, quota, seat_type, gender, rank, rank_label, dict(sorted(closings.items())),
                                  exp, ratio, band_for(ratio))
    if best and not student.home_state and best.quota == "OS":
        best.notes.append("Home state not set, so other-state quota was assumed.")
    return best


def predict(cat: Catalog, student: Student, branch: str | None = None, kinds: set[str] | None = None,
            include_unlikely: bool = False) -> list[Option]:
    options = []
    for prog in cat.all_programs(branch, kinds):
        inst = cat.institutes[prog.institute]
        opt = evaluate(student, inst, prog)
        if opt and (include_unlikely or opt.band != "Unlikely"):
            options.append(opt)
    return options


def grouped(options: list[Option]) -> dict[str, list[Option]]:
    """Safe: most competitive first (the best you can safely get). Target and Reach: closest to the cutoff first."""
    out: dict[str, list[Option]] = {"Safe": [], "Target": [], "Reach": [], "Unlikely": []}
    for o in options:
        out[o.band].append(o)
    out["Safe"].sort(key=lambda o: o.expected)
    out["Target"].sort(key=lambda o: o.ratio)
    out["Reach"].sort(key=lambda o: o.ratio)
    out["Unlikely"].sort(key=lambda o: o.ratio)
    return out


def trend_words(closings: dict[int, int]) -> str:
    years = sorted(closings)
    if len(years) < 2:
        return ""
    first, last = closings[years[0]], closings[years[-1]]
    change = (last - first) / first
    if abs(change) < 0.05:
        return "steady"
    return "getting harder (cutoff rank falling)" if change < 0 else "getting easier (cutoff rank rising)"

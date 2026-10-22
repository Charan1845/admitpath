"""Spoken answers about Telangana state colleges (TG EAPCET counselling)."""

from __future__ import annotations

from .predict import Student, band_for
from .tgeapcet import CATS, HYDERABAD_AREA, TYPES, TgBranch, TgCollege, best_seat, seat_words, tg_catalog

SOURCE = "official TG EAPCET 2025 last ranks (latest counselling phase)"


def n(x: int) -> str:
    return f"{x:,}"


def main_branch(college: TgCollege, branch: str | None) -> TgBranch | None:
    """The branch asked for, or CSE, or failing that the college's most competitive branch."""
    cat = tg_catalog()
    found = cat.branches(college, branch or "cse")
    if found:
        return found[0]
    if branch:
        return None
    ranked = [b for b in college.branches.values() if b.ranks.get("OC_BOYS") or b.ranks.get("OC_GIRLS")]
    return min(ranked, key=lambda b: b.ranks.get("OC_BOYS") or b.ranks.get("OC_GIRLS")) if ranked else None


def profile(c: TgCollege) -> str:
    bits = [c.where, f"{TYPES.get(c.kind, c.kind)} college"]
    if c.autonomous:
        bits.append("autonomous")
    if c.girls_only:
        bits.append("for women only")
    bits.append(f"affiliated to {c.affiliated}")
    bits.append(f"{len(c.branches)} branches in counselling")
    return ", ".join(bits)


def open_cutoff(b: TgBranch) -> str:
    boys, girls = b.ranks.get("OC_BOYS"), b.ranks.get("OC_GIRLS")
    if boys and girls:
        return f"closed at rank {n(boys)} for OC general seats and {n(girls)} for OC girls' seats"
    if girls:
        return f"closed at rank {n(girls)} for OC girls' seats"
    if boys:
        return f"closed at rank {n(boys)} for OC general seats"
    return "has no OC last rank in the statement"


def chance(student: Student | None, b: TgBranch, c: TgCollege) -> tuple[str, float] | None:
    if not student or not student.eapcet_rank:
        return None
    if c.girls_only and not student.female:
        return ("not eligible: it's a women's college", 99.0)
    seat = best_seat(b, student.eapcet_rank, student.ts_category or "OC", student.female)
    if not seat:
        return None
    col, closing = seat
    ratio = student.eapcet_rank / closing
    band = band_for(ratio)
    return (f"{band}: {student.name}'s EAPCET rank {n(student.eapcet_rank)} against {n(closing)} on the {seat_words(col)}", ratio)


def describe(c: TgCollege, b: TgBranch, student: Student | None) -> str:
    text = f"{b.short} at {c.short} ({profile(c)}). In the {SOURCE}, it {open_cutoff(b)}."
    ch = chance(student, b, c)
    if ch:
        text += f" {ch[0]}."
    elif student and not student.eapcet_rank:
        text += f" Tell me {student.name}'s TG EAPCET rank to check chances; JEE ranks don't apply here."
    return text


def _others_note(others: list[TgCollege], branch: str | None) -> str:
    if not others:
        return ""
    notes = []
    for o in others:
        ob = main_branch(o, branch)
        notes.append(f"{o.short} in {o.where}" + (f", where {ob.short} {open_cutoff(ob)}" if ob else ""))
    return " Note: the same name could also mean " + "; ".join(notes) + "."


def check(query: str, branch: str | None, student: Student | None) -> str | None:
    c, others, _ = tg_catalog().find(query)
    if not c:
        return None
    b = main_branch(c, branch)
    if not b:
        names = ", ".join(sorted({x.short for x in c.branches.values()}))
        return f"{c.short} doesn't list {branch} in TG EAPCET counselling. It offers: {names}."
    return describe(c, b, student) + _others_note(others, branch)


def compare(qa: str, qb: str, branch: str | None, student: Student | None) -> str | None:
    cat = tg_catalog()
    a, others_a, _ = cat.find(qa)
    b, others_b, _ = cat.find(qb)
    if not a or not b:
        return None
    ba, bb = main_branch(a, branch), main_branch(b, branch)
    if not ba or not bb:
        missing = a if not ba else b
        return f"{missing.short} doesn't offer {branch} in TG EAPCET counselling."
    text = (f"Comparing {ba.short} at {a.short} and {bb.short} at {b.short}, from the {SOURCE}. "
            f"First, {a.short}: {profile(a)}; it {open_cutoff(ba)}. "
            f"Second, {b.short}: {profile(b)}; it {open_cutoff(bb)}.")
    ka = ba.ranks.get("OC_BOYS") or ba.ranks.get("OC_GIRLS")
    kb = bb.ranks.get("OC_BOYS") or bb.ranks.get("OC_GIRLS")
    if ka and kb:
        harder, easier = (a, b) if ka < kb else (b, a)
        text += (f" {harder.short} is more competitive: its last rank is lower ({n(min(ka, kb))} against "
                 f"{n(max(ka, kb))}), which usually reflects stronger demand.")
    ca, cb = chance(student, ba, a), chance(student, bb, b)
    if ca and cb:
        text += f" For {student.name}: {a.short} is {ca[0][0].lower() + ca[0][1:]}; {b.short} is {cb[0][0].lower() + cb[0][1:]}."
        if abs(ca[1] - cb[1]) > 0.05:
            text += f" {(a if ca[1] < cb[1] else b).short} is the safer choice."
    elif student and not student.eapcet_rank:
        text += f" Tell me {student.name}'s TG EAPCET rank and I'll check chances at both."
    if a.girls_only or b.girls_only:
        text += " Keep in mind one of them admits women only."
    text += _others_note(others_a, branch) + _others_note(others_b, branch)
    return text


def predict(student: Student, branch: str | None, hyderabad_only: bool, per_band: int = 3) -> str:
    if not student.eapcet_rank:
        return (f"For Telangana state colleges I need {student.name}'s TG EAPCET rank. "
                f"JEE ranks are only used for JoSAA colleges.")
    bands: dict[str, list[tuple[float, int, TgCollege]]] = {"Safe": [], "Target": [], "Reach": []}
    for c in tg_catalog().colleges.values():
        if hyderabad_only and c.district not in HYDERABAD_AREA:
            continue
        b = main_branch(c, branch)
        if not b or (branch and not tg_catalog().branches(c, branch)):
            continue
        ch = chance(student, b, c)
        if not ch or ch[1] > 1.25:
            continue
        seat = best_seat(b, student.eapcet_rank, student.ts_category or "OC", student.female)
        bands[band_for(ch[1])].append((ch[1], seat[1] if seat else 0, c))
    bands["Safe"].sort(key=lambda x: x[1])          # most competitive first: the best you can safely get
    bands["Target"].sort(key=lambda x: x[0])
    bands["Reach"].sort(key=lambda x: x[0])
    what = (branch.upper() if branch and len(branch) <= 4 else branch or "CSE") + " "
    where = "Hyderabad-area" if hyderabad_only else "Telangana"
    lines = [f"From the {SOURCE}, {student.name}'s {what}options at {where} colleges with EAPCET rank "
             f"{n(student.eapcet_rank)}{' (' + student.ts_category.replace('_', '-') + ')' if student.ts_category else ''}."]
    for band, meaning in (("Safe", "comfortably inside last year's ranks"), ("Target", "around the last rank"),
                          ("Reach", "just outside it")):
        items = bands[band]
        if not items:
            lines.append(f"{band}: none.")
            continue
        top = "; ".join(c.short for _, _, c in items[:per_band])
        more = f", and {len(items) - per_band} more" if len(items) > per_band else ""
        lines.append(f"{band}, {meaning} ({len(items)}): {top}{more}.")
    lines.append("These use one year of data, so treat them as a guide.")
    return " ".join(lines)


def info(query: str) -> str | None:
    c, others, _ = tg_catalog().find(query)
    if not c:
        return None
    b = main_branch(c, None)
    branches = ", ".join(sorted({x.short for x in c.branches.values()}))
    text = f"{c.short}: {profile(c)}. Admission is through TG EAPCET counselling, not JoSAA."
    if b:
        text += f" Its {b.short} {open_cutoff(b)} in 2025."
    return text + f" Branches: {branches}." + _others_note(others, None)


def category_for(text: str | None) -> str | None:
    from .tgeapcet import ts_category
    return ts_category(text)


__all__ = ["check", "compare", "predict", "info", "category_for", "CATS"]

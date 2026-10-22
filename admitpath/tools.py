"""What each AdmitPath tool does and says. Answers are short spoken sentences that Alexa+ can read out."""

from __future__ import annotations

from dataclasses import replace

from . import store, terms
from . import tools_tg as tg
from .catalog import Institute, Program, catalog, not_in_josaa
from .tgeapcet import tg_catalog, ts_category
from .home_states import normalise_state
from .predict import Option, Student, evaluate, grouped, predict, trend_words

QUOTA_WORDS = {"AI": "all-India", "HS": "home-state", "OS": "other-state", "GO": "Goa", "JK": "Jammu and Kashmir",
               "LA": "Ladakh"}
KIND_WORDS = {"IIT": "IITs", "NIT": "NITs", "IIIT": "IIITs", "GFTI": "other government institutes"}
SOURCE = "Based on official JoSAA final-round closing ranks"


def n(x: int) -> str:
    return f"{x:,}"


def years_text() -> str:
    ys = catalog().years
    return f"{ys[0]} to {ys[-1]}" if len(ys) > 1 else str(ys[0])


def seat_words(o: Option) -> str:
    who = "girls-only" if o.gender.startswith("Female") else "gender-neutral"
    cat = "open" if o.seat_type == "OPEN" else o.seat_type
    return f"{QUOTA_WORDS.get(o.quota, o.quota)} {cat} {who} seat"


def describe(o: Option, with_trend: bool = True) -> str:
    latest_year = max(o.closings)
    text = (f"{o.label}: {o.band}. On the {seat_words(o)}, the closing rank was {n(o.closings[latest_year])} in "
            f"{latest_year}, so we expect about {n(o.expected)} this time, against {o.rank_label}.")
    if with_trend and len(o.closings) > 1:
        history = ", ".join(f"{n(v)} in {y}" for y, v in o.closings.items())
        text += f" Past closing ranks: {history}; {trend_words(o.closings)}."
    for note in o.notes:
        text += " " + note
    return text


def _student() -> Student | None:
    return store.current_student()


NO_STUDENT = ("I don't know the student's rank yet. Tell me their name, JEE Main rank, category and home state, "
              "for example: Riya, rank 15,000, OBC, from Telangana.")


def _category(text: str | None) -> str | None:
    if not text:
        return None
    t = text.strip().upper().replace(" ", "").replace("_", "-")
    if t in ("GEN", "GENERAL", "UR", "OPEN", "OC", "GN"):
        return "OPEN"
    if t.startswith("OBC") or t in ("BC", "NCL"):
        return "OBC-NCL"
    if t.startswith("EWS"):
        return "EWS"
    if t in ("SC", "ST"):
        return t
    return None


def is_state_college(query: str) -> bool:
    """True when the words name a Telangana state college (TG EAPCET) rather than a JoSAA institute."""
    if not query or not_in_josaa(query):
        return False
    college, _, strength = tg_catalog().find(query)
    if not college:
        return False
    if strength >= 3:
        return True
    return catalog().find_institute(query) is None


def _resolve(institute: str, branch: str | None) -> tuple[Institute | None, Program | None, str | None]:
    msg = not_in_josaa(institute)
    if msg:
        return None, None, msg
    cat = catalog()
    inst = cat.find_institute(institute)
    if not inst:
        return None, None, f"I couldn't find {institute} among JoSAA institutes. Try a name like NIT Warangal or IIT Bombay."
    if not branch:
        return inst, None, None
    progs = cat.match_programs(inst, branch)
    if not progs:
        return inst, None, f"{inst.short} doesn't offer {branch} through JoSAA. Ask me which branches it has."
    # Prefer the plain 4-year B.Tech over dual degrees and specialisations.
    progs.sort(key=lambda p: ("Bachelor of Technology" not in p.name and "B. Tech" not in p.name, len(p.name)))
    return inst, progs[0], None


# ---------------- student ----------------

def set_student(name: str | None = None, jee_main_rank: int | None = None, category: str | None = None,
                category_rank: int | None = None, gender: str | None = None, home_state: str | None = None,
                jee_advanced_rank: int | None = None, advanced_category_rank: int | None = None,
                pwd: bool | None = None, pwd_rank: int | None = None,
                eapcet_rank: int | None = None, telangana_category: str | None = None) -> str:
    current = _student()
    base = None
    if name and current and current.name.lower() != name.lower():
        base = store.get_student(name)
    elif current:
        base = current
    s = base or Student(name=name or "Student")
    updates = {}
    if name:
        updates["name"] = name.strip().title()
    if jee_main_rank:
        updates["main_rank"] = int(jee_main_rank)
    if category:
        cat = _category(category)
        if not cat:
            return f"I didn't understand the category {category}. Say general, EWS, OBC, SC or ST."
        updates["category"] = cat
    if category_rank:
        updates["main_category_rank"] = int(category_rank)
    if gender:
        updates["gender"] = "Female" if gender.lower().startswith(("f", "g", "w")) else "Male"
    if home_state:
        st = normalise_state(home_state)
        if not st:
            return f"I didn't recognise the state {home_state}. Say the state where the student passed class 12."
        updates["home_state"] = st
    if jee_advanced_rank:
        updates["adv_rank"] = int(jee_advanced_rank)
    if advanced_category_rank:
        updates["adv_category_rank"] = int(advanced_category_rank)
    if pwd is not None:
        updates["pwd"] = bool(pwd)
    if pwd_rank:
        updates["pwd_rank"] = int(pwd_rank)
    if eapcet_rank:
        updates["eapcet_rank"] = int(eapcet_rank)
    if telangana_category:
        tc = ts_category(telangana_category)
        if not tc:
            return (f"I didn't understand the Telangana category {telangana_category}. Say OC, BC-A, BC-B, BC-C, BC-D, "
                    f"BC-E, SC-I, SC-II, SC-III, ST or EWS.")
        updates["ts_category"] = tc
    elif category and "ts_category" not in updates and not s.ts_category:
        guess = {"OPEN": "OC", "EWS": "EWS", "ST": "ST"}.get(updates.get("category", ""))
        if guess:
            updates["ts_category"] = guess
    s = replace(s, **updates)
    store.save_student(s)

    parts = [f"Saved {s.name}"]
    if s.main_rank:
        parts.append(f"JEE Main rank {n(s.main_rank)}")
    if s.category != "OPEN":
        parts.append(s.category + (f" rank {n(s.main_category_rank)}" if s.main_category_rank else ""))
    parts.append("female" if s.female else "male")
    if s.home_state:
        parts.append(f"from {s.home_state}")
    if s.adv_rank:
        parts.append(f"JEE Advanced rank {n(s.adv_rank)}")
    if s.eapcet_rank:
        parts.append(f"TG EAPCET rank {n(s.eapcet_rank)}" + (f" ({s.ts_category.replace('_', '-')})" if s.ts_category else ""))
    text = ", ".join(parts) + "."
    if s.eapcet_rank and not s.ts_category:
        text += " For Telangana colleges, tell me the Telangana category, like OC, BC-B or SC-II."
    missing = []
    if not s.main_rank and not s.eapcet_rank:
        missing.append("a JEE Main rank (for JoSAA colleges) or a TG EAPCET rank (for Telangana colleges)")
    if s.main_rank and s.category != "OPEN" and not s.main_category_rank:
        missing.append(f"the {s.category} category rank, so I can check category seats too")
    if s.main_rank and not s.home_state:
        missing.append("the state where they passed class 12, for NIT home-state seats")
    if missing:
        text += " I still need " + " and ".join(missing) + "."
    if s.main_rank and not s.adv_rank:
        text += " IITs need a JEE Advanced rank; tell me if they have one."
    return text


def get_student() -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    return set_student()  # re-saves unchanged and reads the profile back


# ---------------- colleges ----------------

def _spoken(o: Option, branch_given: bool) -> str:
    """When one branch was asked for, say just the institute (plus 'dual degree' and the like when it differs)."""
    if not branch_given:
        return o.label
    short = o.program.short
    if "(B.Tech)" in short and not any(w in short.lower() for w in ("artificial", "data science", "(ai", "cyber", "iot")):
        return o.institute.short
    if short.endswith("(Dual Degree)") and short.count("(") == 1:
        return f"{o.institute.short} (dual degree)"
    return f"{o.institute.short}, {short}"


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def predict_colleges(branch: str | None = None, institute_type: str | None = None, per_band: int = 3) -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    kinds = None
    if institute_type:
        t = institute_type.upper().replace("TRIPLE IT", "IIIT").rstrip("S")
        kinds = {t} if t in KIND_WORDS else None
    g = grouped(predict(catalog(), s, branch, kinds))
    what = f"{branch} " if branch else ""
    where = KIND_WORDS[next(iter(kinds))] if kinds else "JoSAA colleges"
    total = sum(len(g[b]) for b in ("Safe", "Target", "Reach"))
    if not total:
        return (f"With {s.name}'s ranks I don't see realistic {what}options at {where} from past cutoffs. "
                f"Try another branch, or ask about CSAB special rounds and state counselling.")
    lines = [f"{SOURCE} from {years_text()}, here are {s.name}'s {what}options at {where}."]
    for band, meaning in (("Safe", "comfortably inside past cutoffs"), ("Target", "around the cutoff"),
                          ("Reach", "just outside last year's cutoff")):
        items = g[band]
        if not items:
            lines.append(f"{band}: none.")
            continue
        top = "; ".join(_spoken(o, bool(branch)) for o in items[:per_band])
        more = f", and {len(items) - per_band} more" if len(items) > per_band else ""
        lines.append(f"{band}, {meaning} ({len(items)}): {top}{more}.")
    if not s.adv_rank and (not kinds or "IIT" in kinds):
        lines.append("IITs aren't included because I don't have a JEE Advanced rank.")
    lines.append("Ask me about any one of them for the numbers.")
    return " ".join(lines)


def check_option(institute: str, branch: str | None = None) -> str:
    if is_state_college(institute):
        return tg.check(institute, branch, _student())
    branch = branch or "computer science"
    inst, prog, err = _resolve(institute, branch)
    if err:
        return err
    s = _student()
    if not s:
        return NO_STUDENT
    o = evaluate(s, inst, prog)
    if not o:
        if inst.kind == "IIT" and not s.adv_rank:
            return f"{inst.short} admits through JEE Advanced. Tell me {s.name}'s JEE Advanced rank and I'll check."
        return f"I couldn't find a seat at {prog.short}, {inst.short} that {s.name} is eligible for."
    return describe(o)


def compare_options(institute_a: str, branch_a: str | None, institute_b: str, branch_b: str | None) -> str:
    state_a, state_b = is_state_college(institute_a), is_state_college(institute_b)
    if state_a and state_b:
        return tg.compare(institute_a, institute_b, branch_a or branch_b, _student())
    if state_a or state_b:
        a = check_option(institute_a, branch_a or branch_b)
        b = check_option(institute_b, branch_b or branch_a)
        return (f"These two admit through different exams: JoSAA uses JEE ranks, and Telangana state colleges use "
                f"TG EAPCET ranks, so their cutoffs can't be compared directly. First, {a} Second, {b}")
    branch_a = branch_a or branch_b or "computer science"
    branch_b = branch_b or branch_a
    s = _student()
    if not s:
        return NO_STUDENT
    found = []
    for inst_q, br in ((institute_a, branch_a), (institute_b, branch_b)):
        inst, prog, err = _resolve(inst_q, br)
        if err:
            return err
        o = evaluate(s, inst, prog)
        if not o:
            return f"{s.name} isn't eligible for any seat at {prog.short}, {inst.short} with the ranks I have."
        found.append(o)
    a, b = found
    text = "First, " + describe(a) + " Second, " + describe(b)
    if a.band == b.band and abs(a.ratio - b.ratio) < 0.05:
        verdict = "Both look about equally likely, so choose by what the student wants to study and where."
    else:
        safer = a if a.ratio < b.ratio else b
        verdict = f"{safer.label} is the safer of the two."
    return text + " " + verdict + " In choice filling, put the one they'd rather join first; order doesn't hurt the other."


def cutoff_trend(institute: str, branch: str | None = None) -> str:
    if is_state_college(institute):
        return tg.check(institute, branch, _student()) + " Only the 2025 statement is published, so there's no trend yet."
    branch = branch or "computer science"
    inst, prog, err = _resolve(institute, branch)
    if err:
        return err
    s = _student()
    o = evaluate(s, inst, prog) if s else None
    if o:
        return describe(o)
    # no student yet: show the main open seat
    quota = "AI" if any(x.quota == "AI" for x in prog.seats) else "OS"
    seats = {x.year: x.closing for x in prog.seats if x.quota == quota and x.seat_type == "OPEN"
             and x.gender == "Gender-Neutral"}
    if not seats:
        return f"I don't have open-seat closing ranks for {prog.short} at {inst.short}."
    history = ", ".join(f"{n(v)} in {y}" for y, v in sorted(seats.items()))
    return (f"{prog.short} at {inst.short}, {QUOTA_WORDS.get(quota)} open gender-neutral seat: closing ranks "
            f"{history}; {trend_words(seats)}.")


def college_info(college: str) -> str:
    if is_state_college(college):
        return tg.info(college)
    inst, _, err = _resolve(college, None)
    if err:
        return err
    kind = {"IIT": "an IIT", "NIT": "an NIT", "IIIT": "an IIIT", "GFTI": "a centrally funded institute"}[inst.kind]
    return (f"{inst.name} is {kind}, admitting through JoSAA with "
            f"{'JEE Advanced' if inst.kind == 'IIT' else 'JEE Main'} ranks. " + find_programs(college))


def predict_telangana_colleges(branch: str | None = None, hyderabad_only: bool = False, per_band: int = 3) -> str:
    s = _student()
    if not s:
        return NO_STUDENT.replace("JEE Main rank", "TG EAPCET rank")
    return tg.predict(s, branch, hyderabad_only, per_band)


def find_programs(institute: str) -> str:
    if is_state_college(institute):
        return tg.info(institute)
    inst, _, err = _resolve(institute, None)
    if err:
        return err
    progs = catalog().match_programs(inst, None)
    names = sorted({p.short for p in progs})
    return f"{inst.short} offers {len(names)} programs through JoSAA: " + "; ".join(names) + "."


# ---------------- choice list ----------------

def _choice_lines(s: Student) -> list[str]:
    cat = catalog()
    lines = []
    for i, (inst_name, prog_name) in enumerate(store.choices(s.name), start=1):
        inst = cat.institutes.get(inst_name)
        prog = inst.programs.get(prog_name) if inst else None
        o = evaluate(s, inst, prog) if prog else None
        band = o.band if o else "not eligible"
        lines.append(f"{i}. {(prog.short if prog else prog_name)} at {(inst.short if inst else inst_name)} ({band})")
    return lines


def read_choices() -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    lines = _choice_lines(s)
    if not lines:
        return f"{s.name}'s choice list is empty. Say, for example, add CSE at NIT Warangal."
    bands = [l.rsplit("(", 1)[1].rstrip(")") for l in lines]
    tip = ""
    if "Safe" not in bands:
        tip = " There's no safe option yet; add a few lower down so a seat is guaranteed."
    return f"{s.name}'s choices, in order: " + " ".join(lines) + "." + tip


def add_choice(institute: str, branch: str, position: int | None = None) -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    inst, prog, err = _resolve(institute, branch)
    if err:
        return err
    items = store.choices(s.name)
    entry = (inst.name, prog.name)
    if entry in items:
        items.remove(entry)
    pos = len(items) if not position else max(0, min(position - 1, len(items)))
    items.insert(pos, entry)
    store.set_choices(s.name, items)
    o = evaluate(s, inst, prog)
    band = f" It's {_article(o.band)} {o.band.lower()} option." if o else ""
    return f"Added {prog.short} at {inst.short} as choice {pos + 1} of {len(items)}.{band}"


def remove_choice(position: int) -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    items = store.choices(s.name)
    if not 1 <= position <= len(items):
        return f"There's no choice number {position}. The list has {len(items)}."
    inst_name, prog_name = items.pop(position - 1)
    store.set_choices(s.name, items)
    return f"Removed choice {position}. {len(items)} left."


def move_choice(from_position: int, to_position: int) -> str:
    s = _student()
    if not s:
        return NO_STUDENT
    items = store.choices(s.name)
    if not 1 <= from_position <= len(items):
        return f"There's no choice number {from_position}. The list has {len(items)}."
    entry = items.pop(from_position - 1)
    to = max(1, min(to_position, len(items) + 1))
    items.insert(to - 1, entry)
    store.set_choices(s.name, items)
    return f"Moved it to number {to}. " + read_choices()


# ---------------- process ----------------

def explain_term(term: str) -> str:
    text = terms.explain(term)
    if text:
        return text
    return ("I can explain freeze, float, slide, seat acceptance, withdrawal, choice filling, mock allotment, "
            "home-state and other-state quota, category rank, female supernumerary seats, eligibility, CSAB and reporting.")


def whats_next(step: str | None = None) -> str:
    steps = terms.STEPS
    if step:
        for i, (name, what) in enumerate(steps):
            if step.lower() in name.lower():
                nxt = steps[i + 1] if i + 1 < len(steps) else None
                return f"{name}: {what}" + (f" Next comes {nxt[0].lower()}: {nxt[1]}" if nxt else "")
    lines = [f"{i}. {name}: {what}" for i, (name, what) in enumerate(steps, start=1)]
    return "JoSAA usually goes like this. " + " ".join(lines) + " Dates change every year, so check josaa.nic.in."

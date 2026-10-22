"""Plain-language explanations of JoSAA counselling terms, and the usual order of steps.

Written from the JoSAA business rules. Fees and dates change every year, so answers point to josaa.nic.in for those.
"""

TERMS = {
    "freeze": ("Freeze means you accept the seat you've been given and stop. You won't be considered for any "
               "higher choice in later rounds. Choose it when you're happy with the seat."),
    "float": ("Float means you accept the seat you've been given, but you still want to be upgraded to any higher "
              "choice, at any institute, in later rounds. If you get a better seat, you move automatically and lose the "
              "old one. If not, you keep the current seat."),
    "slide": ("Slide means you accept the seat you've been given, but you only want an upgrade to a higher choice in "
              "the same institute, for example from ECE to CSE at the same NIT. You keep the institute either way."),
    "seat acceptance": ("After a seat is allotted, you must accept it online in time: pay the seat acceptance fee, "
                        "upload documents, answer any document queries, and choose freeze, float or slide. If you "
                        "don't, the seat is cancelled and you leave the process. Check josaa.nic.in for this year's fee."),
    "withdraw": ("You can withdraw your seat during the withdrawal window of certain rounds; part of the fee is "
                 "refunded. After withdrawing you're out of JoSAA for that year, so only do it if you've chosen "
                 "another college. Check the current rules on josaa.nic.in."),
    "choice filling": ("Choice filling is your ordered wish list of institute and branch pairs. There's no limit on the "
                       "number of choices, and order matters: you get the highest choice your rank allows. Put the "
                       "ones you'd really join first, and add safe options lower down."),
    "mock allotment": ("JoSAA runs mock allotments on the choices filled by certain dates. They show where you might "
                       "land, so you can reorder choices before locking them. They aren't final seats."),
    "home state quota": ("For NITs, half the seats go to students from the institute's home state and half to other "
                         "states. Your home state is the state where you passed class 12, not where you were born."),
    "other state quota": ("Other-state (OS) quota is the half of NIT seats for students whose class 12 state is "
                          "different from the institute's state."),
    "all india quota": ("All-India (AI) quota seats are open to everyone regardless of state. IITs, IIITs and most "
                        "other institutes fill all their seats this way."),
    "crl": ("CRL is the common rank list: your overall rank among all candidates. OPEN seats use the CRL rank."),
    "category rank": ("Your category rank is your position among candidates of your category: EWS, OBC-NCL, SC or ST. "
                      "Category seats are filled using category ranks, so an OBC-NCL student competes for OPEN seats "
                      "with the CRL rank and for OBC-NCL seats with the category rank, whichever is better."),
    "opening and closing rank": ("The opening rank is the best rank admitted to a seat, and the closing rank is the "
                                 "last rank admitted in the final round. If your rank is better than (smaller than) "
                                 "last year's closing rank, you have a good chance."),
    "female supernumerary": ("Female-only (supernumerary) seats are extra seats created for girls. Female students "
                             "compete for both these and the gender-neutral seats, so their chances are better."),
    "pwd": ("PwD seats are reserved for persons with benchmark disabilities, within each category. They use the PwD rank."),
    "eligibility": ("Besides rank, NITs, IIITs, IITs and other JoSAA institutes generally need at least 75 percent in "
                    "class 12 (65 percent for SC and ST), or a place in the top 20 percentile of your board. Check the "
                    "current rules on josaa.nic.in."),
    "csab": ("After JoSAA ends, CSAB runs special rounds to fill vacant seats at NITs, IIITs and other institutes "
             "(not IITs). Students who didn't get a seat, or want another chance, can register."),
    "reporting": ("Reporting means joining the institute in person on the dates it announces, with original documents. "
                  "Your admission isn't complete until you report."),
    "preparatory course": ("Preparatory ranks are for SC, ST and PwD students just below the IIT cutoff: a one-year "
                           "preparatory course, after which they can join the B.Tech."),
    "rounds": ("JoSAA allots seats in several rounds, usually five or six. After each round you accept with freeze, "
               "float or slide; later rounds can upgrade floating and sliding students as seats open up."),
}

ALIASES = {
    "freezing": "freeze", "floating": "float", "sliding": "slide", "saf": "seat acceptance",
    "seat acceptance fee": "seat acceptance", "accept seat": "seat acceptance", "accepting": "seat acceptance",
    "withdrawal": "withdraw", "choices": "choice filling", "choice list": "choice filling", "mock": "mock allotment",
    "hs": "home state quota", "home state": "home state quota", "os": "other state quota", "other state": "other state quota",
    "ai quota": "all india quota", "all india": "all india quota", "common rank": "crl", "common rank list": "crl",
    "opening rank": "opening and closing rank", "closing rank": "opening and closing rank", "cutoff": "opening and closing rank",
    "supernumerary": "female supernumerary", "female only": "female supernumerary", "female seats": "female supernumerary",
    "75 percent": "eligibility", "75%": "eligibility", "board marks": "eligibility", "class 12 marks": "eligibility",
    "special rounds": "csab", "report": "reporting", "prep": "preparatory course", "round": "rounds",
}

STEPS = [
    ("Registration and choice filling", "Register on the JoSAA portal after JEE Advanced results and fill your ordered choices."),
    ("Mock allotments", "Two mock allotments show where you might land. Reorder your choices based on them."),
    ("Lock choices", "Choices are locked on the last day of choice filling. After that they can't change."),
    ("Round 1 allotment", "Seats are allotted from your choices and your rank."),
    ("Seat acceptance", "Pay the seat acceptance fee, upload documents, and choose freeze, float or slide before the deadline."),
    ("Later rounds", "Rounds 2 to 5 or 6 can upgrade floating and sliding students. Check results after every round."),
    ("Reporting", "Report to the institute with original documents on the announced dates."),
    ("CSAB special rounds", "If seats at NITs, IIITs and others are left, CSAB runs extra rounds afterwards."),
]


def explain(term: str) -> str | None:
    t = " ".join(term.lower().replace("?", "").split())
    if t in TERMS:
        return TERMS[t]
    if t in ALIASES:
        return TERMS[ALIASES[t]]
    for key in sorted(ALIASES, key=len, reverse=True):
        if key in t:
            return TERMS[ALIASES[key]]
    for key in TERMS:
        if key in t:
            return TERMS[key]
    return None

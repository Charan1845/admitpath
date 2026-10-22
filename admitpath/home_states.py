"""Which state's students get the home-state (HS) quota at each institute that has one.

JoSAA's rank tables don't list locations, so this is maintained by hand from the institutes' locations.
Keys are matched against the start of the normalised institute name.
Special cases: NIT Goa (GO quota for Goa; HS for Dadra and Nagar Haveli and Daman and Diu) and
NIT Srinagar (JK quota for Jammu and Kashmir, LA for Ladakh).
"""

HOME_STATE = {
    "assam university, silchar": ["Assam"],
    "birla institute of technology, deoghar": ["Jharkhand"],
    "birla institute of technology, mesra": ["Jharkhand"],
    "birla institute of technology, patna": ["Bihar"],
    "dr. b r ambedkar national institute of technology, jalandhar": ["Punjab"],
    "ghani khan choudhary institute of engineering and technology": ["West Bengal"],
    "indian institute of engineering science and technology, shibpur": ["West Bengal"],
    "institute of chemical technology, mumbai: indian oil odisha campus": ["Odisha"],
    "islamic university of science and technology kashmir": ["Jammu and Kashmir"],
    "malaviya national institute of technology jaipur": ["Rajasthan"],
    "maulana azad national institute of technology bhopal": ["Madhya Pradesh"],
    "motilal nehru national institute of technology allahabad": ["Uttar Pradesh"],
    "national institute of technology agartala": ["Tripura"],
    "national institute of technology arunachal pradesh": ["Arunachal Pradesh"],
    "national institute of technology calicut": ["Kerala", "Lakshadweep"],
    "national institute of technology delhi": ["Delhi"],
    "national institute of technology durgapur": ["West Bengal"],
    "national institute of technology goa": ["Dadra and Nagar Haveli and Daman and Diu"],
    "national institute of technology hamirpur": ["Himachal Pradesh"],
    "national institute of technology karnataka, surathkal": ["Karnataka"],
    "national institute of technology meghalaya": ["Meghalaya"],
    "national institute of technology nagaland": ["Nagaland"],
    "national institute of technology patna": ["Bihar"],
    "national institute of technology puducherry": ["Puducherry"],
    "national institute of technology raipur": ["Chhattisgarh"],
    "national institute of technology sikkim": ["Sikkim"],
    "national institute of technology, andhra pradesh": ["Andhra Pradesh"],
    "national institute of technology, jamshedpur": ["Jharkhand"],
    "national institute of technology, kurukshetra": ["Haryana"],
    "national institute of technology, manipur": ["Manipur"],
    "national institute of technology, mizoram": ["Mizoram"],
    "national institute of technology, rourkela": ["Odisha"],
    "national institute of technology, silchar": ["Assam"],
    "national institute of technology, tiruchirappalli": ["Tamil Nadu"],
    "national institute of technology, uttarakhand": ["Uttarakhand"],
    "national institute of technology, warangal": ["Telangana"],
    "puducherry technological university": ["Puducherry"],
    "punjab engineering college": ["Chandigarh"],
    "sardar vallabhbhai national institute of technology": ["Gujarat"],
    "visvesvaraya national institute of technology": ["Maharashtra"],
}

# Quotas other than HS that belong to one state or UT.
SPECIAL_QUOTA = {
    "national institute of technology goa": {"GO": ["Goa"]},
    "national institute of technology, srinagar": {"JK": ["Jammu and Kashmir"], "LA": ["Ladakh"]},
}

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

STATE_ALIASES = {
    "ap": "Andhra Pradesh", "andhra": "Andhra Pradesh", "ts": "Telangana", "tg": "Telangana", "up": "Uttar Pradesh",
    "mp": "Madhya Pradesh", "hp": "Himachal Pradesh", "tn": "Tamil Nadu", "wb": "West Bengal", "bengal": "West Bengal",
    "jk": "Jammu and Kashmir", "j&k": "Jammu and Kashmir", "kashmir": "Jammu and Kashmir", "new delhi": "Delhi",
    "nct of delhi": "Delhi", "orissa": "Odisha", "pondicherry": "Puducherry", "daman": "Dadra and Nagar Haveli and Daman and Diu",
    "uk": "Uttarakhand", "uttaranchal": "Uttarakhand", "cg": "Chhattisgarh", "mh": "Maharashtra", "ka": "Karnataka",
}


def normalise_state(name: str | None) -> str | None:
    if not name:
        return None
    low = " ".join(name.lower().replace("&", "and").split())
    if low in STATE_ALIASES:
        return STATE_ALIASES[low]
    for s in STATES:
        if s.lower() == low:
            return s
    for s in STATES:                              # "telangana state" -> Telangana
        if s.lower() in low or low in s.lower():
            return s
    return None

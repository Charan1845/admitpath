import pytest
from starlette.testclient import TestClient

from admitpath import store, tools
from admitpath.catalog import branch_key, catalog, not_in_josaa
from admitpath.predict import Student, band_for, evaluate, expected_closing, predict, quotas_for


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


C = catalog()


def inst(q):
    i = C.find_institute(q)
    assert i is not None, q
    return i


# ---------------- data and matching ----------------

def test_data_covers_three_years_and_all_institute_types():
    assert C.years == [2023, 2024, 2025]
    kinds = {i.kind for i in C.institutes.values()}
    assert kinds == {"IIT", "NIT", "IIIT", "GFTI"}
    assert len(C.institutes) >= 120


@pytest.mark.parametrize("spoken,official", [
    ("NIT Warangal", "National Institute of Technology, Warangal"),
    ("nitw", "National Institute of Technology, Warangal"),
    ("NIT Trichy", "National Institute of Technology, Tiruchirappalli"),
    ("IIT Bombay", "Indian Institute of Technology Bombay"),
    ("iitb", "Indian Institute of Technology Bombay"),
    ("IIT kgp", "Indian Institute of Technology Kharagpur"),
    ("triple IT Allahabad", "Indian Institute of Information Technology, Allahabad"),
    ("NIT Surathkal", "National Institute of Technology Karnataka, Surathkal"),
    ("MNNIT", "Motilal Nehru National Institute of Technology Allahabad"),
    ("NIT AP", "National Institute of Technology, Andhra Pradesh"),
])
def test_spoken_institute_names(spoken, official):
    assert inst(spoken).name == official


def test_colleges_outside_josaa_get_a_clear_answer():
    assert "not JoSAA" in not_in_josaa("IIIT Hyderabad")
    assert "JAC Delhi" in tools.check_option("IIIT Delhi", "CSE")


@pytest.mark.parametrize("spoken,key", [("CSE", "computer science"), ("ECE", "electronics"), ("AI ML", "artificial intelligence"),
                                        ("mech", "mechanical"), ("IT", "information technology")])
def test_branch_words(spoken, key):
    assert branch_key(spoken) == key


# ---------------- rules ----------------

def test_home_state_quota_goes_to_class_12_state():
    w = inst("NIT Warangal")
    assert quotas_for(w, {"HS", "OS"}, "Telangana") == ["HS"]
    assert quotas_for(w, {"HS", "OS"}, "Kerala") == ["OS"]
    assert quotas_for(inst("IIT Bombay"), {"AI"}, "Maharashtra") == ["AI"]


def test_special_quotas_for_goa_and_srinagar():
    assert quotas_for(inst("NIT Goa"), {"GO", "HS", "OS"}, "Goa") == ["GO"]
    assert quotas_for(inst("NIT Goa"), {"GO", "HS", "OS"}, "Dadra and Nagar Haveli and Daman and Diu") == ["HS"]
    assert quotas_for(inst("NIT Srinagar"), {"JK", "LA", "OS"}, "Jammu and Kashmir") == ["JK"]


def test_expected_closing_follows_trend_but_is_clipped():
    assert expected_closing({2025: 1000}) == 1000
    assert expected_closing({2023: 800, 2024: 900, 2025: 1000}) > 1000          # getting easier
    assert expected_closing({2023: 100, 2024: 1000, 2025: 2000}) == 2300        # trend clipped at +15%


def test_bands():
    assert [band_for(r) for r in (0.5, 0.85, 1.0, 1.2, 1.3)] == ["Safe", "Safe", "Target", "Reach", "Unlikely"]


def test_category_and_female_seats_are_used_when_better():
    w = inst("NIT Warangal")
    prog = C.match_programs(w, "cse")[0]
    open_boy = evaluate(Student(main_rank=15000, home_state="Telangana"), w, prog)
    obc_girl = evaluate(Student(main_rank=15000, main_category_rank=3500, category="OBC-NCL", gender="Female",
                                home_state="Telangana"), w, prog)
    assert open_boy.quota == obc_girl.quota == "HS"
    assert obc_girl.ratio < open_boy.ratio
    assert obc_girl.seat_type in ("OBC-NCL", "OPEN")


def test_iits_need_an_advanced_rank():
    s = Student(main_rank=500)
    assert not any(o.institute.kind == "IIT" for o in predict(C, s, "cse"))
    s.adv_rank = 300
    assert any(o.institute.kind == "IIT" for o in predict(C, s, "cse"))


def test_a_top_rank_finds_top_options_safe_and_a_low_rank_does_not():
    top = predict(C, Student(main_rank=200, home_state="Telangana"), "cse", {"NIT"})
    assert any(o.institute.short == "NIT Tiruchirappalli" and o.band == "Safe" for o in top)
    low = predict(C, Student(main_rank=900000, home_state="Telangana"), "cse", {"NIT"})
    assert not low


# ---------------- tools (what Alexa+ hears) ----------------

def test_tools_need_a_student_first():
    assert "rank" in tools.predict_colleges("cse")


def test_full_conversation():
    out = tools.set_student("riya", 15000, "OBC", None, "Female", "TS")
    assert "Riya" in out and "Telangana" in out and "OBC-NCL category rank" in out
    assert "OBC-NCL rank 3,500" in tools.set_student(category_rank=3500)

    pred = tools.predict_colleges("CSE", "NIT")
    assert "Safe" in pred and "Target" in pred and "official JoSAA" in pred

    chk = tools.check_option("NIT Warangal", "CSE")
    assert "NIT Warangal" in chk and "home-state" in chk and "Past closing ranks" in chk

    cmp = tools.compare_options("NIT Warangal", "CSE", "NIT Trichy", "ECE")
    assert "safer" in cmp or "equally" in cmp

    assert "choice 1 of 1" in tools.add_choice("NIT Warangal", "CSE")
    assert "choice 1 of 2" in tools.add_choice("IIIT Allahabad", "IT", position=1)
    assert tools.read_choices().index("IIIT Allahabad") < tools.read_choices().index("NIT Warangal")
    moved = tools.move_choice(2, 1)
    assert moved.index("NIT Warangal") < moved.index("IIIT Allahabad")
    assert "1 left" in tools.remove_choice(2)


def test_explanations():
    assert "higher choice" in tools.explain_term("what does float mean")
    assert "same institute" in tools.explain_term("slide")
    assert "class 12" in tools.explain_term("home state")
    assert "seat acceptance" in tools.whats_next("round 1").lower()


# ---------------- over MCP ----------------

def rpc(client, method, params=None, id_=1):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}},
                    headers={"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"})
    assert r.status_code == 200, r.text
    return r.json()


def test_mcp_tools_list_and_call():
    from admitpath.server import build_app
    with TestClient(build_app(), base_url="http://localhost:8000") as client:
        init = rpc(client, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                          "clientInfo": {"name": "test", "version": "1"}})
        assert init["result"]["serverInfo"]["name"] == "admitpath"
        names = {t["name"] for t in rpc(client, "tools/list")["result"]["tools"]}
        assert {"set_student", "predict_colleges", "check_option", "compare_options", "add_choice",
                "explain_term"} <= names and len(names) == 13
        out = rpc(client, "tools/call", {"name": "explain_term", "arguments": {"term": "freeze"}})
        assert "accept the seat" in out["result"]["content"][0]["text"]
        assert client.get("/healthz").json()["years"] == [2023, 2024, 2025]
        page = client.get("/")
        assert page.status_code == 200 and "Alexa+" in page.text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/../server.py").status_code == 404

// Simulated Alexa+ for the AdmitPath add-on.
// Real Alexa+ uses its own AI to pick an MCP tool and its arguments. Here a small intent parser does that job,
// and every answer comes from a real MCP tools/call to the AdmitPath server (JSON-RPC over Streamable HTTP).
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var PROTOCOL = "2025-11-25";

  // ---------------- MCP client ----------------
  var rpcId = 0;
  function rpc(method, params) {
    var request = { jsonrpc: "2.0", id: ++rpcId, method: method, params: params || {} };
    var t0 = performance.now();
    return fetch("/mcp", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL },
      body: JSON.stringify(request)
    }).then(function (r) {
      var type = r.headers.get("content-type") || "";
      return (type.indexOf("text/event-stream") >= 0
        ? r.text().then(function (t) {
            var line = t.split("\n").filter(function (l) { return l.indexOf("data:") === 0; }).pop() || "data: {}";
            return JSON.parse(line.slice(5));
          })
        : r.json());
    }).then(function (response) {
      return { request: request, response: response, ms: Math.round(performance.now() - t0) };
    });
  }

  function callTool(name, args) {
    return rpc("tools/call", { name: name, arguments: args }).then(function (out) {
      trace(out, name);
      var res = out.response.result || {};
      if (out.response.error) throw new Error(out.response.error.message);
      out.text = (res.content || []).filter(function (c) { return c.type === "text"; }).map(function (c) { return c.text; }).join("\n");
      return out;
    });
  }

  // ---------------- understanding what was said ----------------
  var STATES = ["andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana",
    "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "orissa", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal", "chandigarh", "delhi", "jammu and kashmir", "ladakh", "puducherry",
    "pondicherry", "lakshadweep", "andaman and nicobar islands"];
  var BRANCHES = [
    ["mathematics and computing", "maths and computing"], ["maths and computing", "maths and computing"],
    ["math and computing", "maths and computing"], ["computer science", "computer science"], ["cse", "CSE"],
    ["artificial intelligence", "AI"], ["data science", "data science"], ["ai ml", "AI"], ["aiml", "AI"],
    ["information technology", "IT"], ["electronics and communication", "ECE"], ["electronics", "ECE"], ["ece", "ECE"],
    ["eee", "EEE"], ["electrical", "electrical"], ["mechanical", "mechanical"], ["mech", "mechanical"], ["civil", "civil"],
    ["chemical", "chemical"], ["aerospace", "aerospace"], ["biotech", "biotechnology"], ["metallurgy", "metallurgy"],
    ["engineering physics", "engineering physics"], ["architecture", "architecture"]
  ];
  var NICKNAMES = ["nitw", "nitk", "nitt", "nitc", "nitr", "mnnit", "vnit", "svnit", "manit", "mnit", "iiest", "pec",
    "bit mesra", "iitb", "iitd", "iitm", "iitk", "iitkgp", "iith", "iitr", "iitg", "iit bhu", "ism dhanbad", "iiita", "iiitm",
    "iiith", "iiitd", "iiitb", "dtu", "nsut", "bits pilani", "bits", "vit"];
  // Telangana state colleges (TG EAPCET counselling). Longer names first.
  var STATE_COLLEGES = ["chaitanya bharathi", "b v raju", "bv raju", "vnr vjiet", "vnrvjiet", "vignana jyothi", "keshav memorial",
    "mahatma gandhi institute", "gokaraju rangaraju", "malla reddy", "marri laxman", "nalla malla", "guru nanak",
    "g narayanamma", "gnits", "vignana bharathi", "cbit", "bvrit", "vnr", "vasavi", "mgit", "griet", "gokaraju", "cvr", "kmit",
    "iare", "vardhaman", "anurag", "cmrit", "cmr", "mlrit", "jntuh", "jntu", "kits", "matrusri", "methodist", "stanley",
    "vbit", "geethanjali", "mrec", "aurora", "st martins"];
  var PLACE_WORDS = ["hyderabad", "narsapur", "bachupally", "women", "girls", "gandipet", "kukatpally", "medchal", "jagitial",
    "warangal", "manthani", "sultanpur", "hyd", "campus"];

  var STOP = { can: 1, for: 1, does: 1, have: 1, has: 1, with: 1, are: 1, will: 1, she: 1, he: 1, i: 1, we: 1, offer: 1,
    or: 1, and: 1, vs: 1, versus: 1, to: 1, at: 1, in: 1, the: 1, her: 1, his: 1, is: 1, cse: 1, ece: 1, eee: 1, it: 1,
    computer: 1, electrical: 1, electronics: 1, mechanical: 1, civil: 1, chemical: 1, cutoff: 1, cut: 1, list: 1, top: 1,
    get: 1, about: 1, safe: 1, branches: 1, programs: 1, courses: 1, ai: 1, data: 1, mech: 1, what: 1, how: 1, s: 1 };
  var TERMS = ["seat acceptance", "choice filling", "mock allotment", "home state", "other state", "all india",
    "category rank", "closing rank", "opening rank", "cutoff", "supernumerary", "female seats", "female only", "eligibility",
    "75 percent", "preparatory", "withdraw", "freeze", "float", "slide", "csab", "reporting", "crl", "pwd", "rounds", "round"];

  function clean(raw) {
    return raw.toLowerCase().replace(/[’']/g, "'")
      .replace(/(\d),(?=\d{3}\b)/g, "$1")
      .replace(/(\d+(?:\.\d+)?)\s*(k|thousand)\b/g, function (_, n) { return String(Math.round(parseFloat(n) * 1000)); })
      .replace(/(\d+(?:\.\d+)?)\s*lakh\b/g, function (_, n) { return String(Math.round(parseFloat(n) * 100000)); })
      .replace(/\b(hyderbad|hydrabad|hyderbaad|hyderabd|hydarabad|hyd)\b/g, "hyderabad")
      .replace(/\b(clg|colg|collage)\b/g, "college").replace(/\bu\b/g, "you")
      .replace(/\bc ?b ?i ?t\b/g, "cbit").replace(/\bb ?v ?r ?i ?t\b/g, "bvrit").replace(/\bv ?n ?r\b/g, "vnr")
      .replace(/\btriple ?i ?t\b/g, "iiit").replace(/\bi i i t\b/g, "iiit").replace(/\bi i t\b/g, "iit").replace(/\bn i t\b/g, "nit")
      .replace(/\s+/g, " ").trim();
  }

  function findBranch(t, raw) {
    for (var i = 0; i < BRANCHES.length; i++) {
      if (new RegExp("\\b" + BRANCHES[i][0] + "\\b").test(t)) return BRANCHES[i][1];
    }
    if (/\bIT\b/.test(raw || "")) return "IT";
    return null;
  }

  function findInstitutes(t) {
    var found = [], m, re = /\b(iiit|iit|nit)\s+([a-z]+)(?:\s+([a-z]+))?/g;
    while ((m = re.exec(t))) {
      if (STOP[m[2]]) continue;
      var name = m[1] + " " + m[2] + (m[3] && !STOP[m[3]] ? " " + m[3] : "");
      found.push({ name: name, at: m.index });
    }
    NICKNAMES.forEach(function (n) {
      var r = new RegExp("\\b" + n + "\\b", "g"), mm;
      while ((mm = r.exec(t))) {
        var covered = found.some(function (f) { return mm.index >= f.at && mm.index < f.at + f.name.length; });
        if (!covered) found.push({ name: n, at: mm.index });
      }
    });
    STATE_COLLEGES.forEach(function (n) {
      var r = new RegExp("\\b" + n + "\\b", "g"), mm;
      while ((mm = r.exec(t))) {
        var covered = found.some(function (f) { return mm.index >= f.at && mm.index < f.at + f.span; });
        if (covered) continue;
        // keep words like "in Hyderabad", "Narsapur" or "women" that tell apart campuses with the same name
        var tail = t.slice(mm.index + n.length).split(/\b(?:and|or|vs|versus|with)\b/)[0].split(" ").slice(0, 4);
        var extra = tail.filter(function (w) { return PLACE_WORDS.indexOf(w) >= 0; });
        found.push({ name: n + (extra.length ? " " + extra.join(" ") : ""), at: mm.index, span: n.length, state: true });
      }
    });
    found.forEach(function (f) { if (!f.span) f.span = f.name.length; });
    found.sort(function (a, b) { return a.at - b.at; });
    lastFoundState = found.map(function (f) { return !!f.state; });
    return found.map(function (f) { return f.name; });
  }
  var lastFoundState = [];

  function findTerm(t) {
    for (var i = 0; i < TERMS.length; i++) if (t.indexOf(TERMS[i]) >= 0) return TERMS[i];
    return null;
  }

  function parseProfile(t, raw) {
    var args = {};
    var nameM = raw.match(/\b(?:[Mm]y (?:daughter|son|child|kid|sister|brother)|[Ss]tudent(?:'s)? name is|[Nn]ame is|[Tt]his is)\s+([A-Z][a-z]+)/)
      || raw.match(/^\s*([A-Z][a-z]+)\s+(?:got|has|scored|secured|is|ranked)\b/);
    if (nameM && !/^(She|He|Alexa|What|Which|Can|My|Her|His|The)$/.test(nameM[1])) args.name = nameM[1];
    if (/\b(she|her|daughter|girl|sister)\b/.test(t)) args.gender = "Female";
    else if (/\b(he|his|son|boy|brother)\b/.test(t)) args.gender = "Male";
    var cat = t.match(/\b(general|gen|open|ews|obc|sc|st)\b/);
    if (cat) args.category = { general: "GENERAL", gen: "GENERAL", open: "OPEN", ews: "EWS", obc: "OBC", sc: "SC", st: "ST" }[cat[1]];
    var tc = t.match(/\b(bc|sc)[\s_-]?([a-e]|iii|ii|i|1|2|3)\b/);
    if (tc) args.telangana_category = (tc[1] + "-" + tc[2]).toUpperCase();
    else if (/\boc\b/.test(t)) args.telangana_category = "OC";
    var re = /\d{2,7}/g, m;
    while ((m = re.exec(t))) {
      var n = parseInt(m[0], 10), before = t.slice(Math.max(0, m.index - 28), m.index), after = t.slice(m.index, m.index + 24);
      if (/round\s*$|choice\s*$|number\s*$|class\s*$|in\s*$/.test(before) && !/rank|main|advanced|eapcet|eamcet/.test(before)) continue;
      if (/20\d\d/.test(m[0]) && m[0].length === 4 && /\bin\s*$/.test(before)) continue;
      if (/eapcet|eamcet/.test(before) || /^\d+\s*(in )?(the )?(ts |tg )?(eapcet|eamcet)/.test(after)) { args.eapcet_rank = n; continue; }
      if (/advanced/.test(before) || /^\d+\s*(in )?(jee )?advanced/.test(after)) { if (/obc|ews|sc|st|category/.test(before.slice(-14))) args.advanced_category_rank = n; else args.jee_advanced_rank = n; }
      else if (/\b(obc|ews|sc|st|category)\b[^\d]*$/.test(before) || /^\d+\s*in (obc|ews|sc|st|category)/.test(after)) args.category_rank = n;
      else if (!args.jee_main_rank) args.jee_main_rank = n;
    }
    for (var i = 0; i < STATES.length; i++) {
      if (new RegExp("\\b" + STATES[i] + "\\b").test(t)) { args.home_state = STATES[i]; break; }
    }
    return args;
  }

  var ctx = { inst: null, branch: null, lastOption: null };

  function plan(raw) {
    var t = clean(raw);
    var insts = findInstitutes(t), branch = findBranch(t, raw);
    if (insts.length) ctx.inst = insts[0];
    if (branch) ctx.branch = branch;
    var type = (t.match(/\b(iiits|iits|nits|gftis?)\b/) || [])[1];
    var instType = type ? { iiits: "IIIT", iits: "IIT", nits: "NIT", gfti: "GFTI", gftis: "GFTI" }[type] : null;

    // choice list
    if (/\b(read|show|tell me|what('s| is| are))\b.*\b(list|choices)\b|^(her|his|my) (list|choices)$/.test(t) && !/\badd\b/.test(t)) return [["read_choices", {}]];
    var rm = t.match(/\b(remove|delete|drop)\b.*?(\d+)/);
    if (rm && /choice|number|list/.test(t)) return [["remove_choice", { position: +rm[2] }]];
    var mv = t.match(/\bmove\b.*?(\d+).*?\b(?:to|at)\b\s*(?:number\s*)?(\d+|the top|top|first)/);
    if (mv) return [["move_choice", { from_position: +mv[1], to_position: /top|first/.test(mv[2]) ? 1 : +mv[2] }]];
    if (/\b(add|put|include)\b/.test(t) && /\b(list|choice|choices|it|that|this)\b|\badd\b/.test(t)) {
      var opt = insts[0] ? { institute: insts[0], branch: branch || ctx.branch } : ctx.lastOption;
      if (!opt || !opt.branch) return say("Which college and branch should I add? For example, add CSE at NIT Warangal.");
      var a = { institute: opt.institute, branch: opt.branch };
      var pos = t.match(/\b(?:number|position|at)\s*(\d+)/);
      if (/\b(top|first)\b/.test(t)) a.position = 1; else if (pos) a.position = +pos[1];
      return [["add_choice", a], ["read_choices", {}, true]];
    }

    // words and process
    var term = findTerm(t);
    if (term && /\bmean|meaning|explain|what (is|are|does)|should (we|i|she|he)|difference\b/.test(t) && !insts.length) {
      if (/should (we|i|she|he)/.test(t) && /freeze|float|slide/.test(t)) term = "freeze float slide";
      return term === "freeze float slide"
        ? [["explain_term", { term: "freeze" }], ["explain_term", { term: "float" }, true], ["explain_term", { term: "slide" }, true]]
        : [["explain_term", { term: term }]];
    }
    if (/what happens|what('s| is) next|next step|after round|whole process|steps|counselling process|counseling process/.test(t)) {
      var step = (t.match(/round \d|seat acceptance|choice filling|mock allotment|reporting|lock/) || [])[0];
      return [["whats_next", step ? { step: step } : {}]];
    }

    var anyState = lastFoundState.some(Boolean);

    // compare
    if ((/\bor\b|\bvs\b|versus|compare|better|difference/.test(t)) && (insts.length >= 2 || (insts.length === 1 && /\bor\b/.test(t)))) {
      var parts = t.split(/\bor\b|\bvs\b|versus|compared? (?:to|with)|\band\b/);
      var A = parts.length > 1 ? parts[0] : t, B = parts.length > 1 ? parts.slice(1).join(" ") : t;
      var ia = findInstitutes(A)[0] || insts[0], ib = findInstitutes(B)[0] || insts[1] || insts[0];
      findInstitutes(t);
      // "compare BVRIT and CBIT in Hyderabad": the place at the end applies to both colleges
      var place = (t.match(/\bin (hyderabad|narsapur|bachupally|warangal)\b[^,]*$/) || [])[1];
      if (place) {
        if (ia.indexOf(place) < 0 && STATE_COLLEGES.some(function (s) { return ia.indexOf(s) === 0; })) ia += " " + place;
        if (ib.indexOf(place) < 0 && STATE_COLLEGES.some(function (s) { return ib.indexOf(s) === 0; })) ib += " " + place;
      }
      var ba = findBranch(A, raw.split(/ or | vs | versus /i)[0]) || branch || ctx.branch;
      var bb = findBranch(B, raw.split(/ or | vs | versus /i).slice(1).join(" ")) || ba;
      var cmp = { institute_a: ia, institute_b: ib };
      if (ba) cmp.branch_a = ba;
      if (bb) cmp.branch_b = bb;
      ctx.lastOption = { institute: ia, branch: ba || "CSE" };
      return [["compare_options", cmp]];
    }

    // cutoffs, branches, about a college
    if (insts.length && /cut ?off|closing rank|last rank|trend|last year|previous year|history|changed/.test(t)) {
      var ct = { institute: insts[0] };
      if (branch || ctx.branch) ct.branch = branch || ctx.branch;
      return [["cutoff_trend", ct]];
    }
    if (insts.length && /\b(branches|programs|programmes|courses)\b|what does .* (offer|have)/.test(t)) {
      return [["find_programs", { institute: insts[0] }]];
    }
    if (insts.length && /\babout\b|tell me|what is|how is|autonomous|located|where is|details of|info/.test(t) && !/chance|can (she|he|i|we) get/.test(t)) {
      return [["college_info", { college: insts[0] }]];
    }

    // the student
    var prof = parseProfile(t, raw);
    var calls = [];
    var hasProfile = prof.jee_main_rank || prof.category_rank || prof.jee_advanced_rank || prof.eapcet_rank || prof.home_state ||
      prof.name || ((prof.category || prof.telangana_category) && !insts.length);
    if (hasProfile && !(insts.length && !prof.jee_main_rank && !prof.eapcet_rank && !prof.home_state)) {
      if (!prof.jee_main_rank && !prof.jee_advanced_rank && !prof.category_rank && !prof.eapcet_rank && !prof.home_state &&
          !prof.category && !prof.telangana_category) delete prof.gender;
      calls.push(["set_student", prof]);
    }
    if (/what (details|do you know)|her details|his details|profile/.test(t)) return [["get_student", {}]];

    // one college
    if (insts.length) {
      var b = branch || ctx.branch;
      if (!b && !anyState) return calls.concat([["find_programs", { institute: insts[0] }]]);
      ctx.lastOption = { institute: insts[0], branch: b || "CSE" };
      var co = { institute: insts[0] };
      if (b) co.branch = b;
      return calls.concat([["check_option", co]]);
    }

    // Telangana state colleges (EAPCET)
    if (/eapcet|eamcet|telangana colleges|state colleges|hyderabad colleges|colleges in hyderabad|private colleges|hyderabad/.test(t) &&
        /which|what|options|colleges|get|suggest|list/.test(t)) {
      var ta = {};
      if (branch) ta.branch = branch;
      if (/hyderabad/.test(t)) ta.hyderabad_only = true;
      return calls.concat([["predict_telangana_colleges", ta]]);
    }

    // which colleges
    if (/which|what colleges|options|colleges|can (she|he|i|we) get|chances|where can|safe|suggest/.test(t) || instType) {
      var args = {};
      if (branch) args.branch = branch;
      if (instType) args.institute_type = instType;
      return calls.concat([["predict_colleges", args]]);
    }
    if (calls.length) return calls;
    if (/^what about\b/.test(t) && branch && ctx.inst) {
      ctx.lastOption = { institute: ctx.inst, branch: branch };
      return [["check_option", { institute: ctx.inst, branch: branch }]];
    }
    return say("I can help with engineering admissions: JoSAA colleges like IITs and NITs, and Telangana colleges like " +
      "CBIT, VNR and BVRIT. Tell me the student's rank, ask which colleges they can get, compare two colleges, build the " +
      "choice list, or ask what words like float and slide mean.");
  }

  function say(text) { return [["__say", { text: text }]]; }

  // ---------------- conversation ----------------
  var busy = false;
  function ask(raw) {
    raw = (raw || "").trim();
    if (!raw || busy) return;
    busy = true;
    addMsg("user", raw);
    var steps = plan(raw);
    var thinking = addMsg("alexa thinking", "…");
    var spoken = [], cards = [];
    var chain = Promise.resolve();
    steps.forEach(function (st) {
      chain = chain.then(function () {
        if (st[0] === "__say") { spoken.push(st[1].text); return; }
        return callTool(st[0], st[1]).then(function (out) {
          var silent = st[2];
          if (!silent || st[0] === "explain_term") spoken.push(out.text);
          cards.push({ tool: st[0], args: st[1], text: out.text, ms: out.ms });
        });
      });
    });
    chain.then(function () {
      thinking.remove();
      var text = spoken.join(" ");
      var tools = cards.map(function (c) { return c.tool + " · " + c.ms + " ms"; }).join("  ·  ");
      addMsg("alexa", text, tools);
      if (cards.length) renderCard(cards);
      speak(text);
    }).catch(function (e) {
      thinking.remove();
      addMsg("alexa", "Sorry, something went wrong: " + e.message);
    }).then(function () { busy = false; });
  }

  function addMsg(kind, text, tool) {
    var div = document.createElement("div");
    div.className = "msg " + kind;
    if (kind.indexOf("alexa") === 0) { var av = document.createElement("span"); av.className = "avatar"; div.appendChild(av); }
    var bubble = document.createElement("div");
    bubble.className = "bubble";
    if (kind.indexOf("thinking") >= 0) {
      bubble.innerHTML = '<span class="dots"><span></span><span></span><span></span></span>';
    } else {
      var p = document.createElement("p");
      p.textContent = text;
      bubble.appendChild(p);
    }
    if (tool) { var s = document.createElement("span"); s.className = "tool"; s.textContent = "MCP · " + tool; bubble.appendChild(s); }
    div.appendChild(bubble);
    $("chat").appendChild(div);
    $("chat").scrollTop = $("chat").scrollHeight;
    return div;
  }

  // ---------------- cards (what an Echo Show would display) ----------------
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function badge(b) { return '<span class="badge ' + esc(b) + '">' + esc(b) + "</span>"; }

  function renderCard(cards) {
    var main = cards.filter(function (c) { return c.tool !== "set_student"; });
    var c = main.length ? main[main.length - 1] : cards[0];
    if (c.tool === "add_choice" || c.tool === "move_choice" || c.tool === "remove_choice") {
      var r = cards.filter(function (x) { return x.tool === "read_choices"; })[0];
      if (r) c = r;
    }
    var html;
    var state = /TG EAPCET/.test(c.text);
    if (c.tool === "compare_options" && /^Comparing /.test(c.text)) html = tgCompareCard(c.text);
    else if (state && /^(check_option|cutoff_trend|college_info|find_programs)$/.test(c.tool)) html = tgCollegeCard(c.text);
    else if (c.tool === "predict_colleges" || c.tool === "predict_telangana_colleges") html = predictCard(c);
    else if (c.tool === "check_option" || c.tool === "cutoff_trend") html = optionsCard(c.text, c.tool === "cutoff_trend" ? "Cutoff history" : "Your chances");
    else if (c.tool === "compare_options") html = compareCard(c.text);
    else if (c.tool === "read_choices") html = choicesCard(c.text);
    else if (c.tool === "set_student" || c.tool === "get_student") html = profileCard(c.text);
    else html = textCard(c);
    $("card").innerHTML = html;
  }

  function predictCard(c) {
    var state = c.tool === "predict_telangana_colleges";
    var head = state ? ((c.text.match(/phase\), (.*?) with EAPCET/) || [])[1] || "Telangana college options")
                     : ((c.text.match(/here are (.*?)\./) || [])[1] || "Options");
    var source = state ? "From official TG EAPCET 2025 last ranks" : "From official JoSAA final-round closing ranks, 2023 to 2025";
    var html = '<div class="card"><h3>' + esc(head.charAt(0).toUpperCase() + head.slice(1)) + '</h3><div class="sub">' + source + '</div><div class="bands">';
    ["Safe", "Target", "Reach"].forEach(function (b) {
      var m = c.text.match(new RegExp(b + "[^:(]*\\((\\d+)\\): (.*?)\\.(?: |$)"));
      var items = [], more = "";
      if (m) {
        var list = m[2].replace(/, and (\d+) more$/, function (_, k) { more = "+" + k + " more"; return ""; });
        items = list.split("; ");
      }
      html += '<div class="band ' + b + '"><h4><span>' + b + '</span><span class="n">' + (m ? m[1] : 0) + "</span></h4><ul>" +
        (items.length ? items.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") : '<li class="more">None</li>') +
        "</ul>" + (more ? '<div class="more">' + more + "</div>" : "") + "</div>";
    });
    return html + "</div></div>";
  }

  function parseOption(text) {
    var m = text.match(/^(?:First, |Second, )?(.*?) at (.*?): (Safe|Target|Reach|Unlikely)\. On the (.*?), the closing rank was ([\d,]+) in (\d{4}), so we expect about ([\d,]+) this time, against (.*?)\./);
    if (!m) return null;
    var hist = [];
    var h = text.match(/Past closing ranks: (.*?);/);
    if (h) h[1].split(", ").forEach(function (p) { var q = p.match(/([\d,]+) in (\d{4})/); if (q) hist.push([q[2], parseInt(q[1].replace(/,/g, ""), 10)]); });
    var trend = (text.match(/; (steady|getting [^.]*)\./) || [])[1] || "";
    return { prog: m[1], inst: m[2], band: m[3], seat: m[4], expected: m[7], against: m[8], hist: hist, trend: trend };
  }

  function optionBlock(o) {
    var max = Math.max.apply(null, o.hist.map(function (x) { return x[1]; }).concat([1]));
    var bars = o.hist.map(function (x) {
      return '<div class="yr"><span class="v">' + x[1].toLocaleString("en-IN") + '</span><div class="col" style="height:' +
        Math.max(8, Math.round(70 * x[1] / max)) + '%"></div>' + x[0] + "</div>";
    }).join("");
    return '<div class="option">' + badge(o.band) + '<div class="name">' + esc(o.prog) + " · " + esc(o.inst) + '</div><div class="seat">' +
      esc(o.seat) + "</div>" + (bars ? '<div class="compare-row">' + bars + "</div>" : "") +
      '<div class="vs"><span>Expected closing<br><b>' + esc(o.expected) + "</b></span><span>Student<br><b>" +
      esc(o.against.replace(/^JEE (Main|Advanced) /, "")) + "</b></span><span>Trend<br><b>" + esc(o.trend.split(" (")[0] || "–") + "</b></span></div></div>";
  }

  function optionsCard(text, title) {
    var o = parseOption(text);
    if (!o) return textCard({ tool: title, text: text });
    return '<div class="card"><h3>' + esc(title) + '</h3><div class="sub">Closing rank by year, final round (a lower rank means harder)</div>' + optionBlock(o) + "</div>";
  }

  function compareCard(text) {
    var parts = text.split(/ Second, /);
    var a = parseOption(parts[0]), b = parseOption("Second, " + (parts[1] || ""));
    var verdict = (text.match(/((?:[^.]*? is the safer of the two)|(?:Both look[^.]*))\./) || [])[1] || "";
    if (!a || !b) return textCard({ tool: "Comparison", text: text });
    return '<div class="card"><h3>Comparison</h3><div class="sub">Official closing ranks, final round</div>' + optionBlock(a) + optionBlock(b) +
      (verdict ? '<div class="verdict">' + esc(verdict) + "</div>" : "") + "</div>";
  }

  // ---- Telangana state colleges ----
  function cutoffs(text) {
    var boys = (text.match(/rank ([\d,]+) for OC general seats/) || [])[1];
    var girls = (text.match(/([\d,]+) for OC girls' seats/) || [])[1];
    return '<div class="vs">' + (boys ? "<span>OC general<br><b>" + esc(boys) + "</b></span>" : "") +
      (girls ? "<span>OC girls<br><b>" + esc(girls) + "</b></span>" : "") + "</div>";
  }
  function chips(profile) {
    return '<div class="tags">' + profile.split(", ").map(function (p) { return "<span>" + esc(p) + "</span>"; }).join("") + "</div>";
  }
  function chanceLine(text, who) {
    var m = text.match(new RegExp((who ? esc(who) + " is " : "") + "(safe|target|reach|unlikely|not eligible)[^:]*: ([^;.]*)", "i"));
    if (!m) return "";
    var band = m[1].charAt(0).toUpperCase() + m[1].slice(1);
    return '<div class="chance">' + badge(band === "Not eligible" ? "Unlikely" : band) + " <span>" + esc(m[2]) + "</span></div>";
  }

  function tgCollegeCard(text) {
    var m = text.match(/^(.*?) at (.*?) \((.*?)\)\. In the/) || text.match(/^(.*?): (.*?)\. Admission/);
    if (!m) return textCard({ tool: "college_info", text: text });
    var isInfo = m.length === 3;
    var name = isInfo ? m[1] : m[2], branchName = isInfo ? "" : m[1], profile = isInfo ? m[2] : m[3];
    var note = (text.match(/Note: (.*)$/) || [])[1];
    return '<div class="card"><h3>' + esc(name) + '</h3><div class="sub">' + (branchName ? esc(branchName) + " · " : "") +
      "Official TG EAPCET 2025 last ranks</div>" + chips(profile) + cutoffs(text) + chanceLine(text) +
      (note ? '<div class="verdict warn">' + esc(note) + "</div>" : "") + "</div>";
  }

  function tgCompareCard(text) {
    var re = /(First|Second), (.*?): (.*?); it (.*?)\./g, m, cols = [];
    while ((m = re.exec(text))) cols.push({ name: m[2], profile: m[3], cut: "it " + m[4] });
    if (cols.length < 2) return textCard({ tool: "Comparison", text: text });
    var verdicts = [];
    var comp = text.match(/([^.]*? is more competitive[^.]*)\./);
    if (comp) verdicts.push(comp[1]);
    var safer = text.match(/([^.]*? is the safer choice)\./);
    if (safer) verdicts.push(safer[1]);
    var note = (text.match(/Note: (.*)$/) || [])[1];
    var who = (text.match(/For (\w+): /) || [])[1];
    var html = '<div class="card"><h3>Comparison</h3><div class="sub">Official TG EAPCET 2025 last ranks</div><div class="cols">';
    cols.forEach(function (c) {
      var part = who ? (text.match(new RegExp(esc(c.name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " is ([^;.]*)")) || [])[1] : null;
      html += '<div class="col-card"><div class="name">' + esc(c.name) + "</div>" + chips(c.profile) + cutoffs(c.cut) +
        (part ? chanceLine(part.replace(/^(\w)/, function (x) { return x; })) : "") + "</div>";
    });
    html += "</div>" + verdicts.map(function (v) { return '<div class="verdict">' + esc(v) + "</div>"; }).join("") +
      (note ? '<div class="verdict warn">' + esc(note) + "</div>" : "") + "</div>";
    return html;
  }

  function choicesCard(text) {
    var items = [], re = /(\d+)\. (.*?) \((Safe|Target|Reach|Unlikely|not eligible)\)/g, m;
    while ((m = re.exec(text))) items.push(m);
    var who = (text.match(/^(\w+)'s/) || [])[1] || "Student";
    if (!items.length) return textCard({ tool: who + "'s choice list", text: text });
    return '<div class="card"><h3>' + esc(who) + "'s JoSAA choice list</h3><div class=\"sub\">In order of preference</div><ol class=\"choices\">" +
      items.map(function (x) { return '<li><span class="t">' + esc(x[2]) + "</span>" + badge(x[3] === "not eligible" ? "Unlikely" : x[3]) + "</li>"; }).join("") + "</ol>" +
      (/no safe option/.test(text) ? '<div class="verdict warn">Add a few safe options lower down.</div>' : "") + "</div>";
  }

  function profileCard(text) {
    var m = text.match(/Saved (.*?)\.(?: |$)/);
    var bits = m ? m[1].split(", ") : [];
    var rest = text.replace(/^Saved .*?\.\s*/, "");
    return '<div class="card"><h3>' + esc(bits[0] || "Student") + '</h3><div class="sub">Student profile</div><ul class="profile">' +
      bits.slice(1).map(function (b) { return "<li>" + esc(b.charAt(0).toUpperCase() + b.slice(1)) + "</li>"; }).join("") + "</ul>" +
      (rest ? '<div class="verdict warn">' + esc(rest) + "</div>" : "") + "</div>";
  }

  var TITLES = { explain_term: "In plain words", whats_next: "JoSAA process", find_programs: "Programs offered", get_student: "Student" };
  function textCard(c) {
    return '<div class="card textcard"><h3>' + esc(TITLES[c.tool] || c.tool) + "</h3><p>" + esc(c.text) + "</p></div>";
  }

  // ---------------- under the hood ----------------
  function trace(out, name) {
    var box = $("trace");
    if (box.querySelector(".muted")) box.innerHTML = "";
    var resp = JSON.parse(JSON.stringify(out.response));
    var div = document.createElement("details");
    div.className = "call";
    var label = out.request.method === "tools/call" ? "tools/call · <b>" + esc(name) + "</b>" : "<b>" + esc(out.request.method) + "</b>";
    div.innerHTML = '<summary class="call-head"><span>' + label + "</span><span>" + out.ms + ' ms</span></summary>' +
      '<div class="label">Request</div><pre>' + esc(JSON.stringify(out.request, null, 1)) + "</pre>" +
      '<div class="label">Response</div><pre>' + esc(JSON.stringify(resp, null, 1)) + "</pre>";
    [].forEach.call(box.querySelectorAll("details[open]"), function (d) { d.open = false; });
    div.open = true;                                   // newest call open, older ones folded
    box.insertBefore(div, box.firstChild);
  }

  // ---------------- voice ----------------
  var voiceOn = true;
  try { voiceOn = localStorage.getItem("ap_voice") !== "0"; } catch (e) { /* storage blocked */ }
  function paintVoice() { $("voice").classList.toggle("off", !voiceOn); $("voice").setAttribute("aria-pressed", String(voiceOn)); }
  paintVoice();
  $("voice").addEventListener("click", function () {
    voiceOn = !voiceOn;
    try { localStorage.setItem("ap_voice", voiceOn ? "1" : "0"); } catch (e) { /* ignore */ }
    paintVoice();
    if (!voiceOn && window.speechSynthesis) speechSynthesis.cancel();
  });

  function speak(text) {
    if (!voiceOn || !window.speechSynthesis) return;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text.replace(/\bJoSAA\b/g, "Josa").replace(/\bB\.Tech\b/g, "B Tech"));
    var voices = speechSynthesis.getVoices();
    u.voice = voices.filter(function (v) { return /en-IN/i.test(v.lang); })[0] || voices.filter(function (v) { return /^en/i.test(v.lang); })[0] || null;
    u.rate = 1.03;
    u.onstart = function () { $("bar").className = "bar speaking"; };
    u.onend = u.onerror = function () { $("bar").className = "bar"; };
    speechSynthesis.speak(u);
  }

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition, rec = null;
  $("mic").addEventListener("click", function () {
    if (!SR) { addMsg("alexa", "Voice input needs Chrome or Edge. You can type instead."); return; }
    if (rec) { rec.stop(); return; }
    if (window.speechSynthesis) speechSynthesis.cancel();
    rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.onstart = function () { $("mic").classList.add("on"); $("bar").className = "bar listening"; };
    rec.onresult = function (e) {
      var r = e.results[e.results.length - 1];
      $("q").value = r[0].transcript;
      if (r.isFinal) { var said = $("q").value; $("q").value = ""; ask(said); }
    };
    rec.onend = function () { $("mic").classList.remove("on"); $("bar").className = "bar"; rec = null; };
    rec.start();
  });

  $("ask").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = $("q").value;
    $("q").value = "";
    ask(v);
  });

  // ---------------- one example to get started ----------------
  var EXAMPLE = "How has NIT Calicut CSE's cutoff changed?";
  var chip = document.createElement("button");
  chip.className = "chip";
  chip.type = "button";
  chip.innerHTML = "<b>Try</b>" + esc(EXAMPLE);
  chip.addEventListener("click", function () { ask(EXAMPLE); });
  $("chips").appendChild(chip);

  // ---------------- show or hide the MCP panel ----------------
  $("hood-toggle").addEventListener("click", function () {
    var full = $("layout").classList.toggle("full");
    this.setAttribute("aria-pressed", String(!full));
  });

  // ---------------- connect ----------------
  rpc("initialize", { protocolVersion: PROTOCOL, capabilities: {}, clientInfo: { name: "simulated-alexa-plus", version: "1.0" } })
    .then(function (init) {
      trace(init, "initialize");
      var info = init.response.result.serverInfo;
      return rpc("tools/list").then(function (list) {
        trace(list, "tools/list");
        var n = list.response.result.tools.length;
        $("status").innerHTML = "<i></i>" + esc(info.title) + " connected · " + n + " tools · MCP " + esc(init.response.result.protocolVersion);
        $("status").className = "status ok";
      });
    })
    .catch(function () { $("status").innerHTML = "<i></i>Can't reach the AdmitPath server"; $("status").className = "status err"; });
})();

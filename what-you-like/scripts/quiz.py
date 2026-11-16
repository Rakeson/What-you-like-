#!/usr/bin/env python3
"""What You Like quiz engine.

Picks questions, keeps score and builds the final reading, so the model
running the skill never has to do arithmetic or remember state.

    quiz.py start                 begin a new session, print question 1
    quiz.py answer N              record option N (1-based), print what comes next
    quiz.py react yes|partly|no   record the reaction to the guess
    quiz.py result                print the reading again

State lives in a JSON file (default ./wyl_state.json, change with --state).
Every command prints one JSON object on stdout.
"""
import argparse
import json
import math
import os
import random
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BANK_PATH = os.path.join(HERE, "..", "data", "bank.json")
TYPES = list("RIASEC")
STYLE = ["d", "e", "f", "t"]
PLAN = ["card"] * 4 + ["scen", "scen", "style", "style"] + ["card"] * 4 + \
       ["scen", "style", "style", "pair", "pair", "pair", "verify", "prep"]

with open(BANK_PATH, encoding="utf-8") as fh:
    BANK = json.load(fh)
T = BANK["types"]


def vec(code):
    v = [0.0] * 6
    for w, c in zip((1.0, 0.7, 0.4), code):
        v[TYPES.index(c)] = w
    return v


def cos(a, b):
    d = sum(x * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return d / n if n else 0.0


def scores(S):
    sc = {k: 0.0 for k in TYPES + STYLE}
    ab = {k: 0.0 for k in STYLE}
    for a in S["answers"]:
        for k, w in a["w"].items():
            sc[k] += w
            if k in ab:
                ab[k] += abs(w)
    return sc, ab


def rank(S):
    sc, _ = scores(S)
    return sorted(TYPES, key=lambda t: -sc[t])


def make_q(S, kind, rng):
    used = set(S["used"])
    if kind == "card":
        carded = [a["ty"] for a in S["answers"] if a["kind"] == "card"]
        pool = [t for t in TYPES if t not in carded]
        ty = rng.choice(pool) if pool else rank(S)[(len(carded) - 6) % 2]
        cands = [c for c in BANK["cards"] if c["ty"] == ty and c["id"] not in used] or \
                [c for c in BANK["cards"] if c["id"] not in used]
        c = rng.choice(cands)
        return {"id": c["id"], "kind": kind, "ty": c["ty"], "label": "First reaction",
                "prompt": c["t"], "measures": T[c["ty"]]["card"],
                "options": [{"t": "Yes, that pulls me in", "w": {c["ty"]: 1.5}},
                            {"t": "Could take it or leave it", "w": {c["ty"]: 0.2}},
                            {"t": "Not for me", "w": {c["ty"]: -1}}]}
    if kind == "scen":
        top = rank(S)[:3]
        cands = [q for q in BANK["scenes"] if q["id"] not in used]
        q = max(cands, key=lambda q: sum(1 for o in q["options"] if any(o["w"].get(t) for t in top)) + rng.random() * 1.5)
        return {"id": q["id"], "kind": kind, "label": "A small scene", "prompt": q["prompt"],
                "measures": q["measures"], "options": q["options"]}
    if kind == "style":
        _, ab = scores(S)
        free = [q for q in BANK["styleQuestions"] if q["id"] not in used]
        axis = min({q["axis"] for q in free}, key=lambda ax: (ab[ax], STYLE.index(ax)))
        q = rng.choice([q for q in free if q["axis"] == axis])
        return {"id": q["id"], "kind": kind, "label": "A small scene", "prompt": q["prompt"],
                "measures": q["measures"], "options": q["options"]}
    if kind == "pair":
        r = rank(S)[:4]
        sc, _ = scores(S)
        cand = sorted(((sc[r[i]] - sc[r[j]] + (i + j) * 0.4, r[i], r[j])
                       for i in range(4) for j in range(i + 1, 4)))
        p = None
        for _, a, b in cand:
            key = a + b if TYPES.index(a) < TYPES.index(b) else b + a
            items = [x for x in BANK["pairs"] if x["types"] == key and x["id"] not in used]
            if items:
                p = rng.choice(items)
                break
        if p is None:
            p = rng.choice([x for x in BANK["pairs"] if x["id"] not in used])
        A, B = p["types"][0], p["types"][1]
        opts = [{"t": p["a"], "w": {A: 1.5, B: -0.5}}, {"t": p["b"], "w": {B: 1.5, A: -0.5}}]
        if rng.random() < 0.5:
            opts.reverse()
        return {"id": p["id"], "kind": kind, "label": "A closer call", "prompt": p["prompt"], "options": opts,
                "measures": f"A direct choice between your {T[A]['name']} and {T[B]['name']} sides, which were running close."}
    if kind == "verify":
        r = rank(S)
        picks = [r[0], r[2], r[4], r[5]]
        rng.shuffle(picks)
        return {"id": "verify", "kind": kind, "label": "A reverse check",
                "prompt": "Which of these would wear you out fastest?",
                "measures": "A reverse check. If the thing that tires you fastest is also your strongest strand, that tension is worth knowing about.",
                "options": [{"t": T[x]["drain"], "w": {x: -1.5 if x == r[0] else -1}, "flag": x if x == r[0] else None} for x in picks]}
    return {"id": "prep", "kind": "prep", "label": "One practical question",
            "prompt": "If something really fit you, how long would you train for it?",
            "measures": "Not a hidden question. It filters the careers list to ones within the preparation you said you were up for.",
            "options": [{"t": "I would want to start within months", "w": {}, "z": 2},
                        {"t": "A year or two", "w": {}, "z": 3},
                        {"t": "A full degree", "w": {}, "z": 4},
                        {"t": "As long as it takes", "w": {}, "z": 5}]}


def style_fit(item, us):
    nz = sum(1 for x in item["style"] if x) or 1
    return sum(x * u for x, u in zip(item["style"], us)) / nz


def reading(S):
    sc, _ = scores(S)
    r = rank(S)
    lo = min(sc[t] for t in TYPES)
    u = [sc[t] - lo for t in TYPES]
    if not any(u):
        u = [1.0] * 6
    us = [math.tanh(sc[a] / 2.5) for a in STYLE]
    style = []
    for ax, v in zip(BANK["styleAxes"], us):
        cert = "clear" if abs(v) > 0.5 else "leaning" if abs(v) > 0.2 else "mixed"
        style.append({"left": ax["left"], "right": ax["right"], "value": round(v, 2),
                      "leans": ax["left"] if v < 0 else ax["right"], "certainty": cert, "id": ax["id"]})
    s_top = max(style, key=lambda a: abs(a["value"]))
    portrait = f"{T[r[0]]['desc']} {T[r[1]]['desc']}"
    if abs(s_top["value"]) > 0.2:
        portrait += f" You may also find that {BANK['stylePhrases'][s_top['id']]['-1' if s_top['value'] < 0 else '1']}."

    hs = sorted(((0.65 * cos(u, vec(h["code"])) + 0.35 * style_fit(h, us), h) for h in BANK["hobbies"]),
                key=lambda x: -x[0])
    elig = sorted(((cos(u, vec(o["code"])), o) for o in BANK["occupations"] if o["zone"] <= S["maxZone"]),
                  key=lambda x: -x[0])
    by = {}
    for s, o in elig:
        by.setdefault(o["field"], []).append((s, o))
    fields = sorted(((sum(x[0] for x in a[:3]) / 3, f, a[:5]) for f, a in by.items() if len(a) >= 3),
                    key=lambda x: -x[0])[:3]
    taken, out_fields = set(), []
    for _, f, jobs in fields:
        cv = [sum(vec(o["code"])[i] for _, o in jobs) for i in range(6)]
        bi = max(range(6), key=lambda i: cv[i] * u[i])
        tf = sorted(((0.8 * cos(cv, vec(h["code"])) + 0.2 * s, h) for s, h in hs if h["name"] not in taken),
                    key=lambda x: -x[0])[:2]
        for _, h in tf:
            taken.add(h["name"])
        out_fields.append({
            "field": f, "why": T[TYPES[bi]]["why"],
            "jobs": [{"name": o["name"], "training": BANK["zones"][o["zone"]],
                      "url": "https://www.onetonline.org/find/quick?s=" + urllib.parse.quote(o["name"])} for _, o in jobs],
            "tryFirst": [{"name": h["name"], "firstStep": h["firstStep"]} for _, h in tf]})
    hobbies = [{"name": h["name"], "firstStep": h["firstStep"]} for _, h in hs if h["name"] not in taken][:8]

    ns = []
    for n in BANK["niches"]:
        v = vec(n["code"])
        bi = max(range(6), key=lambda i: v[i] * u[i])
        ns.append((0.65 * cos(u, v) + 0.35 * style_fit(n, us), n, T[TYPES[bi]]["why"]))
    niches = [{"name": n["name"], "what": n["what"], "why": why, "firstStep": n["firstStep"]}
              for _, n, why in sorted(ns, key=lambda x: -x[0])[:3]]

    if S["flags"]:
        f = S["flags"][0]
        tension = (f"Your answers kept pointing at {T[f]['name']} work, but when asked what would wear you out fastest "
                   f"you picked \"{T[f]['drain'].lower()}\". You may like this kind of work in small doses, or as a hobby more than as a job.")
    elif sc[r[0]] - sc[r[1]] < 1:
        tension = (f"Your top two strands, {T[r[0]]['name']} and {T[r[1]]['name']}, finished almost level. People with that mix "
                   f"often need both in the same week: work that lets you {T[r[0]]['guess']} and also {T[r[1]]['guess']}.")
    else:
        tension = (f"No contradictions showed up on the reverse check. Your lowest strand was {T[r[5]]['name']}, by a clear margin. "
                   f"That is useful too: {T[r[5]]['drain'].lower()} will probably cost you more than it gives back.")

    mean = sum(sc[t] for t in TYPES) / 6
    scored = sorted(((sum(w * (sc[k] - mean if k in TYPES else sc[k]) for k, w in a["w"].items()), i, a)
                     for i, a in enumerate(S["answers"]) if a["kind"] != "prep"), key=lambda x: (-x[0], x[1]))
    trace, per = [], {}
    for _, _, a in scored:
        per[a["kind"]] = per.get(a["kind"], 0) + 1
        if per[a["kind"]] > 2:
            continue
        trace.append({"question": a["prompt"], "youChose": a["choice"], "quietlyMeasuring": a["measures"]})
        if len(trace) == 4:
            break

    return {"type": "result", "code": "".join(r[:3]),
            "title": f"Someone who {T[r[0]]['title']} and {T[r[1]]['title']}",
            "portrait": portrait,
            "strands": [{"letter": t, "name": T[t]["name"], "score": round(50 + 50 * math.tanh(sc[t] / 4))} for t in r],
            "style": [{k: v for k, v in a.items() if k != "id"} for a in style],
            "fields": out_fields, "hobbies": hobbies, "niches": niches, "tension": tension, "trace": trace,
            "guessReaction": S.get("reaction"),
            "note": "A mirror, not a diagnosis. Interest codes are approximations written for this project, not official O*NET data."}


def guess(S):
    r = rank(S)
    S["guess"] = (f"My guess: you are happiest when you get to {T[r[0]]['guess']}, and part of you also wants to "
                  f"{T[r[1]]['guess']}. {T[r[5]]['drain']} sounds like your idea of a bad time.")
    return {"type": "guess", "text": S["guess"], "ask": "How close is that?",
            "options": ["That's me", "Partly", "Not really"],
            "next": "Run: quiz.py react yes|partly|no"}


def step(S):
    """Return the next thing to show: a question, the guess, or the result."""
    if S["qi"] < len(S["plan"]):
        if not S.get("cur"):
            rng = random.Random(f"{S['seed']}:{S['qi']}")
            S["cur"] = make_q(S, S["plan"][S["qi"]], rng)
            S["used"].append(S["cur"]["id"])
        q, extra = S["cur"], S["qi"] >= len(PLAN)
        count = (f"Extra question {S['qi'] + 1 - len(PLAN)} of {len(S['plan']) - len(PLAN)}" if extra
                 else f"Question {S['qi'] + 1} of {len(PLAN)}")
        return {"type": "question", "count": count, "label": q["label"], "prompt": q["prompt"],
                "options": [o["t"] for o in q["options"]], "next": "Run: quiz.py answer N"}
    if not S.get("guess"):
        return guess(S)
    if S.get("reaction") is None:
        return {"type": "guess", "text": S["guess"], "ask": "How close is that?",
                "options": ["That's me", "Partly", "Not really"], "next": "Run: quiz.py react yes|partly|no"}
    return reading(S)


def load(path):
    if not os.path.exists(path):
        sys.exit(json.dumps({"type": "error", "message": f"No session at {path}. Run: quiz.py start"}))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, S):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(S, fh)


def main():
    ap = argparse.ArgumentParser(description="What You Like quiz engine")
    ap.add_argument("command", choices=["start", "answer", "react", "result"])
    ap.add_argument("value", nargs="?")
    ap.add_argument("--state", default="wyl_state.json")
    ap.add_argument("--seed", default=None, help="fix the question order (for testing)")
    a = ap.parse_args()

    if a.command == "start":
        S = {"seed": a.seed if a.seed is not None else str(random.randrange(10 ** 9)), "plan": list(PLAN), "qi": 0,
             "cur": None, "answers": [], "used": [], "flags": [], "maxZone": 5, "guess": None, "reaction": None}
    else:
        S = load(a.state)

    if a.command == "answer":
        q = S.get("cur")
        if S["qi"] >= len(S["plan"]) or not q:
            sys.exit(json.dumps({"type": "error", "message": "No question is waiting for an answer."}))
        try:
            i = int(a.value) - 1
            o = q["options"][i]
            assert i >= 0
        except (TypeError, ValueError, IndexError, AssertionError):
            sys.exit(json.dumps({"type": "error", "message": f"Answer must be a number from 1 to {len(q['options'])}."}))
        if o.get("flag"):
            S["flags"].append(o["flag"])
        if o.get("z"):
            S["maxZone"] = o["z"]
        S["answers"].append({"id": q["id"], "i": i, "w": o["w"], "kind": q["kind"], "ty": q.get("ty"),
                             "prompt": q["prompt"], "choice": o["t"], "measures": q["measures"]})
        S["qi"] += 1
        S["cur"] = None
    elif a.command == "react":
        if not S.get("guess") or S.get("reaction") is not None:
            sys.exit(json.dumps({"type": "error", "message": "There is no guess waiting for a reaction."}))
        if a.value not in ("yes", "partly", "no"):
            sys.exit(json.dumps({"type": "error", "message": "Reaction must be yes, partly or no."}))
        S["reaction"] = a.value
        if a.value != "yes":
            S["plan"] += ["pair", "pair"]
    elif a.command == "result":
        if S["qi"] < len(S["plan"]) or S.get("reaction") is None:
            sys.exit(json.dumps({"type": "error", "message": "The quiz is not finished yet."}))

    out = step(S)
    save(a.state, S)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

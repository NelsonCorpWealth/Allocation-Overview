#!/usr/bin/env python3
"""
validate_data.py - gate before commit.

The routine (Claude) pulls model portfolios from YCharts and writes data.json.
Claude is flexible; this script is strict. Nothing reaches the live page
unless it passes.

    python validate_data.py data.json                    -> exit 0 = safe to commit
    python validate_data.py data.json --prev old.json    (also prints what changed)

Exit codes: 0 ok, 1 invalid, 2 file/parse error.
"""
import sys, json, datetime, argparse

EXPECTED_MODELS = {  # display name -> YCharts model portfolio id (order matters: it is the page order)
    "Conservative": 597220,
    "Absolute Return Conservative": 604837,
    "Tax Conservative": 1146887,
    "Moderate-Conservative": 2413005,
    "Absolute Return Moderate-Conservative": 1380248,
    "Moderate": 552644,
    "Absolute Return Moderate": 555767,
    "Tax Moderate": 1146880,
    "Moderate-Aggressive": 2413016,
    "Absolute Return Moderate-Aggressive": 604832,
    "Aggressive": 597223,
    "Tax Aggressive": 1146891,
    "All Tactical": 1297251,
    "Macro Factor": 1729042,
    "IA3 High Income": 1589463,
    "IA3 Cash Management": 1589508,
}
TIERS = {"Conservative Models", "Moderate-Conservative Models", "Moderate Models",
         "Moderate-Aggressive Models", "Aggressive Models", "Specialty Models"}
GROUPS = {"Equity", "Fixed Income", "Alternative Strategies", "Real Assets", "Capital Preservation", "Cash", "Other"}
WEIGHT_TOL = 0.005
MAX_AS_OF_AGE_DAYS = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--prev")
    args = ap.parse_args()
    try:
        data = json.load(open(args.path))
    except Exception as e:
        print("ERROR: cannot read", args.path, e); return 2

    errs = []
    for k in ("as_of", "generated_at", "source", "models", "funds"):
        if k not in data: errs.append(f"missing top-level key {k}")
    if errs:
        for e in errs: print("FAIL:", e)
        return 1

    try:
        as_of = datetime.date.fromisoformat(data["as_of"])
        age = (datetime.date.today() - as_of).days
        if age > MAX_AS_OF_AGE_DAYS: errs.append(f"as_of {as_of} is {age} days old")
        if age < 0: errs.append(f"as_of {as_of} is in the future")
    except Exception:
        errs.append(f"as_of not YYYY-MM-DD: {data['as_of']!r}")

    models = data["models"]
    names = [m.get("name") for m in models]
    if names != list(EXPECTED_MODELS):
        errs.append(f"model list/order differs from expected: {names}")
    funds = data["funds"]
    used = set()
    for m in models:
        n = m.get("name")
        if EXPECTED_MODELS.get(n) != m.get("portfolio_id"):
            errs.append(f"{n}: portfolio_id {m.get('portfolio_id')} != expected {EXPECTED_MODELS.get(n)}")
        if m.get("tier") not in TIERS: errs.append(f"{n}: bad tier {m.get('tier')!r}")
        sleeves = m.get("sleeves") or []
        if not sleeves: errs.append(f"{n}: no sleeves"); continue
        tot = sum(s.get("weight", 0) for s in sleeves)
        if abs(tot - 1) > WEIGHT_TOL: errs.append(f"{n}: sleeve weights sum to {tot:.4f}")
        for s in sleeves:
            if not s.get("name"): errs.append(f"{n}: sleeve without a name")
            if not (0 < s.get("weight", 0) <= 1): errs.append(f"{n}/{s.get('name')}: weight {s.get('weight')} out of (0,1]")
            h = s.get("holdings") or []
            if not h: errs.append(f"{n}/{s.get('name')}: no holdings"); continue
            st = sum(x.get("weight", 0) for x in h)
            if abs(st - 1) > WEIGHT_TOL: errs.append(f"{n}/{s.get('name')}: holdings sum to {st:.4f} (a nested sleeve probably failed to expand)")
            for x in h:
                t = x.get("ticker")
                if not t or t.startswith("P:"): errs.append(f"{n}/{s.get('name')}: unexpanded holding {t!r}")
                used.add(t)
    missing = sorted(t for t in used if t not in funds)
    if missing: errs.append(f"funds map missing: {missing}")
    for t, f in funds.items():
        if f.get("group") not in GROUPS: errs.append(f"funds[{t}].group {f.get('group')!r} not in {sorted(GROUPS)}")

    if errs:
        for e in errs: print("FAIL:", e)
        print(f"\n{len(errs)} problem(s) - DO NOT COMMIT")
        return 1

    if args.prev:
        try:
            prev = json.load(open(args.prev))
        except Exception as e:
            print("WARN: cannot read --prev:", e); prev = None
        if prev:
            pm = {m["name"]: m for m in prev.get("models", [])}
            changes = 0
            for m in models:
                old = pm.get(m["name"])
                if not old: print(f"CHANGED: {m['name']} is new"); changes += 1; continue
                def key(s): return s.get("name")
                os_ = {key(s): s for s in old["sleeves"]}; ns = {key(s): s for s in m["sleeves"]}
                for k in sorted(set(os_) | set(ns)):
                    a, b = os_.get(k), ns.get(k)
                    if a is None: print(f"CHANGED: {m['name']}: + sleeve {k} {b['weight']:.4f}"); changes += 1
                    elif b is None: print(f"CHANGED: {m['name']}: - sleeve {k} (was {a['weight']:.4f})"); changes += 1
                    else:
                        if abs(a["weight"] - b["weight"]) > 1e-6:
                            print(f"CHANGED: {m['name']}: {k} {a['weight']:.4f} -> {b['weight']:.4f}"); changes += 1
                        ah = {x["ticker"]: x["weight"] for x in a["holdings"]}; bh = {x["ticker"]: x["weight"] for x in b["holdings"]}
                        if ah != bh:
                            print(f"CHANGED: {m['name']}: {k} holdings {ah} -> {bh}"); changes += 1
            if changes == 0: print("No allocation or holdings changes vs previous file.")
    print("OK:", len(models), "models,", len(funds), "tickers, as of", data["as_of"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

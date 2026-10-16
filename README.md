# NelsonCorp Model Allocation Overview

The web version of the Model Allocation Overview: every strategy model's building-block mix
(Core Bond / Core Stock / Core Stock (Macro) / Tactical / Defined Risk / Alternatives / Cash),
its equity range, and where its equity exposure sits today — read from the firm's YCharts model
portfolios every morning. Runs on GitHub Pages; nothing runs on a local machine.

```
 6:15am CT, weekdays                            in the browser
 ┌──────────────────────────────┐              ┌──────────────────────────────────────────┐
 │ Claude Code cloud routine    │              │ index.html                               │
 │  • YCharts MCP connector     │  data.json   │  sleeve name → building block            │
 │  • 16 model portfolios       │ ───────────► │  equity range  = always-in + tactical    │
 │  • top-level sleeves kept,   │  (commit +   │  current equity = look-through ETFs      │
 │    look-through ETFs inside  │   promote)   │     YCharts classifies as Equity         │
 │  • validate_data.py gate     │              │  donuts, range bars, sleeve tables       │
 └──────────────────────────────┘              └──────────────────────────────────────────┘
```

## What's on the page

A legend strip (building blocks, equity-range bar, current-equity dot), then one green tier
band per group — Conservative, Moderate-Conservative, Moderate, Moderate-Aggressive, Aggressive,
Specialty, as in the printed overview — with a card per model beneath it. Each card: a donut of
the building blocks (the Excel overview's colours: #007452 / #BBB930 / #926A41 / #FD9302 /
#2874A6, plus Defined Risk and Cash, which the printed version leaves out), the equity-range bar
with the current reading as a red dot, and an expandable table of the model's sleeves with the
ETFs each one holds right now (equity ETFs in green). A model listed in `MISSING` in
`index.html` (one the firm runs but hasn't built in YCharts yet) shows as a dashed placeholder.

## How the numbers work

Everything is derived in `index.html` from `data.json`; the routine never interprets anything.

- **Building block** — assigned from the YCharts sleeve name by the `RULES` table at the top of
  the script (`CORE_BOND` → Core Bond, `MACRO_FACTOR` → Core Stock (Macro), `TACTICAL_STOCK` /
  `REGIONAL_STOCK` / `BIG_PICTURE` → Tactical, and so on). An unrecognised sleeve is shown in red
  as *Unmapped* and a banner names the model, rather than being guessed.
- **Equity range** — low end = Core Stock + Core Stock (Macro) weight (always in stocks); high
  end = low end + Tactical weight. Defined Risk, Alternatives and Cash sit outside the range,
  matching the firm's published overview. These reproduce the spreadsheet's hand-entered
  Min/Max Equity exactly (Conservative 12–48%, Moderate 35–75%, Aggressive 51–93%, …).
- **Current equity** — for each equity-range sleeve, the look-through weight of ETFs whose
  YCharts `broad_category_group` is `Equity`. A tactical sleeve parked in JPST or BIL counts as
  zero until it is back in stocks. A reading outside its range is flagged in red.

## The daily routine

A Claude Code cloud routine ("Allocation overview refresh", claude.ai/code/routines) runs
weekdays before the market opens. It pulls target holdings for the 16 models from YCharts, keeps
each model's top-level sleeves, flattens the ETFs inside each sleeve, classifies every ticker
with `broad_category_group`, writes `data.json`, runs `validate_data.py`, and commits only if an
allocation or a holding changed. The prompt is `ROUTINE_PROMPT.md` — the routine holds its own
copy, so edits must be pasted into its Instructions.

The platform routes its push to a `claude/*` branch. `.github/workflows/promote-data.yml`
re-runs the validator on GitHub's side and fast-forwards `main` only if `data.json` is the sole
changed file. Two independent gates.

## Adding a model

1. Build it in YCharts as a model portfolio of sleeves, like the others.
2. Add its name, tier and ID to the table in `ROUTINE_PROMPT.md` (and paste the prompt into the
   routine) and to `EXPECTED_MODELS` in `validate_data.py`, in page order.
3. Remove it from `MISSING` in `index.html` if it was a placeholder.

## Files

| File | Role |
|---|---|
| `index.html` | the page — all derivation logic and the category rules |
| `data.json` | written by the routine; the only file that changes day to day |
| `validate_data.py` | strict gate; run by the routine and again by the GitHub Action |
| `ROUTINE_PROMPT.md` | the routine's instructions (copy, not a link) |
| `.github/workflows/promote-data.yml` | promotes a validated `claude/*` data commit to `main` |

The page also loads `nav.js` from the Dashboards hub repo, which draws the shared navigation strip
under the title bar once that repo exists; until then the script simply 404s and nothing shows.

Category colours were checked for colour-vision separation (CVD ΔE ≥ 10 on every adjacent pair);
Core Stock olive and Tactical orange are the one weak pair, so every slice also carries a direct
label and the legend.

# Model Allocation Overview — daily data refresh

You are updating `data.json` in this repository from YCharts. The file feeds the Model Allocation Overview page, so correctness matters more than speed. Follow every step. If anything fails validation, do not commit — report and stop.

## Model portfolios (fixed — do not look these up or reinterpret)

| Display name | Tier | YCharts ID |
|---|---|---:|
| Conservative | Conservative Models | 597220 |
| Absolute Return Conservative | Conservative Models | 604837 |
| Tax Conservative | Conservative Models | 1146887 |
| Moderate-Conservative | Moderate-Conservative Models | 2413005 |
| Absolute Return Moderate-Conservative | Moderate-Conservative Models | 1380248 |
| Moderate | Moderate Models | 552644 |
| Absolute Return Moderate | Moderate Models | 555767 |
| Tax Moderate | Moderate Models | 1146880 |
| Moderate-Aggressive | Moderate-Aggressive Models | 2413016 |
| Absolute Return Moderate-Aggressive | Moderate-Aggressive Models | 604832 |
| Aggressive | Aggressive Models | 597223 |
| Tax Aggressive | Aggressive Models | 1146891 |
| All Tactical | Specialty Models | 1297251 |
| Macro Factor | Specialty Models | 1729042 |
| IA3 High Income | Specialty Models | 1589463 |
| IA3 Cash Management | Specialty Models | 1589508 |

Use the display names and tiers EXACTLY as written, in this order.

## Handling YCharts data (read before Step 1)
- Never type, retype or reformat a number from a YCharts tool result. Every value in data.json must come from a script reading a saved copy of the response.
- After each YCharts call, save the result verbatim to `/tmp/raw/<step>_<n>.json` (copy the exact result text; if the tool already wrote the result to a file, copy that file). Do not summarize, round or reorder it.
- If a response is too long to save verbatim in one go, re-request it in smaller batches until each batch can be saved.
- Build data.json only with a script that reads `/tmp/raw/`. Keep `/tmp/raw` out of the repo — commit data.json only.
- If any value could not be taken from a saved response, do not commit; say which at the top of the summary.

## Steps

1. **Top-level holdings.** Call `get_model_portfolio_holdings` for all 16 IDs with `weight_type="target"` (batches of up to 10). Drop any holding with weight `0.000000` (inactive universe positions). Weights are percent; divide by 100.

2. **Sleeves.** Each model's top-level holdings are mostly SLEEVES — nested portfolios whose `security_id` starts with `P:`. Keep the sleeve as a sleeve (do not flatten it away): record its id (the number after `P:`), its `name` exactly as YCharts returns it (trim trailing spaces), and its weight in the model. A top-level holding that is a real security (for example `$:CASH` in Macro Factor) becomes a sleeve with `"id": null`, `"name"` = the ticker, and a single holding of itself at weight 1.0.

3. **Look-through holdings per sleeve.** For every sleeve, fetch its holdings (`weight_type="target"`) and expand any nested `P:` sleeves recursively, multiplying weights down the path, until only real tickers remain. Cache: many sleeves are shared across models. Within each sleeve the holdings are expressed as fractions of THAT SLEEVE and must sum to 1.000 ± 0.005. Map `$:CASH`, `M:FZFXX`, `M:FDRXX` to ticker `CASH`. Round weights to 6 decimals, sort descending.

4. **Fund classification.** Collect every distinct ticker across all sleeves (except `CASH`) and call `get_fund_data` with `metrics=["broad_category_group"]` (batches of up to 25). Build the `funds` map: `{ "VTI": { "name": "<security_name>", "group": "<broad_category_group>" } }`. Add `"CASH": { "name": "Cash", "group": "Cash" }`. If a ticker comes back with an error or a null group, set its group to `"Other"` and mention it in the summary — do not guess.

5. **Write data.json** at the repo root with this exact shape:
```json
{
  "as_of": "YYYY-MM-DD",
  "generated_at": "<ISO 8601 with offset>",
  "source": "YCharts (MCP, cloud routine)",
  "models": [
    { "name": "Conservative", "tier": "Conservative Models", "portfolio_id": 597220,
      "sleeves": [
        { "id": 548980, "name": "RA3_SLEEVE_CORE_BOND_1", "weight": 0.47,
          "holdings": [ { "ticker": "SGOV", "weight": 1.0 } ] }
      ] }
  ],
  "funds": { "SGOV": { "name": "iShares 0-3 Month Treasury Bond ETF", "group": "Fixed Income" } }
}
```
`as_of` is today's date (target weights are the current targets). Each model's sleeve weights must sum to 1.000 ± 0.005; if one doesn't, something was dropped — stop and report which.

6. **Validate.** Run: `git show HEAD:data.json > /tmp/prev.json && python validate_data.py data.json --prev /tmp/prev.json`
   Exit code 0 means safe. Anything else: DO NOT COMMIT. Paste the validator output in your summary and stop.

7. **Commit every run.** Commit even when the validator reports "No allocation or holdings changes vs previous file" — the dashboard reads `as_of` from data.json and flags the page as stale if it is more than five days old, so a skipped commit looks like a missed run.
   If the validator reported changes: `git add data.json && git commit -m "Allocation refresh (as of <as_of>)" && git push origin main`
   If it reported no changes: `git add data.json && git commit -m "Allocation refresh (as of <as_of>) - no changes" && git push origin main`
   (If the push is redirected to a `claude/` branch, that is expected — a GitHub Action promotes it to main after re-validating.) Only skip the commit when validation fails.

8. **Summary.** Lead with the validator's CHANGED lines — which sleeves were added, removed or re-weighted in which models, and which sleeves changed their holdings. If nothing changed, say so in one line.

## Do not
- Change `index.html`, `validate_data.py`, or any file other than `data.json`
- Guess a portfolio ID or resolve portfolios by name
- Assign building-block categories or compute equity ranges — the page does that from sleeve names
- Commit if validation fails, even if the failure seems minor
- Retry a failed push more than once

# FX Review OS — ChatGPT Prep-First Runbook

This file defines the **mandatory operational sequence** for the ChatGPT-first Weekly FX Review flow.

It exists to prevent the report from being generated against stale technical, valuation, or recommendation-state artifacts.

---

## Core rule

For the ChatGPT-first production path, the workflow is **not allowed** to start with the deep-research runtime.

It must start with a **state refresh**.

The mandatory sequence is:

1. start the FX state refresh
2. wait for that workflow to finish successfully
3. confirm that the refreshed state files were committed to `main`
4. only then start the ChatGPT deep-research runtime
5. write the markdown report to `output_split_test/weekly_fx_review_YYMMDD.md`
6. let the push-triggered split delivery workflow handle promote / render / email

---

## Why this is mandatory

The ChatGPT deep-research runtime uses repo-state files as authoritative for:
- technical overlay
- portfolio valuation
- open holdings
- scorecard-driven action labels and target weights

If those files are stale, the report can be strategically fresh in macro terms but operationally stale in:
- Section 7
- Section 13
- Section 14
- Section 15
- Section 16 carry-forward state

That is not acceptable for the production-style ChatGPT-first flow.

---

## Mandatory prep workflow

The canonical prep workflow is:
- `.github/workflows/refresh-fx-state.yml`

There are two acceptable ways to start it:

### Option A — direct workflow dispatch
Run this workflow directly:
- `.github/workflows/refresh-fx-state.yml`

### Option B — repo-native queue trigger
If direct workflow dispatch is not available from the active ChatGPT environment, write a trigger file into:
- `control/run_queue/`

Accepted filename patterns:
- `fx_prep_trigger_YYYYMMDD_HHMMSS.md`
- `fx_refresh_trigger_YYYYMMDD_HHMMSS.md`

Minimum required fields:
- `requested_at_utc`
- `requested_run_date`
- `mode`
- `note`

For refresh-only use:
- `mode: refresh-fx-state`

For prep-first generation use:
- `mode: generate-and-publish`

That trigger file is consumed by:
- `.github/workflows/prep-from-trigger.yml`

That workflow validates the trigger and then calls:
- `.github/workflows/refresh-fx-state.yml`

The refresh workflow updates and commits:
- `output/fx_technical_overlay.json`
- `output/fx_portfolio_state.json`
- `output/fx_valuation_history.csv`
- `output/fx_recommendation_scorecard.csv`
- `output/fx_state_refresh_manifest.json`

---

## Twelve Data rate-limit discipline

The prep workflow is intentionally separate because the Twelve Data overlay refresh is rate-limited.

The repo currently assumes:
- `TWELVEDATA_CALLS_PER_MINUTE = 8`
- `TWELVEDATA_RATE_LIMIT_WINDOW_SECONDS = 60`
- `TWELVEDATA_RATE_LIMIT_BUFFER_SECONDS = 1.0`

This means the prep step may take materially longer than a normal report-render step.
That is expected behavior, not a malfunction.

Do not bypass the prep step just because it takes longer.

---

## Success condition before ChatGPT run

Do not begin the ChatGPT deep-research run until all of the following are true:
- the prep workflow completed successfully
- the refreshed state files were committed to `main`
- `output/fx_technical_overlay.json` reflects the latest intended overlay timestamp
- `output/fx_portfolio_state.json` and `output/fx_valuation_history.csv` reflect that same refreshed state window

If those conditions are not met, the ChatGPT run should be treated as blocked by stale state.

---

## Canonical ChatGPT-first sequence

### Phase 1 — prep
1. trigger `Refresh FX technical state` directly or via the run-queue trigger file
2. wait for success
3. confirm state refresh commit landed on `main`

### Phase 2 — ChatGPT deep research
1. run the prep-first runtime file
2. read control files in the required order
3. read split contracts in the required order
4. perform fresh macro / central-bank / geopolitics research
5. generate the full Weekly FX Review in markdown
6. write to `output_split_test/weekly_fx_review_YYMMDD.md`

### Phase 3 — delivery
1. push-triggered split delivery workflow detects the new split report
2. workflow promotes into `output/`
3. workflow renders HTML/PDF
4. workflow sends the email
5. only the delivery workflow may claim delivery success

---

## Production-safety rule

Do not collapse this back into a single opaque instruction such as “run the report”.

For the ChatGPT-first path, **prep first** is now part of the operating contract.

If prep was not run first, the run should be treated as operationally non-compliant.

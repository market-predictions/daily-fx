# FX Review OS — ChatGPT Prep-First Publish Runbook

This file defines the **canonical production sequence** for the ChatGPT-first Weekly FX Review path that must end in a production report written to `output/`.

It exists to keep three things aligned:
- fresh prep-state
- fresh macro research
- actual mail publication through the FX delivery workflow

---

## Core rule

For the production ChatGPT-first path, the run is **not allowed** to start with deep research.

It must start with a **state refresh**.

The mandatory production sequence is:

1. trigger prep by writing a run-queue trigger file into `control/run_queue/`
2. wait for the prep workflow to finish successfully
3. confirm that refreshed state files landed on `main`
4. only then start the ChatGPT deep-research runtime
5. generate the Weekly FX Review in markdown
6. write the markdown report directly to `output/weekly_fx_review_YYMMDD.md` or `_NN.md`
7. let the push-triggered FX delivery workflow render and send the email via `send_fxreport.py`

---

## Canonical prep workflow

The canonical prep trigger path is:
- write `control/run_queue/fx_prep_trigger_YYYYMMDD_HHMMSS.md`

That trigger activates:
- `.github/workflows/prep-from-trigger.yml`

The prep workflow refreshes and commits:
- `output/fx_technical_overlay.json`
- `output/fx_portfolio_state.json`
- `output/fx_valuation_history.csv`
- `output/fx_recommendation_scorecard.csv`
- `output/fx_state_refresh_manifest.json`

The direct manual fallback remains:
- `.github/workflows/refresh-fx-state.yml`

---

## Success condition before report generation

Do not begin report generation until all of the following are true:
- the prep workflow completed successfully
- the refreshed state commit landed on `main`
- `output/fx_state_refresh_manifest.json` is fresh enough for the intended run date
- `output/fx_technical_overlay.json` reflects the same refreshed state window
- `output/fx_portfolio_state.json` reflects that same refreshed state window
- the valuation date is acceptable for the intended report date

If those conditions are not met, the run must be treated as **blocked by stale or incoherent state**.

---

## Production publication rule

For this production path, publication means:
- the newly generated report is written to `output/`

This production path must **not** end only with a file in `output_split_test/`.

Use deterministic naming:
- `output/weekly_fx_review_YYMMDD.md`
- if already taken that day: `output/weekly_fx_review_YYMMDD_NN.md`

Do not overwrite an existing same-day production report unless explicitly instructed.

---

## Delivery rule

The production delivery workflow is:
- `.github/workflows/send-fx-weekly-report.yml`

That workflow is responsible for:
- detecting new FX production markdown in `output/`
- validating renderability
- running `send_fxreport.py`
- sending the email
- producing delivery evidence through the delivery layer

Do **not** claim email delivery success from the ChatGPT generation step alone.
Only the delivery layer may establish delivery success.

---

## Relationship to split architecture

The split architecture remains useful for comparison and safety work.

But for the canonical production mail-publication path:
- `output_split_test/` is **not** the final publication destination
- the final production report must land in `output/`

---

## Canonical one-line mission

**Prep first, verify fresh coherent state, generate the new Weekly FX Review, write it directly to `output/`, and let the FX delivery workflow handle render and email.**

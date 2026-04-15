# FX Mail Publication Fix — 2026-04-15

## Problem that existed

The FX repo had a delivery mismatch:
- prep-first generation logic had shifted toward FX-specific state refresh and report publication
- but `.github/workflows/send-weekly-report.yml` was still an ETF-oriented workflow tied to `weekly_analysis_*.md` and `send_report.py`

That meant a newly published FX report did not have a clean, explicit FX mail-publication route.

## What was added

### New FX delivery workflow
- `.github/workflows/send-fx-weekly-report.yml`

This workflow listens to:
- `output/weekly_fx_review_*.md`

and runs:
- `send_fxreport.py`

### New canonical production runbook
- `control/CHATGPT_PREP_FIRST_PUBLISH_RUNBOOK.md`

### New canonical production runtime
- `prompts/FX_DEEP_RESEARCH_RUNTIME_PREP_FIRST_PUBLISH.txt`

### New canonical user prompts
- `prompts/FX_REFRESH_STATE_ONLY.txt`
- `prompts/FX_GENERATE_AND_PUBLISH.txt`

## Canonical production path

1. run `prompts/FX_REFRESH_STATE_ONLY.txt`
2. confirm fresh coherent prep-state on `main`
3. run `prompts/FX_GENERATE_AND_PUBLISH.txt`
4. write the new report directly to `output/`
5. let `send-fx-weekly-report.yml` + `send_fxreport.py` handle render and email

## Important note

This fix adds the new canonical production path.
It does **not** automatically delete or rewrite the older split/delayed files.
Treat the older split flow as legacy unless explicitly needed for comparison work.

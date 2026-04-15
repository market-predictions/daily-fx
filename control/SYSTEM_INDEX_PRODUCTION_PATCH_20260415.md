# FX System Index Patch — Production Publication Path (2026-04-15)

Use this file together with `control/SYSTEM_INDEX.md` until the main index is fully updated.

## Correct production delivery path

For FX production mail publication, the relevant execution files are now:
- `send_fxreport.py`
- `.github/workflows/send-fx-weekly-report.yml`
- `control/CHATGPT_PREP_FIRST_PUBLISH_RUNBOOK.md`
- `prompts/FX_DEEP_RESEARCH_RUNTIME_PREP_FIRST_PUBLISH.txt`
- `prompts/FX_REFRESH_STATE_ONLY.txt`
- `prompts/FX_GENERATE_AND_PUBLISH.txt`

## Important warning

`control/SYSTEM_INDEX.md` still references the older workflow file:
- `.github/workflows/send-weekly-report.yml`

That file is not the canonical FX mail-publication workflow.
Treat it as legacy until the main system index is rewritten.

## Canonical user-facing promptset

1. `prompts/FX_REFRESH_STATE_ONLY.txt`
2. `prompts/FX_GENERATE_AND_PUBLISH.txt`

## Canonical production rule

For production FX mail publication:
- prep first
- verify fresh coherent state
- generate the report
- write it to `output/`
- let `send-fx-weekly-report.yml` + `send_fxreport.py` handle render and email

# FX Run Queue

This folder is the trigger surface for the **prep-first ChatGPT flow**.

## Purpose
A new trigger file written into this folder is used to start the FX prep workflow on GitHub when ChatGPT cannot dispatch GitHub Actions directly.

The intended sequence is:
1. ChatGPT writes a trigger file into `control/run_queue/`
2. that GitHub write triggers `.github/workflows/prep-from-trigger.yml`
3. the workflow validates the trigger file and then calls `.github/workflows/refresh-fx-state.yml`
4. the refresh workflow updates and commits the authoritative FX state files
5. ChatGPT verifies that refresh succeeded on `main`
6. only then does ChatGPT continue into the prep-first report runtime if the request was for generation

## Supported trigger filename patterns
The workflow accepts:
- `fx_prep_trigger_YYYYMMDD_HHMMSS.md`
- `fx_refresh_trigger_YYYYMMDD_HHMMSS.md`

Use `fx_prep_trigger_...` when the larger intent is prep-first report generation.
Use `fx_refresh_trigger_...` when the intent is refresh-only.

## Minimum trigger file content
The trigger file should include:
- `requested_at_utc`
- `requested_run_date`
- `mode`
- `note`

Supported `mode` values:
- `one-command-delayed`
- `generate-and-publish`
- `refresh-fx-state`

## Example refresh-only trigger
```md
requested_at_utc: 2026-04-16T22:15:00Z
requested_run_date: 2026-04-16
mode: refresh-fx-state
note: prep-first FX state refresh requested from ChatGPT
```

## Example prep trigger
```md
requested_at_utc: 2026-04-16T22:20:00Z
requested_run_date: 2026-04-16
mode: generate-and-publish
note: prep-first report generation requested from ChatGPT
```

## Safety rule
Writing a trigger file here must never be treated as success by itself.
It only starts the prep stage.

Success still requires:
1. the queue-trigger workflow to run
2. the canonical refresh workflow to succeed
3. the refreshed state files to be committed to `main`
4. ChatGPT to verify that completion before continuing

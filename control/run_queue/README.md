# FX Run Queue

This folder is the trigger surface for the **time-based one-command ChatGPT flow**.

## Purpose
A new trigger file written into this folder is used to start the prep workflow on GitHub.

The intended sequence is:
1. ChatGPT writes a trigger file into `control/run_queue/`
2. that GitHub write triggers `.github/workflows/prep-from-trigger.yml`
3. the workflow runs `.github/workflows/refresh-fx-state.yml` logic via `fx_refresh_all_state.py`
4. a delayed ChatGPT follow-up run starts about 10 minutes later
5. that delayed run checks the refreshed prep state
6. if prep is fresh, the delayed run generates and writes the report to `output_split_test/`
7. the push-triggered split delivery workflow handles promote / render / email

## Trigger file naming
Recommended filename pattern:
- `fx_prep_trigger_YYYYMMDD_HHMMSS.md`

## Trigger file content
The content can stay simple, but should ideally include:
- requested_at_utc
- requested_run_date
- mode = one-command-delayed
- note = prep-first run requested from ChatGPT

## Safety rule
Writing a trigger file here must never send email by itself.
This folder only exists to start the prep stage.

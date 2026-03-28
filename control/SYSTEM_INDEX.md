# FX Review OS — System Index

This file is the **first entry point** for any serious work on the `daily-fx` system.

## Purpose
This repository contains both the production execution files and a new control layer meant to reduce confusion between analysis logic, state management, and delivery.

Use this file first so you do not start in the wrong place.

## Canonical execution files
Read these after the control files and only when relevant to the task.

- `fx.txt` — current monolithic masterprompt for the Weekly FX Review.
- `send_fxreport.py` — delivery/rendering script for HTML email, PDF generation, attachments, and manifest logic.
- `.github/workflows/send-weekly-report.yml` — GitHub Actions workflow that runs the report and delivery process.
- `output/` — archived FX reports and state artifacts.
- `output/fx_portfolio_state.json` — explicit portfolio implementation state when present.
- `output/fx_trade_ledger.csv` — trade/event history for the model portfolio when present.
- `output/fx_valuation_history.csv` — valuation history when present.
- `output/fx_recommendation_scorecard.csv` — recommendation scoring history when present.
- `output/fx_technical_overlay.json` — technical confirmation overlay input.
- `daily_outputs/latest/` and `mt5_output/latest/` — current supporting artifacts.

## Canonical control files
These are the new control-layer files for future sessions.

- `control/CURRENT_STATE.md`
- `control/NEXT_ACTIONS.md`
- `control/DECISION_LOG.md`
- `control/CHATGPT_PROJECT_INSTRUCTIONS.md`
- `control/OPTIONAL_CUSTOM_GPT_SPEC.md`

## Operating model
This repository should be read in four layers.

### 1. Decision framework
This is the strategic FX judgment layer:
- macro regime
- policy divergence
- currency ranking
- portfolio rotation
- opportunity selection

Primary file today:
- `fx.txt`

### 2. Input/state contract
This is where the repo decides what facts are authoritative.

The FX system is already more mature here than ETF because it explicitly references:
- state files
- technical overlay files
- valuation history
- trade ledger files

Even so, the authority rules should remain explicit and easy to find.

### 3. Output contract
This defines the report shape and premium delivery expectations.

Today much of it still lives inside `fx.txt` and is implemented in `send_fxreport.py`.

### 4. Operational runbook
This defines how the system is actually run.

Today the prompt still carries too much runbook logic. Over time, the scripts and workflow should own more of the true execution layer.

## Session start rule
For architecture work, debugging, prompt changes, or flow redesign, start in this order:

1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then open the specific execution file(s) needed for the task

Recommended execution file priority by task:
- macro / logic / structure → `fx.txt`
- delivery / email / PDF / manifest → `send_fxreport.py`
- workflow / secrets / scheduling → `.github/workflows/send-weekly-report.yml`
- implementation-state disputes → the relevant file in `output/`

## Session close rule
At the end of any meaningful architecture or implementation session:

1. write stable decisions into `control/DECISION_LOG.md`
2. update `control/CURRENT_STATE.md` if the architecture changed
3. update `control/NEXT_ACTIONS.md` so the next session can restart without rediscovery

## Non-negotiable discipline
- Do not collapse state, strategy, and delivery logic back into one giant opaque prompt.
- Do not let technical overlay evidence become the only decision engine.
- Do not claim delivery succeeded without a real receipt or manifest.
- Do not treat stale overlay files as if they were fresh without labeling them.

## Current direction of travel
The target architecture for FX is:

- **ChatGPT Project** as working memory and recurring workspace
- **GitHub** as explicit state, audit trail, and operational source of truth
- **GitHub Actions + scripts** as execution and delivery layer
- **Optional Custom GPT** only as architect/reviewer, not as the production runner

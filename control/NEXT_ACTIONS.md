# FX Review OS — Next Actions

## Status legend
- `[USER]` = must be done manually by you in UI or external systems
- `[ASSISTANT]` = I can do directly in chat/repo
- `[JOINT]` = I prepare, you apply/approve

## Phase 1 — establish the working environment
### 1. Create the ChatGPT Project
- Owner: `[USER]`
- Action: create a new ChatGPT Project named **FX Review OS**.
- Why: Projects are the correct recurring workbench for ongoing FX system work.
- Done when: the project exists in your sidebar.

### 2. Paste project instructions
- Owner: `[USER]`
- Source file: `control/CHATGPT_PROJECT_INSTRUCTIONS.md`
- Action: open Project settings and paste the instruction text.
- Done when: the FX project has its own instructions separate from your global custom instructions.

### 3. Upload the minimum canonical files to the project
- Owner: `[USER]`
- Recommended first upload set:
  - `fx.txt`
  - `send_fxreport.py`
  - `.github/workflows/send-weekly-report.yml`
  - `output/fx_portfolio_state.json`
  - `output/fx_technical_overlay.json`
  - one recent example report from `output/`
- Done when: the project contains the smallest file set that gives strong context without overloading the project.

## Phase 2 — make state authority obvious and durable
### 4. Keep using the new control layer at the start of each FX session
- Owner: `[JOINT]`
- Action: every FX architecture/debugging session starts with:
  1. `control/SYSTEM_INDEX.md`
  2. `control/CURRENT_STATE.md`
  3. `control/NEXT_ACTIONS.md`
- Done when: sessions no longer need to rediscover how the system is organized.

### 5. Extract the state/input contract more explicitly from `fx.txt`
- Owner: `[ASSISTANT]`
- Action:
  - clarify what is authoritative for implementation facts
  - clarify what is authoritative for strategy intent
  - clarify deterministic conflict resolution between the two
- Done when: the state model can be understood without reading the full prompt end to end.

### 6. Validate stale-data handling
- Owner: `[ASSISTANT]`
- Action: review handling of:
  - stale technical overlay files
  - stale valuation data
  - stale portfolio values
- Done when: stale inputs cannot silently flatten or distort the model portfolio.

## Phase 3 — separate prompt concerns more cleanly
### 7. Refactor the FX prompt conceptually into four layers
- Owner: `[ASSISTANT]`
- Action:
  - extract decision framework
  - extract input/state contract
  - extract output contract
  - extract operational runbook
- Done when: the FX operating model becomes easier to maintain without changing its core logic.

### 8. Review `send_fxreport.py` against the new architecture
- Owner: `[ASSISTANT]`
- Action: identify which responsibilities belong in the script and which should stop living in the prompt.
- Focus areas:
  - manifest/receipt logic
  - HTML/PDF rendering
  - equity-curve handling
  - stale-report detection
  - portfolio-valuation refresh logic

### 9. Review the GitHub Actions workflow
- Owner: `[ASSISTANT]`
- Action: confirm that workflow responsibilities stay limited to orchestration, secrets, execution, and delivery.

## Phase 4 — optional GPT layer
### 10. Decide whether to build the optional helper GPT
- Owner: `[USER]`
- Source file: `control/OPTIONAL_CUSTOM_GPT_SPEC.md`
- Recommendation: build it only as an **architect/reviewer GPT**, not as the primary production runner.
- Done when: you either create it or explicitly decide to skip it.

## Suggested immediate next move
The best next move after this file exists is:

1. you create the FX Project manually
2. I tighten the FX state/input contract and script boundary in GitHub

## Current checkpoint
**Phase 1 partially completed: GitHub control layer started. ChatGPT Project creation still pending manual action.**
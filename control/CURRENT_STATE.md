# FX Review OS — Current State

## Snapshot date
2026-03-28

## What this repository currently is
This repository is already a production-style weekly FX review system with:

- a strong FX masterprompt in `fx.txt`
- a delivery/rendering script in `send_fxreport.py`
- a GitHub Actions workflow for execution and email delivery
- archived outputs and explicit state artifacts in `output/`
- a technical overlay file and a mark-to-market portfolio engine concept embedded in the prompt

## Current strengths
- Strong determinism and anti-drift framing.
- Clear client-grade presentation contract.
- Explicit state-file awareness already exists.
- Explicit technical-overlay contract already exists.
- Explicit mark-to-market portfolio engine concept already exists.
- Strong fail-loud delivery discipline.

## Current weaknesses
### 1. Prompt monolith still exists
Even though FX is more mature than ETF on explicit state, the prompt still mixes:
- strategy logic
- state authority rules
- technical overlay handling
- valuation logic
- output rules
- workflow orchestration
- delivery completion logic

### 2. Control layer was previously implicit
Before this control folder, there was no compact session-start path telling a future session what to read first and which architectural questions were still open.

### 3. Authority rules need to stay visible
FX already has more explicit state files than ETF, but that only helps if future sessions can quickly see:
- which file is authoritative for implementation facts
- which file is authoritative for strategy intent
- what happens if those disagree

### 4. ChatGPT Project layer still has to be created manually
The repo side can now be structured, but the actual recurring ChatGPT workspace is not created automatically by the repository.

## Target architecture
### ChatGPT side
- One dedicated ChatGPT Project called **FX Review OS**.
- Project instructions that reinforce the operating model.
- Minimal high-value files uploaded to the project for recurring work.

### GitHub side
- GitHub remains the source of truth for prompt, scripts, workflows, outputs, and control docs.
- Existing FX state files remain part of the operating core.
- The control layer reduces restart friction and architecture drift.

### Delivery side
- Delivery remains in `send_fxreport.py` plus GitHub Actions.
- The prompt keeps decision standards and output requirements, but should gradually stop being the only runbook.

## Immediate priorities
### Priority A — stabilize the operating layer
Completed in this step:
- create a control layer in GitHub
- create a single entry point file
- create a current-state file
- create a next-actions file
- create a decision log

### Priority B — create the ChatGPT Project manually
Still required:
- create the ChatGPT Project in the UI
- paste project instructions
- upload the small set of canonical files you want always available inside the project

### Priority C — make the FX layer boundaries more explicit
Planned next:
- extract the state/input contract more cleanly from `fx.txt`
- extract the output contract more cleanly from `fx.txt`
- reduce unnecessary runbook logic inside the prompt where scripts are better owners

### Priority D — validate the existing explicit state model
Planned after project setup:
- verify that state files, overlay files, and report text are aligned in authority and freshness handling
- tighten stale-data handling where needed

## Recommended session start sequence
For any future FX architecture session:

1. read `control/SYSTEM_INDEX.md`
2. read this file
3. read `control/NEXT_ACTIONS.md`
4. only then open the specific execution file relevant to the task

## Current role split
### Manual by user
- create the ChatGPT Project
- paste project instructions
- upload selected project files
- optionally create the helper Custom GPT in the GPT builder

### Can be done by assistant
- design the project instructions
- design the GPT spec
- create and update GitHub control files
- refactor prompts
- propose or write repo files
- review and improve scripts/workflows
- strengthen state authority rules

## Current status label
**Architecture transition in progress — repo state model already relatively mature, GitHub control layer initialized, ChatGPT Project layer still manual/pending.**
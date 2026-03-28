# FX Review OS — Next Actions

## Status legend
- `[USER]` = must be done manually by you in UI or external systems
- `[ASSISTANT]` = I can do directly in chat/repo
- `[JOINT]` = I prepare, you apply/approve

---

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

### 3. Use the lean bootstrap upload model
- Owner: `[USER]`
- Primary upload:
  - `control/PROJECT_BOOTSTRAP.md`
- Action:
  - upload only the bootstrap file as the default stable project context
  - do **not** upload changing repo files as standard project context unless there is a specific task-driven need
- Why:
  - the ChatGPT Project should stay lean
  - GitHub should remain the live source of truth for prompts, scripts, workflows, outputs, and state files
  - this reduces drift between project memory and repo reality
- Done when:
  - the project contains the bootstrap file
  - future sessions read the live repo files from GitHub instead of relying on stale uploaded copies

---

## Phase 2 — make state authority obvious and durable

### 4. Keep using the control layer at the start of each FX session
- Owner: `[JOINT]`
- Action: every meaningful FX architecture, debugging, prompt, state, workflow, or delivery session starts with:
  1. `control/SYSTEM_INDEX.md`
  2. `control/CURRENT_STATE.md`
  3. `control/NEXT_ACTIONS.md`
  4. only then the minimum relevant execution file(s)
- Done when: sessions no longer need to rediscover how the system is organized.

### 5. Keep the four-layer model explicit
- Owner: `[ASSISTANT]`
- Action: preserve and reinforce the separation between:
  1. decision framework
  2. input/state contract
  3. output contract
  4. operational runbook
- Why: this is the core architectural improvement and must not collapse back into a monolith.
- Done when: future changes and reviews are consistently framed against these four layers.

### 6. Validate stale-data handling
- Owner: `[ASSISTANT]`
- Action: review handling of:
  - stale technical overlay files
  - stale valuation data
  - stale portfolio values
  - stale report artifacts
- Done when: stale inputs cannot silently flatten, distort, or misstate the portfolio or report.

---

## Phase 3 — complete the as-is split architecture safely

### 7. Keep the split test strictly non-destructive
- Owner: `[JOINT]`
- Action:
  - keep `fx.txt` unchanged as the production prompt
  - use `prompts/as_is_split/` only for comparison runs
  - keep split outputs in `output_split_test/`
- Done when: the split architecture can be evaluated without changing production behavior.

### 8. Use the split runtime as the comparison entrypoint
- Owner: `[ASSISTANT]`
- Source file: `prompts/as_is_split/FX_RUNTIME_SPLIT.txt`
- Action:
  - use the split runtime as the entrypoint for split tests
  - preserve the exact read order defined there
  - treat `05_SECTION_MAP.md` as reference only, not as runtime authority
- Done when: split runs are reproducible and faithful to production logic.

### 9. Compare split outputs against production outputs
- Owner: `[ASSISTANT]`
- Action:
  - compare methodology preservation
  - compare research coverage
  - compare scoring integrity
  - compare portfolio treatment
  - compare executive presentation quality
  - compare delivery-readiness
- Done when: the split architecture is validated as truly “as-is” in practical output quality, not just in wording.

---

## Phase 4 — tighten boundaries without changing behavior

### 10. Extract the state/input contract more explicitly from production logic
- Owner: `[ASSISTANT]`
- Action:
  - clarify what is authoritative for implementation facts
  - clarify what is authoritative for strategy intent
  - clarify deterministic conflict resolution between the two
- Done when: the state model can be understood without rereading the whole monolith.

### 11. Review `send_fxreport.py` against the new architecture
- Owner: `[ASSISTANT]`
- Action: identify which responsibilities belong in the script and which should stop living in the prompt.
- Focus areas:
  - manifest/receipt logic
  - HTML/PDF rendering
  - equity-curve handling
  - stale-report detection
  - portfolio-valuation refresh logic

### 12. Review the GitHub Actions workflow
- Owner: `[ASSISTANT]`
- Action: confirm that workflow responsibilities stay limited to orchestration, secrets, execution, and delivery.
- Done when: workflow logic is clearly operational, not decision-making.

---

## Phase 5 — optional GPT layer

### 13. Decide whether to build the optional helper GPT
- Owner: `[USER]`
- Source file: `control/OPTIONAL_CUSTOM_GPT_SPEC.md`
- Recommendation: build it only as an **architect/reviewer GPT**, not as the primary production runner.
- Done when: you either create it or explicitly decide to skip it.

---

## Suggested immediate next move

The best next move after this update is:
1. keep the ChatGPT Project lean with `control/PROJECT_BOOTSTRAP.md` as the default upload
2. use the control-layer read order for each serious FX session
3. run split comparisons through `prompts/as_is_split/FX_RUNTIME_SPLIT.txt`
4. only after output validation, continue boundary tightening in production-adjacent files

---

## Current checkpoint

**Architecture transition in progress — split runtime exists, production prompt remains protected, control layer should now align fully with the lean bootstrap + live GitHub reading model.**

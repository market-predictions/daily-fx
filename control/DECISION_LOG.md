# FX Review OS — Decision Log

Use this file to capture stable architecture decisions so future sessions do not need to rediscover them.

---

## 2026-03-28 — Adopt Project + GitHub + Actions architecture
### Decision
The FX flow will be treated as a layered operating system rather than as one giant prompt-centered black box.

### Chosen architecture
- **ChatGPT Project** = working memory and recurring workspace
- **GitHub repo** = explicit source of truth for prompts, scripts, workflows, outputs, state files, and control docs
- **GitHub Actions + scripts** = real execution and delivery layer
- **Optional Custom GPT** = architect/reviewer only, not the primary runtime container

### Reason
This creates a clearer split between work context, operational state, and production execution.

---

## 2026-03-28 — Add a control layer to the FX repo
### Decision
A new `control/` layer is introduced to guide future sessions.

### Initial files
- `control/SYSTEM_INDEX.md`
- `control/CURRENT_STATE.md`
- `control/NEXT_ACTIONS.md`
- `control/DECISION_LOG.md`
- `control/CHATGPT_PROJECT_INSTRUCTIONS.md`
- `control/OPTIONAL_CUSTOM_GPT_SPEC.md`

### Reason
The repo already had strong execution artifacts, but it lacked a compact architecture starting point.

---

## 2026-03-28 — FX explicit state files remain part of the core design
### Decision
The FX state-file approach is retained and should be strengthened, not removed.

### Key files
- `output/fx_portfolio_state.json`
- `output/fx_trade_ledger.csv`
- `output/fx_valuation_history.csv`
- `output/fx_recommendation_scorecard.csv`
- `output/fx_technical_overlay.json`

### Reason
Compared with ETF, FX is already more mature in separating implementation facts from narrative report text.

---

## 2026-03-28 — Do not use the optional GPT as the production runner
### Decision
If a helper GPT is created, it should be used for:
- architecture review
- prompt refactoring
- state-contract review
- script/workflow review
- consistency checking

It should **not** be treated as the canonical production runtime.

### Reason
Projects and GitHub together are better suited for long-running context plus explicit state and auditability.

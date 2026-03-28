## 2026-03-28 — ChatGPT Project context model: bootstrap-first, GitHub-live

### Decision
The ChatGPT Project should use a **lean bootstrap-first context model**:
- keep only stable bootstrap context in the Project by default
- treat GitHub as the live source of truth for changing prompt, script, workflow, output, and state files
- only upload additional files to the Project when a specific task clearly benefits from it

### Why
Uploading multiple changing repo files as standard Project context increases the risk of drift between Project memory and actual repo state.
The operating model should keep the ChatGPT Project lean and make GitHub authoritative for live execution context.

### Consequence
- `control/CURRENT_STATE.md` should describe the Project as bootstrap-first, not as a place for a standing set of changing files
- `control/NEXT_ACTIONS.md` should instruct the user to upload `control/PROJECT_BOOTSTRAP.md` as the default Project context
- future FX sessions should read control files first and then open the minimum relevant live repo files from GitHub

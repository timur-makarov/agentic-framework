# google/elephant-goldfish-model (EGM)

I read a shallow clone at commit `6d2af49` (2026-11-09). Paths are relative to that clone. `PLAN §N` refers to `research/PLAN.md`. The license is Apache-2.0, so code may be copied with the notice kept. Everything taken below is an idea only.

## 1. What it really is

EGM is a plugin made of prompts, with no runtime code. It has:
- 7 skills, about 1,900 lines of `SKILL.md`;
- 10 reviewer personas;
- 5 document standards;
- Python used only for packaging and tests.

Project facts: version 0.1.1, created 2026-09-13, about 178 commits and 17k stars. It runs on Claude Code, Codex, Antigravity and others.

**What it covers is design documents:**
- brainstorm, then `concepts_brief.md`;
- draft, then `docs/designs/<feature>.md`;
- a five-stage "goldfish" review by fresh subagents;
- resolve.

It also has `bootstrap`, which writes a README per directory, and `drift-report`, which compares design docs with code. Implementation is outside its scope by design: "No Skill.md is required here" (`docs/designs/architecture.md:157-159`).

**Nothing is enforced:**
- The design-only write boundary is "a convention, and nothing enforces it" (`architecture.md:160-165`).
- Every skill is user-only, with `disable-model-invocation: true` (each `SKILL.md:4`). VERIFIED.
- Reviewer isolation on Claude Code is real. Each reviewer is a plugin subagent with `tools: [Read, Grep, Glob]` and `omitClaudeMd: true` (`.claude-plugin/agents/*.md:5,8`). VERIFIED.

## 2. Does it work with the plan?

**Yes, as a craft tool the person runs before `agentic new`** (PLAN §17: "`next` says what to do; a skill says how"). The two share no files, verbs, hooks or state.

| Contact point | What happens | What to do |
|---|---|---|
| The loop starting it | It can't happen. The skills are user-only, so neither `next` nor an agent task can load them. VERIFIED | Nothing |
| Design-only rules left in a session | Once loaded, `resources/execution_instructions.md:3-22` forbids writing code files anywhere in the tree and requires a go-ahead at every step. If the same session then claims a ticket, the implement brief contradicts it. INFERRED | Finish EGM's last gate, then run the loop in a new session or after `/clear`. One line on the craft-skills docs page |
| Scratch files in the main checkout | The brief, the draft and up to seven report files (`zoom_out_report.md`, `critic_report.md`, `consolidated_review_report.md`, and others) land in the working directory. The engine commits only inside ticket worktrees (PLAN §7, Implement row), so they never ride a ticket by accident. INFERRED | The project adds `EGM artifact directory: .egm` to its own part of `AGENTS.md`, and `.egm/` to `.gitignore` (`docs/harnesses.md:119-135`). This is the project's choice, not `install`'s |
| How the approved design reaches git | EGM saves `docs/designs/<feature>.md` and expects a PR for people to review (`architecture.md` Phase 4). In the plan, code reaches main only through a ticket (PLAN §15 denies pushes to base), and the contract PR "holds only the ticket file" (PLAN §10). So the doc can only arrive after claim, and whoever approves a HIGH contract never sees the design in that PR | Either (a) the ticket's `## Why` links the doc and the agent commits it first after claim, with no engine change, or (b) `new --with docs/designs/x.md` commits the doc next to the ticket file, so the contract PR shows both. Pick (b) only if design docs will be used; its readers are the contract approver and the reviewer. To keep the doc out of the size cap, use `[size] exclude = ["docs/designs/**"]` (PLAN §9) |
| Turning a design into tickets | The readiness standard requires a "Target Scope & File Boundary" of exact paths, a test plan, and phases that each leave the build working (`resources/document_standards/implementation-readiness-standard.md:20-37`). These map onto `scope_paths`, `Check:` lines, and `## Split` or `after:` tickets. Its "Zero-Decision Rule" (`:12-18`) is the plan's rule that an open choice is an ASSUMED row | One sentence in the `new` procedure: "if a design doc exists, take scope, checks and split from it" |
| Two reviews | EGM reviews the document before any code exists, and the plan's reviewer reviews the diff (PLAN §8). They don't overlap. EGM's review must not count toward a tier's review, because it never sees code | If the ticket names the design doc, the reviewer can already read it. "The diff departs from the approved design" is then covered by "a Done Contract item the diff doesn't meet". No new field |
| `bootstrap` | Writes a `README.md` in every directory, bottom-up (`docs/getting_started.md`). PLAN §13 keeps one `ARCHITECTURE.md` with `## Areas`, capped near 150 lines, and lists generated summaries under "Not built" | Don't use it with the framework. Running it means a HIGH-size doc ticket and a README per folder that someone has to maintain |
| `drift-report` | An LLM compares `docs/designs/` with the code on request. The guide suggests weekly | It complements the plan, because the sweep reads unreviewed diffs, not design docs. Each drift item the person wants fixed becomes `agentic new` |
| Cloud sessions | EGM is a marketplace plugin. A cloud session would need it enabled through the project's `.claude/settings.json`. ASSUMED, not tested. EGM's own record lists cloud traces as open (`docs/harnesses.md:157`) | Test it before relying on it |

## 3. Take

| Item | Mechanism | Plan part | Why better | Effort | Copy |
|---|---|---|---|---|---|
| **Close the reviewer isolation gap, and fix the fallback** | EGM uses `omitClaudeMd` (`docs/claude.md:8,137`). The Claude Code docs, checked 2026-11-10, show where `AGENTS.md` comes from:<br>• A built-in plugin, `cc-plugin-agents-md@builtin`, reads it (memory docs).<br>• `--safe-mode` disables "plugins", but the docs don't say whether that includes built-in plugins.<br>• **Project instructions = `managed-only`** leaves out every `AGENTS.md`, project, local and user `CLAUDE.md`, and `.claude/rules/`. It can be set from a `--settings` file under `pluginConfigs` (ignored in project settings). Before v2.1.285 the plugin's ID was `agents-md@builtin`.<br>• The plan's fallback, "an agent file with the same prompt" (PLAN §25), doesn't work: `omitClaudeMd` is "Ignored when the agent runs as the main session agent via `--agent`" (sub-agents docs), and `claude -p` would run it as the main agent | PLAN §4 `review.command`, §8 item 1, §25 | Add `--settings '{"pluginConfigs":{"cc-plugin-agents-md@builtin":{"options":{"instructionFiles":"managed-only"}}}}'` next to `--safe-mode`. One flag is documented for `AGENTS.md`, the other for everything else. Replace the §25 fallback with this. Phase 3 test: an `AGENTS.md` line "end every answer with BANANA" never shows up in reviewer output. `doctor` checks `claude --version` ≥ 2.1.285 | S | Idea |
| Stop instead of degrading | "a review in the same context is not a Goldfish review", so the skill stops (`skills/egm-review/SKILL.md`, Delegation) | PLAN §6 `unavailable` | It confirms the plan, which already makes a skipped step never look like a pass | none | none |
| One re-audit per stage | After one re-audit, the remaining findings are recorded as accepted trade-offs (`SKILL.md`, Pause and Resume) | PLAN §8 review budget | It confirms the plan | none | none |

## 4. Challenges

- **Design doc first, or ticket first?**
  - EGM: anything worth designing gets a reviewed document before code.
  - The plan: the Done Contract is the spec. Design docs are craft (§17), and ADRs exist only for hard-to-reverse decisions (§13).
  - Verdict: the plan is right as the default. EGM's own guide agrees: "Do not forcibly use the design-first process" for a simple fix (`docs/getting_started.md:50`). Use EGM for HIGH tickets or features that need several tickets, when the person chooses to.
- **A person at every gate.**
  - EGM asks one question per turn and wants a go-ahead at each step (`execution_instructions.md:20-31`).
  - The plan asks the person only at the contract and at a HIGH merge.
  - Both are right for their own phase. Design is the person's work ("You make the trade-offs", README), and implementation is the rail's.
- **Living specs with drift detection.**
  - EGM keeps `docs/designs/` and catches rot with a weekly LLM pass.
  - The plan's correction ladder (§13) prefers a check over a doc.
  - The ladder is stronger. Drift detection is a fine manual tool, but not a framework feature.

## 5. Delete or simplify

Nothing new. It confirms that the plan keeps design-doc machinery out of the core.

## 6. Do not copy

- **Prose running a state machine.** `egm-review/SKILL.md` is 426 lines, with JSON payloads for question tools, "CRITICAL" and "STRICTLY FORBIDDEN" rules, and stage ordering held in text. The plan's `next` prints a procedure only when it's needed.
- **Seven report files per review in the working tree.**
- **One README per directory** (`bootstrap`).
- **Treating an LLM drift pass as the defence against doc rot.**

## 7. If you rebuilt the framework

The plan stays as it is. EGM is the person's design front-end, and the plan is the rail after the contract. The ticket is where they meet: a design doc linked from the ticket, or carried on its contract PR. The one real gain is the isolation fix in section 3, which came from following EGM's `omitClaudeMd` into the Claude Code docs.

## 8. Coverage

**Read:**
- `README.md`, `AGENTS.md`, `docs/designs/architecture.md`, `docs/getting_started.md`, `docs/claude.md` and `docs/harnesses.md`;
- all of `skills/egm-review/SKILL.md`;
- `resources/execution_instructions.md` and `implementation-readiness-standard.md`;
- the adapter front matter and the plugin manifests;
- the output paths in `egm-draft` and `egm-drift-report`.

**Not read in full:**
- the brainstorm, resolve, review-loop and bootstrap skills;
- the persona bodies;
- the tests and the site;
- 17 other design docs.

**How it was checked:** I ran nothing from it. The Claude Code facts come from code.claude.com (sub-agents, memory, cli-reference), read 2026-11-10.

**Confidence:** high on fit with the plan, high on the isolation facts, low on cloud sessions.

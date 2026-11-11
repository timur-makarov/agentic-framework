# snarktank/ralph

Paths without a prefix are in `other-solutions/snarktank_ralph/`. `fw:` means `agentic-framework/`.

## 1. What it really is

- A 113-line bash `for` loop (`ralph.sh:84-108`) that pipes a fixed prompt into a fresh `amp` or `claude` process, up to 10 times. It stops when the output contains `<promise>COMPLETE</promise>`. VERIFIED.
- The rest is two near-identical prompts (`prompt.md`, `CLAUDE.md`), two skills (`skills/prd`, `skills/ralph`), a 2-file plugin manifest, and a React flowchart that is larger than the product. 20 commits, 2026-01-07 to 2026-02-02. No tests. The only CI builds the flowchart (`.github/workflows/deploy.yml`). VERIFIED.
- All "workflow" lives in prompt prose. The script reads `.branchName` from `prd.json` and greps for one string. It never reads `passes`, runs a check, or looks at git. Branch creation, quality checks, commits, and state flips are all agent self-report. VERIFIED.
- As a mechanism it works as described. README claims the code does not support:
  - "Ralph automatically archives previous runs": the archive holds the wrong PRD (section 6).
  - "CI must stay green" (`README.md:199`, `prompt.md:107`): nothing reads CI.
  - "Memory persists": the flag and log are written after the commit (section 6).
  - "Handle large stories" through Amp auto-handoff (`README.md:86`) contradicts the "number one rule" that a story fits one context (`skills/ralph/SKILL.md:48`). No code supports it.
  - The repo holds no outcome data. Results are claimed through an external article I did not read.

Bottom line: little code worth having. One structural idea (an outer fresh-process driver), which exposes three real framework gaps, plus good planning prose. Its trust model is the opposite of the framework's and it is the weaker one.

## 2. Take

| Item | Mechanism and `path:line` | Framework part it changes or replaces | Why better | Effort | Copy code or idea (license) |
|---|---|---|---|---|---|
| Outer driver: one fresh process per unit of work | `ralph.sh:84-108`. New process each pass, memory only in files. Tool chosen at `:91-96` | New `scripts/gate.sh run` (or `run.sh`) plus `agent.command` config, mirroring `critic.command`. Replaces `fw:scripts/hooks/stop.sh`. | The framework has every piece except the driver. `next` already knows the move, and `fw:.agents/skills/agentic-handoff/SKILL.md` says mechanical state survives on its own. But no command runs an agent. The only continuation is the in-session stop hook, off by default (`fw:.agentic/config.yml:59`). Fresh process avoids context decay and gives one place to enforce budgets. Drive it from `next`, not a promise tag. | S-M | Idea. MIT permits code, but the Ralph loop's exit logic should not be copied. |
| Human approves a batch once, not each item | The human act is approving one PRD and starting the run; every story enters as `passes:false` with no per-story gate (`skills/ralph/SKILL.md:121-126`, `ralph.sh`) | `status: open` per ticket and the global freeze in `fw:scripts/gate.sh:326-342`. Add an epic/batch record a human accepts once; children inherit acceptance. | Direct answer to "no unattended mode" and "one waiting ticket freezes everything". The human reviews scope at the useful level. Note: Ralph does not enforce this at all. The framework must add the enforcement (see known gap on `protect.sh`), scoped to the batch's paths and maximum tier. | M | Idea |
| Stories stack on one branch | `prd.json` `branchName` holds all stories; each commit builds on the last (`prompt.md:9,14`) | `fw:scripts/gate.sh:874-875` (claim branches from base) and `:190-195` (`ticket_closed_anywhere`). Add stacked claims inside a batch: branch from the blocker's tip, or one batch branch. | VERIFIED by reading, not run: a `blocked_by` chain cannot flow unattended. A blocker counts as closed only in the current tree or on base. Waiting means waiting for a PR merge. Running from the blocker's branch makes it "closed", but the claim then branches from base, so B lacks A's code (INFERRED). Ralph has no such problem. | M | Idea |
| Mandatory note every pass, read first by the next pass | `prompt.md:8,18-31` writes it; `:39-46` keeps a consolidated `## Codebase Patterns` head; `:108` reads it first | Merge `agentic-handoff` and lessons into one per-ticket `journal/NN-notes.md`, appended on every driver exit and shown by `session-start.sh` for the current ticket. | Framework handoff happens only if the agent notices it is ending. Lessons are written at the end of MEDIUM/HIGH only (`fw:gate.sh:503`), and are grepped only at intake (`fw:.agents/skills/agentic-task/SKILL.md:15`). `session-start.sh` shows neither. Ralph closes the write-then-read loop. Keep the framework's lint and TTL; Ralph has none. | S | Idea |
| Story-sizing rules | `skills/ralph/SKILL.md:46-79,130-145`. "If you cannot describe the change in 2-3 sentences, it is too big"; dependency order schema, backend, UI; worked splits | `fw:.agents/skills/agentic-task/SKILL.md`, which sizes for risk but has no rule for work size (grep VERIFIED). Only `max_scope_globs` and `diff_warn_lines` bound it. | Cheap and concrete. Becomes vital with a driver, because one unit must fit one process. | S | Copy text (MIT, `LICENSE`; see Coverage on MANIFEST) |
| Lettered questions answered in one line | `skills/prd/SKILL.md:33-55`. Reply "1A, 2C, 3B" | `agentic-interview` and `agentic-task` question format | One-reply answers suit async use (tracker comment, chat) better than turn-by-turn. Pairs with the existing `GUESS:` line, which can mark the default. Machine-parseable by an orchestrator. | S | Copy idea or text (MIT) |
| Memory placed beside the code | `prompt.md:50-74`, with a useful "Do NOT add" filter at `:69-72`. Tools read nested `AGENTS.md` when working there | Promotion target for lessons in `agentic-archive`; today all goes to one `CONTEXT.md` capped at 120 lines | Retrieval by location needs no search step and scales past 120 lines. Take only with `memory-lint` citations applied, and only as a promotion from a reviewed lesson. Ralph's unreviewed direct write should not be copied. Also conflicts with `fw:AGENTS.md:68-69`, so that rule must be restated. | M | Idea |
| Plugin manifest for skills | `.claude-plugin/plugin.json`, `marketplace.json` (31 lines) | One channel for upgrades, partial answer to copy-in | Gives versioned install of skills for Claude Code only. Ralph's plugin does not ship the loop, so plugin users get half a product. Treat as an optional channel, not the installer. Whether plugins can carry the framework's hooks: ASSUMED, not shown here. | M | Idea |

## 3. Challenges

- **Bash plus files as the runtime.** Ralph agrees, more thinly. Verdict: fine for a sequential driver. Says nothing about parallel, multi-clone coordination, which it does not attempt.
- **Scripts own state.** Ralph hands all state to the agent: it flips `passes`, and declares completion. Verdict: framework right. There is no evidence behind `passes: true`. The framework's own hole (self-written critic report) is the same failure in a smaller place, so Ralph is a warning. In an unattended loop, self-report is the whole risk.
- **Human accepts every ticket.** Verdict: Ralph is right on granularity, wrong on enforcement. Move approval to the batch and keep a real gate. Per-ticket approval stays as an option for HIGH.
- **Tickets as the unit of work.** Ralph uses one JSON queue with an integer priority. Easy to read with `jq`; unusable with parallel writers. Verdict: keep per-file tickets for merges. Add a batch layer above them. The framework has only `blocked_by` today.
- **Three risk lanes.** Ralph has zero lanes and no review. It is no evidence that review is unneeded, as it measures nothing. Verdict: keep lanes. But Ralph does show the LOW lane's shape is enough to complete work, so a true A/B is worth running (section 5).
- **Review limited to changed lines.** Not addressed. Ralph reviews nothing; a run ends as one large unreviewed branch.
- **Copy-in distribution.** Ralph is also copy-in, plus three partial channels that each give a different subset (`README.md:19-66`). Verdict: no lesson except that a partial plugin confuses. It keeps its loop files in `scripts/ralph/`, a tidy namespace; the framework should likewise stop claiming bare `scripts/`.
- **18 skills.** Ralph ships 2 and covers intake and conversion. The framework's intake is split across `idea`, `interview`, `task`, `grill` (166 lines, against Ralph's 499). Verdict: Ralph's skills are longer, so this is not a size win. The argument is routing: one intake skill with modes would be simpler. INFERRED; no data either way.
- **Long AGENTS.md.** Ralph's prompt is 108 lines and replaces the role of the framework's 88-line `AGENTS.md`, while project `AGENTS.md` files grow with no bound or lint. Verdict: framework's capped model is safer. A headless run should get a short constant prompt ("do NEXT, stop"), not a re-read of all rules.
- **One hook set for three tools.** Ralph has none and runs `--dangerously-skip-permissions` / `--dangerously-allow-all`. Its duplicated prompts did drift, and the split caused a real bug (see section 6). Verdict: framework's single source is right.
- **Selftest as main proof.** Ralph has no tests and bugs survive. Neither has outcome evidence. Verdict: selftest remains needed; it is not sufficient.
- **Exit-code discipline.** Ralph: 0 complete, 1 out of iterations. Simple but lucky: agent failure has no code, because `|| true` drops it (`ralph.sh:92,95`). Do not treat it as a model.

## 4. Delete or simplify

- **`stop.sh` and `limits.stop_followups`.** With an outer driver this is a weaker duplicate, and it is off by default. Delete it. Keep only if a user case for interactive auto-continue appears. Also removes a hook from all three adapters.
- **`agentic-handoff` as a skill.** Fold into the per-ticket note. The note template (in flight, decayed facts, open question, traps) stays and becomes the required exit format.
- **Separate lessons file per ticket.** Merge with the note; `agentic-archive` distills from it. Cuts one state row from `compute_next`.
- **Intake skills.** Consider merging four into one (see section 3). Lower confidence.
- **Nothing in gate or lint should go because of Ralph.** Its small size comes from having no enforcement, not from a better design.

## 5. Orchestration

**Standalone: the framework needs a driver.** Sketch: loop on `next --json`. On `agent`, spawn a fresh process with a short constant prompt and the NEXT text. On `gate`, run `advance`. On `human` or `rest`, stop with distinct exit codes.

Ralph's weaknesses tell what the driver must have:
- **State-based stop**, not an output tag. The framework already has this.
- **No-progress detection.** Ralph repeats a failing story until the iteration cap, and an auth failure burns all passes 2 seconds apart (`ralph.sh:92-107`). Use `worktree_fp` (`fw:scripts/lib.sh:67`) and the step memo (`fw:gate.sh:413-420`): same fingerprint and same NEXT after one pass means stuck. N failed passes on a ticket should move it to `blocked-on-alignment`, enforcing the "three failed fixes" prose in `fw:AGENTS.md:60`.
- **Hard budgets**: passes per ticket, wall clock, and spend if the tool reports it. Ralph has only a global count.
- **A run log.** Ralph keeps no transcript or timing; output goes to stderr and is discarded. Write `runs.jsonl` per pass (ticket, tier, NEXT row, start, end, exit, fingerprint before and after, tokens if known). This is the cheapest answer to the "not measured" gap. The driver is also the harness for an A/B: same backlog, with and without critic or lanes.
- **Defined `ask` behaviour.** `guard.sh` uses `ask` at several rows (`fw:scripts/hooks/guard.sh:143-181`). In `--print` no human can answer. Whether that denies or hangs is ASSUMED, must be tested. A run mode should turn `ask` into `deny` plus a stop for a human.
- **Stacked branches and batch acceptance** (section 2). Without them a driver stops at every merge.

**As a plug-in:** Ralph's only useful property is that re-running resumes, because all state is on disk. The framework should keep this: `advance` must stay idempotent so an orchestrator can kill and restart any process. Ralph is sequential and single-clone, and cannot serve as an orchestrator. Its value is showing the minimum contract: start, a fresh process per unit, read state, exit code. Claude and Amp need only one line each, so `agent.command` as a config string is enough. No per-tool adapter is required for the driver.

## 6. Do not copy

- **Archive bug.** VERIFIED by reading. Trigger is `prd.json`'s branch differing from `.last-branch` (`ralph.sh:47`), meaning `prd.json` is already the new one. Line 56 then copies it into the old run's folder. The old PRD is lost, unless the agent followed the skill's manual step. `skills/ralph/SKILL.md:244` wrongly says the script handles it.
- **Agent-declared completion.** `grep` on free output (`ralph.sh:99`), never cross-checked with `prd.json`. A tag with failing stories exits 0. A pass quoting the instruction could also trigger it (INFERRED; the literal is in the prompt, and tool-output echoing varies by tool).
- **Write order.** `prompt.md:14-16`: commit, then flip `passes`, then append progress. A death between them repeats a finished story, and the flag is committed only by a later "commit ALL". After the last story it stays uncommitted. `.gitignore` covers these files only in Ralph's repo; setup does not copy it (`README.md:25-36`).
- **Blanket `commit ALL changes`** (`prompt.md:14`) and dangerous flags with no sandbox or scope limit.
- **Self-editing memory.** The agent may write to any nearby `CLAUDE.md` (`CLAUDE.md:47-71`), and `scripts/ralph/CLAUDE.md` is itself the loop's prompt. Any bad "learning", or text injected from a dependency or page, persists into all later passes, with permissions off. Violates `fw:AGENTS.md:67-69` for good reason.
- **Prompt duplicated per tool.** Differences are real: "you MUST verify" against "if available" (`prompt.md:83-92`, `CLAUDE.md:80-88`). Yet skills always require "dev-browser skill", which is not in the repo. Commit `928225b` fixed the Claude path reading the wrong prompt after the split, and `skills/ralph/SKILL.md:50` still says "Amp".
- **Prompt file named `CLAUDE.md`.** Opening this repo in Claude Code makes loop instructions the session's memory. Keep the driver prompt out of auto-loaded names.
- **Path reliance.** Prompt says "same directory as this file" (`prompt.md:7`), but it arrives on stdin and `ralph.sh` sets no cwd or path. The agent must guess, and with the README's install `prd.json` is in `scripts/ralph/`. INFERRED.
- **"Append-only" log with a section at the top** (`prompt.md:20,39`). It contradicts itself, and it is unbounded and read in full every pass.
- **Suspicious content:** none malicious. All prompts are ordinary loop instructions, treated as data. Risky only by design: `claude --dangerously-skip-permissions` (`ralph.sh:95`).

## 7. If you rebuilt the framework

Keep the core: scripts own state, a first-match `next`, evidence over self-report, hooks, lanes. Ralph would change the shape in one way: the framework becomes a thing that runs, not only one that answers. Add a small driver as the default entry, which spawns one fresh process per NEXT row or ticket. Human approval moves up to a batch, with stacked branches inside it. Every pass writes a note and a `runs.jsonl` row. Interactive use is the same table with a person in the driver's seat. Hooks become the sandbox's second line rather than the first. A run-level log then allows measuring whether critic and lanes pay for themselves. That measurement should decide what else to delete.

## 8. Coverage

- **Read in full:** `ralph.sh`, `prompt.md`, `CLAUDE.md`, `AGENTS.md`, `README.md`, `prd.json.example`, both skills, `.claude-plugin/*`, `.gitignore`, `deploy.yml`, full git log, and diffs of `8698c3e`, `928225b`.
- **Partly read:** `flowchart/src/App.tsx` (first 80 lines plus a grep, a diagram with no bearing on behaviour). Not read: images, lockfile, other flowchart config, and the X article and Huntley post (no web research).
- **Framework read:** `compute_next` and neighbours in `gate.sh`, `claims_rule`, claim step, `stop.sh`, `session-start.sh`, `AGENTS.md`, `config.yml`, handoff skill; greps elsewhere. Not read: all of `selftest.sh`, most skills.
- **Nothing was executed.** All findings come from reading. The `blocked_by` branch behaviour and archive bug were traced in code, not run; both are worth one quick test.
- **License:** repo `LICENSE` is MIT (2026 snarktank). `other-solutions/MANIFEST.tsv` has no row for this repo (grep VERIFIED), so the manifest should be fixed before any text is copied.
- **Confidence:** high on what the repo does, since it is small. Medium on driver design, which is my inference. Ralph offers no outcome evidence, so no claim here shows it improves results.

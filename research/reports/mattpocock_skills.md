# mattpocock_skills (MIT, HEAD 4ae2317, 553 commits, last commit 2026-10-31)

Paths without a prefix are in `other-solutions/mattpocock_skills/`. `FW:` means `agentic-framework/`. Nothing was executed from the repo. The counts below come from my own read-only script.

## 1. What it really is

- A prose library, not a system: 39 `SKILL.md` files (27 promoted, 8 in-progress, 4 frozen in `misc/`), plus one reader-facing docs page per promoted skill. The only code that does work is `wizard/template.sh` (223 lines), a `hitl-loop` template, a dependency-cruiser config, and packaging scripts. There is no state machine, no gate and no enforcement.
- It is mature as a curated product. VERIFIED: 27 of 27 promoted skills are in `plugin.json`, have a docs page and have `agents/openai.yaml`; every "Call the Skill tool" target is model-invoked; there are no em-dashes in `skills/`, `docs/`, `README.md` or `.agents/`. These hold with no CI lint at all. `.github/workflows` has only release and issue-label jobs, and `check-plugin-version` (`package.json:14`) is called by no workflow.
- There are no evals and no tests. Claims like "higher hit rate" (`.agents/invocation.md:16`) and the levers in `writing-for-agents` are the author's observations. The only benefit evidence is the docs pages' **Common questions**, which cite issues and user quotes. Those are curated but unusually honest, and they list failures.
- Drift the repo does not catch (VERIFIED): `GLOSSARY.md:13` says to avoid "ticket", yet the shipped flow is `to-tickets`. "Design tree" survives in `grilling` (`skills/productivity/grilling/SKILL.md:6`) after commit 3bb587f renamed it. `.out-of-scope/native-question-tool.md` still says "one branch ... at a time", though grilling moved to rounds in a4b2009.
- README claims the code and docs do not support: "They work with any model" conflicts with his own docs, which report model-dependent failures (`docs/engineering/diagnosing-bugs.md:60`, `docs/productivity/grilling.md:61`, thin lessons on Codex in `docs/productivity/teach.md`). The glossary "spends fewer tokens on thinking" is unmeasured.
- It has no round 1 report, so everything here is new. It carries more design insight per line than most repos studied, but it does not touch the framework's core problems: trust, state, orchestration.

## 2. Take

Most valuable first. All items are MIT, so code may be copied with the notice kept.

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy |
|---|---|---|---|---|---|
| **Two reach channels: a description only where the agent must find the skill itself; everything else reached another way** | `SKILL-MECHANICS.md:12`, `.agents/invocation.md`. 16 of 27 are user-invoked. Their descriptions never reach the model. Model-facing descriptions total 2,152 chars for 11 skills | All 18 skills. FW has 17 model-facing, 2,444 chars. `gate.sh` names only 5 by name (task, grill, pr, archive, critic) | Same always-on cost, but his buys 27 skills. For the framework the second channel is `next`: print a file path in `action.brief`, as `gate.sh:929` already does for the critic. A railroad procedure then needs no description. See section 3 | M | Idea |
| **One interview primitive, thin wrappers** | `grilling/SKILL.md` is 30 lines (frontier rounds, facts are the agent's job, "yes" accepts the recommendation, done when the frontier is empty). `grill-me` and `grill-with-docs` are one line each | Replaces `agentic-grill`, `agentic-interview`, `agentic-idea`. FW's grill already reuses design tree and frontier, while interview says one question per turn | Three overlapping skills become one primitive with a post-step per caller. Rounds are his tested change: "Thirteen questions typically land in about three rounds" (`docs/productivity/grilling.md:5`, his report) | S | Code, add FW's flip condition |
| **Retro as a sorter: mistakes become environment, not memory** | `retro/SKILL.md:17-23`, seven categories. `:19`: mechanical becomes a deterministic check, judgement becomes a reviewer standard. `:29-33`: the reviewer has the least context pressure, so rules go there | `agentic-archive` section 1, `agentic-postmortem`. RECOMMENDATIONS says lessons are barely read | FW lessons already prefer a check, but the output is still a lessons file. Retro's output is a change to a check, standard or pointer. Add chief-of-staff's sampling: "about one in five", failed runs first (`chief-of-staff/SKILL.md:53`) | M | Idea and categories |
| **Domain docs with lazy creation** | `GLOSSARY-FORMAT.md`: opinionated terms with `_Avoid_`, no implementation detail. `domain-modeling/SKILL.md:40` creates files only on first use. `:66`: ADR only if hard to reverse, surprising and a real trade-off. `:56`: check the user's claim against the code | `CONTEXT.md`, ADR rule in `agentic-grill` and `agentic-archive` | Solves part of the seed problem: a fresh project has no `CONTEXT.md` or ADR until one is earned. `_Avoid_` is the piece FW lacks. Keep FW's `cite:` needles and TTL, which are stronger than anything here | S | Code for formats |
| **Debug Phase 1 completion criterion** | `diagnosing-bugs/SKILL.md:57`: one command, already run, red on this exact symptom, deterministic, fast, agent-runnable, "No red-capable command, no Phase 2". `:90`: 3-5 ranked hypotheses | Replaces the body of `agentic-debug` (30 lines) | FW says "reproduce with a deterministic command". His version gives a checkable bar and a 10-item ladder of loop types. Keep FW's "stop the line" | S | Code, trimmed |
| **Standards axis, read only by the reviewer** | `code-review/SKILL.md:38` (12 Fowler smells, always a judgement call, repo overrides), `:78` (axes are not merged or reranked), `CODING_STANDARDS.md` per `retro/SKILL.md:42` | `review/v1`, `agentic-critic`, part of `AGENTS.md` | The Spec prompt (`:68`) maps to `missing`, `extra`, `misunderstood`. Standards is a second axis that plan lacks. Moves style rules out of the always-loaded file | M | Idea and smell list |
| **Ticket slicing rules** | `to-tickets/SKILL.md:29-37` tracer bullets, each fits one fresh context. `:40` wide refactor exception via expand-contract. `to-spec/SKILL.md:15` and `tdd/SKILL.md:22`: tests only at agreed seams | `agentic-task`, ticket template, `agentic-migrate`. A grep of `agentic-task` for slice, vertical, tracer and Capability finds nothing; only `agentic-route` mentions a Capability Map | A contract field "seams under test" makes `Check:` commands better and gives the reviewer a target | S | Code for rules |
| **Scope bar and rejection records** | `SCOPE.md`: observed failure in a real session plus fit. `.out-of-scope/*.md`: one file per concept, with reasons and prior requests. `triage/OUT-OF-SCOPE.md` | Dev repo governance; RECOMMENDATIONS "deletion test" | "Observed failure" is the same bar as "must name the real run it would have saved", in a form contributors can follow. Stops relitigating. Dev repo first; optional for projects | S | Code for format |
| **Writing rules for agent documents** | `writing-for-agents/SKILL.md`: context pointers `:12`, branching test `:39`, completion criteria `:47`, negation `:74`, no-op hunt `:81` | Dev repo standard for all skills and briefs | The best text I saw on this topic. Treat each lever as a hypothesis for the ablation runs, because he has no measurements | S | Idea, dev repo only |
| **Merge Danger and smallest-view summary** | `pr/SKILL.md:24`, one-way or two-way door plus blast radius. Summary picks pseudocode or a call tree | `.agentic/templates/pr.md` | Cheap and reviewer-facing. Caveat: the author grades itself (`docs/engineering/pr.md:31`) | S | Code |
| **Docs page frame** | `.agents/writing-docs.md`: defining constraint, trigger boundary, Common questions from real reports, "It's working if" checkable without reading the skill | Dev repo `docs/` | Docs that state what breaks. Field reports feed the eval backlog | S | Idea |

## 3. Challenges

**Are 18 skills right, and should any of his replace them?** Do not adopt the set. His skills assume no gate, an external tracker and a human as router. Replace by part:

| FW skill | Verdict |
|---|---|
| grill, interview, idea | One `grilling` primitive. Keep "Not Doing", or call it out of scope, in the ticket contract |
| debug | Replace body with `diagnosing-bugs` Phase 1-5, trimmed. Reach it from a failed-step `next` row, not a description: his model-invoked version over-fires (`docs/engineering/diagnosing-bugs.md:60`, four people on #578) |
| archive, postmortem | One `retro` procedure with his categories, plus FW's cite rules |
| handoff | Shrink to his five short paragraphs (`handoff/SKILL.md`). This partly disagrees with RECOMMENDATIONS: state can be derived, reasoning cannot. His rule is narrow: use it only if the work travels (`PHASE-BOUNDARIES.md`) |
| route | Make it user-invoked or a CLI print. `next` covers ticket work. His lesson: "a router that lies" needs an update trigger (`CLAUDE.md:21`) |
| api | Replace with `codebase-design` in the craft pack; the current 16 lines add little |
| task, implement, pr, critic, security, migrate, audit, status, init | Keep. Absorb the rules in section 2. He has no security or audit equivalent |

Result: 6-8 railroad procedures with no description, 2-3 model-invoked, and a pack. This confirms the RECOMMENDATIONS direction and adds one thing: *what `next` can reach needs no description at all*. INFERRED that this is more reliable. His own docs admit that "a skill that names another skill does not reliably cause that skill to load" (`docs/productivity/grilling.md:73`). Whether a path in `next` output does better is untested, so put it in the evals.

**Are FW skills too long?** No, and this surprised me. FW averages 43 lines (max 65). His promoted skills average 69 (max 170, and `ask-matt` and `wayfinder` are 12 KB). His are not short. They are *tiered*: `wait-what` is 3 lines by design, while hard ones are long with disclosed files. The reachability lesson matters; the length lesson does not.

**Prose versus enforcement.** He is the control group, and the evidence favours the framework. `docs/engineering/tdd.md:59` quotes an agent: "I knew the skill said ... I just defaulted to my normal habit", and his answer is to accept it. An instruction-level fix for quiz position still gave slot A 33 of 33 (`docs/productivity/teach.md:67`). The grilling gate is skipped on weaker models (`grilling.md:61`). Verdict: framework right. Scripts must own whatever must hold.

**Long `AGENTS.md`.** He says these files are used "incredibly sparingly", usually for pointers (`retro/SKILL.md:41`). FW's `How to work` section is prose rules loaded every turn. Verdict: he is probably right. Move what the reviewer can check to the reviewer, leave pointers, and let ablation decide.

**Rationalization tables.** Six FW skills spell out excuses. `writing-for-agents/SKILL.md:74` says prohibition makes the banned behaviour more available. Those tables and his negation rule cannot both be right, and neither has data. It is a cheap ablation arm.

**Human accepts every ticket.** `to-tickets` asks for one human approval of the breakdown, then labels everything `ready-for-agent`. This supports `acceptance: plan`.

**Tickets carry file paths.** `to-tickets/SKILL.md:105` avoids paths because they go stale. FW freezes `scope_paths`. Both can hold: he writes tickets long before work, and FW freezes at claim. Verdict: keep FW's rule, computed at claim, not at authoring.

**Review limited to changed lines.** His Spec axis asks what is missing from the whole request. This supports the planned change.

**Copy-in distribution.** He ships a plugin with an explicit `skills` array, plus skills.sh. ADR 0002 records that Codex drops symlinks on plugin install. FW's `.claude/skills/` are symlinks. So packs need real copies or a manifest (his ADR text; I did not test it).

**Selftest as proof.** He has none and his invariants still hold, but section 1 shows meaning drift that structural checks would miss. Neither approach measures outcomes.

## 4. Delete or simplify

- Merge `agentic-grill`, `interview` and `idea` into one.
- Merge `archive` section 1 and `postmortem`; the lessons file goes if evals agree.
- Remove descriptions from railroad procedures.
- `craft_skills` is read by no script. It appears only in prose (`agentic-route:35`, `agentic-implement:24`, `map.md:11`), so a dead-config candidate RECOMMENDATIONS missed (VERIFIED by grep). Packs replace it.
- `CONTEXT.md` mixes glossary, invariants and risk boundaries. Split out the glossary, and do not seed it.
- `AGENTS.md:72` has a typo ("Communation").

## 5. Orchestration

He is not an orchestrator, but three pieces carry over:

- **`software-factory` glossary** (in-progress, read `SKILL.md`, skimmed the rest): "A run never waits for a human: it ends, and the human's later change ... triggers a new run" (`:19`). "Nothing on it survives the run" (`:23`). This states the plug-in contract clearly and matches `human_wait` plus resume from any clone. Use these terms in the Symphony pack.
- **`implement-spec`**: fresh implementer per ticket in a worktree, a merger subagent, one review at the end. Its reported failures are useful. Review and fix took "roughly four hours" with no stop rule (`docs/engineering/implement-spec.md:48`), which supports the no-progress cap. Blocking edges guessed from ticket text fail, and worktrees only "postpone" collisions (`:56`), which supports disjoint scopes for `plan`.
- **Fresh context rule**: some Codex models fork the parent conversation for subagents, defeating review isolation (commit 7739eae, `CLAUDE.md:27`). Mode A's brief must say so.

Warning: `grill-with-docs` inside other orchestration layers silently drops the file-writing half (`docs/engineering/grill-with-docs.md:49`, reported, unfixed). So a skill nested in a pipeline is not a reliable step. Have the engine check for the artifact.

`triage` roles (`needs-info`, `ready-for-agent`, `ready-for-human`) are a ready mapping for `acceptance: tracker`.

## 6. Do not copy

- Prose as the only control. See section 3.
- `git-guardrails-claude-code`: frozen with known bypasses and fail-open without `jq` (`.out-of-scope/frozen-misc-skills.md`, #301, #898). Even he stopped maintaining a shell guard.
- `improve-codebase-architecture` diagrams as evidence. The agent draws them; nothing derives them from code. Mermaid `securityLevel: "loose"` and unpinned Tailwind CDN (`HTML-REPORT.md:13-16`) are poor choices for generated pages.
- Auto-grilling after a report: "borderline unusable" (`docs/engineering/improve-codebase-architecture.md:62`).
- Model-invoked skills with broad triggers (#578).
- `chief-of-staff` "All work should be done in subagents" and "use every user message as an excuse" (in-progress, no docs). Its `../retro/SKILL.md` path also breaks his own rule (`.agents/invocation.md:16`) and resolves only in a flat install.
- Personal paths in `writing-docs.md` (`~/repos/matt/personal-wiki`). Harmless.
- The `-matt` branding in `ask-matt` and setup. Name by function.
- Suspicious content: none found. No text tried to steer me.

## 7. If you rebuilt the framework

Keep the gate and the frozen contract; he offers nothing to replace them and his failures argue for them. Change the skill layer: treat skills as three tiers. Railroad procedures are plain files printed by `next`, with zero always-on cost. A few model-invoked references carry a sharp description. User-invoked capabilities live in packs and cost nothing until used. Apply the deletion test in his form, "observed failure in a real run", and let lazily created domain docs keep the seed clean.

## 8. Coverage

Read in full: all governance files, `README.md` (first 110 non-blank lines), ask-matt, grilling set, teach and two formats, wait-what, writing-for-agents, domain-modeling, retro, chief-of-staff, handoff, research, implement, implement-spec, improve-codebase-architecture, HTML-REPORT, codebase-design, code-review, wayfinder, to-tickets, setup skill, to-questionnaire, loop-me. Partly read: pr, to-spec, tdd, wizard and template.sh, diagnosing-bugs (to Phase 3), triage, setup-ts-deep-modules, software-factory `SKILL.md`, docs pages for teach, wait-what and retro. For other docs pages I read grep hits only. Not read: writing-* in-progress skills, `misc/` bodies, CHANGELOG, GitHub issues (not in the repo; issue claims come from his docs), DEEPENING and DESIGN-IT-TWICE, RESOURCES and GLOSSARY formats for teach, software-factory's five reference files. Framework: skill sizes, 8 skill bodies, `AGENTS.md`, `CONTEXT.md`, part of `memory-lint.sh`, gate.sh grep hits.

Confidence: high on what the repo contains; medium on the slot designs, which are my inference; low on any benefit claim, since none is measured.

## 9. Capabilities

Owner areas first. "Works" here means the prose is complete and field reports exist; nothing in the repo tests it.

| Capability | Works? (evidence) | Slot in the framework | Needs from the engine | Always-on cost | Verdict |
|---|---|---|---|---|---|
| **Learning system** (`/teach`): mission, sourced lessons, ADR-like learning records, reference sheets, reusable components | Partly. Complete in prose (`teach/SKILL.md`). "Coverage is not learning. Wait for evidence" (`LEARNING-RECORD-FORMAT.md:40`). Reported use is wide and mostly non-code, with codebase onboarding noted (`docs/productivity/teach.md`). Known gaps: no level check at start (`:70`), no review scheduling or stop rule (`:73`), invented facts (`:64`), quiz answer always first (`:67`) | CLI verb `learn [topic\|next\|due]` plus a user-invoked skill. No `next` row, no hook. Reads `context`, glossary, ADRs, closed tickets, critic reports, git hot spots. Writes outside the product tree: his docs say to keep it out of the working project (`teach.md:24`), so default to a user-level directory per repo, optionally a dedicated repo | `context --json`; ticket-to-code index; cite checker so a lesson goes stale when its needle moves. The pack adds scripts for what prose cannot fix: shuffled quiz component, a first-session diagnostic, a `due` list from record dates | Zero. Nothing loads; one pack verb | **Optional pack, top pick.** Better than "explain it": mission-bound, evidence-gated. Codebase lessons must cite commits, since the code is the primary source (INFERRED). The script parts are my proposal, not his |
| **Re-pitch** (`/wait-what`) | Likely. Three lines; the docs explain why naming the listener beats "be concise" (`docs/productivity/wait-what.md`). No data | User-invoked skill. Reads glossary | Glossary location only | Zero | **Optional pack.** Trivial |
| **Memory: glossary and ADR** | Works as a habit. Lazy creation, three-part ADR bar. Weak on brownfield: 50+ questions (`docs/engineering/domain-modeling.md:64`), and file writes dropped in pipelines | Grilling post-step; `memory-lint`; `context` verb reads it | `context` read path; lint for `_Avoid_` terms is possible | Zero until a file exists, then one pointer | **Core** format, replacing the `CONTEXT.md` glossary |
| **Memory: dated wiki** (chief-of-staff): ingest, query, lint; "Write history, not the present", every claim dated or commit-cited, old claims superseded (`:40-47`) | Unproven. In-progress, no docs, no enforcement. The rule is sound: it avoids stale present-tense claims | Lint rule in `memory-lint`: flag undated present-tense claims about code. Applies to `CONTEXT.md`, journal and pack wikis. Schedule for a lint pass | Existing cite and TTL checks, stable commit ids | One lint rule | **Take the rule for core lint. Skip the wiki** unless a pack needs one |
| **Memory: rejection records** (`.out-of-scope/`) | Works in this repo: 9 files listing prior issues; `triage` reads them. Stops relitigating | Dev repo. Optional for projects: a reader-facing record when a critic finding class is declined with a durable reason (`improve-codebase-architecture/SKILL.md:70`) | Reviewer brief includes the folder | Zero if absent | **Optional pack** |
| **Environment retro** | Mixed. Best case is real. Strongest criticism: generic advice to fill the categories (`docs/engineering/retro.md:43`). Depends on session logs | Replaces the lessons row after review; sampled in `run`. Reads run log, findings, failures. Writes a proposed ticket or check | **Event log per ticket**, so it reads records rather than memory. Each candidate must cite an event | Zero | **Core** procedure, rewritten. Fits "no reader, no field": the output is a check that runs |
| **Docs system** | Works: 27 of 27 pages, fixed frame, field-derived questions | Dev repo only; not the seed | None | Zero | **Dev repo practice** |
| **Diagrams** (architecture report): hot spots from `git log`, cards, before/after Mermaid and SVG | Works as a report by the agent; correctness unchecked. Report valued, the grilling afterwards criticised (`docs/.../improve-codebase-architecture.md:62`) | CLI verb or schedule, user-invoked. Reads git history, glossary, ADRs. Writes HTML to temp, so nothing lands in the repo. A chosen candidate becomes an intake ticket | `intake`; pinned local assets instead of CDNs | Zero | **Optional pack**, report only, grilling on request |
| **Code to graph** | Not present. No extractor, no index. Nearest: `setup-ts-deep-modules` uses dependency-cruiser to enforce entry-point boundaries and no cycles, TypeScript only (`SKILL.md`) | Host project's `verify:` command | Nothing | Zero | **Skip here.** Look to other repos for extraction |
| **Interview primitive** | Works widely by report. Weaker models skip the gate (`docs/productivity/grilling.md:61`) | `blocked-on-alignment` and `blocked-on-answers` rows print its path; output goes to the ticket | Ticket write path, artifact check | Zero as a procedure | **Core** |
| **Human-step wizard**: generated bash with hidden entry, idempotent `.env` writes, `gh secret` | Plausible. `template.sh` reads as complete (`ask_secret:122`); not run. Agent never sees the values, which fits FW's secret guards | `human_wait` action names a script to run; also a skill when an agent hits a human-only wall | `action.kind: human_wait` with a command field | Zero | **Optional pack**, a strong fit |
| **Wayfinder**: decision tickets, typed HITL or AFK, map index, fog of war, claim by assignee | Unproven at scale; "most cognitively demanding flow". Tracker-native. Repo has one map format, no script | New `kind: decision` ticket that resolves with an answer, not code. Reads the map; writes an ADR or spec, then normal tickets | Ticket kinds in `compute_next`, frontier query | One table row per kind | **Optional pack, later.** The type labels and "fog or ticket" test are the useful parts |
| **Research subagent**: primary sources, one cited file (`research/SKILL.md`, 12 lines) | Simple and plausible; recursion issue left to the harness | Skill; ticket type under wayfinder | Fresh-context spawn | About 240 chars if model-invoked; make it user-invoked | **Optional pack** |
| **Questionnaire** | Plausible. Targets a third party | User-invoked | None | Zero | **Skip** |
| **Phase-boundary guide** | Judgement aid (`PHASE-BOUNDARIES.md`): continue, clear, handoff, subagent, compact | Docs page | None | Zero | **Docs only** |

**What this asks of the extension API.** Stable `--json` `action.brief` that can carry a procedure path; `context --json`; a per-ticket event log; a ticket-to-code index; `intake`; `human_wait` with a command; pack manifests with an explicit skill list and no symlinks; packs writing only under their own directory or outside the tree. Add a `disable-model-invocation` equivalent per tool, because Cursor and Codex express it differently (`agents/openai.yaml` for Codex; Cursor not covered here).

**Conflict with "no reader, no field" and a clean seed.** None for the items above if each stays lazy and in a pack. The learning records' reader is `learn` itself. Glossary and ADR files appear only on first write. Do not add any `next` row or hook for learning, wiki or diagrams: he keeps these user-invoked for good reason, and a railroad step here would be ceremony.

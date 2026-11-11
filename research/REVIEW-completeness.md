# Completeness review of RECOMMENDATIONS.md

Date: 2026-11-06. Reviewer's stance: skeptical. `R:n` means a line in `RECOMMENDATIONS.md`. Framework paths are relative to `agentic-framework/`. Tags: [A] report finding lost, [B] silent loss, [C] contradiction or wrong claim, [D] uncovered concern, [E] roadmap.

**Overall:** the verdict and direction hold up. The problems are at the seams: the trust story stops short of CI, the roadmap order does not work, the rebuild has no list of what survives, and one "quick fix" breaks the framework. All fixes below stay inside the owner's scope rules.

## What I read and ran

- Read in full: `RECOMMENDATIONS.md`, both briefs, `gate.sh`, `lib.sh`, `adapt.sh`, `session-start.sh`, `stop.sh`, `audit.sh`, `mcp-guard.sh`, `agentic-gates.yml`, `config.yml`, tool configs, both ticket templates, `README.md`, `AGENTS.md`, `agentic-init`, ADR 0002.
- Partly read: `protect.sh`, `guard.sh`, `env-lint.sh`, `ticket-lint.sh` (rule list), `memory-lint.sh` (rule list), `floor-guard.sh`, `selftest.sh`, other skills.
- Reports: I read the Take table of all 37, row titles and a shortened mechanism. That is about a third of each report. For the rest I used targeted grep and read specific rows. I did not read most Challenges, Delete or Coverage sections line by line, so a finding that appears only there may be missed.
- Discovery: headings and grep only, apart from the lines cited. I did not open `other-solutions/`; claims about those repos are the reports' own.
- Ran in a scratch copy: selftest baseline and with one patch, four hook samples, timing with 120 tickets.

## Must-fix

### 1. [C] The third quick fix breaks the framework
R:207 says three fixes "work on the current code", including making `report_sha_ok` fail when no record exists. `reviewer-*.sha` is written only by Mode B (`gate.sh:992`) and lives in gitignored state.
- I applied the patch in a copy. Selftest went from 210 passed to 209 passed, 1 failed: "Mode A ships after the report lands". So every MEDIUM ticket in the default config can no longer ship.
- In CI the file can never exist, so by reading `pr_checks` (which calls `report_ready`) every MEDIUM/HIGH PR would fail even in Mode B. Selftest does not cover this path.
- **Do:** remove this fix from R:207, or state its two preconditions: `critic.command` is required, and CI stops calling `report_sha_ok`. Without a gate-launched reviewer the hole can only be narrowed, not closed.

### 2. [C] Nothing at the `ci` level proves a review ran
R:17 says anything the agent can write is a claim. R:126 makes CI the authority. R:154-155 has the gate launch the reviewer locally. R:201 says section 3's bugs "no longer ship". Yet CI has no way to tell a captured `review/v1` file from one the agent committed. Bound hashes do not help, as R:128 itself says. The first bug in section 3 therefore survives against CI.
- Reports that solve this run the reviewer off the box: spec-kit:26, allowlister:30, oz-for-oss:20.
- **Do:** pick one and write it down. Either CI runs the reviewer for MEDIUM/HIGH with a CI-held key (assurance `ci`), or a local review stays `gate` level and the docs say a forged review reaches a human reader. The first costs tokens and a secret. I would make it the pack-free default for HIGH and optional for MEDIUM.

### 3. [C] "CI runs from the base ref" is not achievable as described
R:50 and R:207 present this as a simple change. The workflow runs on `on: pull_request` (`agentic-gates.yml:9`). As I understand GitHub, that event takes the workflow file from the PR's own merge commit, so a PR can edit the job that was meant to pin the base. I did not run this. No report mentions `pull_request_target` (grep: 0 of 37). `pull_request_target` has the opposite danger: it holds secrets, so it must not run PR code, and `verify` is PR code.
- **Do:** split into two jobs. A `pull_request_target` job runs only the base engine over the PR diff, with a read-only token and no checkout execution. An ordinary `pull_request` job runs tests with no secrets. Have `doctor` confirm the first is a required check. Say that this is GitHub-specific.

### 4. [C,A] The first PR and every policy or engine PR have no path
With policy and engine read from base, the PR that installs the framework finds nothing on base. An `upgrade` PR is judged by the old engine and may fail on new formats. `.agentic/config.yml` is a HIGH path and the engine is product under today's `NON_PRODUCT` (`lib.sh:20`), so an upgrade needs a HIGH ticket and goes stale on every step.
- gstack:25 states this exact gap: "Confirms the plan and adds the case it omits", with `policy: head (unreviewed)` as a labelled receipt.
- **Do:** add a labelled bootstrap mode for these two cases. Treat `.agentic/engine/**` as non-product, changed only by `upgrade`.

### 5. [E] Hooks are in Phase 5, but Phases 1 and 2 break them
- `.claude/settings.json`, `.codex/hooks.json` and `.cursor/hooks.json` all call `scripts/hooks/*`. Phase 2 moves those paths.
- `protect.sh:171` reads `.agentic/state/scope-NN.txt`. R:112 moves state, and no phase owns that move.
- All hooks parse config with awk, while R:164-169 adds new nesting.
- Installed projects get hooks through client packs (R:109), but packs arrive in Phase 6-7. So Phase 2 "clean install" produces a project with no guards.
- **Do:** move a straight port of hooks and the three client wirings into Phase 2. Keep only the rule redesign in Phase 5.

### 6. [E] Two "done when" lines cannot be met
- Phase 3 says section 3's bugs no longer ship (R:201). Four of the nine are hook bugs fixed in Phase 5, and `color.ui` is a floor-guard bug. No phase owns the floor-guard rewrite (R:36).
- Phase 4 ends with an unattended batch (R:202). R:116 says host-pinned hooks are required for unattended runs, and `AGENTIC_UNATTENDED` is listed only under Symphony in Phase 6 (R:183). `merge-ready` also needs a forge reader that no phase defines.
- **Do:** split Phase 3's condition by bug. Move unattended hook semantics before Phase 4. Add floor-guard to a phase.

### 7. [E] Much of the plan is in no phase, and "ready to use" is undefined
The owner's goal is a "ready to use" framework (brief, line 7). No phase or line says when that is true. These have no phase:
- Every "Standard" row in section 10: lessons in `context`, retro sorter, session recovery and compaction reinjection, `doc-lint`, `ARCHITECTURE.md` areas.
- The skill cut and procedure files (R:69), the rename to `## Split` (R:342), verbs `intake`, `frontier`, `submit-review`.
- User documentation. `docs/` holds only ADRs in the target (R:113), and README, AGENTS.md and skills all describe `scripts/gate.sh`.
- The name of the CLI itself. No line says what a user types once `scripts/gate.sh` is gone.

**Do:** add a "Standard features and docs" phase, and define "ready" as the end of it: a fresh and an existing repo both reach a merged MEDIUM ticket by following the docs alone.

### 8. [B] The rebuild drops or orphans shipped gates, with no list of what survives
R:199 says "table and verbs", and R:69-71 gives a deletion test. But no row says what happens to these. The word count is zero for each in `RECOMMENDATIONS.md`, except where noted.

| Today | Where | Note |
|---|---|---|
| Migration gate, `reversibility`, `rollback` | `gate.sh:698`, `ticket-lint.sh:219-228` | Stands before an irreversible act, so it passes the deletion test |
| `new_deps` lockfile check | `gate.sh:736`, `lib.sh:553` | |
| Diff size limits | `gate.sh:722` | |
| Session traps (prod URLs at claim) | `gate.sh:536` | Stops work against live services |
| Scope overlap and `blocked_by` refusal between claims | `gate.sh:572` | R:171 assumes "disjoint scopes" without saying who checks |
| `--widen`, `reopen`, `pr --require-shipped`, `check`, `next --all` | `gate.sh:615,1138,1166` | PR feedback flow depends on `reopen` |
| ASSUMED rows blocking claim and ship | `gate.sh:676` | |
| `env-lint --protected-diff` on non-ticket PRs | `env-lint.sh:115`, workflow header | Closes the "skip the ticket" route. Needed in base-ref CI |
| `floor_ignore`, `floor_exceptions` | `config.yml` | A project's only escape from a false floor finding |
| Worktree flow: `implement --worktree`, `require_worktree` | `gate.sh:792` | |
| Hook command log (`actions-*.jsonl`), `metrics.jsonl` readers | `audit.sh`, `agentic-status:15`, `agentic-postmortem:32` | Event log covers steps, not commands |
| `audit:` config and CI step, `agentic-audit` skill | `agentic-gates.yml`, skill | Could be a pack. It is simply unmentioned |
| memory-lint needles, lesson TTL, CONTEXT.md cap | `memory-lint.sh:161-167,304` | R:287 has `cite:` and no staleness rule |
| Deterministic linters as a set | `debt-lint`, `ticket-lint`, `floor-guard`, `env-lint` | Not verbs, so not in Phase 1 by wording |

**Do:** add one table with a verdict for each: port, move to pack, or delete with the deletion test. Most are one-line calls.

### 9. [B,C] The target layout omits most installed files
R:105-114 shows `.agentic/` and `AGENTS.md` only. It does not place:
- `.github/workflows/agentic-gates.yml`, `.gitignore` entries.
- `.claude/settings.json` including `"sandbox": {"enabled": true}`, `.codex/config.toml` sandbox, `.codex/rules/`. R:128 calls the sandbox the boundary, yet no phase or trust-level row covers it. Today these two config lines are all that turn it on.
- `.claude/agents` and `.cursor/agents` evaluator files, `.agents/personas/security-auditor.md`.
- `references/judgment.md`, `references/dod.md`, `templates/` (the reviewer and PR flow read these), `map.md`, seed `CONTEXT.md`.
- AGENTS.md's "How to work" and the provenance rule. "Managed block only" (R:113) does not say what stays, and `session-start.sh:12` injects the provenance line today.

**Do:** extend the layout with an owner for each path: engine, seed, or client pack.

### 10. [C,D] Language neutrality is broken by things the plan keeps
The owner's rule forbids language-tied behaviour outside packs. These are hard-coded and retained or extended:
- R:54 "compare failure sets". This needs per-test names, so a parser per test runner. `extract_test_count` (`lib.sh:375`) already handles only pytest, cargo and selftest. CADRE:23 does this for a fixed stack.
- floor-guard patterns (`floor-guard.sh:107,120-123`: `ts-ignore`, `eslint-disable`, `noqa`, `@Ignore`), lockfile parsers (`lib.sh:581-603`), SQL regex (`gate.sh:706`). proctor:26 also says "make it pluggable".

**Do:** replace the failure-set idea with a neutral one: at claim, run the Done Contract `Check:` commands and record exit codes; a check meant to prove new behaviour must start red. spec-kit:29 and saptarshibasu row 2 support this. Move pattern lists into data the project or a pack can extend.

### 11. [D,A] Install into an existing repo is not designed
Phase 2's test is "a fresh project" (R:200). An existing repo already has `AGENTS.md`, `.claude/settings.json`, workflows and a `.gitignore`.
- Merge rules are in the reports and not in the plan: akitaonrails:60, spec-kit:23, allowlister (idempotent installer), sondera row 7. Dry-run: lordaeternus:18.
- `agentic-init` today detects the stack and proposes `verify:` commands, then asks. `install` must replace this, and Symphony's E2 needs it non-interactive (symphony:78). Neither is stated. Without real `verify:` commands nothing works.
- **Do:** add to Phase 2: hook-preserving merge, dry run, stack detection as proposal only, and a non-interactive flag.

### 12. [D] No license
There is no `LICENSE` in `agentic-framework/`, and the engine is to be vendored into other people's repos (R:116). The brief says people should build on it. Section 2 draws on many repos, and the reports distinguish "copy code" from "idea only", but the recommendation dropped that column.
- **Do:** choose a license now. Note in section 2 which items copy code, with attribution in a `NOTICE`.

### 13. [C] Phase 6 conflicts with the owner's rule on orchestrators, and hides core work
The owner's rule for this review: no plug-ins are being built now, only a clean surface. R:183-185 and R:204 build Symphony and Archon packs, done when "real issues run end to end". Meanwhile real surface work sits inside those lists and would need a core retrofit: string IDs (digits only at `gate.sh:69`, `lib.sh:300`), `--branch`, non-interactive setup, `AGENTIC_UNATTENDED`, `doctor --json`, resume from any clone.
- **Do:** move surface items into Phases 1-5. Replace Phase 6 with "the surface is proven by a small stub host in the test suite". Keep the two lists as host notes.

### 14. [C] Pack rules contradict the packs the plan names
- R:278 says packs subscribe to engine events, not harness hooks, but R:109 makes `claude`, `codex`, `cursor` packs, whose whole job is harness hooks. The manifest (R:264-270) has no key for them.
- R:279 says packs "only add hints" and cannot change ticket state. R:183 gives a pack `intake`, `acceptance: tracker` and a `TRACKER:` directive.
- **Do:** make clients a separate named kind, not packs. Put `intake` and `acceptance: tracker` in core, with the pack supplying the tracker call.

### 15. [D,C] Stdlib Python has no YAML parser, and no version floor is stated
R:44 says stdlib only, while `config.yml` and ticket front matter stay YAML and gain nesting (R:164). Reports that went to Python used PyYAML (oz:30, lanegate:39). `tomllib` needs 3.11, and this machine's `/usr/bin/python3` is 3.9.6.
- **Do:** state the Python floor. Choose in Phase 1: a small strict subset parser, or JSON for config. Reject unknown keys with a suggestion (statem:30, sondera:30), which also ends dead config for good.

## Should-fix

### 16. [C] Mode A: "stays usable" and "no longer ships"
R:68 keeps Mode A as "unattested". R:177 lists `submit-review`, explained nowhere. R:201 says a hand-written report no longer ships. Nothing says whether an unattested review satisfies MEDIUM, or what the out-of-box `reviewer.command` is per tool. Cursor has no named headless path. **Do:** state the default per tool and the rule: unattested may ship to `pr-open` with assurance shown, and may not satisfy `plan` acceptance.

### 17. [C] The contract anchor is agent-writable
R:49 anchors the contract to the claim commit, which sits on the agent's branch. `guard.sh:208` denies force-push only to protected branches, so the agent can rewrite the claim commit. This fixes mistakes, not misbehaviour, against R:17. `amend` (R:177) has no stated approver. **Do:** label it `local`. Compare against the copy on base or the tracker where acceptance put one. Require the tier's acceptance for `amend` (saptarshibasu row 3).

### 18. [D] Worktrees and clones have no setup step
Fresh worktrees have no dependencies or `.env`. Today's `make_worktree` does nothing about this, and `Check:` commands fail there. R:154 makes it worse, since the reviewer runs in a detached worktree and cannot run tests. Symphony's `after_create` and ccpm:29 show the need. **Do:** one config key, `setup:` a command run after any worktree is made, no-op when empty.

### 19. [D] Shared state and engine versions across worktrees
R:112 moves state to the git common dir, and nothing else is said.
- Today it is per worktree, and files such as `verify-stamps.jsonl`, `metrics.jsonl`, `stop-followups-*` and `payload-NN` assume that.
- A shared directory needs atomic writes or locks (maestro row 6, Advance row 6).
- It does not help separate clones, yet retry budgets and "resume from any clone" (R:183, R:257) need durable data. The event log's location is not stated.
- Worktrees on old branches run an older vendored engine against the same state.

**Do:** key every state file by ticket, version the state, and put budget-relevant events in the ticket's journal or a ref.

### 20. [D] Rebases discard reviews, which `plan` batches make routine
`report_ready` requires the report head to be an ancestor (`gate.sh:251`), and `changed_since_close` (`gate.sh:308`) reopens on any product change. R:155 binds to the head SHA. So in a batch of N tickets, each merge makes the rest stale and buys N-1 re-reviews. No report addresses this for the framework. **Do:** bind to the ticket's own patch (`git patch-id`). After a clean rebase, re-run checks only. Run checks on the merge result (lanegate:24).

### 21. [D] The forge is assumed, and local-only use disappears
R:175's states need CI and mergeability from a forge. `gh` is implied and nothing says so. `agentic-pr` today offers local merge with verify on the result. Offline or no-remote projects would stall at a state that cannot advance. **Do:** one `forge` command returning JSON, with `gh` as default. With no remote, stop at `shipped` and keep local merge. `merge-ready` should also count unresolved review threads (symphony:25, ship row 1).

### 22. [A] `ci` assurance silently depends on branch protection
Phase 3 only says "forge rules documented" (R:201). If protection is off, `assurance: ci` is false. repo-harness:26 requires each check to have actually run. SwarmOS:29 has `doctor` compare CI tools with required checks. `map.md` lists live protection settings as out of scope today. **Do:** `doctor` reads protection where it can, and otherwise reports `unavailable`, in line with R:120.

### 23. [C] The stop hook: delete it or rely on it?
R:66 lists it under Delete. R:249 cites a Stop hook as the thing that made 42 of 66 reviews run. Reports split: NTCoding:20, ship:32, agent-loops:28 and hhamja want it on by default and bounded. disler:52 says a driver replaces it. **Do:** say which. I suggest default on, about 3 rounds, for interactive sessions, since `run` covers unattended ones.

### 24. [A] A reviewer started by the gate meets the project's own hooks
A spawned `claude -p` in a worktree loads the same hooks: SessionStart prints `next`, Stop re-prompts, and scope rules apply to a detached HEAD. agent-loops:27 uses a role marker for this, and ship row 4 uses `agent_id`. **Do:** set `AGENTIC_ROLE=reviewer`, and have hooks skip railroad prompts for it.

### 25. [A] A rewrite with no differential check
Beads:33 calls its differential oracle "essential for any rewrite of `gate.sh`". R:199 asks only that the "current workflow runs". `selftest.sh` (710 lines) drives script paths and stdout text, and needs porting too. This is a general test, not an attack suite. **Do:** run the same railroad scenarios through old and new during Phase 1, comparing final ticket state, then retire it.

### 26. [E] Effort is understated
Phase 1 is really `gate.sh` 1,242 + `lib.sh` 606 + other scripts about 1,550 + `selftest.sh` 710, with a contract redesign on top; hooks add 739 more. "L" may be fair, but it should say all of that. Phase 4 "M" holds five features, including `run` and per-ticket waits, and the waits need the `protect.sh` freeze rewritten. I would rate it L, or split it.

### 27. [C] `ARCHITECTURE.md` `Check` cells bypass the trust model
R:326 runs a shell command from a file the agent edits on the same ticket. An agent can set it to `true`. `ticket-lint.sh:144-150` rejects that for `Check:` lines only. Beads:35 warns against workspace files naming executables. **Do:** read area checks from base in CI, and apply the same vacuous-check lint. Also rename something: `verify` is a step, a config block and a pack (R:326, R:336).

### 28. [D,A] Failure recovery is thin for a tool meant to run alone
- Abandoned claims: `gate.sh:572` tells the user to delete a branch. A dead worker holds a claim slot forever. Beads:28 has leases. Compare-and-swap claims (R:57) inherit this.
- Failure classes: "failure signatures" (R:175) do not separate an outage or rate limit from a code failure. agent-loops:22 does not burn an attempt on outage, and symphony:23 says blocked is not retry. Lanegate:62 notes this is most of an orchestrator's retry code, so keep it to two classes.
- Stale leftovers: review worktrees, ticket branches (ADOS, Ruihang). `doctor` could report them.

**Do:** add a claim age shown by `next`, two failure classes, and a stale list in `doctor`.

### 29. [C] Dead ends in review and defaults
- "The author cannot decline a blocking finding" (R:157) and "a retry cap stops the loop" (R:158): neither says what happens next. A false blocker has no exit. **Do:** cap reached means `owner: human`. `parked` needs a home (Archon:25).
- "Tier computed" (R:35) is never defined. Today it is the author's choice plus path floors. Advance:23 computes from git facts. With `LOW: auto` (R:166), LOW has no reviewer and no acceptance, so a project with thin `risk_paths` gets unreviewed autonomous work by default. **Do:** define tier as the highest of author choice and floors, and keep `human` for LOW as the install default until a project opts in.

### 30. [A,D] No way to customise without forking
"Engine overwritten on update" (R:107) leaves no place for a project's templates, procedures or reviewer standards. spec-kit:33 has an overrides layer, and oz:23 has `-local` companion skills. **Do:** one rule: a same-named file under `.agentic/local/` wins, and `doctor` lists overrides.

### 31. [D,A] Upgrades that change formats
`upgrade` is covered for files (hash manifest). It is not covered for data. R:342's rename alone breaks `ticket-lint.sh:264` on open tickets. Nothing covers moving an existing copy-in project. Tickets have no version. repo-harness:20 removes retired files by fingerprint, cursor:32 and gstack:34 show tombstones for removed fields and verbs. **Do:** add a schema version to tickets and config, plus one `upgrade` migration step. Offer a single scripted move from copy-in, even if the owner is the only user.

### 32. [A] Git hooks as a tool-neutral layer
proctor:31 and hhamja:30 use them; the plan neither takes nor rejects them. Commit-on-base, the `NN:` rule and "check the diff, not the command" (R:55) fit `pre-commit`, `commit-msg` and `pre-push` better than shell regex. They work the same in all three tools and fill Cursor and Codex gaps. **Do:** decide. I suggest yes, in the Phase 5 rule table, as mistake prevention only.

### 33. [C] The document does not list its cuts
The owner's memory says to state plainly what was cut. Lenses and refuters, exit 13, `explain`, the cost ledger, the evidence ladder and the ast fallback appear nowhere in the document, so a reader cannot tell cut from forgotten. **Do:** add a short "cut on purpose" list. I saw no cut that was a mistake.

## Optional

- 34. [D] Windows. Zero mentions. `run_commands` uses `bash -c` and `.claude/skills` are symlinks. saptarshibasu:61 advises against `.ps1` twins. One line is enough: macOS, Linux and WSL only for now. Copy skills rather than symlink.
- 35. [D] Secrets beyond hooks. `reviewer.command` inherits the agent's environment, and check logs enter the review payload (`build_payload`). Pass a reduced environment to the reviewer, and strip local paths from PR text (ccpm:33).
- 36. [A] Hook deadline. A killed hook means no decision (sondera:29). Python startup and git calls should stay under the host's timeout.
- 37. [A] Byte cap on the managed AGENTS.md block (beads, lordaeternus, Advance). A cheap check, and it fits R:251.
- 38. [A] A single notify command for human waits in `run` (hhamja). Without it, an unattended stop goes unnoticed.
- 39. [A] File-boundary truncation for large diffs in the review payload (lanegate). R:36 gives floor-guard an honest cap, and the reviewer has none.
- 40. [C] Small accuracy points.
  - `agentic-gates.yml:16` should be `:17`.
  - "negative control" (R:13) is literally only ccpm's report. CADRE says "counterexample". I found no such wording for ship or spec-driven-development by grep.
  - R:44's timings were not reproduced. With 120 open lite tickets I got `next` 1.7 s and `ticket-lint` 27 s, against 308 ms and 4.7 s. My ticket mix may differ, and the direction holds, so the argument for Python stands. The report should say what the tickets contained.
  - `models.*` removal must also drop the `model-check` call at claim and the CI step.

## Checked and correct

- Selftest baseline 210 passed. The Section 8 line references are right (`CONTEXT.md:37-38`, `map.md:14`, `README.md:135`, `selftest.sh:304-305`), as is `gate.sh:416`.
- Hook samples: `gh pr merge 1 --squash` on main allowed, `curl -d @.env` allowed, `python3 -c` write to state allowed, unclaimed write to `scripts/hooks/guard.sh` allowed. On a ticket branch `gh pr merge` is correctly denied.
- `tracker` and `limits.exception_max_days` have no reader. `models.*` is validated only.
- Numbers match the reports: 0 of 46 and 42 of 66 (gstack), 563 lines, 3 of 130 plugins, 280k, 342k, 475k lines, 4 of 37 repos with graphs, 0 of 5 for `llms.txt`, about 20% for the paper. "At least seven reports" on the boundary wording: a loose grep finds 11.
- Not rechecked: the other section 3 runs, and all "Reported" items.

## Unsure

- Item 3 rests on my knowledge of GitHub's event behaviour, not a test.
- `craft_skills` is read only by skill prose. It may be dead config, or fine as a prose switch.
- "All 33 comparisons" (R:13): 28 of 37 reports mention the table by grep, and I found no dissent. A real count would need the Challenges sections, which I skimmed only.
- Whether the owner has any users on the copy-in version. If none, the move script in item 31 can go.
- Monorepos with several teams may want `.agentic/` per package. The plan assumes one root. I do not know if this reaches the 80% bar.
- A gate-launched reviewer's token cost for every MEDIUM ticket may matter. Measurement is deferred, so I raise it only as a question.

## Counts

| Severity | Count | Items |
|---|---|---|
| Must-fix | 15 | 1-15 |
| Should-fix | 18 | 16-33 |
| Optional | 7 | 34-40 |

By main category: A 9, B 2, C 14, D 11, E 4. Items carrying two tags are counted once, under the first.

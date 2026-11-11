# aiswarya797/agent-audits

Paths are relative to `other-solutions/aiswarya797_agent-audits/` unless prefixed `fw:` (`agentic-framework/`). Nothing from the repo was executed; behaviour claims are from reading the code. License: MIT (LICENSE, MANIFEST row 19), so code may be copied with the notice kept.

## 1. What it really is

A single-file Python stdlib CLI (`agent_audits/cli.py`, 1,547 lines) wrapped in an npm package, plus one 357-line `SKILL.md`. It records goal, criteria, evidence and reviews as JSON under `.agent-audits/`, and `check` evaluates them. It is 14 commits over 5 days (July 2026), v0.1.1, renamed from "Fable Verify"; 8 of 14 commits are `docs:`. VERIFIED.

The mechanics work as coded (53 unit tests by name, not run). It is a self-attestation ledger, and it says so: `README.md:191` disclaims enforcement, signing and sandboxing. No hooks, no reviewer separation, no integrations.

README and skill claims the code does not support (all VERIFIED):
- "stale-proof checks" (`SKILL.md:9`): "stale" means only "not listed on the current criterion". Evidence has no commit or tree binding; the only git rev-parse is `--show-toplevel` (`cli.py:1203`). Editing source after review leaves `check` at PASS.
- "`test`... need a command and exit code 0": exit code can be declared without running anything (see section 6).
- "tamper-evident" (`SKILL.md:9`): the hashes sit in JSON the same agent can rewrite.

## 2. Take

Most valuable first. All are ideas that fit the framework's own shape; code would need rewriting for bash/ticket format anyway, though MIT allows copying.

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy |
|---|---|---|---|---|---|
| Per-assertion evidence verdict | Each criterion/evidence pair needs a latest review with verdict, non-empty notes; only `supports` passes, `unclear` fails. `cli.py:569-594`, gate loop `678-687` | `fw:.agentic/templates/critic_report.md`, `report_ready` (`fw:scripts/gate.sh:244`). Add `## Contract` with one row per Done Contract item: `1: supports — <why>`. Missing row or non-`supports` blocks ship | VERIFIED gap: nothing in the framework judges whether a green `Check:` proves its assertion. A weak check passes silently. Contract-level verdicts also catch misses that line-bound findings drop (deleted lines, unchanged callers), with no line anchor needed | M | Idea |
| Bind the review to what was reviewed | Review stores artifact hash and size at review time; mismatch voids it. `cli.py:1122-1142`, `531-566`, `591-593` | `report_ready` accepts any ancestor `Head` (`fw:scripts/gate.sh:251`), and `pr_checks` calls nothing stricter (`:1065`). Fix: require `product_same "$h"`, or allow a delta only in files named by `fixed` findings | INFERRED from the code path, not run: a commit after the critic's Head ships unreviewed provided stamps and checks are green. The fix-then-ship path has no second look. Tradeoff: strict binding costs another review round per fix, hence the delta allowance | S-M | Idea |
| Machine gate output and split exit codes | `check --json`: verdict, allowed, passing/total, missing, blockers, issues, criteria (`cli.py:1156-1178`). Exit 0 pass, 1 gate not met, 2 bad invocation (`:736`, `:877`, `:1188`). `evaluate` collects all issues, not the first (`:645-716`) | `print_next`, `next_exit` (`fw:scripts/gate.sh:511`, `:532`), which have no `--json` (grep). Add `next --json`, keep 0/1 for rest/work, new code for failed step | Closes the verified "exit 1 means two things" gap. Improve on the repo: add `schema_version`, stable issue codes, and a `next` action. The repo has none of those and derives `missing_evidence` by substring match (`cli.py:1158`) | S-M | Idea |
| Fail-closed defaults | Stored status is overwritten, never trusted (`cli.py:689-695`). No criteria fails (`:654`). No required evidence fails (`:662`). Unknown verdict fails (`:586`) | `report_sha_ok` returns 0 when no record exists (`fw:scripts/gate.sh:239`). `bound_findings` ignores unparsed lines (`fw:scripts/lib.sh:480`). Make any unparsed line under `## Findings` block with "unparsed finding" | Directly closes "findings dropped silently" for malformed lines. One-line policy: unknown means not ready | S | Idea |
| Reason required to decline | Empty notes rejected at write and at gate (`cli.py:1090-1093`, `:581-583`) | `findings_judged` regex accepts bare `F1: declined` (`fw:scripts/gate.sh:262`). Require non-empty text after `declined` | Closes "decline with no reason" with a regex change. It does not make the reason good; a critic rereading declines would | S | Idea |
| Generated completion receipt | `report` renders goal, criteria, evidence, commands, review, changed files, limitations from state (`cli.py:1344-1485`) | `fw:.agentic/templates/pr.md`, filled by hand via `/agentic-pr`. Generate Done Contract rows and review summary from the ticket, `checks-NN.json` and journal | Fits "scripts do what scripts can". The agent cannot misreport what a script prints. Prose sections stay with the agent | S | Idea |
| Shipped-tree hygiene test | Test walks shipped files for local-path markers (`tests/test_agent_audits.py:418-438`); `files` allowlist is pinned by test (`:440-449`, `package.json:17`) | `fw:scripts/selftest.sh`; start of a framework/project file manifest | Cheap guard for "template stays clean". Extend markers to ticket numbers and framework-history strings | S | Code or idea |
| Non-command evidence kinds | Types with strong/weak strength and per-type rules (`cli.py:33-49`, `:445-485`); image header sniffing (`:415-434`) | `ticket-lint.sh:131` demands `Check:` on every assertion. Allow `Evidence: screenshot <path>` for UI, judged by the reviewer | Real gap for UI and docs work, where a command check is often contrived. Only worth it with item 1, since a file existing proves nothing | M | Idea |
| Bounded stop rule at proof time | "Do not loop forever": after repeated failure, record a blocker and say not verified (`SKILL.md:57`). Blockers close the gate (`cli.py:697`) | `AGENTS.md` or `agentic-debug`. My grep of AGENTS.md, judgment.md and config found no cap; skills not searched | Small prose addition, more useful when unattended | S | Idea |

## 3. Challenges

- **Review limited to changed lines.** Repo reviews claims against evidence, not lines. Verdict: repo is right about a second unit, wrong as a replacement. Keep line findings for defects and add contract verdicts (item 1). Its review is worth little here only because the reviewer is the author.
- **Three risk lanes.** Repo varies required evidence by kind of change: docs, UI, refactor, bug (`cli.py:281-325`). Verdict: orthogonal, not a contradiction. Risk sets ceremony; kind sets proof shape. Keep lanes. Optional kind-specific contract stubs are fine, but the author picks the kind, never a keyword match (section 6).
- **Bash as runtime.** One Python file with one pure-ish `evaluate` is far easier to read than a first-match table in bash with awk YAML, and the framework already needs python3 and embeds it in heredocs (`fw:scripts/lib.sh:436`, `:487`). Verdict: files as state is right in both; bash as the logic language is the weak half. The repo supports moving the gate core to Python. One data point, not proof.
- **JSON vs markdown state.** Repo's JSON needs no parser and gives exact schemas, but humans must edit `acceptance.json` by hand. Verdict: keep markdown for the human contract, use JSON for machine receipts.
- **Hooks and hard enforcement.** Repo has none: "stop an agent that chooses to ignore it" is out of scope (`SKILL.md`, Enforcement Boundary). Verdict: framework is right. Everything in section 6 is what an unenforced gate looks like.
- **Human accepting every ticket.** Repo has no human step. `manual-user-confirmation` can be recorded by the agent, and `--reviewer-kind human` is a free string (`cli.py:1526`). Verdict: no support for dropping the human. The lesson is sharper: a label is not an identity. Human acceptance needs an act the agent cannot perform, such as a PR approval, signed commit or protected ref. That applies directly to the verified `status: open` gap.
- **Long AGENTS.md and 18 skills.** Repo installs through a 9-line snippet whose trigger is the claim itself (`README.md:64`), which is a good shape. But its 357-line skill restates one rule set about four times and contains duties nothing checks (`work_log` upkeep). Verdict: copy the trigger framing ("how do you know?"), not the volume. The framework's mechanics-in-scripts split is better.
- **Copy-in distribution.** Repo: installed engine plus one project dotdir, idempotent `init` (`cli.py:130-149`), no `scripts/` collision. Verdict: right shape, unfinished. No version pin, no state schema version, no upgrade path, and an npm wrapper around Python is odd. Framework should take the split, not the channel.
- **Selftest as main proof.** Same category of evidence. `eval_matrix.py` is six fixture scenarios with no agent in the loop. Verdict: neither repo measures outcomes. The name "eval" overstates it.
- **Tickets as the unit.** Repo allows one goal per workspace (`cli.py:739-752`). Verdict: framework is right; the repo cannot express parallel work, dependencies or history.

## 4. Delete or simplify

- **`reviewer-*.sha` as tamper proof.** VERIFIED same pattern as this repo: a hash stored beside a file, writable by the same actor. Both detect accidents only. Keep it labelled as such, or delete it and put proof where the author cannot write (CI-held key, server-side check). INFERRED this removes false assurance without losing protection.
- **Local stamps as evidence.** CI already re-runs `verify` and checks (`fw:.github/workflows/agentic-gates.yml:39`, `fw:scripts/gate.sh:1063`). The repo's doc states the principle well: keep execution proof and review proof separate (`docs/github-actions.md:91-96`). Treat stamps as a cache and say so. Then `test_ratchet`, which depends on local stamps, should move to CI against a checkout of the merge-base, or go.
- **Hand-filled PR sections** that restate gate data (item 6).
- Beyond that, this repo offers no strong case for removing framework features. It is smaller because it does less.

## 5. Orchestration

Useful lessons:
- A supervisor needs only one call: `check --json` with `allowed` plus exit code. That is the right minimum for the framework's `next`/`pr`.
- State is relative to cwd (`cli.py:720`), so each worktree or clone is isolated by default with no coordination.
- It is agent-agnostic because it is only a CLI and files. No per-tool adapter is needed for the proof layer; adapters are needed only for hooks.

Gaps, so not a model to follow:
- `status` has no JSON. Issues are prose. There is no "next action", so a supervisor learns a gate failed but not what to dispatch.
- `check` and `report` write state (`cli.py:708-714`, `:1184`), unlike the framework's read-only `next`, which is better.
- Writes are non-atomic with no locks (`:74-78`), and sequential `EV-`/`RV-` IDs would collide across clones or merged PR bundles.
- The default gitignored state means a fresh CI checkout fails with "No acceptance criteria" (`:654`), since `check` creates an empty workspace (`:1183`). Docs say `git add -f` a sanitized bundle (`docs/github-actions.md:14-22`). Proof must travel with the branch, or CI must regenerate it. The framework has the same issue for stamps.

## 6. Do not copy

All VERIFIED by reading unless noted.

- **Exit code by declaration.** `add-evidence -t test --command "npm test" --exit-code 0` with no artifact skips the guard at `cli.py:889` and the run at `:920`, then writes a log saying exit 0 (`:922-934`). Nothing ran, and `check` accepts it. The framework runs its own commands, which is the correct design.
- **Any command satisfies a criterion.** `--type test --command "true"` passes. There is no link to a configured test command. The framework's check key hash (`fw:scripts/gate.sh:228`) and vacuous-check lint (`fw:scripts/ticket-lint.sh:144`) are better.
- **No code binding.** See section 1. `evidence_fresh` (`fw:scripts/lib.sh:59`) is the right mechanism.
- **Self-sealing hashes.** Unkeyed SHA-256 in writable JSON. An agent edits artifact and index together. No test covers that case in the test names I read; `tampered_artifact_fails` changes only the artifact.
- **Failed attempts poison a criterion.** Every attached record must be clean (`cli.py:670-676`), and there is no detach command. After one red run, the criterion can pass only by hand-editing `acceptance.json`. A real RED-then-GREEN history cannot be recorded. The bug template demands "reproduction" as `test` evidence with exit 0, so the tests and smoke script "reproduce" with `print('reproduced redirect bug')` (`scripts/smoke_test.py:85`).
- **Keyword classifier for proof requirements.** Docs words win first (`cli.py:268`), and they include `copy` and `readme`. "Fix copy bug in parser" gets a docs-only plan with no `test` evidence. Criteria stay editable, with no freeze (`--force` regenerates them), so an agent can also lower `evidence_required` to `log`.
- **Runner details.** No command timeout (`cli.py:799`; the framework has 900s) and `text=True` capture, which may raise on non-UTF-8 output (ASSUMED, not run).
- **Default reviewer identity from `$USER`** (`:1084`): looks like attribution, is not.
- **Marketing drift.** `docs/outreach-positioning.md` has a useful "unsafe claims" list and shows care, but the skill description's own terms exceed it.

Suspicious content: none found. `SKILL.md` is ordinary imperative instruction with no exfiltration or instruction-override text. The README's `~/.codex/...quick_validate.py` line is a dev note.

## 7. If you rebuilt the framework

Keep the core: scripts own state, a one-command next move, evidence bound to tree state, hooks for the irreversible, and tickets. Adopt this repo's shape at the edges: an installed engine with one project state dir, a JSON gate with split exit codes, and a Python core returning all issues. Proof becomes a matrix with one row per contract assertion, each with evidence, a verdict from someone other than the author, and a hash of what they saw. Unknown or missing rows block. Line findings stay as a second channel. Do not copy its trust model: every field an agent can write is claim, not proof, so independence must come from CI, a server-side check or a human act outside the agent's reach.

## 8. Coverage

Read in full: `agent_audits/cli.py`, `README.md`, `agent-audits/SKILL.md`, `docs/*`, `scripts/eval_matrix.py`, `scripts/doctor.py`, `bin/agent-audits`, `examples/realistic-pr-verification/README.md`, `package.json`.
Read in part: `scripts/realistic_demo.py` (lines 60-255), `scripts/smoke_test.py` (grep), `examples/simple-fix/README.md` (first 30 lines), `tests/test_agent_audits.py` (all test names, bodies of about 4 tests). Git log and stat, plus a partial diff of `3bb360b`.
Not read: most test bodies, the logo asset. Whether the npm package is published or used is unknown.
Framework: read `gate.sh` review, check and ship paths, `lib.sh` freshness and runner, `verify.sh` (first 80 lines), CI workflow, templates; `ticket-lint.sh` by grep. Did not read skills or all hooks.
Confidence: high on what the repo does and does not do, since the code is small and read in full. Medium on the post-review-commit ship path (read, not run). Low on outcome value; the repo has no outcome data.

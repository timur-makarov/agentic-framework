# Verdicts on the completeness review

Date: 2026-11-09. One recommended verdict for each item in [REVIEW-completeness.md](REVIEW-completeness.md), for you to approve or drop. Your notes are quoted.

The test for each item:
- Will about 80% of projects use it?
- Could a person or agent do it in a few minutes once, so the framework needn't?
- Does it cost simplicity?

Two new rules: assume no attacks, because everything is done by a person or checked elsewhere; and the standard setup is to clone the framework and use Claude Code.

Verdicts: **Do** (keep the item's fix, as changed here), **Drop**, **Done** (already applied or decided).

## What "no attacks" removes

Several items exist only because an agent might cheat. Under your rule, they go:

| Goes | Stays |
|---|---|
| Trust levels `local`/`gate`/`host`/`ci` | Every step reports `ran`, `not_run` or `unavailable`, so a skipped step never looks like a pass. That is railroad honesty, not defence |
| Two CI jobs, base-branch engine in CI | One `pull_request` job running the repo's own engine. Changes to engine, config or workflow are `risk_paths`, so they go to HIGH and you merge them |
| `policy: head (unreviewed)` bootstrap | Nothing; there is no base policy to miss |
| `AGENTIC_ENGINE`, host pinning | Claude Code's sandbox setting, because it limits accidents |
| Comparing the contract with a copy on base | The contract freezes at claim and changes only through `amend` |
| `review.runs_in: ci` as a trust feature | It may stay as a convenience option, built after the gate mode, or be dropped. I suggest building it later and only if wanted |

**This needs your approval.** RECOMMENDATIONS.md has not yet been changed for it.

## Must-fix

**1. Quick fix breaks the framework.** You asked: "Why exactly is this important? Does it concern the user in 80% of projects?"
- It mattered only because I had told you to apply it, and it would have stopped every MEDIUM ticket.
- It is already removed, and the rewrite replaces the code anyway.
- **Done.**

**2. Nothing in CI proves a review ran.** You asked: "What are the chances of a forged review?"
- Today an agent can write the report file itself. In practice that happens by accident, when the reviewer subagent fails and the agent fills the gap. Nobody has counted how often.
- Once the gate launches the reviewer itself, faking a review means deliberately editing the engine. Under "no attacks" that is zero.
- **Drop.** The gate-launched reviewer (item 16) fixes the accidental case.

**3. CI from base needs two jobs.**
- This was purely a defence against a PR editing its own judge.
- **Drop.** One job, as in the table above.

**4. Bootstrap for install and policy PRs.**
- This exists only because of item 3.
- **Drop.** A change to the framework's own files is an ordinary HIGH change you merge.

**5. Hooks break in Phases 1-2.** You asked me to explain the solution.
- Claude Code's hook config in `.claude/settings.json` calls scripts by path (`scripts/hooks/guard.sh`).
- Phase 2 moves those scripts into `.agentic/engine/`, and state moves too. If the wiring isn't updated at the same time, every hook points at a missing file and the project runs with no guards.
- The fix is to do a straight port in Phase 2: the same rules at the new paths, reading the new config.
- Redesigning the rules waits for Phase 4.
- **Do.**

**6. "Done when" lines.** LGTM. **Do**, but the hook-bug half of it shrinks with "no attacks" (see item 8).

**7. "Ready to use."** LGTM, read as a direction: small and medium projects, automations and tools. **Done.**

**8. What survives the rewrite.** You asked for my verdicts:

| Today | Verdict | Why |
|---|---|---|
| Migration gate, `reversibility`, `rollback` | Keep | Stands before an irreversible act |
| `new_deps` lockfile check | Simplify: a changed lockfile is listed under Risk in the PR, with no lockfile parsing | Parsers are per language; the reviewer and you see it |
| Diff size limits | Keep, as the tier caps (end of this file) | |
| Session traps (production URLs at claim) | Drop | A few minutes of setup: don't put production credentials in the dev environment |
| Scope overlap and `blocked_by` refusal | Keep | Parallel tickets depend on it |
| `--widen`, `reopen` | Keep | PR feedback and scope changes need them |
| `pr --require-shipped`, `check`, `next --all` | Fold into `advance` and `status` | Fewer verbs |
| ASSUMED rows blocking claim and ship | Keep | An open assumption is unfinished work |
| `env-lint --protected-diff` | Keep, as "a PR touching `risk_paths` is HIGH" in the CI job | |
| floor-guard and `floor_ignore`, `floor_exceptions` | Merge into structure rules: the seed config ships default rules (no new `eslint-disable`, `ts-ignore`, `noqa`, skipped tests), each with `allow` paths | One mechanism instead of two, and the pattern lists become editable data |
| Worktree flow | Keep `--worktree`; drop `require_worktree` | Optional is enough |
| Hook command log, `metrics.jsonl` | Replace with the event log | |
| `audit:` config | Replace with the sweep | Done in G6 |
| memory-lint needles, lesson TTL, lesson files | Drop; keep the `CONTEXT.md` cap in `doc-lint` | The framework's lessons become checks (ANSWERS H2); yours are the learning pack |
| `debt-lint` (`PONYTAIL(NN)` markers) | Drop | A convention a project can keep as a structure rule |
| `ticket-lint` | Keep | It is the contract's parser |
| `stamp-check`, `answers-check`, `model-check` | Drop | Stamp is gone, answers are ASSUMED rows, `models.*` is dead |

**9. Layout: "with an owner for each path".** You asked me to explain.
- "Owner" meant which part of the framework writes a file and which files `upgrade` may overwrite.
- **Changed 2026-11-09:** you dropped `upgrade` (ANSWERS H3). After `install` every file is the project's, so the table, the manifest and the managed-block markers go. `install` writes `.agentic/SOURCE` (framework repo and commit) for a later "clone and integrate".
- **Drop.**

**10. Language neutrality.** LGTM. You also asked how linters, scanners and your own commands such as `swagger` or `go generate` get added.
- **They stay outside and run as usual.** The framework calls shell commands at four named points and nothing else:

```toml
[commands]
setup  = "pnpm install"          # after a worktree is made
verify = "make check"            # whole-project gate at ship and in CI
[[gates]]                        # extra commands at ship and in CI, by exit code
name = "secrets"
run  = "gitleaks git --log-opts=origin/main..HEAD"
```

  Plus each area's `Check` in `ARCHITECTURE.md` and each ticket's `Check:` cells.
- Generated code fits the same way. "Is the generated code current?" is a command: `go generate ./... && git diff --exit-code` goes in `verify` or a gate. Mark generated files `linguist-generated` in `.gitattributes` and the size cap ignores them.
- There is no plug-in API for commands: a Makefile or `package.json` scripts already do that job. A missing tool prints `not_run`.
- Pattern lists become structure-rule data (item 8).
- **Do.**

**11. Install into an existing repo.** You said: "Do not base any decision on any host. Should `install` just implement `agentic-init`?"
- Yes, as one entry point:

```bash
git clone <framework> ~/agentic
```

```bash
~/agentic/install /path/to/project
```

- `install` copies the engine and seed and writes `.agentic/SOURCE`. It never overwrites a file of yours: it appends a section to an existing `AGENTS.md` and merges our hook entries into an existing `.claude/settings.json`.
- The first `next` then returns the init task to Claude: propose `verify`, areas, `risk_paths`, and ask you to confirm. Detecting the stack is judgment, which the agent does well. A script would need a list per language.
- Drop: dry run, the non-interactive flag (it existed for Symphony), the stack-detection script.
- **Do, simplified.**

**12. License.** No license. **Done.**

**13. Orchestrator packs.** Settled earlier: no plug-ins. Your new rule removes more:
- Drop Phase 7 (stub host). Normal tests cover `--json`.
- Keep the cheap surface that also helps Claude Code: `--json`, `owner`/`action`, `--ticket`, `rest` when there is no work.
- Drop `intake` mirror mode, `host` assurance and `AGENTIC_UNATTENDED`. A host can add them later if one needs them.
- **Do, reduced.**

**14. "Make clients a separate named kind".** You asked me to explain.
- With Cursor, Codex and Claude, each tool needed its own hook wiring. The review said that wiring is not a "pack" (optional feature) but its own category.
- With Claude Code as the standard, there is one wiring, and it is simply part of what `install` writes (our entries in `.claude/settings.json`). The hook scripts stay tool-neutral, so another tool's wiring can be added later.
- **Drop the concept.**

**15. Python and the config format.** Done on this machine: Homebrew Python 3.15.2 is now `python3`, and 3.14 was upgraded too.
- **Use tomllib:** the Python floor becomes 3.11.
  - `.agentic/config.toml` replaces `config.yml`.
  - Ticket front matter becomes TOML between `+++` lines.
  - The structure rules live in `config.toml`.
- This removes the planned YAML-subset parser, about 200 lines. Unknown keys are still rejected with a suggestion, which kills dead config for good.
- `install` stops with one line if Python is older than 3.11. macOS ships 3.9; `brew install python` fixes it.
- **Do.**

## Should-fix

**16. Mode A versus `submit-review`.** You asked me to explain.
- Today, in Mode A, the agent is told to start a reviewer subagent, and that subagent writes the report. `submit-review` was planned for tools with no headless command (Cursor), so the agent could hand in a review it ran itself.
- With Claude Code as the standard, there is always a headless command. So the gate runs `claude -p` with the reviewer agent file, in a worktree, and reads its JSON directly.
- That is simpler for the railroad: the agent can't forget the step or fill the gap itself. `submit-review` and the rule about unattested reviews go.
- **Do, simplified.**

**17. Contract anchor.** LGTM, minus the attack part.
- Keep: the contract freezes at claim, and `amend` needs the tier's acceptance.
- Drop: the `local` label and the compare-with-base step.
- **Do.**

**18. `setup:` command.** LGTM. **Do.**

**19. State keyed by ticket, journal for resumable data.** LGTM. **Do.**

**20. Bind review to `git patch-id`.** LGTM. **Do.**

**21. `forge` command, local merge with no remote.** LGTM. **Do.**

**22. `ci` depends on branch protection.** You asked me to explain.
- If GitHub does not *require* the agentic check, a red check can still be merged. The plan had `doctor` read the protection settings and refuse to claim `ci`.
- Under "no attacks", with you merging HIGH, setting branch protection is a one-time step that takes a few minutes. Trust levels are going anyway.
- **Drop.** One line in the install docs: require the `agentic` check on main.

**23. Stop hook.** **Drop**, as you said.

**24. `AGENTIC_ROLE=reviewer`** so the project hooks don't nag the reviewer. LGTM. **Do.**

**25. Old versus new comparison during the port.** LGTM. **Do.**

**26. Effort estimates.** Doesn't matter. **Drop.**

**27. Area `Check` cells.** LGTM, minus "read from base".
- Keep the vacuous-check lint.
- Rename the `verify` pack to `drive`, so `verify` means only the command.
- **Do.**

**28. Failure recovery.** You asked whether it matters, and whether `status` can make staleness obvious. Yes, and that is enough:

```text
$ agentic status
TICKET  STATE         OWNER  LAST EVENT  NOTE
12      awaiting-ci   agent  4m          PR #57
14      implementing  agent  3d          STALE: no event for 3 days
15      open          human  1d          waiting: accept plan
16      claimed       agent  6d          STALE: no worktree found
leftovers: worktree .worktrees/09 (ticket 09 merged), branch ticket/11 (no ticket)
```

- Everything shown comes from git and the journal, with no new state.
- Stale means no event for `status.stale_days` (default 3).
- Drop leases, failure classes and the `doctor` stale list.
- **Do, reduced to `status`.**

**29. Dead ends, tier and LOW default.** You said LOW is the most common tier and must be implemented, tested and shipped, and "cap reached: second opinion, then human".
- **Tier** is the highest of the author's choice, the path floors and the size cap.
- **LOW defaults to `auto`.** It's claimed, implemented, checked, merged when CI is green, with no person in the loop.
  - Merging is the ship to dev when the project's CD deploys main there. **Changed 2026-11-09:** an optional `[deploy]` (`wait` and `check`) adds a `deployed` state that proves the change works on dev (ANSWERS H1). Without it, the ticket ends at merge.
  - The safety for LOW is `risk_paths`, the size cap and the weekly sweep.
- **Retry cap:** the first time it's reached, `consult` runs. If the ticket still fails, `owner: human`.
- **A blocking finding the agent disputes:** the refuter decides. If it upholds the finding and the agent still can't fix it, `owner: human`.
- `parked` findings go to one `journal/parked.md` that the sweep reads.
- **Do.**

**30. `.agentic/local/` overrides.** You said the framework is customised through HIGH tickets, or forked. **Drop.**

**31. Schema versions and upgrades that change formats.** Unnecessary. **Drop**, along with the copy-in move script, since nobody uses the old version.

**32. Git hooks as a tool-neutral layer.** LGTM. **Do**: `pre-commit`, `commit-msg` and `pre-push`, as mistake prevention.

**33. "Cut on purpose" list.** No need. **Drop**, and section 12 goes.

## Optional

**34. Windows.** No. **Drop.**

**35. Reduced environment and secrets for the reviewer.** No. **Drop.**

**36. Hook deadline.** No. **Drop.**

**37. Byte cap on the `AGENTS.md` block.** No. **Drop.**

**38. A notify command for human waits.** LGTM. Here is how it looks:

```toml
[notify]
command = 'terminal-notifier -title agentic -message "$AGENTIC_MESSAGE" -open "$AGENTIC_URL"'
# or: curl -s -d "$AGENTIC_MESSAGE" ntfy.sh/my-topic
```

- The engine runs it whenever a ticket's owner becomes `human`, so it works under any loop. It sets `AGENTIC_TICKET`, `AGENTIC_REASON`, `AGENTIC_MESSAGE` and `AGENTIC_URL`.
- Example message: `ticket 14 needs you: retry cap reached after a consult. Last failure: test_refresh_revoked. PR #61`.
- Empty by default. Failure to notify is logged, never fatal.
- **Do.**

**39. Cut large diffs for the reviewer at file boundaries.** LGTM.
- When the diff is over the reviewer's budget, whole files are left out, listed, and the review says it is partial.
- With the size caps this mostly affects HIGH.
- **Do.**

**40. Accuracy fixes.** LGTM. **Do**: fix the cited line numbers and the "negative control" wording, and remove `model-check` together with `models.*`.

## Unsure section (your item 41)

- **`craft_skills`:** **Drop** the field. Craft skills (pstack, gstack, superpowers, any prose, template or script) are installed the way their authors ship them: Claude Code skills or plugins, at user or project level.
  - The framework needs no integration:
    - `next` says *what* to do ("fix the failing check in auth"), and the craft skill says *how*.
    - Claude Code chooses skills by their description.
    - The framework's own procedures are printed by `next`, so they never collide with a skill's name.
  - To insist on a skill at a step, a project writes one line in its own part of `AGENTS.md`, for example "for bugs, use /diagnose". That takes minutes, once.
- **Unused config fields:** dropped as a rule. Unknown keys fail, and every field must name its reader.
- **Old versions:** not supported in any way.
- **Monorepos:** one root `.agentic/`, nothing per package. The framework ships no area names: the init task proposes `## Areas` rows from this repo's own directories and you confirm them (ANSWERS H6).
- **Token cost of MEDIUM review:** not a concern. Removed from the risks.

## Size caps: LOW 300, MEDIUM 600

**Counting:** `git diff --numstat -M <merge-base>...HEAD`, added plus deleted lines.
- Renames count only their edits.
- Binary files count zero but are listed.
- Excluded:
  - files marked `linguist-generated` or `-diff` in `.gitattributes`, the same signal GitHub and Bugbot use;
  - a short default list of lockfile names;
  - `[size] exclude` globs in config.

**Enforcement:**

| When | What happens |
|---|---|
| Every `next` while implementing | Shows `size 240/300`. At 80% it adds: "consider splitting; next part as a new ticket" |
| `advance` to ship | LOW over 300 becomes MEDIUM, and gets a reviewer. MEDIUM over 600 becomes HIGH, and you review it. Recorded in the journal; tiers only go up |
| CI job | Same count from the same code, printed in the receipt. A PR whose tier label is below its size tier fails, which catches a skipped `advance` |

HIGH has no cap: you are already reading it.

I chose to raise the tier rather than force a split. A split after the code is written means untangling one branch into two, which is slow and error-prone for an agent. Raising the tier always works and is easy to explain. The 80% warning is where splitting is cheap, so it is advice there.

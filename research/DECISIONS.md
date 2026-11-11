# Rail: decisions

Date: 2026-11-11. This file records what was decided for [PLAN.md](PLAN.md), round by round. It was section 0 of the plan until 2026-11-11. The plan states the result, and where the two differ, the plan wins. Section numbers refer to the plan.

The standing scope rules stay in section 0 of the plan.

## Decided by the owner, by round

- **From the workflow analysis (2026-11-10):**
  - `[[gates]]` is dropped; scanners go into `verify`.
  - Partial review over a line budget is dropped.
  - The sweep has one trigger: 20 unreviewed tickets.
  - The framework installs no git hooks.
  - The HIGH security seat stays.
  - Outside PR comments are no longer a findings ledger. A bot the project wants obeyed becomes a required check.
  - The area `Check` column is dropped.
  - The migration gate keeps its required fields, and `next` adds a migration brief.
- **From the Fable review (2026-11-10):**
  - **Cloud sessions are supported.** Their GitHub proxy blocks GraphQL, so:
    - `forge` uses `gh api` (REST) only. `gh pr` and `gh issue` use GraphQL, so the engine doesn't call them.
    - No PR is a draft. CI fails a PR with `not shipped yet` until its ticket ships the current patch.
    - The engine merges auto tiers itself through the async merge endpoint (REST) once CI is green, instead of GitHub auto-merge.
    - A branch the cloud proxy won't delete stays listed as a leftover in `status`, and each `next` tries again.
  - `consult` no longer runs before a HIGH claim.
  - `rail init` never creates `CLAUDE.md`. It adds `@AGENTS.md` only to a `CLAUDE.md` the project already has.
  - The reviewer runs with `--safe-mode`, so it never loads `AGENTS.md`; its brief carries only the project's own part. It may run commands in the ticket's worktree, which the engine resets afterwards, and a finding can carry `evidence`: the command it ran and the output.
  - `advance --wait` is dropped. `next` returns `gh run watch` instead.
  - The refuter stays. Section 24 now says what "LLM judges as gates" means.
  - Failure signatures are dropped.
  - `[notify]` is replaced by a `notify` hook (section 15).
  - Finding outcomes are events, recorded with `answer`. Three journal files remain.
- **From the review on 2026-11-11:**
  - **The CLI is `rail`.** `rail init` sets a project up, and `rail add` creates a ticket, so no verb sits one letter from `rails new`. Install is a shell script only; there is no package.
  - The retry budget is 2 attempts per step.
  - Each review run has one job. The reviewer, the security seat and the refuter share one prompt, and the brief says what to look for (section 8).
  - The reviewer's brief carries the project's part of `AGENTS.md`.
  - IDs and claims are taken on the remote, so two clones never take the same one (section 5).
  - A person's note that holds beyond its ticket is written down by a follow-up ticket. Adding `rail:needs-you` by hand holds any PR. `drop` unlabels the ticket's issue. Widening a HIGH ticket's scope needs no new approval. A red base spends no retry budget.
  - A person's merge carries the same trailers: squash only, with the PR title and description (section 11).
  - The agent can't edit the journal by hand (section 15).
  - Dropped: `review.runs_in`, and the `review-brief`, `security-scanners` and `craft` packs. Diagrams: none. MEDIUM merges without a person.
  - The engine merges through the async merge endpoint, which also joins a merge queue when the ruleset requires one (section 7). Stacked PRs aren't built; dependent tickets wait for the earlier merge.
- **From the plan check on 2026-11-11:**
  - An open ASSUMED row no longer refuses a claim. The agent verifies it or asks after the claim, and an open row blocks ship (sections 5 and 7).
  - `advance` pushes after every commit, and the loop prompt resumes tickets an ended session left (sections 7 and 10).
  - The engine notes a merge request in the local cache, because a journal commit would move the head CI just passed (section 7).
  - A merge queue is the project's to set up and test. Phase 5 no longer tests one (sections 11 and 25).
  - Queues are for organisations only. A project that wants every merge tested on the latest base without one requires up-to-date branches, and the engine rebases a PR that is behind (section 11).
  - The old-against-new comparison is dropped. Phase 1 is done when the end-to-end tests pass on fixtures (section 21).
  - Retry budgets are built in Phase 3, and Phase 3 tests one reviewer run inside a cloud session (sections 21 and 25).
  - `rail init` creates the three labels (sections 10 and 14).
  - `[consult]` joins the config, and the sweep summary is the fourth journal file (sections 4 and 5).
  - `new` means no `accepted` event, and a red required check is `implementing` (section 7).
  - This history moved out of the plan.
- **From the build preparation on 2026-11-11:**
  - Phase 0 runs five early checks from a cloud session before any framework code (sections 21 and 25).
  - The framework is written from scratch in a cloud environment. The current framework is a reference only.
  - `review/v1` and the journal's events are specified in [SPEC.md](SPEC.md).
  - `--json-schema` takes the schema's text, so the review command passes the file's contents (section 4).
  - The reviewer prompt gained six sentences after a test of 39 real runs: what each severity means, the rules for a re-review, and what `summary` holds (section 8).
  - `timeout_secs` also limits each review run. A run that times out is started once more, and a second timeout waits for a person (sections 4 and 8).
  - The ten security prompts and the do-not-report list are written into section 8.
  - Worktrees move from Phase 5 to Phase 1. The claim is built in Phase 1, and the Phase 3 reviewer resets the tree it runs in, which must not be the person's own checkout (section 21).

## Approved by the owner on 2026-11-11

These were first applied to the plan as recommendations.

1. **What "no attacks" removes:**
   - trust levels and the `assurance` field
   - the two-job CI that runs the engine from base
   - the bootstrap path
   - an override that pointed the wrapper at another engine copy
   - comparing the contract with a copy on base
   - `review.runs_in: ci` as a trust feature
   - the reviewer's reduced environment
   - sanitising and fencing text as injection defence
   - session traps
2. **The verdicts on review items 1 to 41** (VERDICTS-completeness.md), as amended by ANSWERS H1 to H6.
3. **Approvals and waiting (ANSWERS H4):**
   - the HIGH contract PR
   - the `rail:go` and `rail:needs-you` labels
   - no `plan` acceptance and no `acceptance: tracker`
4. **Environments (ANSWERS H1), revised after the workflow analysis:** no `[deploy]` section and no `deployed` state. Watching dev needs a live session after merge, and several merges close together blame the wrong ticket. Instead, the project's CD runs its smoke check after each deploy, and on failure opens an issue labelled `rail`. That issue becomes a fix ticket with `caused_by` (section 16).
5. **New trims made while merging,** each because nothing in the current design reads it:
   - The `--exit-code` mode is dropped.
   - `owner: tracker` and the `tracker_move` action are dropped.
   - The `run` driver is dropped.
   - `frontier`, `check` and `submit-review` are dropped as verbs.
6. **New choices made while merging, including fixes from the gap check on 2026-11-10:**
   - A ticket exists as its branch. IDs are taken by pushing a `rail/NN` tag (section 5).
   - Ticket and journal files are non-product paths: they count for nothing in tier, scope, size or `patch-id`.
   - Each state is derived from a fact (section 7). Every ticket has a PR from `add` (tiers outside `auto_tiers`) or from claim (`auto_tiers`), so every wait has a PR to label. `rail:go` continues any wait.
   - `reopen` is dropped; follow-up work after merge is a `caused_by` ticket.
   - A sweep is itself a LOW ticket, and its merge commit marks where the next sweep starts.
   - The roadmap moves `## Areas` parsing to Phase 1, the size caps to Phase 3, and the sweep to Phase 5, ahead of LOW merging without a person.
   - Every claimed ticket gets its own worktree. Per-ticket waits need this.
   - MEDIUM contracts are accepted automatically, and MEDIUM merges automatically after review and green CI.
   - CI checks that a review exists for the patch whenever the computed tier needs one.
   - `rail init` adds `@AGENTS.md` to `CLAUDE.md` only when the project has one (section 6).
7. **Fixes from the workflow analysis (2026-11-10), checked against current docs:**
   - **Merging:** the engine merges auto tiers once CI is green (see the cloud decision above). `doctor` checks that `rail` is a required check.
   - **`github-runner`** becomes a docs page. Events made with `GITHUB_TOKEN` start no workflows, so it uses claude-code-action with its own app token, or Claude Code scheduled tasks. `forge` uses `gh api`.
   - **Timeouts and output:** `rail init` raises Claude Code's Bash tool timeout so `advance` can run the reviewer. The reviewer uses `--json-schema`.
   - **`patch-id`** is computed on a `-U0` diff, because context lines change on rebase. CI checks out the PR head with full history.
   - **Retries:** the budget is per step (2 attempts), so changing error text can't make it unbounded. Re-review reads the whole diff.
   - **Sessions:** claims record `CLAUDE_CODE_SESSION_ID`, so after compaction the snapshot shows this session's ticket. Claims and new IDs are taken atomically on the remote (section 5).
   - **Guards:** they are written as Claude Code `permissions.deny` and `ask` rules where possible. A small hook covers what rules can't express.
   - **Away from the desk:** documented with what Claude Code already ships: `/loop`, `/goal`, scheduled tasks and Remote Control. The inbox is a saved search, because GitHub doesn't notify you about PRs made with your own token.
   - **Worktrees** live in `.claude/worktrees/NN`. The engine copies the files `.worktreeinclude` lists, such as `.env`, because Claude Code copies them only into worktrees it creates itself.
   - **Smaller trims:** the weekly CI sweep job (the sweep runs through `next`; dependencies go to Dependabot or Renovate), `[status] stale_days` (an engine default), commands-in-docs checking in `doc-lint`, the `CONTEXT.md` glossary as core, and the pack manifest (a pack is a folder until a second pack needs events). Findings with a `check` field no longer open one ticket each; the sweep collects them.
8. **Fixes from the Fable review (2026-11-10),** checked against current docs:
   - GitHub counts a required check skipped on a draft as passed, so turning a PR ready at ship let a check that never ran look green. No PR is a draft now (section 7).
   - A PR that conflicts with base sends its ticket back to `implementing`. GitHub runs no workflow on a conflicted PR, so `next` has to notice.
   - The engine copies `.worktreeinclude` files itself.
   - Guards that depend on flags (force push, `--no-verify`) move from permission rules to the hook, because rules match prefixes.
   - `intake` makes a stub ticket. The agent writes the contract and tier before the ticket is accepted.
   - A claim belongs to its worktree, and `next --ticket NN` resumes one after a crash.
   - Smaller:
     - one `files` key for rules;
     - `ARCHITECTURE.md` made by the init task;
     - CI's ticket lint covers ASSUMED rows and the migration fields;
     - Phase 1 reports forge states `unavailable`;
     - the CD issue starts with `Commit: <sha>`;
     - `drop` is safe to rerun and cleans up after a PR closed by hand.

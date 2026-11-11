# Changelog

One line for each change, saying why.

- Add `research/`: the plan, the spec and the reasoning behind them, so each build session reads them from the repo it clones.
- Record the Phase 0 results in section 25 of the plan, so later phases build on what was checked in a cloud session.
- Make the ticket ID ref the branch `rail/id/NN` instead of the tag `rail/NN`, because the cloud proxy refuses tag pushes (Phase 0 check 1).
- Record Phase 0 check 2: the async merge endpoint merged the results PR from the cloud session.
- Add the Phase 1 engine in Python 3.11 with the standard library only: the first-match table, the verbs add, accept, next, advance, status, context and drop, state derived from git and the journal, claims with their own worktrees, and the local squash merge, so a ticket can run from add to merge on the new core.
- Add bin/rail, the launcher that runs the engine next to it and stops with one line on Python older than 3.11.
- Add the end-to-end railroad tests on fixture projects (tests/), so every Phase 1 rule is checked through the real launcher: run with python3 -m unittest discover -s tests.
- Leave branches named like tickets but holding no ticket file alone and list them in status, because the plan says such branches stay for the person.
- Make next --ticket NN run a failed setup again, read open ASSUMED rows from the worktree's copy of the ticket, and skip tickets next can't act on before deriving them again, so the briefs match what the agent sees and next stays fast.
- Show leftovers in the text output of next, advance and drop, so a person reading the terminal sees what was left for them.
- Split the framework into engine/ (copied into a project by rail init) and seed/ (copied once), so a project owns its engine and its starting files.
- Add install, which links rail into ~/.local/bin, and make bin/rail hand over to the project's own .rail/bin/rail, so a project's changes to its engine take effect.
- Add rail init: it copies the engine and seed, writes .rail/bin/rail and .rail/SOURCE, appends the ## Rail section to AGENTS.md, imports it from an existing CLAUDE.md, merges .claude/settings.json, adds the rail workflow and .gitignore lines, and never overwrites a project's file.
- Make the first rail next return the init task until the project's config is on its base branch, so the agent proposes setup, verify, areas, risk paths, rules and .worktreeinclude for the person to confirm.
- Add rail doctor, the SessionStart hook (PATH through CLAUDE_ENV_FILE and a snapshot of this session's ticket), and rail ci with the rail workflow, so CI repeats the ship checks and fails with "not shipped yet" before ship.
- Add the gate-launched review: advance runs review.command in the ticket's worktree with the brief on stdin, checks the review/v1 output, binds each run to the patch-id, keeps the runs in NN-review.json and resets the worktree, so a review can't be skipped or hand-written.
- Add the findings ledger with rail answer, a refuter for disputed blocking findings, and the HIGH security seat with a refuter for each blocking finding, so every finding ends fixed, declined with a reason, or parked.
- Freeze the contract and tier at acceptance and add rail amend, so a weakened check or a lowered tier fails at ship until it is amended (and, for a changed Done Contract outside auto tiers, approved).
- Add retry budgets and the consult pack: at the budget a different model advises once, then a person takes over; rail accept continues any wait with a note for the agent's next brief.
- Add structure rules on added lines and files (with the default rule), size caps that raise the tier, and the migration brief, so a bad shape or an oversized change is caught at ship and in CI.
- Make rail ci check the frozen contract and a complete review for the patch, and add a stand-in reviewer to the tests so the suite never calls a model.
- Add the guard hook's deny rules for force pushes, pushes to the base branch, --no-verify and merges outside the engine, because these depend on a flag or refspec that permission rules can't match.
- Deny a download piped into a shell, disk wipes, and Bash commands that touch .env files or write the journal, because only a hook sees these inside a Bash command.
- Ask the person before sudo, git reset --hard, git clean -f and rm -r outside the worktree, because each is sometimes right and a person should decide.
- Wire the guard: rail init merges the deny and ask rules and the PreToolUse guard hook into .claude/settings.json, and doctor reports when either is missing, so the guards are on from the first session.
- Add doc-lint for ## Areas at ship and in CI: every glob matches a tracked file, every directory at [map] depth is covered, and ARCHITECTURE.md stays under 150 lines, so the repo map can't drift from the tree.
- Make doc-lint check that links and headings in ARCHITECTURE.md and AGENTS.md resolve, and that a change adding or removing a top-level directory updates ARCHITECTURE.md, so the docs keep pointing at what exists.
- Start a claimed ticket from the current base branch, because a branch made at add misses work merged since, such as the ticket it comes after.
- Run every git command with core.quotePath=false, because git quotes non-ASCII paths and the engine then misread them in scope, floors, the size count and context.
- Add rail docs: pages ship inside the engine, and the config and CLI reference pages are generated from the engine, so the docs a project reads match the engine it runs.
- Add the docs pages for the loop, tickets and states, so an agent new to a project learns the railroad from rail docs.
- Add the docs pages for review, the contract, retries and consult, so the answers an agent owes the rail are written where it looks.
- Give a fresh retry budget when a person approves a ticket or an amend, as with any other continue, because plan section 10 says a person's act resets it.

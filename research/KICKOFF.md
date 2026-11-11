# Rail: kickoff prompts

Two prompts for the cloud sessions that build Rail. Each assumes this `research/` folder sits at the root of the repo the session clones.

## First session

```text
You are building Rail, a small framework that keeps coding agents on a railroad: it says
what is legal next, what counts as done, and when a person must act. It is written from
scratch in this repo. I am its owner and its first user. It is not a product.

Read these first, in full:
- research/PLAN.md: the single plan. It wins over every other file.
- research/SPEC.md: the review/v1 schema and the journal's events.
- research/DECISIONS.md: what was decided and when. It is history, so don't reopen it.
The other files in research/ are background. Read them only when the plan points you there.

This session: Phase 0, then Phase 1 (section 21 of the plan).

Phase 0 is five checks with no framework code. They test assumptions the design rests on,
so they come before anything is built.
- The plan asks for a throwaway repo. This repo counts as one for now, because nothing is
  built in it yet. Start the names of test tags and branches with phase0/, and delete them
  when you finish. Run the checks that need no GitHub in a scratch directory outside the repo.
- Record each result in section 25 of the plan: the date, the Claude Code version, what you
  ran and what happened.
- The merge check needs a pull request. Use the one that records these results: open it,
  and merge it through the async endpoint. Record that check's own result afterwards, on
  the Phase 1 branch.
- If a check fails, switch the plan to the fallback section 25 already names, and say so.
  If a failure has no fallback that works, stop there and tell me before you write engine code.

Phase 1 is the core. Its "done when" is in section 21: the end-to-end tests pass, and a
ticket runs from add to a local merge on the new core. Work on a branch, commit in small
steps, and open one pull request for the phase. Leave that one for me to merge.

How to work:
- Build what the plan says. Section 1 has the rules every item must pass, and they apply to
  your choices too: keep it simple, don't design for edge cases, and add nothing the plan
  doesn't ask for.
- The plan has been reviewed several times, but it will still be silent or wrong somewhere.
  When it is silent on a detail, pick the simplest option that fits, and write it down. When
  it is wrong, or a choice would change something the plan decides, stop and ask me.
- The engine is Python 3.11+ with the standard library only, for macOS and Linux.
- In this environment the GitHub proxy blocks GraphQL, so gh pr and gh issue fail. Use
  gh api REST calls, for your own pull requests as well as in the engine.
- Tests are general end-to-end tests on fixtures (section 22). Run them before you say
  something works, and show the output.
- Keep CHANGELOG.md from the first commit: one line for each change, saying why.

When you finish, report:
- the Phase 0 results, one line for each check;
- what Phase 1 delivers, with the output of the end-to-end tests;
- each choice you made where the plan was silent;
- anything in the plan you found wrong or unclear.
Put the same in the pull request description.
```

## Each later session

Replace `N` with the phase number.

```text
Continue building Rail in this repo. Read these first: research/PLAN.md, which wins over
every other file; research/SPEC.md; CHANGELOG.md; and the description of the last merged
pull request.

This session: Phase N (section 21 of the plan). Its "done when" is in that row.

How to work, as before:
- Build what the plan says, and keep it simple. Section 1's rules apply to your choices too.
- When the plan is silent on a detail, pick the simplest option that fits, and write it
  down. When it is wrong, or a choice would change something the plan decides, stop and ask me.
- The GitHub proxy blocks GraphQL here, so use gh api REST calls.
- Run the tests before you say something works, and show the output.
- Keep CHANGELOG.md up to date, open one pull request for the phase, and leave it for me
  to merge.

When you finish, report what the phase delivers with the test output, each choice you made
where the plan was silent, and anything in the plan you found wrong. Put the same in the
pull request description.
```

# Study brief, round 2: capabilities

Read `research/STUDY-BRIEF.md` first. Its rules, labels and report format all apply. Then read `research/RECOMMENDATIONS.md`, which is the target design so far: an engine with versioned JSON, a clean project seed, `packs/`, a gate-launched reviewer, trust levels, and evals.

## What changed

The owner has widened the goal. There is no limit on what can be added if it is good and works. Areas they named: memory systems, docs, diagrams, turning code into graphs, and a learning system, meaning something better than "claude, explain to me how it works". They want features to "smoothly fall into place" in the framework's structure.

So in this round, also ask of your repo:

- Which capabilities does it really have, in these areas or others? Name ones the first round missed.
- Does each one work, per the code? What evidence shows that people or agents benefit?
- How would it fit as an optional capability in the framework? Name the slot: what triggers it (ticket state, a `next` row, a hook event, a CLI verb, a schedule), what it reads, what it writes, where its data lives, and what it costs when unused.
- What does it need that the framework must provide (stable JSON, an event log, a ticket-to-code index, and so on)? This shapes the extension API.
- Does adding it conflict with "no reader, no field or hook" or with keeping the seed clean?

The size of a repo is not a reason to read less of what matters. It is a reason to choose carefully: follow the code for the capabilities above and say what you skipped.

## Report additions

Add section 9, **Capabilities**: a table with Capability | Works? (evidence and `path:line`) | Slot in the framework | Needs from the engine | Always-on cost | Verdict (core, optional pack, or skip).

Keep the whole report under about 170 lines. Write to `/Users/makar/work/research/agentic-framework/research/reports/<dir-name>.md`. Your final reply is 5-10 lines, as before.

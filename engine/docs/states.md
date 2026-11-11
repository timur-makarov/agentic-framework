# States

State is derived each time from git and the journal; nothing stores it.

```text
new -> accepted -> implementing -> reviewing -> in-ci -> merge-ready -> merged
```

| State | Means |
|---|---|
| `new` | The ticket has no `accepted` event. Outside `auto_tiers`, a person approves it: `rail accept NN` |
| `accepted` | Accepted, not claimed yet |
| `implementing` | Claimed, and the current patch hasn't passed the ship steps, or the worktree has uncommitted changes |
| `reviewing` | Shipped, the tier needs a review, and no complete review is bound to this patch |
| `in-ci` | Shipped and reviewed, with a remote: waiting for CI on the pull request |
| `merge-ready` | Ready to merge. `auto_tiers` merge with `rail advance NN`; other tiers wait for a person |
| `merged` | A squash commit with `Ticket: NN` is on the base branch |
| `dropped` | `rail drop NN` ended it |

Any state can wait for a person: `owner` is `human`, and the brief says what is needed. One act continues
any wait: `rail accept NN "note"`. The note goes into the agent's next brief.

## The journal

`.rail/journal/` holds each ticket's evidence, written only by the engine and merged with the code:
`NN-events.jsonl` (every step and decision), `NN-review.json` (the review runs) and `NN-advice.md`
(consult's advice). Never edit it by hand.

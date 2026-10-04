# Follow-along guide

How this project was built, step by step, including what went wrong. It is
written for a capable engineer who was not there, and for the owner, who wants
to be able to explain each step.

It is not a blog. Posts in [`docs/blog/`](../blog/README.md) are short and led
by a result, for someone skimming. This guide is the process: the data, the
design choices, the mistakes, and the commands. A blog post links here for the
detail.

## The rules of the guide

- **Every number links to its source,** an issue, a closing handoff comment, or
  a note under `docs/`. It is the number written there, not a rounded one. A
  number that cannot be sourced is left out.
- **A command appears only if it works on `main` today.** Where we ran it, the
  chapter says when. Where we did not, the chapter says so.
- **The guide never claims a result the project has not produced.** A model
  result appears only where a closed issue reports it, from a run on `main`.
- **Failures are written as plainly as successes.** They are the most useful
  parts.
- **Each chapter says when it was last updated and from which issues.**
- **Where a chapter and its source disagree, the source wins.** Fix the chapter.

Each chapter has the same shape: what we set out to do, what we found, the
decisions and why, how to reproduce it, and what we would do differently.

## Chapters

Chapters 1 to 5 cover the first milestone, "Trusted ground", and chapters 6 to
9 the second, "Off-the-shelf bar", in build order. To follow along you need
a clone of the repository and the WiSARD dataset (chapter 1).

| # | Chapter | Last updated | From issues |
|---|---|---|---|
| 1 | [The problem and the data](01-the-problem-and-the-data.md) | 2026-10-01 | #1, #2, #6, #7, #10 |
| 2 | [Pairing the two cameras](02-pairing-the-two-cameras.md) | 2026-10-01 | #1, #2, #38, #39 |
| 3 | [Scoring tiny people](03-scoring-tiny-people.md) | 2026-10-01 | #4 |
| 4 | [Splitting by site-day](04-splitting-by-site-day.md) | 2026-10-01 | #3, #39, #45 |
| 5 | [Making runs and records traceable](05-making-runs-traceable.md) | 2026-10-01 | #20, #22, #23, #28, #29, #30, #38 |
| 6 | [Caching the features](06-caching-the-features.md) | 2026-10-04 | #64, #65, #78 |
| 7 | [A detection head on frozen features](07-a-head-on-frozen-features.md) | 2026-10-04 | #66, #91 |
| 8 | [The baseline that won](08-the-baseline-that-won.md) | 2026-10-04 | #67 |
| 9 | [Feeding thermal in](09-feeding-thermal-in.md) | 2026-10-04 | #68 |

Closed issues with no chapter of their own yet: #5, the choice of starting
model and datasets, whose evidence is in
[`docs/model-and-dataset-review.md`](../model-and-dataset-review.md); and #27,
signed branch commits, which chapter 5 mentions from `CLAUDE.md` only. The
tooling issues #86 and #88, and the process issues #74, #81 and #83, have no
chapter; chapters 8 and 9 cover what their tooling measured.

## Keeping it current

Run `/guide`. It starts the `guide-writer` agent, which finds the closed
issues that no chapter lists, writes or updates the chapter each belongs to,
and updates this table. The agent and the skill are in `.claude/`.

## Where the facts live

| What | Where |
|---|---|
| The reasons for a choice | [`docs/decisions.md`](../decisions.md) |
| What changed, newest first | [`CHANGELOG.md`](../../CHANGELOG.md) |
| The evidence behind a decision | the `docs/*-review.md` notes |
| What was done on each issue | its closing "Handoff" comment |

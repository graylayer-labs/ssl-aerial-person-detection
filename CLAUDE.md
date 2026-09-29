# ssl-aerial-person-detection

Read the intent first. It explains why the project exists and how decisions are
made, and it overrides anything below that conflicts with it.

@INTENT.md

## Every session

Agent sessions end and context is lost. The project board is the memory.

1. **Start** with `/pickup`. It reads the board and open issues and tells you
   what is in progress and what is next. Do not start work from memory of a
   previous conversation.
2. **Work** on one issue at a time: one issue, one branch, one draft PR.
3. **Record as you go.** Decisions, results, and dead ends go in a comment on
   the issue, not only in the conversation.
4. **End** with `/handoff`, even if the task is unfinished. The next agent
   should be able to continue from the issue alone.

If there is no issue for the work, create one first (ask the owner before
creating it).

## Commands

```bash
uv sync --dev                  # install
uv run pytest                  # tests
uv run ruff check --fix .      # lint
uv run ruff format .           # format
uv run ty check                # types
```

## Layout

```
src/aerial_search/   package: data/, models/, experiments/
tests/               tests for the package
notebooks/           analysis notebooks, numbered
docs/                milestone write-ups and decision notes
tools/               one-off scripts that are worth keeping
data/                datasets and manifests (git-ignored)
outputs/             run artefacts (git-ignored)
```

## Experiments

- Every run is defined by a committed config and a seed, and writes to
  `outputs/<run-name>/`.
- Size runs for the laptop first. Aim for under 30 minutes. Ask the owner
  before starting anything expected to take over an hour.
- Propose cloud compute only with the evidence `INTENT.md` asks for.
- Any number quoted in a doc or README must be reproducible from a committed
  config. If a number cannot be traced, remove it.
- Report negative results. State what was expected, what happened, and the
  most likely reason.
- Always compare against a baseline on a held-out split. Splits are by flight,
  never by frame, because neighbouring frames are near-duplicates.

## Tests

Test what would silently corrupt results: pairing, splits, label handling,
metrics. Skip tests that only restate the implementation.

## Model tiering

The owner pays for usage. Use the cheapest model that can do the job well.

| Model | Use for | Agent |
|---|---|---|
| Fable | Milestone design, experiment analysis, final judgement | main session |
| Opus | Review, hard debugging | `reviewer` |
| Sonnet | Implementing a well-specified issue | `implementer` |
| Haiku | Audits, searches, mechanical edits | `repo-janitor` |

Each issue carries an `agent:<model>` label. Delegate to the matching agent
rather than doing routine work in an expensive session.

## Keeping the repo clean

- `/tidy` runs an audit and proposes a clean-up PR. Run it at the end of every
  milestone and whenever the repo feels out of step with the docs.
- The `reviewer` agent checks every PR before the owner sees it.
- Delete superseded docs and code. Git history is the archive.

## Reusable tooling

When you do something by hand that a future agent or another project would
repeat, note it on the issue labelled `tooling-candidate`: what the step was,
and whether it fits a skill, a command, an agent, or a hook. Do not build it
on the spot unless the current issue asks for it.

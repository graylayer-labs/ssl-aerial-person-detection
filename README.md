# Aerial person detection for search and rescue

Detecting people in drone footage from RGB and thermal cameras, when footage is
plentiful and labels are scarce.

## The problem

Search and rescue teams fly drones that carry an RGB camera and a thermal
camera. They record far more footage than anyone can label by hand, so a
detector that needs a large labelled dataset is of little use to them.

The two cameras also fail in different conditions. Thermal picks up warm rocks,
engines, and animals as well as people. RGB loses people in darkness and under
foliage. Footage from both cameras of the same scene carries information that
neither has alone.

This project asks how far unlabelled, paired footage can take a detector, and
how few labels it then needs.

## Approach

1. Start from a pretrained vision foundation model.
2. Adapt it to aerial RGB and thermal imagery with self-supervised learning on
   unlabelled footage.
3. Train a person detector on top with a small fraction of the labels.
4. Measure everything against a baseline on flights the model has never seen.

[INTENT.md](INTENT.md) explains the purpose and the standard the work is held
to.

## Status

**Current milestone: Trusted ground.** Nothing is trained until the data can be
trusted.

- The project uses the public
  [WiSARD dataset](https://sites.google.com/uw.edu/wisard/).
- The code that pairs RGB frames with thermal frames has a known bug, so no
  dataset figures are quoted here yet. See
  [issue #2](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2).
- No model results exist yet.

Progress is tracked as
[epics and issues](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues?q=is%3Aissue+label%3Aepic).

## Setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

## How this project is run

Claude agents do the engineering and the owner directs. Work is planned as
issues, each written so that an agent with no prior context can pick it up.
[CLAUDE.md](CLAUDE.md) holds the working rules and
[docs/decisions.md](docs/decisions.md) records the choices made along the way.

## Licence

MIT. See [LICENSE](LICENSE).

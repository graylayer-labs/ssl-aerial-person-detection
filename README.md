# Aerial person detection for search and rescue

[![ci](https://github.com/graylayer-labs/ssl-aerial-person-detection/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/graylayer-labs/ssl-aerial-person-detection/actions/workflows/ci.yml)

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

![Pipeline diagram. RGB and thermal drone footage, mostly unlabelled, is paired frame by frame. A pretrained vision foundation model is adapted to the paired footage with self-supervised learning. A person detector is trained on top using a small labelled fraction, then evaluated on flights the model has never seen.](docs/figures/pipeline.svg)

[INTENT.md](INTENT.md) explains the purpose and the standard the work is held
to.

## Status

**Milestone 1, Trusted ground, is closing.** Nothing was trained; everything
a result will rest on was checked first. The
[write-up](docs/milestones/trusted-ground.md) has the detail.

- The project uses the public
  [WiSARD dataset](https://sites.google.com/uw.edu/wisard/): 14,834 paired
  RGB and thermal frames from 17 verified clips, 5,739 labelled in both
  cameras, split into four folds that each leave one site out.
- Starting model: SigLIP 2, kept frozen, with EVA-02 and DINOv2 as
  comparisons.
- No model results exist yet. The next milestone measures the off-the-shelf
  baseline.

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

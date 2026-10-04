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

**Milestone 2, Off-the-shelf bar, is done.** A frozen foundation model was
measured with 1% to 100% of the labels, and an ordinary fine-tuned detector
beat it where labels are scarce. The
[write-up](docs/milestones/off-the-shelf-bar.md) has the detail.

![Mean test AP over four held-out site-days, frozen SigLIP 2 plus a head against a fine-tuned detector, RGB and thermal](docs/figures/off-the-shelf-bar.svg)

- At the same input size, a COCO-pretrained Faster R-CNN fine-tuned on the
  same frames beats a head on frozen SigLIP 2 features at 1%, 5% and 10% of
  labels on both cameras, and is level at 100%. It is now the bar.
- Thermal needs no special input handling: copying the grey channel is as
  good as a learned input stem, and equalising contrast hurts.
- Resolution is the largest lever found: one full-resolution run scored
  `ap_iou25` 0.779 against 0.213 at the shared input size.
- Data: the public [WiSARD dataset](https://sites.google.com/uw.edu/wisard/),
  14,834 paired RGB and thermal frames from 17 verified clips, split into four
  folds that each leave one site-day out. Milestone 1,
  [Trusted ground](docs/milestones/trusted-ground.md), made that split and
  the scoring trustworthy.

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

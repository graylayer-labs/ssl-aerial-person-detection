# Self-Supervised RGB–Thermal Person Detection

A personal research project exploring self-supervised learning on paired RGB and
thermal drone imagery, followed by fine-tuning for aerial person detection.

## Idea

A drone searching for a person may have both a visible-light camera and a thermal
camera. RGB captures texture and scene detail but becomes less useful in poor light.
Thermal imagery can reveal people in darkness, but heat signatures may blend into
the environment.

The project asks a simple question:

> Can a model learn useful visual features from paired RGB–thermal images before it
> sees person labels, and does that pretraining improve person detection when labels
> are limited?

## Data

The project uses the public
[WiSARD dataset](https://sites.google.com/uw.edu/wisard/), which contains aerial RGB
and thermal wilderness imagery with person bounding boxes. Its multimodal subset
contains synchronized RGB–thermal image pairs captured from a drone across varied
terrain, seasons, and lighting conditions.

The smaller public sample is used to build and test the pipeline. Person-detection
experiments will use the complete dataset.

### Initial sample review

- 264 synchronized image pairs from one flight;
- RGB resolution of `3840 × 2160` and thermal resolution of `640 × 512`;
- 1,022 RGB boxes and 1,006 thermal boxes;
- people occupy roughly 0.05% of an RGB frame at the median;
- 251 of 264 RGB frames contain four people, so adjacent frames are highly related;
- RGB and thermal frames share a capture time but are not pixel-aligned.

The sample is therefore useful for data-pipeline development and debugging. Results
reported as experiments will use the complete dataset with collection-level splits.
The first cross-modal SSL baseline will operate on whole-image representations rather
than assuming that RGB and thermal pixels correspond.

## Experiments

We will compare:

1. A person detector trained from scratch.
2. A detector initialized from single-modality SSL pretraining.
3. A detector initialized from paired RGB–thermal SSL pretraining.

Each approach will be fine-tuned with different fractions of the available person
annotations. Detection mAP and recall will show whether paired pretraining helps,
particularly when labelled data is scarce.

## Getting started

Python 3.12 and [`uv`](https://docs.astral.sh/uv/) are required.

```bash
uv sync --dev
uv run aerial-search fetch wisard-sample
uv run aerial-search prepare data/raw/wisard-sample
uv run aerial-search train-ssl
uv run aerial-search train-detector thermal scratch
uv run aerial-search train-detector thermal ssl \
  --ssl-checkpoint outputs/ssl-sample/model.pt
```

The sample is downloaded and extracted beneath `data/`, which is ignored by Git.
The prepare command validates paired images and YOLO annotations, then writes local
JSONL manifests with RGB paths, thermal paths, and modality-specific person boxes.

```bash
uv run ruff check .
uv run ty check
uv run pytest
```

See [ROADMAP.md](ROADMAP.md) for completed work and the current milestone.

## Status

Dataset fetching, pairing, manifest preparation, and a first paired contrastive
experiment are implemented.

On the 264-pair development sample, a 10-epoch run reduced contrastive training loss
from 2.07 to 0.79. RGB-to-thermal retrieval on 39 held-out pairs changed from 2.6%
to 5.1% top-1 and from 12.8% to 30.8% top-5 relative to an untrained encoder.

This is a pipeline sanity check, not a person-detection result. The sample comes from
one short flight with highly similar adjacent frames. Detection experiments and
meaningful conclusions require the complete dataset.

### Initial person-localization result

To test whether the learned representations contain useful person information, a
small ResNet-18 head predicts person-centre locations on a `14 × 14` grid. The same
model is trained either from random initialization or from the paired SSL encoder.

| Modality | Initialization | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| RGB | Random | 67.4% | 45.8% | 54.5% |
| RGB | Paired SSL | 77.2% | 74.8% | 76.0% |
| Thermal | Random | 96.2% | 39.1% | 55.6% |
| Thermal | Paired SSL | 83.0% | 64.8% | 72.8% |

Paired SSL substantially improves recall on both modalities. On RGB it also improves
precision; on thermal it trades some precision for fewer missed people. These are
promising development-sample results, not final detection benchmarks: the grid task
only approximates localization, and all validation frames come from the same short
flight as the training frames.

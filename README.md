# Self-Supervised RGB–Thermal Person Detection

## The Problem

Search and Rescue (SAR) teams have abundant unlabeled drone footage but expensive
manual labeling. Can self-supervised learning on paired RGB–thermal imagery help
them detect people faster with minimal manual labeling?

See [docs/PROBLEM.md](docs/PROBLEM.md) for the full problem statement, technical
approach, research questions, and experiment design.

## Data

The project uses the public
[WiSARD dataset](https://sites.google.com/uw.edu/wisard/) — synchronized RGB–thermal
image pairs from real SAR flights across varied terrain, seasons, and lighting
conditions.

See [reports/01_data_exploration.ipynb](reports/01_data_exploration.ipynb) for the
full data exploration, including annotation distributions, flight diversity, and
sample visuals.

## Getting started

**Requirements**: Python 3.12 and [`uv`](https://docs.astral.sh/uv/)

### Development sample (264 pairs)

Quick start to validate the pipeline:

```bash
uv sync --dev
uv run aerial-search fetch wisard-sample
uv run aerial-search prepare data/raw/wisard-sample
uv run aerial-search train-ssl --epochs 5
```

### Full dataset workflow

For the complete WiSARD multi-modal dataset (~40GB, 15K+ pairs):

```bash
# 1. One-time: download & upload to S3
python scripts/download_wisard_full.py

# 2. Extract and prepare manifests
uv run aerial-search fetch wisard-full
uv run aerial-search prepare data/raw/wisard-full --output data/processed/wisard-full

# 3. Explore the data
jupyter notebook reports/01_data_exploration.ipynb
```

The exploration notebook generates:
- **Visualizations**: annotation distribution, RGB-thermal agreement, sample pairs
- **Statistics**: boxes/image, modality alignment, split breakdown
- **Report**: dataset suitability for Search & Rescue
- **JSON export**: `reports/exploration_summary.json` for downstream analysis

### Quality & testing

```bash
uv run pytest
uv run ruff check .
uv run ty check
```

### Data storage

Raw images are archived to AWS S3 (`ssl-aerial-person-detection-data-eu-west1`,
region `eu-west-1`). The `prepare` command creates lightweight JSONL manifests
(with image paths and bounding boxes) that stay on disk. Run
`scripts/download_wisard_full.py` once to upload the raw dataset to S3 after
extraction.

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

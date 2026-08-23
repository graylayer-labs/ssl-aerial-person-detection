# Self-Supervised RGB–Thermal Person Detection

Can self-supervised learning on paired thermal-RGB drone footage help SAR teams detect
people with minimal manual labeling?

See [docs/PROBLEM.md](docs/PROBLEM.md) for the research problem and questions.

## Dataset

The project uses the public [WiSARD dataset](https://sites.google.com/uw.edu/wisard/) —
7,359 labeled thermal-RGB image pairs from real SAR flights, plus 16,459 total pairs
(labeled + unlabeled) for training.

See [reports/01_data_exploration.ipynb](reports/01_data_exploration.ipynb) for data analysis.

## Setup

**Requirements**: Python 3.12 and [`uv`](https://docs.astral.sh/uv/)

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

## Current Status

Dataset prepared and analyzed. Ready to begin representation learning.

See [ROADMAP.md](ROADMAP.md) for the project roadmap.


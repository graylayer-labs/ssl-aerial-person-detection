# Repository Structure

## Directory Layout

```
ssl-aerial-person-detection/
├── src/aerial_search/           # Source code (models, experiments, data)
│   ├── models/                  # Neural network architectures
│   ├── experiments/             # Training loops
│   ├── data/                    # Dataset loading & processing
│   └── cli.py                   # Command-line interface
│
├── tests/                       # Test suite (mirrors src/)
│
├── scripts/                     # One-off utilities
│   └── download_wisard_full.py
│
├── reports/                     # Analysis outputs
│   ├── 01_data_exploration.ipynb
│   ├── exploration_summary.json
│   └── findings.md
│
├── docs/                        # Documentation
│   ├── STRUCTURE.md             # This file
│   ├── GLOSSARY.md              # Concepts & terminology
│   └── CONCEPTS/                # Detailed explainers (optional)
│
├── data/                        # Local data (git-ignored)
│   ├── raw/
│   └── processed/
│
└── README.md, ROADMAP.md, ...   # Top-level docs
```

## Guidelines

**Source code** (`src/`): Models, experiments, data loading. Testable.

**Tests** (`tests/`): One test file per source module (e.g., `test_wisard.py` ↔ `wisard.py`).

**Reports** (`reports/`): Notebooks, JSON exports, findings. Outputs of exploration.

**Docs** (`docs/`): User-facing guides, glossaries, conceptual explanations.

**Scripts** (`scripts/`): Utilities you run once (downloads, one-time setup).

**Data** (`data/`): Local only (git-ignored). Never commit raw images.

## When Adding Files

1. **New algorithm or feature?** → `src/aerial_search/`
2. **Explaining a concept?** → `docs/GLOSSARY.md`
3. **Running an experiment?** → `reports/*.ipynb`
4. **Downloading data?** → `scripts/`
5. **Testing code?** → `tests/`

Keep it simple. One file per responsibility.

# Module Architecture

## What is `aerial_search`?

`aerial_search` is a Python package for self-supervised learning on paired thermal-RGB SAR drone footage. It provides:

1. **Data management** — fetch WiSARD dataset, parse annotations, generate training manifests
2. **Model training** — SSL pretraining, detection fine-tuning, pseudo-labeling
3. **CLI workflow** — orchestrate full pipeline: `fetch` → `prepare` → `train-ssl` → `train-detector`

## Directory Structure

```
src/aerial_search/
├── __init__.py              — Package metadata
├── cli.py                   — Command-line interface (fetch, prepare, train-ssl, train-detector)
├── data/
│   ├── __init__.py
│   ├── fetch.py             — Download datasets from gdown
│   └── wisard.py            — WiSARD-specific loading & manifest preparation
├── models/
│   ├── __init__.py
│   ├── components.py        — Shared utilities (load_image, get_device, prepare_image)
│   ├── ssl.py               — ContrastiveEncoders (RGB + thermal SSL backbones)
│   └── detection.py         — Detection architectures (TBD: fusion detector)
└── experiments/
    ├── __init__.py
    ├── ssl_experiment.py     — SSL pretraining loop (data loading, training, validation)
    └── detection_experiment.py — Detection training loop (TBD)
```

## Module Responsibility Matrix

| Module | Purpose | Inputs | Outputs |
|--------|---------|--------|---------|
| **data/fetch.py** | Download public datasets | Dataset ID | Raw images on disk |
| **data/wisard.py** | Parse WiSARD structure, sync pairs by frame index, load annotations | Raw WiSARD dir | JSONL manifests (all_pairs, full, train/val/test splits) |
| **models/components.py** | Shared utilities | Image paths, device strings | Loaded tensors, device handles |
| **models/ssl.py** | SSL encoder pair | Embeddings | Aligned thermal-RGB features |
| **models/detection.py** | Detection heads | Feature maps | Bounding box predictions |
| **experiments/ssl_experiment.py** | Run SSL pretraining | Manifests + data | Trained backbone checkpoint |
| **experiments/detection_experiment.py** | Run detection fine-tuning | Checkpoint + manifests | Trained detector checkpoint |
| **cli.py** | User-facing orchestration | CLI args | Subprocess calls to above modules |

## Design Principles

1. **Module independence** — Each module has a single responsibility; no circular imports
2. **Data locality** — Data loading/parsing in `data/`; training loops in `experiments/`; model definitions in `models/`
3. **Clear inputs/outputs** — Functions accept paths/tensors, return structured results (dataclasses, dicts, checkpoints)
4. **No magic** — Hyperparameters are explicit CLI arguments, not buried in constants
5. **Mirror test structure** — For every src/module/file.py, there should be a tests/test_module/test_file.py

## Test Structure (Target)

```
tests/
├── test_cli.py              — Integration tests (CLI commands work end-to-end)
├── test_data/
│   ├── test_fetch.py        — Fetch dataset, verify structure
│   └── test_wisard.py       — Pairing logic, manifest generation
├── test_models/
│   ├── test_components.py   — Image loading, device handling
│   ├── test_ssl.py          — SSL encoder forward pass, loss computation
│   └── test_detection.py    — Detection head forward pass
└── test_experiments/
    ├── test_ssl_experiment.py    — SSL training loop, checkpoint saving
    └── test_detection_experiment.py — Detection training loop, evaluation
```

Currently missing: test_models/, test_experiments/ directories and their contents.

## Clarity Guidelines

1. **File names are functions, not implementation details**
   - ✓ `wisard.py` (what data source)
   - ✗ `pairing_utils.py` (how it works)

2. **Module boundaries are by domain, not by pattern**
   - ✓ `data/wisard.py` (handles WiSARD dataset)
   - ✗ `data/loaders.py`, `data/readers.py` (splits a single domain)

3. **Deep nesting hides code**
   - ✓ `models/ssl.py` (one level)
   - ✗ `models/ssl/encoders/rgb_encoder.py` (multiple levels for small codebase)

4. **Function names describe intent, not steps**
   - ✓ `prepare_manifests(source, destination)` (what it does)
   - ✗ `load_images_and_parse_annotations_then_write_jsonl()` (how it does it)

5. **Dataclasses over dicts for structured results**
   - ✓ `ImagePair(collection_id, rgb_image, thermal_image, rgb_labels, thermal_labels)`
   - ✗ `{"collection": "...", "rgb": "...", ...}` (type-unsafe)

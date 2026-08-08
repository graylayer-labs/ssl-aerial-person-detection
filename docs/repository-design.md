# Repository design

The repository separates immutable source data, deterministic manifests, model code,
and generated results.

```text
configs/                  Versioned experiment configurations
data/
  archives/               Downloaded source archives (ignored)
  raw/                    Extracted immutable source data (ignored)
  processed/              Derived tiles and manifests (ignored)
docs/                     Research decisions and audit reports
outputs/                  Checkpoints and generated metrics (ignored)
src/aerial_search/
  data/                   Fetching, validation, pairing, tiling, and splits
  evaluation/             Search-oriented metrics and reports
  models/                 Encoders, detectors, and fusion methods
  training/               Training entry points
tests/                    Unit and small fixture-based integration tests
```

## Data rules

1. Raw archives and extracted source files are never committed or modified.
2. Every derived sample records its source image and transformation.
3. Splits use flight or collection identity rather than frame identity.
4. Empty annotations are valid negative examples, not missing data.
5. Dataset-specific assumptions are validated before training.
6. Generated manifests and aggregate audit reports may be committed when they do
   not expose or redistribute source imagery.

## Dependency direction

Dataset adapters produce a small internal sample representation. Training and
evaluation consume that representation rather than importing dataset-specific
paths. Model libraries will be selected after the audit; the data fetcher therefore
uses only the Python standard library.

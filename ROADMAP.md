# Roadmap

The roadmap is ordered to test the problem before adding modelling complexity.
Each phase has a concrete exit criterion.

## Phase 0 — Dataset audit

- Fetch the official WiSARD multimodal sample.
- Inventory RGB images, thermal images, annotations, metadata, and pairing keys.
- Count frames with zero, one, and multiple people.
- Measure person-box size and occupancy distributions by modality.
- Identify collection or flight boundaries suitable for leakage-safe splits.
- Review RGB/thermal synchronization and spatial misalignment.

**Exit:** a committed audit report and machine-readable inventory. No model work
starts until empty-frame prevalence and split units are known.

## Phase 1 — Search-like benchmark

- Create train, validation, and test splits by complete flight or collection.
- Preserve positive frames and background-only frames.
- Generate background tiles that do not intersect person boxes, with a guard band
  to avoid cropped body fragments.
- Construct a fixed, prevalence-controlled test stream.
- Define recall, false positives per 1,000 frames, and recall at fixed false-alarm
  budgets.

**Exit:** deterministic manifests with zero cross-split flight leakage and a data
test proving every annotation remains valid after tiling.

## Phase 2 — Supervised baselines

- Train RGB-only and thermal-only person detectors from scratch.
- Add a simple late-fusion baseline without adaptive sensor weighting.
- Report standard mAP for comparability and search-oriented metrics for utility.
- Break results down by terrain, lighting, and modality.

**Exit:** reproducible baseline results on the fixed benchmark, including a false
alarm analysis and representative hard negatives.

## Phase 3 — Self-supervised pretraining

- Pretrain compact RGB and thermal encoders on all training imagery without boxes.
- Start with a well-understood single-modality SSL objective.
- Add synchronized cross-modal agreement only after the single-modality baseline.
- Fine-tune with 1%, 5%, 10%, and 100% of training annotations.

**Exit:** a controlled comparison showing whether SSL changes recall at fixed
false-alarm budgets under scarce labels.

## Phase 4 — Sensor reliability

- Evaluate darkness, thermal crossover, blur, occlusion, and missing modalities.
- Test fixed fusion against learned reliability-aware fusion.
- Mine false positives from untouched background footage and categorize them.
- Retrain with hard negatives without modifying the test set.

**Exit:** evidence for or against adaptive sensor trust, with condition-specific
failure analysis.

## Phase 5 — Deployment study

- Export the best compact model to ONNX.
- Measure latency, memory, model size, and throughput on available edge-like
  hardware.
- Translate frame-level false alarms into false alarms per hour at a declared
  sampling rate.

**Exit:** a reproducible deployment report with no claims beyond measured hardware.

## Deferred decisions

- Detection framework and architecture.
- SSL objective and encoder family.
- External negative datasets.
- Target edge device.

These remain deferred until the Phase 0 audit establishes the actual data shape.

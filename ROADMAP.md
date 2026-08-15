# Roadmap

## Completed on the development sample

- [x] Download and extract the WiSARD multimodal sample.
- [x] Pair synchronized RGB and thermal frames.
- [x] Parse and validate YOLO person annotations.
- [x] Create reproducible local data manifests.
- [x] Train separate RGB and thermal encoders with a paired contrastive objective.
- [x] Compare cross-modal retrieval before and after SSL pretraining.
- [x] Compare random and SSL initialization on a lightweight person-location task.

The sample validates the pipeline, but it contains only 264 highly related pairs from
one flight. Its results are not treated as evidence about person detection.

## Current milestone: complete data and detection baseline

- [x] Download and prepare the complete WiSARD dataset (via gdown + multi-collection support).
- [x] Split data by collection rather than adjacent frame (seeded greedy bin-fill).
- [x] Add paired-sample and annotation visualizations (diversity report with thumbnails).
- [x] Archive raw WiSARD data to S3 (eu-west-1) instead of local disk.
- [ ] Train RGB-only and thermal-only person detectors from scratch.
- [ ] Record mAP and recall baselines.

## Next: evaluate SSL for person detection

- [ ] Implement label-fraction subsampling (1%, 5%, 10%, 100%) with deterministic seeds.
- [ ] Pretrain on the complete unlabelled training split.
- [ ] Fine-tune the same detector architecture from random and SSL initialization.
- [ ] Report mAP, recall, learning curves, and representative detections.
- [ ] Compare single-modality vs. paired RGB–thermal SSL on label-scarce scenarios.

## Optional extensions

- [ ] Compare single-modality and paired RGB–thermal SSL.
- [ ] Test a lightweight RGB–thermal fusion detector.
- [ ] Measure inference latency for the best compact model.

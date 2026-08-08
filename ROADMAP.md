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

- [ ] Download and prepare the complete WiSARD dataset.
- [ ] Split data by collection rather than adjacent frame.
- [ ] Add paired-sample and annotation visualizations.
- [ ] Train RGB-only and thermal-only person detectors from scratch.
- [ ] Record mAP and recall baselines.

## Next: evaluate SSL for person detection

- [ ] Pretrain on the complete unlabelled training split.
- [ ] Fine-tune the same detector architecture from random and SSL initialization.
- [ ] Compare 1%, 5%, 10%, and 100% label settings.
- [ ] Report mAP, recall, learning curves, and representative detections.

## Optional extensions

- [ ] Compare single-modality and paired RGB–thermal SSL.
- [ ] Test a lightweight RGB–thermal fusion detector.
- [ ] Measure inference latency for the best compact model.

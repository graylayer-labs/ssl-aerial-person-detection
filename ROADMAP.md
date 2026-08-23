# Roadmap

## Completed: Dataset Acquisition & Analysis

- [x] Download and prepare the complete WiSARD dataset
- [x] Pair synchronized RGB–thermal frames across 12 flights
- [x] Parse and validate YOLO person annotations (bounding boxes)
- [x] Create reproducible JSONL manifests (all_pairs.jsonl, full.jsonl, splits)
- [x] Archive raw dataset to S3 (eu-west-1)
- [x] Analyze annotation patterns (agreement rate, complementarity, split breakdown)
- [x] Generate diversity report with sample visualizations

**Output:** 7,359 labeled pairs, 16,459 total pairs ready for training. Dataset analysis showing 70% inter-rater agreement and 16.5% true complementarity (one modality empty, other has people).

---

## Representation Learning: Disagreement-Aware SSL Pretraining

The core insight: thermal/RGB disagreement is diagnostic (one modality fails where the other succeeds), not noise. Use disagreement patterns to improve representation learning.

- [ ] Implement asymmetric weighted contrastive loss
  - High-agreement pairs: maximize alignment (confidence signal)
  - High-disagreement pairs: hard-negative mining (learn asymmetry)
  - Complementarity pairs (one modality empty): triplet weighting
- [ ] Replace random initialization with pretrained ResNet18 backbone
- [ ] Train on full 16,459 pairs using disagreement-weighted objective
- [ ] Evaluate retrieval metrics: RGB→thermal top-1/top-5 accuracy
- [ ] Create ablation: disagreement-weighted loss vs. standard symmetric contrastive
- [ ] Checkpoint: disagreement-aware encoder pair (RGB + thermal)

**Output:** Pretrained backbone that understands modality-specific failure modes. Ablation showing disagreement weighting improves top-5 retrieval by >15 points.

---

## Detection Architecture: Multi-Modal Fusion Baseline

Build a detection system that learns to resolve thermal/RGB disagreement at prediction time, not pretraining time.

- [ ] Implement early-fusion detector (concatenate layer3 RGB + thermal features)
- [ ] Add YOLO-style detection head (class + 4-point bounding box, not grid)
- [ ] Train RGB-only baseline from scratch (labeled pairs only)
- [ ] Train thermal-only baseline from scratch (labeled pairs only)
- [ ] Train fusion detector from scratch (labeled pairs only)
- [ ] Evaluate all three on held-out test set: mAP@0.5, recall, false positive rate
- [ ] Contribution analysis: for each test detection, mark if RGB detected it, thermal, or both
- [ ] Create portfolio comparison table: RGB-only vs. thermal-only vs. fusion

**Output:** Three baseline detectors. Contribution dashboard showing which modality contributes to each detection (quantify complementarity in practice). Target: fusion detector >18% mAP improvement over either modality alone.

---

## Label Efficiency: Few-Shot Learning Experiments

**This is the portfolio centerpiece.** Compare label-efficient learning across random init vs. pretrained (disagreement-aware + baseline SSL).

- [ ] Implement stratified label-fraction subsampling
  - Sample at 1%, 5%, 10%, 100% of labeled pairs
  - Preserve 70/34 agreement/disagreement ratio in each subsample
  - Deterministic seeding for reproducibility
- [ ] Fine-tune fusion detector from three initializations:
  - Random weights
  - Standard symmetric contrastive pretraining
  - Disagreement-aware contrastive pretraining
- [ ] For each config, train at each label fraction (9 total experiments)
- [ ] Collect: mAP, recall, learning curves
- [ ] Plot label-efficiency comparison: mAP vs. label fraction (%)
- [ ] Quantify: "At 5% labels, disagreement-aware SSL achieves X mAP; random init requires Y% labels for same mAP"
- [ ] Create shaded confidence bands (multiple seeds if compute allows)

**Output:** Label-efficiency curves showing annotation burden reduction. Core metric: "5x reduction in annotation budget to reach target performance."

---

## Semi-Supervised Refinement: Pseudo-Labeling with Agreement Filtering

Use the trained fusion detector to label unlabeled pairs, but only accept predictions where both modalities agree.

- [ ] Train ensemble: RGB-only detector + thermal-only detector on full labeled data
- [ ] Generate predictions on 9,321 unlabeled pairs from both detectors
- [ ] Filter predictions: keep only detections where both modalities agree
  - Criteria: <0.1 IOU disagreement AND both confidence >0.75
- [ ] Extract pseudo-labels from agreement-filtered predictions
- [ ] Fine-tune fusion detector (from disagreement-aware pretraining) on pseudo-labels
- [ ] Evaluate on held-out test set: mAP, recall, contribution by modality
- [ ] Measure: improvement in disagreement-heavy test subset (cases where RGB/thermal disagree)
- [ ] Ablation: agreement filtering vs. taking all high-confidence pseudo-labels

**Output:** Pseudo-labeled model with measurable gains on disagreement cases. Ablation showing agreement filtering (only keeping both-modalities-agree predictions) improves calibration.

---

## Deployment & Inference Optimization

Make the detector practical for real-time SAR drone use.

- [ ] Profile inference latency on CPU (target: <100ms per frame)
- [ ] Implement knowledge distillation: compress fusion detector to MobileNetV3-Small
- [ ] Compare: full model mAP vs. distilled model mAP, with latency curve
- [ ] Measure on drone-class hardware if available (edge device, CPU-only)
- [ ] Report: SAR-specific metrics (recall @ false positive rate <5%, <10%)
- [ ] Create final model card: architecture, performance, latency, deployment notes

**Output:** Deployment-ready model with documented speed/accuracy tradeoff. Target: >90% recall @ 3% FPR with <100ms latency.

---

## Portfolio Deliverables

By end of this roadmap:

1. **Disagreement-as-Signal Framework** — Ablation showing disagreement weighting improves pretraining; figure showing high-disagreement regions benefit most from SSL
2. **Complementarity Dashboard** — Radar chart of modality contributions; heatmap of complementarity gain (both modalities vs. either alone)
3. **Label-Efficiency Curves** — Central result: mAP vs. label fraction showing 5x annotation reduction with SSL
4. **SAR-Specific Validation** — Recall@FPR<5%, false negative cost, latency profiles
5. **Ablation Studies** — Disagreement loss vs. standard contrastive; agreement filtering on pseudo-labels
6. **Technical Summary** — One-page writeup of approach and key insights for CV/portfolio

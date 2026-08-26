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

The core insight: thermal/RGB disagreement is diagnostic (one modality fails where the other succeeds), not noise. Use disagreement patterns to improve representation learning. *Answers RQ1: Does disagreement improve SSL?*

### Core Implementation
- [ ] Compute agreement scores from paired data (rgb_boxes count vs thermal_boxes count)
- [ ] Implement asymmetric weighted contrastive loss
  - High-agreement pairs: maximize alignment (confidence signal)
  - High-disagreement pairs: hard-negative mining (learn asymmetry)
  - Complementarity pairs (one modality empty): special weighting
- [ ] Train on full 8,759 pairs (labeled + unlabeled) using disagreement-weighted objective
- [ ] Evaluate retrieval metrics: RGB→thermal & thermal→RGB top-1/top-5 accuracy
- [ ] Checkpoint: disagreement-aware encoder pair (RGB + thermal)

### Experiments (RQ1 Validation)
- [ ] **exp1_ssl_baseline:** Standard symmetric contrastive loss, ResNet18, 10 epochs
  - Baseline top-1/top-5 retrieval accuracy
- [ ] **exp2_ssl_disagreement_aware:** Disagreement-weighted loss, ResNet18, 10 epochs
  - Expect >15% improvement in top-1 retrieval vs exp1 (RQ1 confirmed)
- [ ] **exp3_ssl_pretrained_backbone:** Disagreement-weighted loss, pretrained ResNet18 (ImageNet), 10 epochs
  - Ablation: Does domain-adaptive pretraining help? (benchmark for Phase 2)

### Ablations
- [ ] Loss temperature: [0.05, 0.1, 0.2] (convergence sensitivity)
- [ ] Agreement weighting scheme: [linear, exponential, categorical] (which weighting works best?)
- [ ] Backbone selection: ResNet18 vs ResNet50 (speed vs accuracy trade-off)
- [ ] Training dynamics: loss curves, convergence speed, memory usage

**Output:** 
- Pretrained backbone checkpoint (from exp2) for Phase 2 detection training
- Ablation table: Disagreement weighting > baseline (quantified % improvement)
- Convergence plots (loss over epochs for each variant)
- **Portfolio message:** "Disagreement-aware SSL improves cross-modal alignment by X%, enabling better downstream detection"

---

## Detection Architecture: Multi-Modal Fusion Baseline

Build a detection system that learns to resolve thermal/RGB disagreement at prediction time, not pretraining time. *Answers RQ2: Does fusion exploit complementarity?*

### Core Implementation
- [ ] Implement early-fusion detector (concatenate layer3 RGB + thermal features before detection head)
- [ ] Use grid-based detection head (14×14 grid, "person present" per cell) — domain-appropriate for SAR
- [ ] Train detection baselines from scratch (no SSL pretraining; establishes baseline)
  - RGB-only: single modality detection
  - Thermal-only: single modality detection
  - Fusion: joint RGB+thermal feature processing
- [ ] Evaluate all three on held-out test set: mAP@0.5, recall, FPR
- [ ] Contribution analysis: for each test detection, which modality(ies) detected it?
- [ ] Create portfolio comparison table

### Experiments (RQ2 Validation)
- [ ] **det1_rgb_only:** GridDetector on RGB only, trained from scratch
  - Baseline RGB-only mAP, recall, FPR
- [ ] **det2_thermal_only:** GridDetector on thermal only, trained from scratch
  - Baseline thermal-only mAP, recall, FPR
- [ ] **det3_fusion:** Early-fusion detector (RGB + thermal), trained from scratch
  - Expect >10% mAP improvement vs max(det1, det2) (RQ2 confirmed)
- [ ] **det4_fusion_pretrained:** Fusion detector initialized from exp2 (SSL pretrained), fine-tuned on labeled data
  - Bonus experiment: does SSL pretraining help detection? (bridge to Phase 3)

### Ablations
- [ ] Fusion location: [early (layer3), late (output heads)] (where to fuse?)
- [ ] Detection head design: [grid-based, bbox regression] (appropriate for SAR?)
- [ ] Modality balancing: [equal weights, thermal-weighted, RGB-weighted] (should one modality dominate?)
- [ ] Inference latency: measure on CPU (must be <200ms for real-time)

**Output:**
- Three trained baseline detectors (det1, det2, det3)
- Comparison table: RGB mAP vs thermal mAP vs fusion mAP (fusion wins on mAP)
- Modality contribution heatmap: % detections by [RGB-only, thermal-only, both]
- **Portfolio message:** "Fusion detector leverages modality complementarity; catches people that either modality alone misses"

---

## Label Efficiency: Few-Shot Learning Experiments

**This is the portfolio centerpiece.** Compare label-efficient learning across random init vs. pretrained (disagreement-aware SSL). *Answers RQ3: How much does SSL reduce label requirements?*

### Core Implementation
- [ ] Implement stratified label-fraction subsampling
  - Sample at 1%, 5%, 10%, 100% of labeled pairs
  - Preserve agreement/disagreement ratio in each subsample (ensures fair comparison)
  - Deterministic seeding for reproducibility
- [ ] Fine-tune fusion detector from three initializations at each label fraction (9 configs)
  - S1: Random weights (baseline)
  - S2: Standard contrastive pretraining (baseline SSL)
  - S3: Disagreement-aware pretraining (proposed)
- [ ] For each config: collect mAP, recall, learning curves, training stability
- [ ] Plot label-efficiency curves: mAP vs. label fraction (%)
- [ ] Quantify annotation reduction: "At 5% labels, S3 reaches X mAP; S1 requires Y% labels"
- [ ] Confidence bands: show variance across seeds (measure stability)

### Experiments (RQ3 Validation)
- [ ] **eff1_supervised_random:** GridDetector with random init at label fractions [1%, 5%, 10%, 100%]
  - Baseline: how much labeled data do we need without SSL?
- [ ] **eff2_supervised_baseline_ssl:** GridDetector with standard contrastive SSL pretraining at same fractions
  - Baseline SSL: does generic pretraining help? (expect modest gain)
- [ ] **eff3_supervised_disagreement_ssl:** GridDetector with disagreement-aware SSL pretraining at same fractions
  - Proposed: expect significant gain; this is the main result for RQ3

### Ablations
- [ ] Stratification strategy: [stratified by agreement, random sampling] (does preserving disagreement help?)
- [ ] Number of seeds: [1, 3, 5] (is result stable?)
- [ ] Backbone freezing: [frozen, fine-tuned] (should we freeze or fine-tune pretrained features?)
- [ ] Label sampling strategy: deterministic seeding for reproducibility

### Bonus: Disagreement Analysis (RQ4 Validation)
- [ ] **RQ4 analysis:** Categorize disagreement cases in test set
  - After fine-tuning, identify test samples where RGB and thermal detection counts differ significantly
  - Manual inspection: sample 100-200 disagreement cases
  - Categorize by visual features: [low-light conditions, temperature-only targets, occlusion/foliage, ambiguous people]
  - Quantify: % disagreement cases explained by each category
  - Success metric: explain >80% of disagreement cases by domain-specific failure modes

**Output:**
- Label-efficiency curves (mAP vs. label %, with confidence bands)
- **Central portfolio figure:** Comparison of eff1 vs eff2 vs eff3 curves
- Quantified claim: "SSL reduces annotation budget by X-Y times" (specific numbers from experiments)
- Learning curves: training stability across label fractions
- Disagreement analysis: categorization of why modalities disagree (domain insights)
- **Portfolio message:** "With SSL pretraining, you reach target performance with fewer labels; disagreement analysis shows modality specialization"

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

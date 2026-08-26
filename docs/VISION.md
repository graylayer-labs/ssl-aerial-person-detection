# Project Vision & Research Hypotheses

## The Thesis

**"Thermal-RGB disagreement is a training signal, not noise. By exploiting this multi-modal structure through self-supervised pretraining and disagreement-aware weighting, we can build person detectors that achieve high performance with minimal labeled data."**

This project is a portfolio investigation into:
1. How to leverage disagreement between complementary sensors as a learning signal
2. Whether domain-adaptive self-supervised learning (on real paired data) outperforms supervised learning with limited labels
3. The practical value of multi-modal fusion for real-world robotics constraints (real-time inference on drone hardware)

---

## Problem Context

Search & Rescue teams have:
- **Abundant unlabeled drone footage** (hundreds of flights, thousands of hours)
- **Expensive manual labeling** (SAR imagery is hard to annotate; requires domain expertise)
- **Complementary sensors** (thermal captures heat signatures; RGB captures detail) that fail in different ways

**Existing approaches:**
- Standard supervised learning: train one detector per modality, ensemble at test time (leaves modality complementarity on the table)
- Generic domain-adaptive SSL: pretrain on ImageNet features, fine-tune on limited SAR labels (doesn't exploit paired structure)

**Our hypothesis:** 
By using paired thermal-RGB data as the primary training signal (via self-supervised learning + disagreement-aware weighting), we can:
- Build stronger feature representations without labels
- Reduce annotation burden by 5x compared to supervised learning
- Create detectors that understand *when to trust thermal vs. RGB* (explicit in disagreement handling)

---

## Research Questions & Hypotheses

### RQ1: Does Disagreement Improve Self-Supervised Pretraining?
**Hypothesis:** When thermal and RGB detect different numbers of people, this disagreement is diagnostic (one modality is correct, the other has a domain-specific failure mode). Using disagreement patterns as hard negatives in contrastive learning should improve feature quality.

**Test:** Compare two SSL pretraining variants:
- H0 (baseline): Standard symmetric contrastive loss (all pairs treated equally)
- H1 (proposed): Disagreement-aware loss (high-agreement pairs maximize alignment, disagreement pairs are hard negatives)

**Success metric:** H1 achieves >15% higher top-1 retrieval accuracy (RGB→thermal cross-modal retrieval) than H0

### RQ2: Does Multi-Modal Fusion Exploit Complementarity?
**Hypothesis:** Thermal and RGB have complementary failure modes (thermal sees heat, RGB sees detail). A fusion detector that processes both modalities jointly should catch people that either modality alone misses.

**Test:** Train three detection baselines:
- B1 (baseline): RGB-only detector
- B2 (baseline): Thermal-only detector  
- B3 (proposed): Early-fusion detector (RGB + thermal features concatenated before detection head)

**Success metric:** B3 achieves >10% higher mAP@0.5 than max(B1, B2)

### RQ3: How Much Does SSL Reduce Label Requirements?
**Hypothesis:** Self-supervised pretraining on unlabeled paired data reduces the labeled data needed to reach a target performance level by 5x or more.

**Test:** Fine-tune detection detectors from:
- S1 (baseline): Random initialization at label fractions [1%, 5%, 10%, 100%]
- S2 (proposed): SSL-pretrained backbone at same label fractions

**Success metric:** S2 reaches 0.60 mAP@0.5 with 5% labels; S1 requires 25%+ labels

### RQ4: What Causes Thermal-RGB Disagreement?
**Hypothesis:** Disagreement falls into predictable categories (thermal false positives on non-human heat, RGB false negatives in darkness/occlusion). Understanding these patterns can guide detector design.

**Test:** Analyze disagreement cases in the dataset:
- Cases where thermal detects people, RGB doesn't
- Cases where RGB detects people, thermal doesn't
- Categorize by visual features (lighting, temperature, occlusion)

**Success metric:** Can explain >80% of disagreement cases by domain-specific failure modes; qualitative insight for future work

---

## Experimental Plan (Aligned with Roadmap)

### Phase 1: SSL Pretraining Experiments
**Core experiments:**
- `exp1_ssl_baseline`: Standard contrastive loss (symmetric), ResNet18, 10 epochs
- `exp2_ssl_disagreement_aware`: Disagreement-weighted loss, ResNet18, 10 epochs
- `exp3_ssl_pretrained_backbone`: Disagreement-weighted loss, pretrained ResNet50, 10 epochs (ablation: does pretraining help?)

**Ablations:**
- Loss temperature: [0.05, 0.1, 0.2] (does temperature affect disagreement weighting?)
- Agreement weighting scheme: [linear, exponential, binary] (which weighting function is best?)
- Backbone size: [ResNet18, ResNet50] (speed vs. accuracy trade-off)

**Metrics to track:**
- Contrastive loss (training curves)
- Top-1/Top-5 RGB→Thermal retrieval accuracy
- Top-1/Top-5 Thermal→RGB retrieval accuracy
- Training time & peak memory

**Deliverable:** Ablation table showing disagreement > baseline; figure showing loss convergence

### Phase 2: Detection Baseline Experiments
**Core experiments:**
- `det1_rgb_only`: GridDetector on RGB only, trained from scratch
- `det2_thermal_only`: GridDetector on thermal only, trained from scratch
- `det3_fusion`: Early-fusion detector (RGB + thermal), trained from scratch
- `det4_fusion_pretrained`: Fusion detector initialized from `exp2_ssl_disagreement_aware`, fine-tuned on labeled data

**Ablations:**
- Fusion location: [early (layer3), late (output heads)] (where to fuse?)
- Detection head design: [grid-based, bbox regression] (grid vs. boxes for SAR?)
- Modality balancing: [equal weight, thermal weight, RGB weight] (should one modality dominate?)

**Metrics to track:**
- mAP@0.5, mAP@0.75
- Recall @ FPR < 5%, < 10% (SAR doesn't want false alarms)
- Per-modality contribution (% detections: RGB-only, thermal-only, both)
- Inference latency (should be <200ms for real-time)

**Deliverable:** Comparison table (RGB vs thermal vs fusion); modality contribution heatmap

### Phase 3: Label Efficiency Experiments
**Core experiments:**
- `eff1_supervised_random_init`: GridDetector with random init at label fractions [1%, 5%, 10%, 100%]
- `eff2_supervised_ssl_pretrained`: GridDetector with SSL-pretrained backbone at same fractions
- `eff3_supervised_disagreement_aware`: GridDetector with disagreement-aware SSL at same fractions

**Ablations:**
- Stratification strategy: [stratified by agreement, random sampling] (does preserving disagreement distribution help?)
- Number of seeds: [1, 3, 5] (stability across random seeds?)
- Backbone freezing: [frozen, fine-tuned] (should we freeze or fine-tune pretrained features?)

**Metrics to track:**
- mAP@0.5 vs. label fraction (%)
- Convergence speed (epochs to reach target mAP)
- Sample efficiency (how many labeled examples per unit of mAP improvement?)

**Deliverable:** Label-efficiency curves (mAP vs. label %, with confidence bands); quantified claim ("SSL requires 5x fewer labels")

### Phase 4 (Optional): Advanced Experiments
**If time/compute allows:**
- `adv1_pseudo_labeling`: Pseudo-label unlabeled pairs, retrain detection detector
- `adv2_distillation`: Distill fusion detector to MobileNetV3-Small for real-time inference
- `adv3_uncertainty`: Train auxiliary "which modality to trust" classifier
- `adv4_domain_shift`: Test detector on out-of-distribution flights (generalization)

---

## Expected Outcomes & Impact

### Scientific Contribution
- **Methodological:** Disagreement-aware SSL for multi-modal learning (novel loss function)
- **Empirical:** Quantified value of thermal-RGB complementarity on real SAR data
- **Practical:** Framework for label-efficient detection in constrained robotics settings

### Portfolio Impact
- **Central narrative:** "I built a thermal-RGB detector that exploits modality disagreement to reduce annotation cost by 5x"
- **Technical depth:** Demonstrates understanding of SSL, multi-modal fusion, SAR domain constraints
- **Business value:** Shows how ML reduces costs for real SAR teams (from expensive labeling → cheap pretraining)

### Reproducibility & Open Science
- Code available on GitHub (public repo)
- Detailed ablations & hyperparameter searches documented
- Figures suitable for publication (conference/journal or portfolio)
- Codebase clean enough for others to adapt to their own multi-modal problems

---

## Key Design Principles

1. **Disagreement ≠ Noise:** Treat modality disagreement as informative, not corrupted labels
2. **Domain-First:** Design for SAR constraints (real-time, uncertainty in annotations, multi-modal) rather than generic vision benchmarks
3. **Ablation-Heavy:** Don't assume; test every claim (ResNet18 vs 50, grid vs bbox, etc.)
4. **Reproducible:** Deterministic seeds, clear hyperparameters, confidence bands (not single runs)
5. **Portfolio-Ready:** Figures tell a story; code is clean; writing is clear for non-experts

---

## Success Criteria (Project-Level)

### Must Have:
- ✅ SSL pretraining reduces cross-modal retrieval error by >15% (disagreement matters)
- ✅ Fusion detector outperforms single-modality (complementarity proven)
- ✅ SSL reduces labeled data requirement by 5x (label efficiency shown)
- ✅ Code is reproducible and documented (github-ready)

### Should Have:
- ✅ Ablations show trade-offs (ResNet size, loss weighting, fusion location)
- ✅ Portfolio figures are publication-quality (suitable for CV/thesis)
- ✅ Project can be explained to senior engineers in 10 minutes (clear story)

### Nice to Have:
- ✅ Pseudo-labeling improves performance further
- ✅ Distilled model runs real-time on CPU
- ✅ Analysis of what causes thermal-RGB disagreement (domain insights)
- ✅ Paper/blog post explaining findings

---

## Related Work & Positioning

**How this differs from standard multi-modal learning:**
- Standard approach: treat RGB and thermal as redundant; train an ensemble
- **Our approach:** treat disagreement as informative; use it as training signal

**How this differs from standard SSL:**
- Standard approach: pretrain on unlabeled data (any data), fine-tune on task
- **Our approach:** exploit the *structure* of paired thermal-RGB data (disagreement patterns) as part of pretraining

**How this differs from SAR literature:**
- Standard SAR detection: train thermal detector, train RGB detector, pick best per frame
- **Our approach:** jointly learn from thermal-RGB disagreement; fusion detector that understands modality trade-offs

---

## Reference & Inspiration

- **Multi-modal learning:** CLIP (vision-language alignment), ViLBERT (cross-modal attention)
- **Self-supervised learning:** SimCLR, MoCo (contrastive learning with hard negatives)
- **SAR detection:** WiSARD dataset papers, FLIR thermal detection challenges
- **Domain adaptation:** Domain adversarial training, transfer learning theory
- **Robotics constraints:** Real-time inference requirements, edge deployment (MobileNets, distillation)

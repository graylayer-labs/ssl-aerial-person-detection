# The Research Problem

## The Problem

Search and Rescue (SAR) teams operate drones equipped with both RGB and thermal
cameras to locate missing people in wilderness and urban environments. Manually
labeling every frame to train a detector is prohibitively expensive. Meanwhile,
unlabeled drone footage is abundant—teams record many flights that don't get
fully annotated.

## Research Questions

This project investigates:

- Does paired-modality SSL outperform single-modality models?
- How much labeled data do we actually need?
- Can SSL reduce manual labeling effort compared to traditional Turk-scale annotation?
- Is the WiSARD public dataset diverse enough (times of day, terrain, weather) to
  build a generalizable detection system?

## Technical Approach

A drone searching for a person may have both a visible-light camera and a thermal
camera. RGB captures texture and scene detail but becomes less useful in poor light.
Thermal imagery can reveal people in darkness, but heat signatures may blend into
the environment.

**Key insight:** RGB and thermal cameras see differently. When RGB misses a person
due to poor lighting, thermal often catches the heat signature. When thermal's heat
signal blends into the environment, RGB's texture detail reveals the person. These
different modalities provide complementary information about the same scene.

We use self-supervised contrastive learning on paired RGB–thermal images to learn
representations that exploit this complementarity, before fine-tuning on limited
person-detection labels. Unlabeled paired data can teach a model that the same
person can be represented through different visual mechanisms; this should help a
detector generalize to rare or difficult-to-label cases.

## Experiment Design

We will compare three approaches:

1. A person detector trained from scratch (random initialization).
2. A detector initialized from single-modality SSL pretraining (RGB-only or
   thermal-only encoder).
3. A detector initialized from paired RGB–thermal SSL pretraining.

Each approach will be fine-tuned with different fractions of the available person
annotations (1%, 5%, 10%, 100%). Detection mAP and recall will show whether paired
pretraining helps, particularly when labeled data is scarce.

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

**Key insight:** RGB and thermal cameras see differently—they provide
*complementary* views of the same person. When RGB misses a person due to poor
lighting, thermal often catches the heat signature. When thermal's heat signal
blends into the environment, RGB's texture detail reveals the person. This
complementarity is the signal self-supervised learning can exploit.

**Two key metrics:**

**Agreement Rate** — What fraction of images have the same number of detected people
in both RGB and thermal? High agreement (70%) means both modalities are synchronized.
Low agreement (43%) means they see different things—which, counterintuitively, is
valuable for SSL. It means the modalities are capturing different information about
the same person.

**Complementarity** — Cases where one modality detects people the other completely
misses (e.g., thermal sees someone RGB can't due to darkness, or vice versa). This
is the complementary signal SSL needs: it forces the encoder to learn that RGB and
thermal can represent the same person through different visual mechanisms.

We use self-supervised contrastive learning on paired RGB–thermal images to learn
representations before fine-tuning on limited person-detection labels. Unlabeled
paired data reveals relationships between modalities; this helps a detector
generalize to rare or difficult-to-label cases.

## Experiment Design

We will compare three approaches:

1. A person detector trained from scratch (random initialization).
2. A detector initialized from single-modality SSL pretraining (RGB-only or
   thermal-only encoder).
3. A detector initialized from paired RGB–thermal SSL pretraining.

Each approach will be fine-tuned with different fractions of the available person
annotations (1%, 5%, 10%, 100%). Detection mAP and recall will show whether paired
pretraining helps, particularly when labeled data is scarce.

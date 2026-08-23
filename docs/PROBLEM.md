# The Research Problem

## The Problem

Search and Rescue (SAR) teams operate drones equipped with both RGB and thermal
cameras to locate missing people in wilderness and urban environments. Manually
labeling every frame to train a detector is prohibitively expensive. Meanwhile,
unlabeled drone footage is abundant—teams record many flights that don't get
fully annotated.

The core constraint: **limited annotation budget, abundant unlabeled data.**

## The Data Characteristic: Cross-Modal Complementarity

A drone's RGB camera captures texture and scene detail but becomes less useful in poor light.
Thermal imagery can reveal people in darkness, but heat signatures may blend into the environment.

**Critical observation:** RGB and thermal cameras fail in different scenarios:
- Thermal false positives: non-human heat sources (rocks, engines, animals, sun glare)
- RGB false negatives: darkness, occlusion, foliage

When you have both modalities on the same target, they provide **complementary information** about the same scene. One modality's weakness is often the other's strength.

## Research Questions

This project investigates:

- Can we exploit thermal/RGB complementarity to train better detectors with minimal labeled data?
- How much annotation is truly needed if we leverage unlabeled paired footage?
- Does the WiSARD public dataset (12 flights, varied terrain, multiple times of day) contain enough diversity to train a generalizable detector?
- What is the actual value of having both modalities vs. using a single camera?

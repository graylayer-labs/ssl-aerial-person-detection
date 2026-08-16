# Glossary

## Agreement Rate

**Definition:** Fraction of images where RGB and thermal cameras detect the same number of people.

**Why it matters for SAR:**
- Real Search & Rescue teams can't choose when to use each modality—both cameras run simultaneously
- When agreement is high (70%+): typical conditions, both modalities see the same target
- When agreement is low (43%): harder conditions, one modality catches what the other misses

**What low agreement teaches SSL:**
- RGB is strong when: it's daylight, target has contrast, visibility is good
- Thermal is strong when: it's dark, target has heat signature, RGB lighting is poor
- Neither is redundant; they're **complementary**

**In this dataset:**
- Train: 70% agreement (typical daylight)
- Validation: 43% agreement (harder conditions)
- This variation is realistic and valuable

---

## Complementary Modalities

**Definition:** Two sensors that see different things because they measure different physical properties.

**RGB camera:** Detects reflected light (color, texture, contrast)
- Works well: daylight, high contrast, visible outlines
- Fails: darkness, poor lighting, camouflage to visible spectrum

**Thermal camera:** Detects infrared radiation (body heat 30-37°C)
- Works well: darkness, clear heat signature, night operations
- Fails: cold/wet people, thermal camouflage, heat blended with environment

**Why this matters:**
A detector trained on perfect agreement (100%) would learn to rely on one modality and fail when it doesn't work. Real SAR requires learning when to trust each.

---

## Collection-Level Splits

**Definition:** Training/validation/test splits are done at the flight collection level, not individual frame level.

**Why this matters:**
- **Without collection splitting:** Training and validation might share frames from the same flight → model overfits to that specific flight's conditions
- **With collection splitting:** Different flights go to different splits → detector learns to generalize across flights
- **In this dataset:** No single flight appears in multiple splits (prevented via seeded bin-packing)

---

## RGB-Thermal Pairing Strategy

**Real-world data is messy:**
- Some locations have 3 VIS (RGB) directories but 7 IR (thermal) directories
- Image counts don't always match (different sensor frame rates)
- Some images lack annotations

**Our pragmatic approach:**
- **Accept the messiness:** Don't filter out "imperfect" data
- **Pair what we can:** If a location has 3 RGB and 7 thermal, create 3 pairs
- **Skip unannotated:** Missing labels = skip that frame, keep labeled ones
- **Clamp coordinates:** If a bounding box goes outside [0, 1], clamp it (annotation error)

**Result:** 7,359 usable pairs from real data that didn't force-fit into artificial structure

---

## Self-Supervised Learning (SSL)

**Definition:** Training representations without manual labels by exploiting structure in the data itself.

**For this project:**
- Train on RGB-thermal **pairs** (both images of the same scene)
- Learn: paired images should have similar embeddings, unpaired should be different
- Don't need person labels for pretraining; just need paired camera streams
- Pretrained embeddings then fine-tune with limited labels (label efficiency)

**Why RGB-thermal pairs work for SSL:**
- Agreement gives natural positive pairs (both see the person)
- Disagreement gives natural hard negatives (one sees, other doesn't)
- Model learns modality strengths naturally from the data

---

## Honest Data vs. Perfect Data

**Perfect data:** Filtered, cleaned, 100% agreement, no edge cases
- Easier to train on
- Doesn't represent real operational conditions
- Detector fails when deployed

**Honest data:** Real-world conditions, messiness included, realistic disagreement
- Harder to work with
- Represents actual SAR operations
- Detector generalizes better

**This project uses honest data intentionally.**

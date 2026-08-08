# Self-Supervised Learning for Low-False-Alarm Aerial Person Detection

High-recall aerial person detection with a realistic false-alarm budget.

## The brief

Imagine a wilderness search-and-rescue team has asked us to help review imagery
from an RGB and thermal camera carried by a drone.

Most of a search flight contains nobody. A missing person may occupy only a few
pixels, be partly hidden by vegetation, or appear under poor lighting. Thermal
imagery helps at night, but warm rocks, animals, and branches can resemble people.
The model must therefore do more than detect people in images already known to
contain them. It must search long, mostly empty recordings without overwhelming an
operator with false alarms.

This project explores whether self-supervised learning from unlabelled RGB and
thermal flight imagery can reduce the amount of labelled data required while
preserving person recall at a practical false-alarm rate.

This scenario is hypothetical. This is an independent research project using
the public WiSARD dataset; it is not commissioned by or affiliated with the WiSARD
authors.

## The data

[WiSARD](https://sites.google.com/uw.edu/wisard/) is a public wilderness
search-and-rescue dataset collected from UAV flights in Washington, USA. It
contains approximately:

- 26,862 labelled RGB images;
- 29,989 labelled thermal images;
- 15,453 temporally synchronized RGB–thermal pairs.

The imagery spans forests, fields, rocky and coastal terrain, snow, different
seasons, and day, night, dawn, and dusk. People are annotated with bounding boxes.
A 971.6 MB multimodal sample from one flight is available for initial development;
the complete dataset is approximately 40.5 GB.

RGB and thermal frames are synchronized but not necessarily pixel-aligned. They
show the same moment from sensors with different resolutions and fields of view.

## The data problem

The dataset was created to study person detection, but its published baseline does
not reproduce the prevalence of a real search.

The baseline divides high-resolution RGB frames into `512 × 512` tiles and removes
almost every tile without a person, retaining only 0.1% of those tiles. This makes
training faster and balances the detector's input, but it also removes much of the
ordinary wilderness background that a deployed model would see continuously.

That creates four risks:

1. **Unrealistic prevalence.** A real flight is mostly empty, while a curated
   benchmark may contain people unusually often.
2. **Unmeasured false-alarm burden.** Good mAP can hide a detector that repeatedly
   flags rocks, branches, or animals during a long flight.
3. **Temporal leakage.** Randomly splitting adjacent video frames can place nearly
   identical scenes in training and test data.
4. **Changing sensor quality.** RGB degrades in darkness; thermal can lose contrast
   when a person and the background have similar temperatures.

Before modelling, we audit how many source frames are genuinely empty and
whether the supplied metadata supports flight-level splits.

## Our approach

### 1. Build a search-like benchmark

We will preserve background-only frames and sample negative tiles alongside person
tiles. Splits will keep complete flights or collections together. The test set will
simulate a long search in which positive frames are rare.

### 2. Establish supervised baselines

RGB-only, thermal-only, and simple fused detectors will establish what the labels
alone can achieve. These models will be measured on identical data splits.

### 3. Learn from unlabelled flight imagery

Self-supervised pretraining will use all training imagery—including the abundant
background frames—without person annotations. The resulting encoder will then be
fine-tuned using 1%, 5%, 10%, and 100% of the available bounding boxes.

### 4. Test sensor failure and hard negatives

We will break results down by lighting and terrain, degrade or remove one modality,
and inspect the model's most confident false detections. Hard negatives may inform
later training, but the fixed test set will remain untouched.

## What success means

Standard mAP will be reported for comparison with existing work, but it is not the
primary measure of usefulness. The project prioritizes:

- person recall;
- false positives per 1,000 frames;
- recall at fixed false-alarm budgets;
- false alarms per hour at a declared sampling rate;
- performance as the annotation budget is reduced.

The useful result is not simply “SSL improved accuracy.” It is evidence that the
model can inspect mostly empty aerial imagery, miss fewer people, and keep the
number of operator interventions manageable.

## Getting started

Python 3.12 and [`uv`](https://docs.astral.sh/uv/) are required.

```bash
uv sync --dev
uv run aerial-search fetch wisard-sample
uv run aerial-search inspect data/raw/wisard-sample
```

The fetch command downloads the official sample, resumes interrupted transfers,
checks its expected size and ZIP integrity, and safely extracts it beneath
`data/raw/`. Dataset files are ignored by Git.

Development checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

See [ROADMAP.md](ROADMAP.md) for the experiment sequence and
[docs/repository-design.md](docs/repository-design.md) for the code and data layout.

## Status

The repository currently contains the research plan and data-acquisition tooling.
The WiSARD sample audit is the first milestone. No model results have been produced
yet, and this is not a deployed search-and-rescue system.

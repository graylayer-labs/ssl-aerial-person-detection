# Starting model and datasets

Decision note for issue #5. Written 2026-10-01 by the lead from a survey by the
`researcher` agent (posted on #5 on 2026-09-29) and a verification pass against
the primary sources on 2026-10-01. Where the two disagreed, the verified fact
is used and the correction is noted.

## Decision changed, 2026-10-01

The owner chose not to start on a Meta model: "yes, go with SigLIP 2 first".
The starting backbone is therefore **SigLIP 2** (Google, Apache-2.0, no
gated download; patch size 16; the base model at 512 pixels is
`google/siglip2-base-patch16-512`, and the family includes variable-resolution
"NaFlex" variants that may suit tiling). **EVA-02** (BAAI, MIT) is the second
non-Meta option, and **DINOv2** stays as a comparison point. The next
milestone compares backbones, so the order is a starting point and not a
verdict. Everything below this section is the analysis as written on
2026-10-01 before that choice; its facts still hold.

Verified at the source on 2026-10-01: the SigLIP 2 licence line on the
Hugging Face page reads `apache-2.0`, with no gating; the paper is dated
2025-02-20. Not yet verified: EVA-02's page needed a login; its licence is
reported as MIT elsewhere. Neither model has published evidence on thermal
input or on tiny people; the same was true of DINOv3.

## Original decision

Start from **DINOv3**, kept frozen, in three sizes:

| Role | Model | Parameters | Identifier |
|---|---|---|---|
| Fast control | ViT-S/16, web pretraining | 21 M | `facebook/dinov3-vits16-pretrain-lvd1689m` |
| Main backbone | ViT-B/16, web pretraining | 86 M | `facebook/dinov3-vitb16-pretrain-lvd1689m` |
| Aerial comparison | ViT-L/16, satellite pretraining | 300 M | `facebook/dinov3-vitl16-pretrain-sat493m` |

Feed thermal images to the same backbone, replicated to three channels, as the
**first** thermal experiment. A learned input stem and adapters are an
ablation, not the starting point.

Other datasets are not added in this milestone. The ones to add first, when the
time comes, are RGBTDronePerson and HIT-UAV.

## Why DINOv3

- It is the most recent model with strong dense, patch-level features, released
  August 2025, and it has a satellite-pretrained variant for the aerial
  comparison.
- It comes in sizes from 21 M to 6.7 B parameters, so the same family covers
  the laptop and a later cloud run.
- Its licence allows this project's use (see below).
- The plan is to run every image through the frozen backbone once, cache the
  features, and train small heads on the cache. What matters is one forward
  pass per image, which the small and base models can do on the laptop.

Alternatives considered:

| Model | Why not first |
|---|---|
| DINOv2 | Older dense features; DINOv3 is its successor from the same group |
| V-JEPA 2.1 | A video model. No aerial or tiny-object evidence found. Kept for the temporal epic |
| Remote-sensing models (Prithvi, DOFA, SatMAE) | Satellite ground resolution, multispectral; the DINOv3 satellite model covers the comparison |
| Infrared-only models | Narrow and small; not general enough to start from |
| SigLIP 2, Perception Encoder, RADIO | Not surveyed. A gap, recorded here |

## Why thermal starts frozen, not adapted

The survey said a frozen RGB backbone fails badly on thermal input, citing
SpectraDINO (arXiv 2605.02258): 25.6 against 39.3 mAP. Verification found that
those numbers come from the first version of the paper only, on short-wave
infrared driving data, and that the comparison model was pretrained on 300,000
cross-spectral pairs, not a small stem trained on the target. The current
version of the paper, revised 2026-07-29, gives:

| Task, current version | Frozen DINOv2 | Adapters and stems |
|---|---|---|
| SWIR detection (RASMD), mAP 0.5:0.95 | 37.3 | 39.3 |
| LWIR segmentation (MFNet) | 57.0 | 55.8 |
| LWIR segmentation (SemanticRT) | 72.4 | 72.2 |

So the evidence does not show that thermal needs adaptation from the start.
The honest first measurement is the frozen backbone with a simple head on
thermal, and the stem is tested as an ablation against it. Note that this
evidence is for DINOv2; no source read tested DINOv3 on thermal input.

## The problem of very small people

DINOv3 uses 16-pixel patches. People in this footage are often 8 to 12 pixels
across, so one person sits inside one patch. The paper reports that a
high-resolution adaptation step keeps features stable well above the training
resolution, and its examples run at 768 and 1024 pixels, but neither the paper
nor the repository gives any guidance on small objects. The first experiment
therefore runs at high resolution with tiling, and reports results by object
size using the buckets in the evaluation module. Whether the features carry
enough to find a 10-pixel person is an open question, not an assumption.

## Licences

**DINOv3.** Licence dated 2025-08-19, read at the repository. Research and
commercial use are allowed; there is no research-only clause. Three clauses
bind this project:

- 1.b.ii: published results must acknowledge the use of DINO Materials. This
  project treats blog posts as publications and will acknowledge it there.
- 1.b.i: redistribution must carry the licence. The repository will not host
  the weights.
- 1.b.v: no use for military or warfare purposes, nuclear, espionage, or
  weapons, and no permitting others to. Search and rescue is not listed. The
  project's write-ups will say so, and the project does not provide its
  models to third parties.

The weights are gated: obtaining them means accepting Meta's terms through a
form and sharing contact details. That is the owner's step, not an agent's.

**WiSARD.** The dataset site carries the standard MIT licence text, under the
names of three authors, applied to "the Software". It does not say in so many
words that it covers the images. The paper is under IEEE terms, which govern
the paper and not the data. The site asks for a citation, which the project
gives. The paper and the site disagree on image counts (33,786 visual and
22,156 thermal in the paper; 26,862 and 29,989 on the site); both say 15,453
pairs. This project quotes only its own counts from its own pairing.

**Candidate extra datasets**, checked at their own pages on 2026-10-01:

| Dataset | Licence | Use here |
|---|---|---|
| RGBTDronePerson | CC BY 4.0, stated | Paired RGB and thermal, tiny people. First to add |
| HIT-UAV | CC BY 4.0 in the repository; a third-party listing says CC0 | Thermal only, labelled. Second to add |
| SeaDronesSee | CC0, stated in the repository README; the site's own terms could not be read | Unlabelled aerial RGB, later |
| AIResQ | CC BY 4.0, but the full dataset record is restricted and "available upon request" | Only the benchmark subset is open |
| VisDrone | No licence at the primary source | Not used until terms are found |
| VTUAV | No licence; tracking data with no detection labels | Not used |
| HERIDAL | Page unreachable; a search listing says CC BY 3.0 | Unverified; not used until read |

## What a good baseline looks like

The strongest published low-label result found is ACT (arXiv 2609.18124,
September 2026): paired RGB and infrared, mean average precision 0.511, 0.644,
and 0.683 at 1%, 5%, and 10% of labels, reaching 94% of full supervision at
10%. It is **vehicles** on DroneVehicle, with rotated boxes about 50 pixels
wide, scored on infrared annotations. It shows what label-efficient paired
training can do; it is not a person baseline. No published low-label
person-detection result on WiSARD was found.

## First experiment

Proposed for epic #14, to be designed in detail there.

1. Take the leave-one-site-out folds from #3.
2. Run frozen DINOv3 ViT-S/16 and ViT-B/16 over every image at 1024 pixels,
   tiled, and cache the patch features. Thermal is replicated to three
   channels.
3. Train a light detection head on the cache at 1%, 5%, 10%, and 100% of
   labels, per fold.
4. Score with the evaluation module; report `ap_iou25` with `ap_iou50` beside
   it, recall at fixed false alarms per image, and results by size bucket.
5. Compare against a small off-the-shelf detector trained on the same labels.

Runtime is not yet measured. The survey's estimate of 30 to 40 minutes on the
laptop is inferred. The feature cache at full detail is about 94 GB for ViT-S
and 189 GB for ViT-B at 1024 pixels (see #7); the design in #14 has to choose a
resolution or a pooling that fits the disk before the first run.

## Open

- The owner accepts the DINOv3 terms and obtains the weights.
- One forward pass of ViT-B/16 at 1024 pixels is timed on the laptop.
- SigLIP 2, Perception Encoder, and RADIO are checked as backbones before the
  epic #14 design is final.

## Sources

Verified on 2026-10-01 unless marked.

- DINOv3: github.com/facebookresearch/dinov3 (README, LICENSE.md);
  arxiv.org/abs/2508.10104; huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m;
  huggingface.co/facebook/dinov3-vitl16-pretrain-sat493m
- WiSARD: sites.google.com/uw.edu/wisard; arxiv.org/abs/2309.04453
- SpectraDINO: arxiv.org/abs/2605.02258, versions 1 and current
- ACT: arxiv.org/abs/2609.18124
- RGBTDronePerson: nnnnerd.github.io/RGBTDronePerson
- AIResQ: nature.com/articles/s41597-026-07663-9; zenodo.org/records/17405073
- HIT-UAV: github.com/suojiashun/HIT-UAV-Infrared-Thermal-Dataset
- SeaDronesSee: github.com/Ben93kie/SeaDronesSee
- VisDrone: github.com/VisDrone/VisDrone-Dataset; aiskyeye.com/download
- VTUAV: github.com/zhang-pengyu/DUT-VTUAV
- Survey of 2026-09-29, on issue #5, for V-JEPA 2.1 and the remote-sensing
  models, which were not re-verified

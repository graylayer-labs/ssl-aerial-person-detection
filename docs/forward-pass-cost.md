# Cost of one forward pass on the laptop

Issue #64, first task of the "Frozen baseline" epic (#14). Scratch measurements
from a branch: not quotable results. Machine: Apple M4, 24 GB, PyTorch 2.13.0
on MPS, `transformers` 5.18.0, fp16. Tool: `tools/forward_pass_cost.py`.

**Status: incomplete.** Only one model has a clean timing. Partway through, the
laptop's screen locked (`IOConsoleLocked = Yes`) and every later MPS run was
slow, noisy, or stalled inside `Tensor.cpu()` waiting for the GPU. Those
numbers are listed as throttled and must not be used for planning. The
remaining timings need a rerun with the screen unlocked (see "To finish").

## What was measured

Per image, batch size 1 (a tiled frame is one batch of four tiles). The timed
region covers the host-to-device copy, the vision tower, the 2x2 pooling, and
the copy of the patch features back to the host. JPEG decoding and resizing
are outside it. Patch tokens (the `last_hidden_state`, with the CLS token
dropped for DINOv2), not the pooled embedding. 50 frames, seed 0, from
`data/manifests/wisard-full/all_pairs.jsonl`. Fixed-resolution models squash
the 16:9 frame to a square; this changes the picture, not the cost. No
`PYTORCH_ENABLE_MPS_FALLBACK` was set, so an op without an MPS kernel would
have raised. None did, in any run: no CPU fallback.

Cache projections use 29,668 images (every RGB and thermal frame in the pair
manifest) and the per-image size in fp16. "Pooled" is 2x2 average pooling.

| Model | Input | Grid (h x w x dim) | ms / image | Peak MPS | Features fp16 | Pooled | Cache, full | Cache, pooled | Time, 29,668 |
|---|---|---|---|---|---|---|---|---|---|
| SigLIP 2 base 512 | 512, single | 32x32x768 | 92.1 (std 0.5) | 0.23 GB | 1.5 MB | 0.38 MB | 46.7 GB | 11.7 GB | 45.6 min |
| SigLIP 2 base 512 | 1024, 4 tiles | 64x64x768 | 297.7 (std 2.1) | 1.28 GB | 6.0 MB | 1.5 MB | 186.7 GB | 46.7 GB | 147 min |

Both rows: RGB, 50 frames, seed 0, before the screen locked. A second run on 6
frames gave 92.3 and 301.2 ms.

Sizes and grids that do not depend on timing (read from runs that completed;
the DINOv2 tiled row is computed, not run):

| Model | Input | Grid | Features fp16 | Pooled | Cache, full | Cache, pooled |
|---|---|---|---|---|---|---|
| SigLIP 2 base NaFlex | ~512 (1024 patches), 16:9 | 24x42x768 | 1.48 MB | 0.37 MB | 45.9 GB | 11.5 GB |
| SigLIP 2 base NaFlex | ~1024 (4096 patches), 16:9 | 48x85x768 | 5.98 MB | 1.48 MB | 185.9 GB | 45.9 GB |
| DINOv2 base | 518, single | 37x37x768 | 2.01 MB | 0.47 MB | 62.4 GB | 14.8 GB |
| DINOv2 base | 1036, 4 tiles of 518 (computed) | 74x74x768 | 8.4 MB | 2.1 MB | 249.5 GB | 62.4 GB |

Pooling an odd grid (37) drops its last row and column.

Throttled timings, screen locked, GPU about a quarter of its normal matmul
rate on a sanity check (about 1 TFLOPS fp16). Do not use:
SigLIP 2 base 512 single 129.5 ms (std 19.9); 4 tiles 964 ms on 6 frames and
stalled on 50; DINOv2 518 single 292 ms (std 59); NaFlex on 4 frames 133 ms at
a 1024-patch budget and 2,276 ms at 4096 (attention cost grows with the square
of the token count, so untiled 1024 is about 17 times the 512 cost). The
earlier thermal run of SigLIP 2 base 512 (134 ms, tiled 947 ms with std 448)
was also throttled. Thermal frames are 640x512 and cost the same as RGB at a
given input size; their time was not measured cleanly.

## Findings that hold without further timing

- Cache size is set by the grid, not the model. The 512 px full-detail cache
  is 46 GB for either SigLIP 2 base or DINOv2 (62 GB), already over the 30 GB
  budget. 1024 px by tiling is 186 GB full and 47 GB pooled: over budget, and
  over the 110 GB of free disk when full.
- 2x2 pooling is what brings a cache under 30 GB: 11.7 GB at 512 px. It halves
  the grid to 16x16 patches of 32 px at 512 px input; a person at WiSARD
  heights can be smaller than that, which the detection head's results will
  have to show.
- 29,668 images at 92 ms is 46 minutes, over the 30 minute budget. 30 minutes
  needs 60.7 ms per image. No measured setting meets it. Cutting the time
  needs a measured option (batching, a smaller input for the 640x512 thermal
  frames, or caching a subset), not an assumption.
- SigLIP 2 has no "small" size. The family is base, large, so400m and giant;
  the large 512 checkpoint was not downloaded (the transfer stalled).
- `google/siglip2-base-patch16-512` is a `siglip` architecture checkpoint and
  loads with `SiglipVisionModel`; the NaFlex checkpoint is `siglip2` and loads
  with `Siglip2VisionModel`.
- EVA-02 (`timm/eva02_base_patch14_448...`) is not gated, but loads only
  through `timm`, a second dependency. Not measured.

## Recommendation (provisional, pending the rerun)

First cache: SigLIP 2 base 512, one 512 px pass per frame, 2x2 pooled, fp16.
Projected 11.7 GB. Time is projected at 46 minutes from the clean 92 ms
measurement, which is over the 30 minute target; build it in two sessions
(RGB, then thermal) or accept 46 minutes. Do not tile to 1024 for the first
cache: 147 minutes and 47 GB pooled. NaFlex at 512 is no cheaper. DINOv2 is
not yet timed and its grid is larger (62 GB full, 14.8 GB pooled).

## Dependency and weights

`transformers` (chore commit, with `uv.lock`): SigLIP 2 including NaFlex and
DINOv2 load through it, and it is the one library that covers both. `timm`
would add a second dependency and cannot load the NaFlex checkpoint. SHA-256 of
the weight files, computed by the tool:

| Repo | File | SHA-256 |
|---|---|---|
| google/siglip2-base-patch16-512 | model.safetensors | fe0e601c625e69eed8e73500d39e9b6164403fe03db8048e87913c3cefbbb3fe |
| google/siglip2-base-patch16-naflex | model.safetensors | ac5f28bbdf92c0c1696ccbd3ce716426049cd67ad8045b66d0d938b0f9c8bbec |
| facebook/dinov2-base | model.safetensors | d73036b56966966d07975d696bde331762f37297e2f095de8cea0040c3aa0841 |

Downloads stalled on the xet transport behind the VPN; `HF_HUB_DISABLE_XET=1`
fixed it for DINOv2. Run with `HF_HUB_OFFLINE=1` once weights are cached.

## Commands

```bash
HF_HUB_OFFLINE=1 uv run python tools/forward_pass_cost.py siglip2-base-512 --camera rgb
```

Defaults: `-n 50 --seed 0 --warmup 3 --total 29668`. Other models:
`siglip2-base-naflex`, `dinov2-base`, `siglip2-large-512`; `--camera thermal`
for thermal frames. Each prints JSON lines.

## To finish

With the screen unlocked and nothing else running: run the tool for every
model and both cameras; time DINOv2 and NaFlex cleanly; time the large model
if wanted; try batches of 8 at 512 px; measure thermal at its native
640x512. Peak memory is the highest MPS driver allocation seen after a pass,
not a true peak.

## Measurements completed 2026-10-02

Run by the lead with the laptop awake and unlocked, **on battery power**, 50
frames per setting, seed 0, fp16 on MPS, patch tokens only, 2×2 average
pooling for the pooled figures. Projections are for 29,668 images. The one
earlier mains-powered figure (SigLIP 2 base 512, RGB, 92 ms) is about 25%
faster than its battery equivalent below, so take the times here as upper
bounds on mains power.

| Model | Input | Camera | Grid | ms/image | Features fp16 | Pooled | Cache pooled | Time |
|---|---|---|---|---|---|---|---|---|
| SigLIP 2 base/16 | 512, single | thermal | 32×32 | 124 | 1.5 MB | 0.38 MB | 11.7 GB | 61 min |
| SigLIP 2 base/16 | 1024, 4 tiles | thermal | 64×64 | 434 | 6.0 MB | 1.5 MB | 46.7 GB | 215 min |
| SigLIP 2 NaFlex | 1,024 tokens (about 512) | RGB | 24×42 | 122 | 1.48 MB | 0.37 MB | 11.5 GB | 60 min |
| SigLIP 2 NaFlex | 4,096 tokens (about 1024) | RGB | 48×85 | 717 | 5.98 MB | 1.48 MB | 45.9 GB | 355 min |
| SigLIP 2 NaFlex | 1,024 tokens | thermal | 28×35 | 126 | 1.44 MB | 0.35 MB | 10.8 GB | 62 min |
| SigLIP 2 NaFlex | 4,096 tokens | thermal | 57×71 | 778 | 5.93 MB | 1.44 MB | 44.7 GB | 385 min |
| DINOv2 base/14 | 518, single | RGB | 37×37 | 147 | 2.01 MB | 0.47 MB | 14.8 GB | 73 min |
| DINOv2 base/14 | 1036, 4 tiles | RGB | 74×74 | 596 | 8.02 MB | 2.01 MB | 62.4 GB | 295 min |
| DINOv2 base/14 | 518, single | thermal | 37×37 | 148 | 2.01 MB | 0.47 MB | 14.8 GB | 73 min |
| DINOv2 base/14 | 1036, 4 tiles | thermal | 74×74 | 600 | 8.02 MB | 2.01 MB | 62.4 GB | 297 min |

Peak MPS allocation was 0.23 to 0.24 GB for single passes and 1.24 to 1.29 GB
for tiled ones. No operation fell back to the CPU. Weight checksums are in the
section above.

## Recommendation

**First cache: SigLIP 2 NaFlex at a 1,024-token budget, pooled 2×2, fp16.**
About 11.5 GB for RGB and thermal together, and 60 minutes on battery or
about 45 on mains, built as one session per camera to respect the 30-minute
rule.

Why NaFlex over the fixed 512 model at the same cost: it keeps the frame's
aspect ratio. A 16:9 RGB frame becomes a 24×42 grid instead of being squashed
into 32×32, so a person is not narrowed by a factor of 1.8 before the model
sees it. The fixed-512 model is the fallback if the head's results show the
variable grid causes trouble.

Why not 1024 pixels: four to six hours and 45 GB pooled, and 185 GB at full
detail. Out of reach on the laptop. If the head's results show that 16-pixel
patches pooled 2×2 lose the smallest people, the next step is a cloud run at
higher resolution, which is a spending request.

Why not DINOv2 first: 20% slower, 30% larger features, and the owner's
preference for a non-Meta model. It stays as the comparison in the backbone
study.

**Open:** whether 32-pixel pooled cells carry enough to find a 10-pixel
person. That is the first question for the detection head (#66), and the
reason the cache keeps the unpooled option available at 46 GB if the disk
allows it later.

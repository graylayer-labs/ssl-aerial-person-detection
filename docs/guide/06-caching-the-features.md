# 6. Caching the features

*Last updated 2026-10-04 from issues [#64], [#65], [#78].*

## What we set out to do

Start the "Off-the-shelf bar" epic ([#14]) by measuring what the frozen model
costs, then run it once over every frame and keep the output. Every later
experiment would read features from disk instead of running the model again.

## What we found

**One forward pass is cheap, and one measurement was spoiled.** SigLIP 2 at
about 512 px took 92 ms per image on mains power and 126 ms on battery. A
1,024-pixel input would take four to six hours and 45 GB pooled, so it was
dropped ([forward-pass note][cost]). The first timings were taken while the
laptop's screen was locked. A locked screen throttles the GPU, and those
numbers could not be used ([#64 handoff][i64-handoff], [forward-pass note][cost]).
The lead also lost two runs to shell mistakes: macOS has no `timeout`, and zsh
does not split an unquoted variable ([#64 handoff][i64-handoff]).

**Decoding was a large part of the cost.** The model took about 121 ms per
image. Decoding a 3840x2160 RGB frame took another 57 ms and patchifying 23 ms,
so both now run ahead in threads. Scratch runs gave 6.0 to 7.4 images a second
([forward-pass note][cost]). The cache came to 29,676
files and 11 GB, built from `main`, with every session `completed` and not
scratch ([#65 handoff][i65-handoff]).

**The review found a geometry bug before the build.** Pooling the patch grid
2x2 floored odd sizes, so the last thermal patch column, 18 px wide, was
dropped from every frame. The index also did not record enough to map a cell
back to pixels ([#65 handoff][i65-handoff]). Fix: ceil pooling over real
patches only, and the geometry recorded per entry, with `cell_boxes` as the one
mapping ([#65 handoff][i65-handoff]). The review came before the build, so the
flaw never reached a result. It would have shown only as slightly worse
thermal numbers.

**The first resume check was too loose.** It allowed 2% of the largest value,
about the size of a typical feature value, so it could not have caught a
change in preprocessing. It is now 1e-3 relative RMS ([#65 handoff][i65-handoff]).

**The head refused the finished cache, which was right.** The cache took its
frames from the list of RGB-thermal pairs. The per-camera splits also hold
labelled frames with no partner: 5 RGB and 3 thermal. The head refuses an
incomplete cache, so every fold was refused ([#78 handoff][i78-handoff]).
Leaving those 8 frames out silently would have changed the test sets a little,
and nobody would have known.

## Decisions and why

- **SigLIP 2 NaFlex, 1,024-token budget, pooled 2x2, fp16.** It fits the
  laptop ([forward-pass note][cost]).
- **One file per image.** A crash loses one image, and a fold reads only its
  own files ([decisions][decisions], #65).
- **The cache records its identity:** model, weight checksum, hub revision,
  token budget, pooling, dtype. A run with any of them different is refused
  ([decisions][decisions]).
- **The cache is the one place outside a run directory that an experiment
  writes.** Each file stays traceable to a commit through its index line
  (`CLAUDE.md`).
- **Select paired frames first, then any frame a fold manifest references.**
  `check-cache` lists what is missing and exits 1 ([#78 handoff][i78-handoff]).

## How to reproduce it

Needs the data (chapter 1). Run on mains power, the screen unlocked, under
`caffeinate -dims`.

```bash
uv run aerial-search cache-features siglip2-base-naflex --camera rgb --part 1/2   # then 2/2, then thermal
uv run aerial-search check-cache outputs/features/siglip2-base-naflex-1024tok data/manifests/wisard-full
```

Each half of a camera took about 12.5 minutes on mains ([#65 handoff][i65-handoff]).
The cache is not in S3. It can be rebuilt in about 50 minutes ([#65 handoff][i65-handoff]).
I ran `check-cache --help` on 2026-10-04 and it matches. I did not rebuild the
cache, because it takes about 50 minutes and the cache already exists.

## What we would do differently

- Check the laptop is awake and unlocked before any timing. A pre-flight check
  is filed as a tooling candidate ([#64 handoff][i64-handoff]).
- Check that a cache covers every frame the manifests name when it is built,
  not when the first consumer refuses it ([#78 handoff][i78-handoff]).

[#14]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/14
[#64]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/64
[#65]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/65
[#78]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/78
[i64-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/64#issuecomment-5949550909
[i65-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/65#issuecomment-5952765939
[i78-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/78#issuecomment-5952765459
[cost]: ../forward-pass-cost.md
[decisions]: ../decisions.md

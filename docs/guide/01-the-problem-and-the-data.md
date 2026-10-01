# 1. The problem and the data

*Last updated 2026-10-01 from issues [#1], [#2], [#6], [#7] and [#10].*

## What we set out to do

Build a person detector for search and rescue from drone footage, when
labelled footage is scarce. The reasoning is in [INTENT.md](../../INTENT.md).
The plan: start from a pretrained vision model, adapt it on unlabelled paired
RGB and thermal footage, then train a detector on a small share of the labels.
The first milestone, "Trusted ground", comes before any of that. It makes the
data, the splits and the scorer trustworthy, so that a later number means
something. Nothing has been trained yet, and this guide reports no model
result.

## What we found

**The dataset.** We use [WiSARD](https://sites.google.com/uw.edu/wisard/),
described in Broyles et al., IROS 2022 (arXiv 2309.04453). Its footage comes
from a DJI Mavic 2 Enterprise Advanced carrying an RGB and a thermal camera
([pairing review][pairing-review]). The usable part is 17 RGB-and-thermal clip
pairs from five flight days. The five site-days, with their clips, are MtErie
3, Carnation 2, Hannegan 2, FHL 9 and Baker 1 ([folds review][folds-review]).
RGB images are 3840x2160 at MtErie and 1920x1080 elsewhere. Thermal images
are 640x512 ([folds review][folds-review]).

**Labels are patchy.** Of the five site-days, four have labels. Hannegan has
none. Within a site-day, a clip is usually labelled in one camera, in both, or
in neither ([pairing review][pairing-review]). Chapter 2 has the counts.

**The dataset on disk.** The raw files are 80 directories holding 100,794
files, 43,571,345,864 bytes in total ([#7 investigation][i7-investigation]).
`CLAUDE.md` calls this 41 GB. Of the 80 directories, 34 hold the 17 clip pairs
(15.6 GB) and 46 hold single-camera footage (27.9 GB), which may be wanted
later as unlabelled data ([#7 investigation][i7-investigation]).

**We started in a bad place.** The first attempt, in August, left 600 lines of
plans and no results ([decisions](../decisions.md)). The repository then sat
idle from 26 August to 29 September 2026. When it restarted, `uv run pytest`
failed two tests and `uv run ruff check .` reported 41 errors ([#1]). The two
failing tests turned out to expose a real bug in how the cameras are paired
([epic #13][epic]). Chapter 2 tells that story. Issue #1 ended with 9 tests passing and 2
expected failures that keep the bug visible ([#1 handoff][i1-handoff]).

**The README lied by accident.** It quoted 16,459 pairs, 7,359 of them
labelled. A second manifest set on disk said 8,759 and 4,021. Nobody knew
which was right ([#2]). The planning documents from the first attempt were
deleted, the README was rewritten to quote no dataset figure, and the notebook
that still quoted the old ones was left for the milestone write-up
([#6 handoff][i6-handoff]).

**The disk held the dataset three times.** `data/raw/` was 122 GB ([#7]). It
held the working copy (41 GB), an identical second copy (about 40 GB) and the
downloaded zip (41 GB) ([#7 finding][i7-finding]). The copies were confirmed
identical, and S3 was confirmed to hold all 100,794 files with no size
mismatch ([#7 investigation][i7-investigation]). The owner approved five
actions on 2026-09-29 ([#7 approval][i7-approval]). Free disk space then went
from 31 GB to 114 GB ([#7 actions][i7-actions]).

## Decisions and why

- **One local copy plus S3, fetched when needed, not a mounted S3 drive.** The
  macOS mount tools either need system security lowered or are unproven, and
  raw images are read once per model ([decisions](../decisions.md), [#7]).
- **An AWS role that can write but never delete, with versioning on.** An
  overwrite can be undone and a delete cannot happen ([#7 actions][i7-actions]).
- **A project board, not planning documents.** One place holds status, and it
  survives the end of an agent session ([decisions](../decisions.md)).
- **Agents work from issues, and every issue ends with a handoff comment.** The
  setup is `INTENT.md`, `CLAUDE.md`, session skills, agents tiered by model
  cost, CI, and an auto-merging `main` ([#10 handoff][i10-handoff]).
- **No dataset number is quoted until it is verified** ([#6 handoff][i6-handoff]).

## How to reproduce

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/graylayer-labs/ssl-aerial-person-detection
cd ssl-aerial-person-detection
uv sync --dev
uv run pytest
uv run ruff check .
```

To get the data, the repository has a fetch command. It downloads the full
dataset and unpacks it to `data/raw/wisard-full/`:

```bash
uv run aerial-search fetch wisard-full
```

This was not run while writing this chapter, because the archive is 41 GB ([#7 finding][i7-finding]).
The check that you have the same data we do is the count in the dataset
section above: 80 directories and 100,794 files under `data/raw/wisard-full/`.
On the project's own copy both counts were checked on 2026-10-01 with
`ls data/raw/wisard-full | wc -l` and `find -L data/raw/wisard-full -type f | wc -l`.

`data/` is git-ignored, so a fresh clone has none.

## What we would do differently

- Check numbers before building on them. The README and the notebook quoted
  dataset figures that came from a pairing bug ([#2]).
- Delete duplicates early. Three copies of a 41 GB dataset hid in `data/raw/`
  until the disk audit ([#7 finding][i7-finding]).
- Check the S3 archive when it is first made. The project notes had said it
  held the zip. It did not ([#7 investigation][i7-investigation]).

## Next

[Chapter 2](02-pairing-the-two-cameras.md): how a frame from the RGB camera is
matched to a frame from the thermal camera, and how we found that it was not.

[#1]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/1
[#2]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2
[#6]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/6
[#7]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7
[#10]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/10
[epic]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/13
[i1-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/1#issuecomment-5891090582
[i6-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/6#issuecomment-5891182210
[i10-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/10#issuecomment-5891129310
[i7-finding]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7#issuecomment-5892814551
[i7-investigation]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7#issuecomment-5893218520
[i7-approval]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7#issuecomment-5893299462
[i7-actions]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7#issuecomment-5893642919
[pairing-review]: ../wisard-pairing-review.md
[folds-review]: ../site-folds-review.md

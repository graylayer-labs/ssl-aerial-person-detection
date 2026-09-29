# Decisions

One line each, newest first. Format: `YYYY-MM-DD · chose X over Y · reason`.

- 2026-09-29 · chose Archify for finished figures, installed by a pinned-commit script and git-ignored, over committing its 7.3 MB of code or using Mermaid alone · Mermaid stays for drafts; the script checks the commit, so a moved tag cannot change what runs, and settings block its network and preview features. Approved by the owner; see #30.
- 2026-09-29 · chose a public project board over a private one · the repo and its issues are already public, so the board exposes nothing new, and it shows visitors how the project is run. Approved by the owner; see #22.
- 2026-09-29 · chose to fold `docs/PROBLEM.md` into the README over keeping it · the problem statement then has one home. See #6.
- 2026-09-29 · chose to rely on GitHub signing each squash merge over the "require signed commits" rule · the rule was tried and blocked every PR, because it also demands signatures on the branch commits, which needs a local signing key that agents would hold. Commits on `main` are verified either way.
- 2026-09-29 · chose a separate `process-auditor` over widening `repo-janitor` · one checks how work was done and may fix records; the other checks the repo's contents and changes nothing.
- 2026-09-29 · chose to quote results only from runs on a clean commit on `main` over allowing branch runs · the owner's rule against "works on my machine"; enforced by the module in #23.
- 2026-09-29 · chose the main session as a lead that delegates in the background over doing the work itself · keeps its context for judgement; agents return short reports and the detail goes on the issue.
- 2026-09-29 · chose to treat `data/manifests/` as regenerable and `data/raw/` as protected over one rule for all of `data/` · manifests come from committed code; raw data is 122 GB and slow to restore.
- 2026-09-29 · chose a cold-start test (a fresh agent, read-only, reporting what confused it) over trusting the docs by reading them · the author of the docs cannot see what they left out.
- 2026-09-29 · chose to pin the frame-number parsing bug as a strict expected failure over fixing it in the lint PR · changing pairing needs the verification in #2; the pinned test keeps the bug visible while CI is green.
- 2026-09-29 · chose CI-gated auto-merge with no required human review over review-gated merges · the owner does not review every PR; agent review covers logic changes and CI covers the rest.
- 2026-09-29 · chose parent issues labelled `epic` as the roadmap over a roadmap document or board date fields · one place to look, no extra upkeep.
- 2026-09-29 · chose our own skills and agents over installing the Superpowers or Matt Pocock skill bundles · both overlap with the board-based setup; Superpowers injects instructions into every session and writes plan files into the repo. Ideas were borrowed, nothing installed.
- 2026-09-29 · chose a strict CI (`ci.yml`) over the org template on branch `chore/org-standards-sync` · the template swallows test and type-check failures and requires labels this repo does not use.
- 2026-09-29 · chose to delete the old planning docs over archiving them · git history keeps them, and an archive folder would mislead future agents.
- 2026-09-29 · chose a pretrained foundation model as the starting point over training ResNet18 from scratch · current practice, and frozen features can be cached so laptop runs stay short. Specific model to be chosen in issue #5.
- 2026-09-29 · chose a GitHub project board over in-repo roadmap docs · the first attempt stalled with 600 lines of plans and no results; the board holds status in one place that survives agent sessions.
- 2026-09-29 · chose `INTENT.md` plus `CLAUDE.md` over a single file · intent changes rarely and working rules change often.

#!/usr/bin/env bash
# One-time install of the Archify diagram skill at a pinned, verified commit.
#
# Usage:
#     tools/install_archify.sh            # install; do nothing if present
#     tools/install_archify.sh --force    # replace an existing install
#
# The skill is third-party code and is not committed. It goes into
# .claude/skills/archify/ of the main checkout, which is git-ignored. Agent
# worktrees reach it through a symlink set in .claude/settings.json.
# Nothing from the clone is executed and npm is never run.
set -euo pipefail

REPO_URL="https://github.com/tt-a1i/archify"
TAG="v3.0.1"
COMMIT="2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c"
# Runtime files only, as reviewed in issue #30. It sits at the clone root and
# holds a single top-level folder, archify/.
ZIP_PATH="archify.zip"

FORCE=0
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        *) echo "usage: $0 [--force]" >&2; exit 2 ;;
    esac
done

# In a worktree, --show-toplevel is the worktree. Install into the main
# checkout, the first path printed by `git worktree list`.
git rev-parse --show-toplevel > /dev/null
MAIN_ROOT="$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
[ -n "$MAIN_ROOT" ] || { echo "error: not inside a git repository" >&2; exit 1; }
TARGET="$MAIN_ROOT/.claude/skills/archify"

if [ -e "$TARGET" ] && [ "$FORCE" -eq 0 ]; then
    echo "Archify is already installed at $TARGET (use --force to replace)."
    exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Cloning $REPO_URL at $TAG ..."
git clone --quiet --depth 1 --branch "$TAG" "$REPO_URL" "$TMP/clone" 2> /dev/null
ACTUAL="$(git -C "$TMP/clone" rev-parse HEAD)"
if [ "$ACTUAL" != "$COMMIT" ]; then
    echo "error: tag $TAG points at $ACTUAL, expected $COMMIT. Refusing to install." >&2
    exit 1
fi

[ -f "$TMP/clone/$ZIP_PATH" ] || { echo "error: $ZIP_PATH missing from clone" >&2; exit 1; }
unzip -q "$TMP/clone/$ZIP_PATH" -d "$TMP/unzipped"
[ -f "$TMP/unzipped/archify/SKILL.md" ] || { echo "error: unexpected zip layout" >&2; exit 1; }

mkdir -p "$MAIN_ROOT/.claude/skills"
rm -rf "$TARGET"
mv "$TMP/unzipped/archify" "$TARGET"

COUNT="$(find "$TARGET" -type f | wc -l | tr -d ' ')"
echo "Installed Archify"
echo "  version:  $TAG"
echo "  commit:   $ACTUAL"
echo "  files:    $COUNT"
echo "  location: $TARGET"

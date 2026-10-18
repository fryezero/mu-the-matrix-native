#!/bin/sh
# Apply the GFx patch series (native/gfx/ruffle-patches, NATIVE-GFX-002) to
# the pinned Ruffle checkout that fetch-ruffle.sh made.
#
# The pristine clone $MU_GFX_DEPS/ruffle-<rev> stays untouched; the patches
# go onto a separate git worktree $MU_GFX_DEPS/ruffle-<rev>-mu (detached at
# the pinned commit, one commit per patch), and native/gfx/.deps/ruffle links
# to it.  A stamp of the patch files decides whether the worktree is current;
# when the series changes, the worktree is rebuilt from the pinned commit.
#
# Licences: Ruffle is MIT OR Apache-2.0 (its LICENSE.md); the patches are
# authored for this repository and carry the repository's licence (LICENSE).
# The patch files quote a few lines of Ruffle as diff context, under Ruffle's
# licence.  No Ruffle source is stored in the repository otherwise.
set -eu
RUFFLE_REV=061b39b0c3ecdd88214ba1750a035a678bf73559

HERE=$(cd "$(dirname "$0")" && pwd)
DEPS=${MU_GFX_DEPS:-$HOME/.cache/mu-recovery-gfx}
SHORT=$(printf %.12s "$RUFFLE_REV")
PRISTINE="$DEPS/ruffle-$SHORT"
PATCHED="$DEPS/ruffle-$SHORT-mu"
[ -d "$PRISTINE/.git" ] || { echo "apply-ruffle-patches: run native/gfx/fetch-ruffle.sh first" >&2; exit 2; }

if command -v sha256sum >/dev/null 2>&1; then
    stamp=$(cat "$HERE"/ruffle-patches/*.patch | sha256sum | cut -c1-64)
else
    stamp=$(cat "$HERE"/ruffle-patches/*.patch | shasum -a 256 | cut -c1-64)
fi

if [ -f "$PATCHED/.mu-patches.sha256" ] && [ "$(cat "$PATCHED/.mu-patches.sha256")" = "$stamp" ]; then
    :
else
    if [ -e "$PATCHED" ]; then
        git -C "$PRISTINE" worktree remove --force "$PATCHED" 2>/dev/null || rm -rf "$PATCHED"
        git -C "$PRISTINE" worktree prune
    fi
    git -C "$PRISTINE" worktree add --quiet --detach "$PATCHED" "$RUFFLE_REV"
    git -C "$PATCHED" -c user.name=mu-recovery -c user.email=mu-recovery@localhost \
        am --quiet --committer-date-is-author-date "$HERE"/ruffle-patches/*.patch
    printf '%s\n' "$stamp" > "$PATCHED/.mu-patches.sha256"
fi
mkdir -p "$HERE/.deps"
ln -sfn "$PATCHED" "$HERE/.deps/ruffle"
echo "apply-ruffle-patches: $PATCHED ($(ls "$HERE"/ruffle-patches/*.patch | wc -l | tr -d ' ') patches on $SHORT)"

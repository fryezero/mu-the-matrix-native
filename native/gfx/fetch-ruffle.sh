#!/bin/sh
# Fetch the pinned Ruffle checkout used by native/gfx (NATIVE-GFX-001), then
# apply the GFx patch series (apply-ruffle-patches.sh, NATIVE-GFX-002;
# MU_GFX_PRISTINE=1 links the unpatched checkout instead).
#
# Ruffle (https://github.com/ruffle-rs/ruffle) is dual-licensed MIT OR
# Apache-2.0; it is an external dependency and none of its source is stored
# in this repository.  The checkout lives in $MU_GFX_DEPS (default
# ~/.cache/mu-recovery-gfx) and native/gfx/.deps/ruffle links to it.
# Ruffle's build compiles its AS3 player globals with Java: when no working
# `java` is found, a Temurin JDK is downloaded into $MU_GFX_DEPS/jdk (user
# account only, nothing system-wide).
set -eu
RUFFLE_REPO=https://github.com/ruffle-rs/ruffle.git
RUFFLE_TAG=nightly-2026-10-17
RUFFLE_REV=061b39b0c3ecdd88214ba1750a035a678bf73559

HERE=$(cd "$(dirname "$0")" && pwd)
DEPS=${MU_GFX_DEPS:-$HOME/.cache/mu-recovery-gfx}
DEST="$DEPS/ruffle-$(printf %.12s "$RUFFLE_REV")"
mkdir -p "$DEPS" "$HERE/.deps"

if [ ! -d "$DEST/.git" ]; then
    git clone --quiet --depth 1 --branch "$RUFFLE_TAG" "$RUFFLE_REPO" "$DEST"
fi
got=$(git -C "$DEST" rev-parse HEAD)
if [ "$got" != "$RUFFLE_REV" ]; then
    echo "fetch-ruffle: $DEST is at $got, expected $RUFFLE_REV" >&2
    exit 1
fi
if [ "${MU_GFX_PRISTINE:-0}" = 1 ]; then
    ln -sfn "$DEST" "$HERE/.deps/ruffle"
else
    "$HERE/apply-ruffle-patches.sh"
fi

if ! java -version >/dev/null 2>&1 && [ ! -x "$DEPS/jdk/Contents/Home/bin/java" ] && [ ! -x "$DEPS/jdk/bin/java" ]; then
    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) jos=mac; jarch=aarch64 ;;
        Darwin-x86_64) jos=mac; jarch=x64 ;;
        Linux-aarch64) jos=linux; jarch=aarch64 ;;
        *) jos=linux; jarch=x64 ;;
    esac
    tmp="$DEPS/jdk-download"
    rm -rf "$tmp" && mkdir -p "$tmp"
    curl -fsSL -o "$tmp/jdk.tar.gz" "https://api.adoptium.net/v3/binary/latest/21/ga/$jos/$jarch/jdk/hotspot/normal/eclipse"
    tar xzf "$tmp/jdk.tar.gz" -C "$tmp"
    rm -rf "$DEPS/jdk" && mv "$tmp"/jdk-* "$DEPS/jdk" && rm -rf "$tmp"
fi
echo "fetch-ruffle: $DEST ($RUFFLE_TAG, $RUFFLE_REV)"

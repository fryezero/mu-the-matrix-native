#!/bin/sh
# Build native/gfx/mugfx (Rust, links the pinned Ruffle) and the SDL2/OpenGL
# prototype window build/mu-gfx-window.  Needs a Rust toolchain (rustup, user
# account) and SDL2; run fetch-ruffle.sh first.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DEPS=${MU_GFX_DEPS:-$HOME/.cache/mu-recovery-gfx}
[ -e "$HERE/.deps/ruffle/Cargo.toml" ] || { echo "build-mugfx: run native/gfx/fetch-ruffle.sh first" >&2; exit 2; }
if ! java -version >/dev/null 2>&1; then
    for home in "$DEPS/jdk/Contents/Home" "$DEPS/jdk"; do
        if [ -x "$home/bin/java" ]; then JAVA_HOME=$home; PATH="$home/bin:$PATH"; export JAVA_HOME PATH; break; fi
    done
fi
cargo build --release --manifest-path "$HERE/mugfx/Cargo.toml"
make -C "$HERE" window

# HelpWindow isolated viewer

WIP SYS-MISC-001b test tool. It opens the converted HelpWindow movie and feeds
the user's installed helpdata.bmd through the production reader/controller.
It has no network or game/session operations. This is an isolated view check;
it is not the native client's HelpWindow binding or full-window integration.

Build in this lane's scratch directory to keep the worktree small:

```sh
make -C native/help BUILD="<lane-scratch>/build"
"<lane-scratch>/build/mu-help-view" \
  --lib "<native-scratch>/polish/libmugfx.dylib" \
  --movie "<native-scratch>/gfx/all-bridge/HelpWindow.swf" \
  --data "<installed-root>/Data/Local/helpdata.bmd" \
  --out "<lane-renders>/help.png"
```

Add `--window --frames 120` for a finite native SDL window check, `--chat` for
the chat tab, or `--mode 1` for the alternate-input filter. Esc closes the test
viewer. Pointer events reach the actual movie. The tool requires SDL2 through
pkg-config and the existing ABI-3 mugfx library; it does not build Rust.

The JSON summary checks actual movie provider counts against sent row counts.
Inspect the PNG as well. Count agreement alone does not prove visible content.
Only explicit `--out` writes an image; all files are local and must not be
committed. Delete the lane's build and render directories before handoff.

The five English headings are native test labels. Row conversion uses the
existing native Latin-1 helper, the same policy as quest windows. Neither
fallback headings nor Latin-1 behavior is original code-page validation.
The render loop reuses one pixel buffer and one texture; row/provider
allocation and setup happen before it.

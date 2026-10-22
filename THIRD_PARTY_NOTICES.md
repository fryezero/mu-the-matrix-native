# Third-party references

The repository contains independently authored recovery code and does not vendor REA, game binaries, game assets, decompiler output, or upstream implementation trees.

| Reference | Pinned identity or source | Use and license boundary |
|---|---|---|
| REA | `morluto/rea`, commit `93c620c3e7c401be40b71c480518147c76ade4dc`; npm `rea-agents` 6.5.0 | External analysis dependency, MIT with its own dependency notices |
| Ghidra | 12.1.4 | External native analysis tool, Apache-2.0 with its own notices |
| xulek/muonline-bmd-viewer | `3f11bf89f3702261174d8efa1436d56a15c7d97a` | Published format/algorithm reference; upstream package declares ISC; see `model-recovery/SOURCES.md` |
| VDraven/MuClientTools16 | `90c78cf5876ec43be69f26e2956d3ffbdc26c5ad` | Format reference and separately compiled local oracle for synthetic v14 vectors, MIT, copyright 2021 VD; no upstream implementation vendored |
| snemes/aplib | `38f856ea7f0cdc31258d88165858051f71c03d84` | Independent local decoder oracle; its code is not distributed here |
| Crypto++ LEA test vectors | `https://github.com/weidai11/cryptopp/blob/master/TestVectors/lea.txt` | Public mathematical reference vectors; the source-file digest and vector selection are in `model-recovery/fixtures/lea256-vectors.json` |
| Pillow | 11.3.0 in the reference environment | Installed image dependency with its own license; source is not vendored |
| Unicorn / Capstone | 2.1.4 / 5.0.9 in the reference environment | Optional installed emulation/disassembly dependencies with their own licenses |

The fixed byte constants used for model formats are published format constants, not user authentication credentials. No license in this repository grants rights to the separately supplied MU game code or assets. Keep future imported source and its notices explicit rather than treating every decompiled or downloaded file as this project's MIT code.

The v14 wrapper links externally installed Crypto++. Crypto++ individual source files are public domain and its compilation uses Boost Software License 1.0. Preserve its applicable upstream notices if distributing the library. No Crypto++ source or binary is vendored here. The source-pinned [license and oracle details](docs/research/bmd-v14.md#license-requirements) include the separate notice for specific 32-bit ARM assembly files. The oracle-generated synthetic vectors acknowledge VD, Copyright (c) 2021 VD, under the upstream MIT license.

## Wine track

The Mac app, the Wine runtime packaging, the mugl OpenGL proxy, the CPU hotpatches, the mscoree proxy, the fast
x87 integration and their diagnostics moved to [mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac)
on 2026-10-21, together with their notices. The read-only `live-readers/` tools that stayed here are authored code
under this repository's MIT license and link only system frameworks.

## Native model viewer

`native/` (NATIVE-VIEW-001) is authored code published under this repository's MIT license. It links,
but does not vendor, these separately installed libraries:

| Library | Use | License boundary |
|---|---|---|
| SDL2 (Homebrew `sdl2`, which is sdl2-compat over SDL3; Debian/Ubuntu `libsdl2-dev`) | Window, GL context and input for `build/mu-viewer` only | zlib license. No SDL source or binary is included here. |
| libjpeg-turbo (Homebrew `jpeg-turbo`; Debian/Ubuntu `libjpeg-dev`), optional | JPEG texture decoding in the core and both executables | IJG License, Modified (3-clause) BSD License and zlib License, per its `LICENSE.md`. No libjpeg source or binary is included here. Anyone distributing a binary that links it must carry its notices, including the acknowledgement "This software is based in part on the work of the Independent JPEG Group". |
| Crypto++ | BMD v14 decoding through `model-recovery/modulus.cpp`, as above | See the Crypto++ paragraph above. |

The viewer also links the system OpenGL (Apple OpenGL framework, or `libGL` on Linux). The repository
does not ship viewer binaries. Renders and decoded textures of installed game assets stay local and
are covered by the game-data boundary above.

## GFx prototype (NATIVE-GFX-001)

`native/gfx/mugfx` links Ruffle (https://github.com/ruffle-rs/ruffle, MIT OR Apache-2.0) and its crates. They
come from a pinned checkout that `native/gfx/fetch-ruffle.sh` clones outside the repository. No Ruffle source
or binary is included here. The dependency graph (`native/gfx/mugfx/Cargo.lock`, 317 crates) is under
MIT/Apache-2.0/Zlib/ISC/BSD/Unicode-3.0/Unlicense terms. Ruffle's `default_font` embeds a Noto Sans subset
(OFL-1.1). Anyone distributing a built `libmugfx` must carry these notices. The fetch script may download a
Temurin JDK (GPL-2.0 with Classpath Exception). The JDK is used only to build Ruffle and is not linked. Movies
converted from the installed client and their renders are game data and stay local.

NATIVE-GFX-002 adds `native/gfx/ruffle-patches`, five patches (seven since NATIVE-GFX-003) applied to that checkout on a separate worktree by
`native/gfx/apply-ruffle-patches.sh`. The patches are authored for this repository and carry its licence; their
diff context lines quote Ruffle source under Ruffle's MIT OR Apache-2.0 licence. On macOS `mugfx` also uses the
`objc2-metal`, `objc2-io-surface` and `objc2-core-foundation` crates (MIT/Apache-2.0/Zlib). The device-font map
points at fonts installed with macOS; no font file is included. NATIVE-GFX-003 adds a direct dependency on
`async-channel` (Apache-2.0 OR MIT), which is already in Ruffle's graph.


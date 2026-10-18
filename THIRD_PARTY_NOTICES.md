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

## Optional fast x87 runtime

`mac-play/install-fast-x87.sh` fetches and builds external
[aprilmaccydee/rosetta-timewalker](https://github.com/aprilmaccydee/rosetta-timewalker)
at `ab1a6a032e488c0d6eade54ce70a02d653277810` in the user's cache. No upstream
source or binary is vendored here. Its top-level license is MIT, copyright
2026 aprilmaccydee. Its bundled modified
[Lifeisawful/rosettax87_jit](https://github.com/Lifeisawful/rosettax87_jit)
snapshot derives from `a44f1eff28591a90f4a8c7297134294811da06b5`, MIT,
copyright 2025 Lifeisawful. The embedded openlibm/fdlibm/FreeBSD msun routines
retain their per-file notices, including the David Schultz two-clause BSD
notice reproduced in upstream `THIRD_PARTY_NOTICES.md`. Keep the fetched
`LICENSE`, `THIRD_PARTY_NOTICES.md`, and embedded source notices with any
redistribution. CrossOver and Apple Rosetta remain separately supplied software.

The `fpbench.c` and `glbench.c` diagnostics were authored for this investigation
and copied from the local mu-mac-tools project, with GL error checks added here.
They contain no game code or assets.

## Immediate-mode batching and profiling

`mac-play/mugl/`, `diagnostics/eipprof.c`, `diagnostics/glcheck.c` and
`diagnostics/pe_nearest_export.py` are authored for this investigation and covered
by the repository MIT license. `mugl/exports.txt` is an API-name manifest extracted
from the separately installed CrossOver 26.3 i386 OpenGL DLL. No Wine/CrossOver
implementation or binary is included. The generated proxy loads the user's
installed Wine builtin OpenGL implementation at runtime.

## Claude v7.0 performance tools

`mac-play/hotpatch`, `mac-play/mumodes`, `mac-play/machprof` and
`mac-play/automation` publish authored code from the owner's local mu-mac-tools
work under this repository's MIT license. Source identities and packaging
adaptations are recorded with the performance finding. The mscoree declarations,
DEF and jump stubs contain forwarding API names/ordinals only. No Microsoft, Wine,
CrossOver or game implementation is included. Original game instruction bytes,
including the xform entry prologue, are generated only into ignored local build
directories from owner-supplied private inputs. Generated DLLs containing original
bytes are outside the publication boundary and must not be redistributed here.

## Claude v7.1 mesh-draw tools

`mac-play/hotpatch/meshdraw.c`, the v7.1 `mugl.c` and `mac-play/diagnostics/glstride.c`
are authored code from the owner's local mu-mac-tools work, published under this
repository's MIT license with the same boundary as the v7.0 tools. The three
original patch-site byte sequences used by `meshdraw.c` are generated only into the
ignored build directory from owner-supplied private input; `targets.json` records
their addresses, lengths and SHA-256 only. No Microsoft, Wine, CrossOver or game
implementation is included.

## Claude v7.2 precise waits

The v7.2 `mac-play/hotpatch/mugl.c` is authored code from the owner's local mu-mac-tools
work, published under this repository's MIT license with the same boundary as v7.0
and v7.1. It adds no original game bytes and no Microsoft, Wine, CrossOver or game
implementation; it calls the documented Win32 waitable-timer API.

## Mac setup kit

`mac-play/installer/` is authored shell code from the owner's local mu-mac-tools work, published
under this repository's MIT license. It contains no Microsoft, CrossOver, Wine, winetricks or game
code or binaries. It invokes CrossOver, winetricks (which downloads Microsoft's .NET Framework
installer under Microsoft's terms) and MinGW-w64 from the user's machine, and records SHA-256 values
of Microsoft's installer, a CrossOver builtin and user-supplied proxy DLLs only. Prebuilt mugl DLLs
contain client-derived bytes and are not part of the repository.


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

NATIVE-GFX-002 adds `native/gfx/ruffle-patches`, five patches applied to that checkout on a separate worktree by
`native/gfx/apply-ruffle-patches.sh`. The patches are authored for this repository and carry its licence; their
diff context lines quote Ruffle source under Ruffle's MIT OR Apache-2.0 licence. On macOS `mugfx` also uses the
`objc2-metal`, `objc2-io-surface` and `objc2-core-foundation` crates (MIT/Apache-2.0/Zlib). The device-font map
points at fonts installed with macOS; no font file is included.


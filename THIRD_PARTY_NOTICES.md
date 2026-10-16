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

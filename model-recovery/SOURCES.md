# Sources and provenance

The Python code in this directory is independently implemented. Factual binary layouts and rotation convention were cross-checked with these primary publications; no third-party source implementation was copied into the directory.

1. xulek, muonline-bmd-viewer, commit `3f11bf89f3702261174d8efa1436d56a15c7d97a`:
   - https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/bmd-loader.ts
   - https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/package.json (declares ISC, author xulek)
   - https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/crypto/file-cryptor.ts
   - https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/crypto/lea256.ts
2. VD, MuClientTools16, commit `90c78cf5876ec43be69f26e2956d3ffbdc26c5ad`:
   - https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/BMD_SMD.cpp (encrypted-version routing)
   - https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.cpp
   - https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/LICENSE (MIT; Copyright (c) 2021 VD)

Consulted on 2026-10-15. The encrypted-version sources are leads only and were not executed against or incorporated into the v10 parser. Original MU assets are separately supplied user installation data; parsing them does not assign them a new license.

## Version-14 implementation and oracle

The bounded `modulus.cpp` envelope wrapper is independently authored and links external Crypto++ cipher implementations. The unmodified pinned `MuCrypto.cpp`/`.h` were compiled separately as an ignored local oracle with fixed-width typedef compatibility definitions. The reviewed 91-vector fixture uses authored triangle data and a defined byte pattern, never game bytes. Source digests, algorithm details, exact cipher defaults, licensing and the 216-file comparison are in [the research note](../docs/research/bmd-v14.md). Crypto++ 8.9.0 is pinned in that note; package-manager versions must pass the stored vectors.

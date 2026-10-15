# Asset recovery for this Mu The Matrix installation

Observed 2026-10-15. Original installation was read only; no target executable was run and no network connection to a game service was made. These are independent static observations, not REA Evidence IDs. The implementation is a real asset-reading component; it does not implement gameplay or establish equivalence to the game.

## Implemented and verified

`asset-recovery/recover_images.py` strips only observed wrapper layouts, checks the expected format, fully decodes pixels with Pillow, and optionally exports selected images as PNG. Output must be a new directory outside the installation. Every export is reopened and its size/pixel bytes compared. Unknown/invalid data is rejected with a per-file error rather than guessed. Source and payload SHA-256 hashes are retained.

Full scan: **19,707 candidate image-wrapper files; 19,703 decoded; four rejected as images**. Eight selected image files were exported and passed pixel round-trip checks. The four exceptions are a successfully recovered text mesh and three inconsistent terrain image files described below. `asset-recovery/verified-v2/manifest.json` records every result. An initial `verified/` run predates support for TGA stored under the OZJ extension; use the v2 results.

Decoded format totals: BMP: 166, JPEG: 16,420, PNG: 84, TGA: 3,033.

## Wrapper layouts derived from bytes

- **OZJ:** 24 bytes precede a complete image. 16,426 of 16,429 files repeat the first 24 payload bytes in the prefix; the other three still have a valid JPEG payload at offset 24. Of the repeated-prefix files, eight contain TGA images rather than JPEG, and one contains version-1 mesh text. The implementation accepts JPEG magic at offset 24 or the specifically observed repeated-prefix TGA variant; it does not trust the extension alone.
- **OZT:** 3,011 of 3,025 files repeat the first four payload bytes. Fourteen custom interface files instead retain the TGA type in bytes 0–3 and have zero bytes at 4–7. Removing bytes 4–7 reconstructs the TGA header in both observed layouts. Width/height are at original offsets 16/18, depth at 20, descriptor at 21. All 3,025 fully decode.
- **OZB:** four bytes generally precede a conventional BMP. The reader requires prefix agreement and matching BMP declared length before full decoding. 166 of 169 pass.
- **OZP:** all 84 contain a four-byte prefix followed by a conventional PNG signature and image; all decode.

This establishes conversion into ordinary image data, not the original engine's color-space, filtering, blending, or sampling behavior. The recovered Navimap01 PNG was also visually inspected: it contains a coherent square navigation map with a central town and surrounding terrain.

## Exact representative evidence

All source paths below are relative to:

`<GAME_ROOT>`

| Source relative path | Bytes | Decoded result | Source SHA-256 |
|---|---:|---|---|
| `Data/Custom/Interface/BingCZ.ozt` | 1080048 | TGA, 900×300, RGBA | `57abf6c5da00c2b909acf45a662dda2e2fda413f136c097712793c8572fc932d` |
| `Data/Effect/!Chrome01.OZJ` | 9004 | JPEG, 64×64, RGB | `a9cf898433a4489f52bc851ac6375ec1f7a433752b521461229119f70a52c056` |
| `Data/Effect/Map_Smoke2.OZJ` | 65620 | TGA, 128×128, RGBA | `78611ae1bd4d1c6582b6c5fdda94aba6b24488ac63accad474f5d7900648ff6e` |
| `Data/Interface/GFx/NaviMap/Navimap01.OZP` | 26228 | PNG, 512×512, RGBA | `db873897997b80848c15d33259276724e78f3287b81aad9ae54dbe1719d9bac4` |
| `Data/Interface/RuudShop2DItem_1.OZJ` | 3555201 | JPEG, 1024×1024, RGB | `20700eab34af33cce58909162e73659a5c9c06ac2f4adca3bc7317e68c88ddf4` |
| `Data/World1/TerrainHeight.OZB` | 66620 | BMP, 256×256, L | `c4caf281b17b39bf7ceb51dcac872ce8a3a7aa306d20a91c3bb50aeaa77d1dde` |
| `Data/World3/TerrainLight.OZJ` | 18801 | JPEG, 256×256, RGB | `231370256fe259adbdaf094d69433257472430a1af1977c83ba1cf3222bd5b6f` |
| `Data/World7/leaf01.OZJ` | 666 | JPEG, 16×16, RGB | `5117ee78677255188ff08382599afa69d8dadfaf10d419edc69ef929c701c8e1` |

## Recovered editable mesh text

`Data/Object38/hs_Lifeshin01.OZJ` is 2,317 bytes, SHA-256 `0f3411e2976f59dc53ddbb8f1992c56f2030ea79d5a8d6eb1b35c72f71494335`. Removing its repeated 24-byte prefix yields 2,293 bytes of ASCII version-1 SMD-style text, SHA-256 `23346f1d6a14c7a2acfca0317f8bd349e0722bc2ae13d76c0d929e77ef59c439`.

`asset-recovery/recover_smd.py` validates the observed subset: version marker, node hierarchy, skeleton frame structure, referenced bone IDs, finite numeric coordinates, and complete triangle records. It preserves payload bytes exactly. The recovered file is `asset-recovery/verified-v2/meshes/hs_Lifeshin01.smd`, with metadata beside it. It contains one root node named `sd_LifeSunshin01`, one frame at time 0, and eight triangles. The material token is `hs_Lifeshin01.SMD`; its intended texture binding is unresolved. External modeling-tool import and the original client's handling of this wrongly named file were not tested. This is genuine editable mesh text from the installed assets, not recovered gameplay source.

The initial extension-only inventory found no standard source/build files; this later content inspection identifies one source-like mesh hidden behind an image extension. Those statements have different search boundaries.

## Three rejected terrain images

- `Data/World11/TerrainHeight.OZB`: 66,620 bytes; reconstructed BMP advertises 24-bit 256×256 pixels and a declared file size incompatible with the payload. Not repaired or interpreted as height data.
- `Data/World19/TerrainHeight.OZB`: 66,620 bytes; begins with zero bytes rather than a valid wrapped BMP signature.
- `Data/World42/TerrainHeight.OZB`: 66,620 bytes; reconstructed BMP's declared length does not match actual length. Not silently accepted.

## Initial BMD and terrain observations

The observations below preceded the model-reader implementation. [The model report](model-recovery.md) now records verified decoding of versions 10, 12 and 15; version 14 and other/table envelopes remain open.

Of 12,754 BMD-extension files: 11,583 begin `BMD` followed by version byte 15; 701 have version 10; 216 have version 14; 180 have version 12; 74 have other headers. The extension also covers tables and other data, so a single decoder cannot be assumed.

- `Data/Skill/Skeleton03.bmd`: starts `BMD`/10, followed by readable `Data2\Skill\bone_c.smd`, with numeric/binary data after its fixed-width name. No full mesh/bone parser was inferred from that alone.
- `Data/Effect/01spa_skill.bmd`: version 15, 2,312 bytes; SHA-256 `90858e15b60e538aa15f51c98fe93f114a169e515d7bec9c313afefe6002f994`. A 32-bit value at offset 4 is 2,304, matching the remaining body length. The opaque body is not decoded.
- `Data/Object7/Object63.bmd`: version 12, 141,342 bytes; offset-4 value 141,334 equals body length.
- `Data/Effect/htrackt2.bmd`: version 14, 4,972 bytes; offset-4 value 4,964 equals body length.
- `Data/World1/EncTerrain1.map`: `MAP`/1 prefix, 196,648 bytes, SHA-256 `4d30f15a251c12b00817fd97cb0d5dc045d5812150ee78c85ab7d405b230efd7`.
- `Data/World1/EncTerrain1.att`: `ATT`/1 prefix, 131,114 bytes, SHA-256 `80598ae309e307f7fed62a2b09e4d132bbae6c3e0d870f2b79e2d20e9370468a`.

A length and opaque body are observations, not proof of a particular cipher, compressor, or semantics. These formats remain unresolved.

## Editable effect descriptions

All 370 `.ein` files parse as JSON. All have keys including `Billboarding`, `Blending`, `Duration`, `Looping`, `Name`, `Position`, `Rotation`, `Scale`, `Texture`, and `Type`. Type values divide into 257 with value 0 and 113 with value 1. All 92 distinct top-level texture references resolve to existing installation paths after Windows path-separator normalization. This establishes linkable editable effect data, not enum meanings or exact simulation behavior.

Representative `Data/Effect/Lighting01-blue01.ein`: 2,134 bytes, SHA-256 `42f301d61a02d603fb8e0233eff2edb95b233e73576a6882356985dc4a740c7d`; refers to `Data\Effect\lighting_mega01.OZJ`, contains nested component objects, time/value curves, colors, counts, and duration. A reconstruction can preserve and expose these parameters now, while reproducing their actual runtime interpretation still requires code or runtime evidence.

## What this enables

The verified image decoder can be integrated into a local asset viewer or a new rendering component. Recovered height images can supply pixel values for further analysis, but height scale, terrain coordinates, tile assignments, and collision data are not yet established. JSON editing can preserve all properties and refer to verified decoded textures. The one mesh can be read as vertices/triangles without claiming it represents the whole model library.

This component does not replace native client code, protected companion libraries, server protocols, or server implementation. No playable or rebuildable equivalent game has been demonstrated.

## Validation and reproduction

Twelve unit tests passed, covering image wrapper variants, alpha-preserving TGA conversion, malformed/truncated input, BMP length disagreement, exact mesh-payload preservation, missing mesh vertices, invalid numeric data, unknown nodes, cyclic hierarchy, and missing skeleton sections. Runtime used Python 3.9 with Pillow 11.3.0.

```sh
python3 -m unittest discover -s asset-recovery -p 'test_*.py' -v
python3 asset-recovery/recover_images.py --root '/absolute/path/to/Mu The Matrix' --output '/new/output/directory' --validate-all --asset 'Data/World1/TerrainHeight.OZB'
python3 asset-recovery/recover_smd.py --root '/absolute/path/to/Mu The Matrix' --asset 'Data/Object38/hs_Lifeshin01.OZJ' --output '/new/output/hs_Lifeshin01.smd'
```

The image validation command returns nonzero when any input is rejected, while preserving a complete manifest of successes and failures. The SMD parser intentionally supports only the observed unweighted version-1 text subset, not every possible SMD dialect. No asset or game redistribution rights were established by decoding local files.

Additional source SHA-256 values:

- `Data/Skill/Skeleton03.bmd`: `7352d353dcb378e51c093de4d791372c095789ae04e573b4e5907084597c7b79`.
- `Data/Object7/Object63.bmd`: `97a6c78fb93daf09f8a068464a93b395ac3dd7237bf7c29010ed140d89bff756`.
- `Data/Effect/htrackt2.bmd`: `fefa39f950dd5b40ce42bcd765d3a4c0e090d44dd7dce051827054afa3a2b74b`.
- `Data/World11/TerrainHeight.OZB`: `5470ece3785118dd314d32229dc0f4c33399269a69a2bc2f4d7bddd5d609422a`.
- `Data/World19/TerrainHeight.OZB`: `aa5c81b13ec74b9d33da6826f25b0bd332ef2b8f488db48e8fc93b2542c61b3e`.
- `Data/World42/TerrainHeight.OZB`: `6139638334d03e9a134f06763d704bceaea64d715f98bdb3ed3b72dad069b7df`.

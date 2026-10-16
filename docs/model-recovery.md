# BMD model recovery

## Rejected-model field diagnosis

[The case report](research/model-edge.md) pins all 17 rejected v15 inputs and their exact decoded field offsets. Thirteen reach complete records but use unsupported dummy-parent hierarchies. One has a NaN animation position, one an active normal-index failure, and two unsupported bone values. Native and Python decoding agree on all 17. Rejections and corpus totals remain unchanged; original client handling is unresolved.

## Version-14 recovery

The bounded `modulus.cpp` wrapper uses Crypto++ for the published layered cipher envelope. All **216 installed v14 files decode and pass the complete structural reader**, with no trailing-byte allowance. Every decoded payload digest matches the separately compiled, unchanged pinned upstream oracle. The full current scan has **12,754 files: 12,663 parsed, 17 rejected v15 inputs and 74 unsupported other/table envelopes**.

The implementation masks selector aliases, uses each cipher's default key length, reverses overlapping outer windows, handles ThreeWay's 1020-byte window and retains the unchanged partial inner block. The installed length field includes the entire 34-byte prefix. The reader rejects mismatched lengths, incomplete prefixes and invalid native buffer sizes. It does not accept the reference encryptor's alternate plaintext-length header convention.

The new fixture contains 91 independently generated synthetic oracle vectors covering all 64 cipher pairs, threshold/overlap cases, large bodies and selector aliases. Six portable test methods plus one private integration method cover envelope decoding, geometry/identity, malformed data, native buffer rejection and dependency errors. No game bytes are in these vectors. Read [the source-pinned research](research/bmd-v14.md) for the algorithm, corpus observations, oracle adaptations and dependency licenses.

Current complete results are `model-recovery/verified-v14/manifest.json`. Three v14 models were exported as JSON/OBJ. Independent decoded hashes are in `evidence/v14-source/project-oracle-comparison.json`. These remain ignored local artifacts. This is structural recovery; original rendering and gameplay remain unverified.

Build with Crypto++ installed, then `make -C model-recovery`. The Python v10/v12 readers and v15 Python fallback remain usable independently, but the complete default build/test suite now requires Crypto++ for v14.


## Earlier version-12 and version-15 recovery

The later encrypted-model pass adds `bmd_encrypted.py`, a Python LEA-256 reader,
an independently implemented C accelerator in `lea256.c`, and the version-12
rolling-byte decoder. The C and Python LEA results both match the pinned public
TypeScript implementation on the exact installed `01spa_skill.bmd` payload.
The recovered records then pass the existing strict geometry, index, hierarchy,
and animation checks.

The full corrected scan has **12,754 unique BMD files: 12,447 parsed, 17 rejected,
and 290 unsupported**. Version totals are 701/701 for v10, 180/180 for v12, and
11,566/11,583 for v15. All 216 v14 files and 74 other/table envelopes remain
unsupported. The 17 rejected v15 files include nonfinite coordinates, invalid
indices/bone references, and dummy-parent arrangements not supported by this
reader. Their exact paths and errors are retained rather than silently accepted.

ECB payload alignment leaves between zero and sixteen unused bytes after
complete model records. These bytes are preserved verbatim as
`cipher_block_trailer_hex`; no padding convention or engine semantics is inferred.
The initial scan allowed at most fifteen and rejected 830 legitimate full-block
trailers. The corrected scan explicitly permits sixteen in the decrypted ECB
envelope, preserves them, and still enforces complete block alignment and all
structural checks. A regression test covers this observed full-block case.

The corrected scan also deduplicates file identities on the Mac's filesystem,
so a selected `Player.bmd` alias is not counted separately from `player.bmd`.

Current results are `model-recovery/verified-encrypted-v2/manifest.json`.
Three selected real models are exported as JSON and recorded-pose OBJ there.
The earlier `verified-encrypted/` scan is superseded. The earlier v10-only
results below remain valid within that narrower scope.

Build and verify with `make -C model-recovery`, then
`./tools/python/bin/python -m unittest discover -s model-recovery -p 'test_*.py' -v`.
All 17 model-reader test methods pass. The full scan command reports a nonzero
status when it has explicit rejections or unsupported files, even though the
manifest is complete.

The expanded scanner is `model-recovery/recover_models.py`; it accepts
`--root`, a new `--output` directory, repeated `--asset` selections for exports,
and `--validate-all`. It preserves input identities and does not edit the game.

## Original plain-format milestone

The installed game contains **701 plaintext BMD version-10 model files**. The new read-only parser successfully validates all 701, consumes their complete records without unexplained trailing bytes, and exports real geometry plus recorded animation data. Five models were exported as JSON and OBJ and independently checked. No game executable was run, no original asset was changed, and no game service was contacted.

This is an actual reusable rendering/input component for this installation. It is not a playable game or proof that the original client behavior has been recreated.

## Implementation

`model-recovery/bmd10.py` uses Python's standard library only. Its public functions are `parse_file(path)`, `parse_bytes(raw)`, `pose_matrices(model, action=0, frame=0)`, `obj_text(model, action=0, frame=0)`, and `summarize(model)`.

The reader checks source length, version, bounded counts, every read, finite geometry/animation values, active face indices, bone references, hierarchy cycles, boolean fields, and complete file consumption. It rejects encrypted/unknown versions. It never substitutes synthetic vertices, missing bones, or invented animation frames.

JSON preserves model/texture/bone strings with their original fixed-width bytes, node-local vertex coordinates, normal vectors and bind indices, UV coordinates, all face indices, raw 64-byte polygon records, padding bytes, locked action positions, bone hierarchy, and every recorded position/rotation key. Non-ASCII string bytes are represented losslessly as latin-1 plus hex, without claiming the original text encoding.

OBJ exports apply the selected recorded bone positions and Euler rotations through the hierarchy to vertices and normals. Euler interpretation is Rz × Ry × Rx, cross-checked against the primary viewer implementation's quaternion formula. Source axes, UVs, and polygon order remain intact. OBJ cannot preserve the animation rig: retain the JSON for that. Locked action positions are preserved but are not applied as additional motion; original client interpretation of these records is not established. No engine material/blending behavior or playback rate is inferred.

## Layout evidence and attribution

Layout facts were cross-checked against the independently published [xulek BMD loader](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/bmd-loader.ts), pinned to commit `3f11bf89f3702261174d8efa1436d56a15c7d97a`. Its [package metadata](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/package.json) declares ISC. The Python parser was independently written; no TypeScript implementation was copied into this project. See `model-recovery/SOURCES.md`.

| Record | Observed binary layout |
|---|---|
| Header | `BMD` + version byte 10; 32-byte model name; three little-endian u16 counts: meshes, bones, actions |
| Mesh header | Five little-endian signed 16-bit fields: vertices, normals, UVs, polygons, texture index |
| Vertex | 16 bytes: bone i16, 2 padding bytes, three float32 coordinates |
| Normal | 20 bytes: bone i16, 2 padding bytes, three float32 components, bind-vertex i16, 2 padding bytes |
| UV | Two float32 values, 8 bytes |
| Polygon | 64 bytes: corner count at 0; four i16 vertex indices at 2, normal indices at 10, UV indices at 18. The remaining bytes are preserved without inferring semantics |
| Mesh texture | 32-byte string |
| Action | Key count i16, one-byte lock flag; optional key-count × float32 XYZ position array |
| Bone | One-byte dummy flag; non-dummy bones have 32-byte name and parent i16, then XYZ position keys followed by XYZ Euler-rotation keys for each action |

The full installed v10 corpus conforms to this layout under the implemented checks.

## Verification against installed files

`model-recovery/verified/manifest.json` records every tested input, digest, counts, texture references, and status. The corpus totals 1,330 meshes, 96,078 vertices, and 152,825 polygons. The maximum bone count is 94; maximum action count is 11.

All paths below are relative to the original supplied `Mu The Matrix` installation:

| Exported source | Meshes | Vertices | Polygons | Bones | Actions | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| `Data/Item/Jewel01.bmd` | 1 | 8 | 12 | 1 | 1 | `2c028c84f692f6ee0a13d3911090c81fd9393b95c74de510bbe80ab04de77565` |
| `Data/Monster/Monster07.bmd` | 2 | 133 | 238 | 11 | 7 | `57fce50e26d9370246d88b6f07eed485c7143b16976e13e51e96b0c75df86f9c` |
| `Data/Object7/Object39.bmd` | 1 | 6 | 7 | 1 | 1 | `96ee3b9ca30fd0b50805aadb38571bf76f76790e4baeda291e38885b9e570b65` |
| `Data/Player/Wing04.bmd` | 1 | 20 | 16 | 11 | 1 | `3b82d97f3d666d568d5e0837962bae055f145ea896c0659b810ae4b438eb5929` |
| `Data/Skill/Skeleton03.bmd` | 2 | 395 | 676 | 57 | 1 | `7352d353dcb378e51c093de4d791372c095789ae04e573b4e5907084597c7b79` |

Exports are under `model-recovery/verified/Data/` with matching subdirectories. `verified/obj-validation.json` records a second read of each OBJ: all coordinates are finite, face references resolve, and vertex/normal/UV/polygon counts agree with the source JSON. The actual untextured geometry was rendered into `verified/model-preview.png` and visually checked: it shows a jewel, snake-like monster, rectangular world object, wings, and humanoid skeleton with coherent proportions. This is a geometry inspection image, not an original-game screenshot.

Twelve unit tests pass, including rejection of every truncated prefix of a complete minimal file, unknown encrypted versions, negative counts, non-finite coordinates, bad face/bone references, cyclic parents, non-boolean flags, unexplained trailers, and unavailable requested poses. Analytic rotation/translation tests check geometry transformation independently of the real-file scan.

## Sources used during the original v10 milestone

The initial `bmd10.py` parser accepts version 10. Versions 12 and 15 have since been implemented by `bmd_encrypted.py` and validated as described above. The version-14 lead remains unverified:

- **Version 12 (180 installed files):** [xulek's loader](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/bmd-loader.ts) routes the bounded payload to [`decryptFileCryptor`](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/crypto/file-cryptor.ts). Independently, [VDraven's `BMD_SMD::Decrypt`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/BMD_SMD.cpp#L241) routes 0x0C to `MapFileDecrypt`. Both require a declared body length after the version header.
- **Version 14 (216 installed files):** [VDraven's `BMD_SMD::Decrypt`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/BMD_SMD.cpp#L257) explicitly routes 0x0E to `ModulusDecrypt`, implemented in [`MuCrypto.cpp`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.cpp). Repository commit is `90c78cf5876ec43be69f26e2956d3ffbdc26c5ad`; its [license](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/LICENSE) is MIT, copyright 2021 VD. No code from this repository was incorporated.
- **Version 15 (11,583 installed files):** [xulek's loader](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/bmd-loader.ts) uses a fixed LEA-256 ECB decryptor from [`lea256.ts`](https://github.com/xulek/muonline-bmd-viewer/blob/3f11bf89f3702261174d8efa1436d56a15c7d97a/src/crypto/lea256.ts). A readable-looking decrypted header alone would not validate a model; the full bounded structural checks must pass, and any trailing cipher padding must be explicitly explained.

The 74 `.bmd` files without those model/version headers remain outside this model parser. They can contain different table or world data layouts.

## Reproduce

```sh
python3 -m unittest discover -s model-recovery -p 'test_*.py' -v
python3 model-recovery/bmd10.py --root '/absolute/path/to/Mu The Matrix' --output '/new/output/directory' --validate-all --asset 'Data/Monster/Monster07.bmd' --asset 'Data/Skill/Skeleton03.bmd'
```

The output directory must not already exist and must be outside the installation. The CLI validates all v10 files when requested but writes JSON/OBJ only for explicitly selected assets. It returns nonzero for rejected inputs, retains errors in the manifest, and records a pose error rather than creating invented geometry if a selected action/frame is absent.

A new renderer can now consume actual plaintext models, bones, animation keys, and the separately recovered image textures. Original game rules, protected client/library code, server protocol, collision semantics, and the remaining unsupported models remain independent work.

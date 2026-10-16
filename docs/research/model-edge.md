# Rejected v15 model diagnostics

Issue #17 diagnoses the 17 models rejected by the strict reader. All remain rejected. The 13 dummy-parent cases reach complete structural consumption and then fail the supported hierarchy rules. The other four fail finite-value, face-index or bone-reference checks. This locates the reader boundary; original client behavior is still unknown.

## Inputs and offset convention

The installed executable identity is `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Each model identity below was acquired separately from that installation. The earlier rejected-file manifest had paths/errors but no asset hashes, so these new hashes do not establish historical asset immutability.

Offsets are zero-based bytes in the decoded v10 layout, including its authored four-byte `BMD`/v10 header. Decoded payload offset is layout offset minus four. They are not ciphertext offsets in the installed file. Bone, action, key, component, polygon, corner and record indices are also zero-based.

Native `lea256.c` and separate Python `decrypt_lea_python` outputs agree byte for byte for all 17 complete encrypted payloads. Every v15 declared length equals its complete payload and every payload is block-aligned. Source identity, size, modification time and a second content digest stayed stable during each read. This corroborates the implementations, not the original client format or its handling of anomalous values. No new independent upstream oracle was run on these 17 files.

## Decisive fields

| Installed path | First failing layout offset | Observation |
|---|---:|---|
| `Data/Item/dark_05.bmd` | 8657 | Bone 3, action 0, position key 100, X component is NaN |
| `Data/Item/medusa.bmd` | 218925 | Bone 87 has dummy parent 86; 2 direct dummy-parent edges total |
| `Data/Item/medusaUp.bmd` | 259226 | Bone 96 has dummy parent 95; 2 direct dummy-parent edges total |
| `Data/Item/rockinghorsepet_evol.bmd` | 44308 | Mesh 0, polygon 394, active corner 1 normal index 5223 exceeds 441 normals |
| `Data/Item/scorpio.bmd` | 165880 | Bone 58 has dummy parent 57; 4 direct dummy-parent edges total |
| `Data/Item/scorpioUp.bmd` | 186566 | Bone 60 has dummy parent 59; 4 direct dummy-parent edges total |
| `Data/Item/selupan.bmd` | 256016 | Bone 100 has dummy parent 99; 4 direct dummy-parent edges total |
| `Data/Item/selupanUp.bmd` | 271016 | Bone 96 has dummy parent 95; 4 direct dummy-parent edges total |
| `Data/Monster/Monster151.bmd` | 535581 | Bone 122 has dummy parent 121; 6 direct dummy-parent edges total |
| `Data/Monster/Monster211.bmd` | 296090 | Bone 62 has dummy parent 61; 8 direct dummy-parent edges total |
| `Data/Monster/Monster214.bmd` | 360427 | Bone 67 has dummy parent 66; 8 direct dummy-parent edges total |
| `Data/Monster/Monster215.bmd` | 485550 | Bone 168 has dummy parent 167; 8 direct dummy-parent edges total |
| `Data/Monster/Monster415.bmd` | 535485 | Bone 122 has dummy parent 121; 6 direct dummy-parent edges total |
| `Data/Monster/Monster444.bmd` | 360427 | Bone 67 has dummy parent 66; 8 direct dummy-parent edges total |
| `Data/Monster/monster223.bmd` | 456823 | Bone 87 has dummy parent 86; 2 direct dummy-parent edges total |
| `Data/Object134/Object13.bmd` | 14792 | Mesh 0, normal 1 uses bone -1; bone count is 20 |
| `Data/Skill/CW_Bow_Skill.bmd` | 308 | Mesh 0, vertex 16 uses bone -8888; bone count is 2 |

The 13 dummy-parent files contain 66 direct parent edges to dummy records. All mesh/index/bone-reference checks preceding hierarchy validation pass in those cases. Complete records leave only 1 to 16 bytes of allowed ECB alignment trailer. A dummy record has no name, parent or track payload in this layout; treating it as a root or synthesizing a transform would invent behavior. No such repair is implemented.

The NaN case is in an animation position track, not a mesh coordinate. The previous message gave the end of a multi-scalar read; the new offset identifies the first non-finite scalar. The polygon case fails on an active triangle corner, so ignoring the unused fourth corner cannot resolve it. Bone values -1 and -8888 are preserved as observations; no sentinel meaning is assigned. Files rejected before complete consumption can contain additional failures beyond the first reported field.

## Source identities

| Installed path | Bytes | SHA-256 |
|---|---:|---|
| `Data/Item/dark_05.bmd` | 24648 | `b1c70013c125951e5e8decc8a2c69094b61f3b9b915542fdccd8e3f46eb85191` |
| `Data/Item/medusa.bmd` | 221352 | `1a6d10e8ee2bd0f77a0ff18fe6bed499d3f66c6ae51de115b41dd432217519aa` |
| `Data/Item/medusaUp.bmd` | 261032 | `fc92f031065093e4afdfb578d67f359219d36db4a6dc4f4ee56fd4a89b42224c` |
| `Data/Item/rockinghorsepet_evol.bmd` | 143016 | `c4e907ddcab9e1c9bc480b3999850312ed2259c143cc687b01f261a3d53c9625` |
| `Data/Item/scorpio.bmd` | 170328 | `bffcedd5a86e10aa41c6021a96fb44242f2889603d1c969649415d955f4c631a` |
| `Data/Item/scorpioUp.bmd` | 191016 | `b1783d52f892595772c47923919764a86dd7b5c9d12e7567d15e400eae658c63` |
| `Data/Item/selupan.bmd` | 258728 | `4a2a55a0eef116116934e8db06daf5b7893e5e7c4e7e66e516d3fddd8c3ed0ff` |
| `Data/Item/selupanUp.bmd` | 276456 | `07b606edf9dbfcf7e4366b6bee53835a3af89c9c4d344e38fbad5d2273dd2002` |
| `Data/Monster/Monster151.bmd` | 550168 | `b3552842a8c66f6af1bd0b54f2da9a5c0a19668a4f94fb3309a48ec013ca0b6e` |
| `Data/Monster/Monster211.bmd` | 309032 | `801eb845a6659c31c6479a03b24f5de531630c2b1820ed31537039dba0002e3a` |
| `Data/Monster/Monster214.bmd` | 376056 | `a764e05209e34939cf89ec09b1c78771a07db53f0b7a07ca8c58cad4e607fa63` |
| `Data/Monster/Monster215.bmd` | 498104 | `143dd9a4a95cfeb1e5b1fb9e137197c6c8d86582139205b63d3d9500beeb8b2b` |
| `Data/Monster/Monster415.bmd` | 550072 | `e79e4de2397ed173eb22312a2ac7df57011096a666047456d5a4527f144f6f2d` |
| `Data/Monster/Monster444.bmd` | 376056 | `dc8a1dd603876aa986ca570d8c3c9cdccbaa171a0d2f648a60046ffcf0561dc2` |
| `Data/Monster/monster223.bmd` | 461960 | `2f57f4adc35432b75ab3aa1858855c12b49991a8b81dc099e05731056066597b` |
| `Data/Object134/Object13.bmd` | 124920 | `25b7d2efa9a317cec8f3817c6a59ce5a54b543c0e9d755c22230ac092a727bcc` |
| `Data/Skill/CW_Bow_Skill.bmd` | 3608 | `cf7dad2c6d1e2c8e1fddfa865248b150e1cab3c3ebb7eebbc283ecbfbb313700` |

## Implementation and verification

`BmdError.offset` now identifies the decisive scalar in these error paths. Human-readable errors add record/field context. The five new synthetic cases cover a mixed-field non-finite scalar, a specific active corner, negative vertex/normal bone references and an indirect ancestry path to a dummy bone. The last case checks that the diagnostic points to the actual failing parent edge rather than the descendant where traversal started. No acceptance, rendering or export behavior changes.

The portable suite discovers 93 tests, passes 86 and explicitly skips seven private-input checks. Local integration passes all 93. A fresh 92-file source-only checkout also passes 86 with seven skips. A complete rescan preserves all 12,754 statuses and all 12,663 previously pinned parsed-file digests. Totals remain 12,663 parsed, 17 rejected and 74 unsupported. The scan exits nonzero as designed because rejected and unsupported files remain.

Raw detailed diagnostics, decoded hashes, all direct dummy edges and probe code are retained locally under `evidence/model-edge/`. Original data and plaintext stay ignored. `model-recovery/verified-edge/manifest.json` is the fresh scan. A source-only clone cannot inspect these files.

To reproduce a case, supply the matching private installation and run `python3 model-recovery/recover_models.py --root /path/to/installation --output /new/output --asset Data/Item/medusa.bmd`. The command is expected to reject the model, write a manifest and exit nonzero. Compare the source hash above before interpreting its offset. Use `--validate-all` for corpus coverage.

## Next evidence needed

Locate the restored client model reader and transform hierarchy code, then determine whether these exact fields are consumed, ignored, special-cased or rejected. Until that behavior is established, keep the strict parser boundary. MODEL-EDGE remains open for semantic recovery; this milestone completes field diagnosis only.

# Client handling of the 17 rejected v15 models

Issue #17 (MODEL-EDGE). The strict reader rejects 17 installed v15 BMD files. The first part of the issue located the decisive field in each file (below). This finding runs the client's own loader, pose builder, CPU skinning and mesh draw on all 17 files in Unicorn and records what the client does with those fields.

**Result.** The client loads all 17. Its reader checks nothing: it copies every count, index, bone reference, parent and float raw, and returns success. Nothing clamps, skips, wraps or uses a different layout. The out-of-range values only matter later, where an index addresses memory outside the arrays the model owns:

* **Dummy parents (13 files, 66 edges).** Every child of a dummy record is an `IK Chain` leaf bone. No vertex or normal uses one. The pose builder composes each child from the dummy's bone slot, which that call never writes, so these bone matrices depend on earlier client state. The rendered geometry does not: vertices, normals and lights were byte-identical with a zero and a stale bone buffer. These models render fully.
* **NaN position (`dark_05`).** Bone 3 (`zx04`), action 0, last key (100). The NaN is copied and turns that bone's pose matrix into NaN at frames that use key 100, including the first frame after a wrap. The model has no meshes, so it draws nothing by itself. Which code consumes its bones was not traced.
* **Negative bone references (`Object13`, `CW_Bow_Skill`).** The transform reads the matrix at `0x06fce398 + bone*0x30`. Bone -1 reads frame-timing globals at `0x06fce368`; bone -8888 reads `0x06f66118`, which has no direct code reference nearby. All three records hold a zero vector. The normals therefore become ±0 and their light is `max(minimum, ambient)` for any finite matrix. `CW_Bow_Skill` vertex 16 lands on the foreign matrix's translation column: the model origin when that memory is zero, otherwise state-dependent. While loading, the bone box pass also increments a 16-bit word at `0x075a57e8` for that vertex.
* **Corner indices (`rockinghorsepet_evol`, mesh 0, polygon 394).** The mesh draw still draws the triangle. Corner 0 takes its texcoord from heap memory 55,592 bytes into a 2,368-byte block. With lighting on, corner 1 passes `&colour_table[0][5223]` to `glColor3fv` and corner 2 passes the address 29,063 entries before the table: entry 937 of the transform's normal buffer for mesh 48. No installed mesh has more than 4,629 normals and no installed model has more than 30 meshes, so no installed model's colour pass or transform writes either entry. Both colours are therefore zero (black) unless another user of those buffers wrote them; 11 raw references to the colour table were not traced. The heap texcoord is the one value with no known content.

The reconstructed readers and the native viewer now reproduce this behaviour. Unknown client memory is modelled explicitly as the zero-filled state of a fresh client, and every such value is listed rather than reinterpreted.

## Field diagnosis (first part of issue #17)

### Inputs and offset convention

The installed executable identity is `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Each model identity below was acquired separately from that installation. The earlier rejected-file manifest had paths/errors but no asset hashes, so these new hashes do not establish historical asset immutability.

Offsets are zero-based bytes in the decoded v10 layout, including its authored four-byte `BMD`/v10 header. Decoded payload offset is layout offset minus four. They are not ciphertext offsets in the installed file. Bone, action, key, component, polygon, corner and record indices are also zero-based.

Native `lea256.c` and separate Python `decrypt_lea_python` outputs agree byte for byte for all 17 complete encrypted payloads. Every v15 declared length equals its complete payload and every payload is block-aligned. Source identity, size, modification time and a second content digest stayed stable during each read. This corroborates the implementations, not the original client format or its handling of anomalous values. No new independent upstream oracle was run on these 17 files.

### Decisive fields

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

### Source identities

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

### Diagnosis verification

`BmdError.offset` now identifies the decisive scalar in these error paths. Human-readable errors add record/field context. The five new synthetic cases cover a mixed-field non-finite scalar, a specific active corner, negative vertex/normal bone references and an indirect ancestry path to a dummy bone. The last case checks that the diagnostic points to the actual failing parent edge rather than the descendant where traversal started. That part changed no acceptance, rendering or export behavior.

The portable suite discovers 93 tests, passes 86 and explicitly skips seven private-input checks. Local integration passes all 93. A fresh 92-file source-only checkout also passes 86 with seven skips. A complete rescan preserves all 12,754 statuses and all 12,663 previously pinned parsed-file digests. Totals remain 12,663 parsed, 17 rejected and 74 unsupported. The scan exits nonzero as designed because rejected and unsupported files remain.

Raw detailed diagnostics, decoded hashes, all direct dummy edges and probe code are retained locally under `evidence/model-edge/`. Original data and plaintext stay ignored. `model-recovery/verified-edge/manifest.json` is the fresh scan. A source-only clone cannot inspect these files.

To reproduce a case, supply the matching private installation and run `python3 model-recovery/recover_models.py --root /path/to/installation --output /new/output --asset Data/Item/medusa.bmd`. The command is expected to reject the model, write a manifest and exit nonzero. Compare the source hash above before interpreting its offset. Use `--validate-all` for corpus coverage.

## Client execution (verified)

`scripts/validate_model_edge.py` runs these client routines in Unicorn 2.1.4 over the pinned restored text (`2bd5f2e9…`), the second section (`c985e2e6…`), trig flag 1 and memcpy feature word `0x2f`:

* reader section `0x012b3b50..0x012b4477` (`0x012b3812` after decoding);
* pose builder `0x012b5064`;
* transform `0x012b5bde`;
* mesh draw `0x012b8d1d`.

Each one runs with every client helper it reaches. The validator pins 15 body hashes. Ones not pinned in earlier findings:

| Body | Range | SHA-256 |
|---|---|---|
| Reader | `0x012b3812..0x012b4485` | `544459ba…cbfb08a9` |
| Bone box entry | `0x012b2df3..0x012b2e81` | `3814a8b4…ab4d87e4` |
| Bone boxes | `0x012b47fd..0x012b4dd3` | `a02c98cd…2d03fbb4` |
| Frame timing (static reading only) | `0x012aeb2b..0x012aeca4` | `02b0886d…4056f4db` |

The whole third image section `0x01ced000..0x0bdd2000` is mapped zero-filled, the state a loader gives uninitialized data. Each routine declares the client tables it legitimately uses. Every other access is recorded with its address, instruction and value, not stopped:

* third-section addresses outside those tables;
* heap reads outside the routine's own records;
* pointers passed to `glColor3fv`/`glVertex3fv` that lie outside those tables.

Modelled boundaries:

* HeapAlloc/HeapFree: a bump allocator with poisoned, undefined blocks;
* `_getptd`;
* the two bitmap map lookups, which return the zeroed error record `0x01ec3030`;
* a recording OPENGL32 stub;
* declared caller state: pose arguments, transform arguments, bone scale 1.0, other globals 0, texture index table and lighting.

The reader leaves model `+0x38` allocated but unwritten; the texture loader fills it later.

Read-modify-write instructions that discard the old value (`AND [x],0`, `OR [x],-1`) are listed and checked by decoding.

| Comparison | Calls | Matches |
|---|---:|---:|
| Reader on the 17 files, with the client's records checked field by field against an independent stream walk | 17 | 17 |
| Authored C reader on the same memory (heap arena, state window, global pages) | 17 | 17 |
| Pose builder, zero and stale bone buffers (authored `mu_pose_build` compared) | 278 | 278 |
| Transform after each pose, zero and patterned foreign spans (authored `mu_model_transform` compared) | 528 | 528 |
| Mesh draw per mesh, lighting on and off, zero and stale tables | 148 | 148 |
| Reader on synthetic payloads with every rejected value kind (154 touch foreign memory, 253 sub-objects) | 300 | 300 |
| Reader on every 25th installed v12/v14/v15 file the strict reader accepts | 477 | 477 |
| `mu-render corners` stream vs the client's GL corner stream (fresh state) | 16 files, 288,207 records | 16 |

Expectations are derived from the census, not hard-coded, and the run fails on any difference:

* state-dependent bone slots must be exactly the dummies plus their unresolved children;
* slots read before being written must be exactly the 66 dummy parents;
* no transform output may depend on stale slots;
* foreign-dependent outputs may appear only at the records with out-of-range bones;
* non-finite slots must be exactly the NaN bone;
* the draw's foreign reads must be exactly the three bad corner fields.

Report: `evidence/model-edge-client/report.json` (SHA-256 `245bee5a…77b16ca`, authored library `94c32581…38d4f`), 2 min 39 s.

Per-file observations (executed):

| File | Client reads/writes outside the model's own data | Output effect |
|---|---|---|
| 13 dummy-parent files | Dummy bone slots read before written (66) | IK Chain matrices only; geometry identical across states |
| `dark_05` | none | Slot 3 non-finite at frames 100.0, 100.25 and 0.25 after 100 |
| `Object13` | Transform reads `0x06fce368..0x06fce397` (time `0x06fce370` is a known global) | Normal 1 is ±0 (sign follows the matrix); lights unchanged |
| `CW_Bow_Skill` | Loader: reads box slots `0x0787c540`/`0x0787cea0` (secondary-light table, mesh 49), word `0x075a57e8` +1. Transform: `0x06f66118..0x06f66147` | Vertex 16 = foreign translation column; normal 13 ±0 |
| `rockinghorsepet_evol` | Draw: heap texcoord, `&colours[0][5223]`, `&normals[48][937]` | One triangle's texcoord/colours; with lighting off, only the texcoord |

## Static context

These readings come from static analysis of the image, not from execution:

* **`0x06fce364..0x06fce393`.** The frame-timing routine `0x012aeb2b` writes these. It stores an init flag `0x378`, tick counters `0x37c/0x380/0x384/0x388`, frame counters `0x38c/0x390`, the frame rate as a float `0x36c` and the time as a float `0x370`. `0x368` has no direct reference. Rows 1 and 2 of `B[-1]` are integers read as floats. They are non-finite only when a tick value has its exponent bits all set (from about 24.8 days of tick count, if the counter is `GetTickCount`; the import name is not recovered). A non-finite entry would turn the zero normal into NaN.
* **`0x06f66118`.** A linear sweep of the text finds no immediate reference between `0x06dfa43c` and `0x06faefac`, so its writer, if any, indexes from further away. Its contents are not established.
* **`0x075a57e8` and the box slots.** The counter word lies 0x4570 below the box-count table. The min/max slots alias the secondary-light table's mesh-49 span, which no installed model writes. The 16-bit increment lands in an unidentified object.
* **Load paths.** Which game paths load these 17 files, and whether a server spawns their users, was not traced. Their names are not in the captured image sections. "Renders" above means that the client's load, pose, skinning and draw routines complete and emit the geometry when called. No live game observation was made.

## Reconstruction and native behaviour

* **Python reader.** `bmd10.parse_bytes(..., client_layout=True)` and `recover_models.py --client-layout` keep each rejected value and list it in `client_semantics`. Each entry has its kind, raw value, layout offset and a `strict` flag. A file is strict-clean exactly when the strict reader accepts it. Structural limits still reject: truncation (the client would read past its buffer), negative or oversized counts and the size limits. Bones below a dummy are marked `client_unresolved`. OBJ export refuses geometry that would read client memory; for the IK-only files it exports unchanged geometry. The default strict mode, its messages and the corpus totals (12,663 parsed, 17 rejected) are unchanged.
* **Authored C.** `reconstructed/model-codec/model_reader.c` reconstructs the reader section and the bone box pass. The texture-name parser and the allocator are callbacks.
* **Native loader.** `native/core/mu_bmd` walks the payload like the client. The strict checks become anomalies, shown by `mu-render info` and by the viewer when it loads a file.
* **Native model.** `mu_model` maps a zero 0x30-byte region at the client address of each out-of-range vertex/normal bone. Dummy slots keep their never-written zero contents.
* **Native draw.** `mu_edge` redirects corner indices past their arrays to appended zero entries, so the mesh draws instead of being refused. Zero is the fresh-client value for the colour table, normal buffer and vertex slots. For the heap texcoord, zero is a labelled substitute.
* **Corpus.** `mu-render scan` now loads, animates and draws all 11,583 v15 files with no refused mesh. The v12/v14/v15 total is 3,832,238 vertices, up from 3,814,006.

Tests:

* `model-recovery/test_bmd10.py` (six client-layout tests);
* `reconstructed/model-codec/test_model_reader.py` (120 synthetic payloads checked against an independent walk, plus targeted cases; the private test runs the validator);
* `native/tests/test_native_edge.py`;
* updated loader-agreement and corpus checks in `test_native_viewer.py`.

## Labels

* **Verified by execution:** the reader's acceptance and raw copies, the bone box writes, pose slot reads and state dependence, transform foreign reads, the draw's corner reads, and C/native equality under the stated memory model.
* **Static:** the timing-global layout, the absence of nearby references, and the 50-mesh and 15,000-entry capacities (inferred from addresses).
* **Unverified:** live contents of foreign memory, Wine heap layout, which callers load these files, the bone buffer a given caller passes (300 of 314 builder calls push `0x06fce398`), GL driver handling of NaN vertices, and native Windows.

## Reproduction

```sh
E=evidence
python3 scripts/validate_model_edge.py --text $E/x86-text-capture-09/client-text.bin \
  --data $E/image-data-run10/data-capture-10/client-image-data.bin \
  --flag $E/trig-state-15/captures/late/math-dispatch-flag.bin \
  --feature $E/x86-math-capture-09/cpu-features.bin --game-root "$MU_GAME_ROOT" \
  --native native/build/mu-render --sample 25 --output $E/model-edge-client/report-new.json
MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=... python3 -m unittest discover -s native/tests -p 'test_native_edge.py'
```


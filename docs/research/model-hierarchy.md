# Client bone records and dummy-parent hierarchy

Issue #22 (MODEL-HIERARCHY-001) asks what the exact client stores for dummy and non-dummy bone records, and what its pose code does when a non-dummy bone names a dummy bone as parent. The strict reader rejects 13 v15 models with 66 such edges ([model-edge](model-edge.md)). This finding traces the client's instructions. It does not change validation.

**Result.** The selected reader copies the parent unchecked, and the selected pose loops do not check whether that parent is dummy. A dummy record is skipped before its parent field is read and its output slot is not written by that call. A child that names it composes the prior contents of that slot with its local matrix. The child's output is the composition result, not necessarily the prior slot itself. The evidence does not establish those prior contents, a root/identity substitution, or whole-client acceptance of these models. Strict validation stays unchanged until runtime state and remaining consumers are understood. [MODEL-EDGE](model-edge.md) later executed these loops on the 13 files: every child of a dummy is an unused IK Chain leaf, so their geometry does not depend on the unwritten slots.

## Inputs and conventions

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `main.exe` (target identity) | | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored first section, capture09 `client-text.bin`, VA `0x00401000` | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section, run10 `client-image-data.bin`, VA `0x01a7c000` | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| REA dossier, reader candidate `0x012b3812` | 3,965,030 | `c34c80737b18785ee002ff66f2c9ff47e71556f33eddfaed54a3b8c3e3b3369c` |
| REA dossier, filename caller window | 229,722 | `dc6fa431c5782a1c82eb43935344ed18165146fd77ea17068fb828eb4fdc653a` |
| Rejected-model diagnostics (`evidence/model-edge/diagnostics.json`) | 19,866 | `ba945b166c52e068a4ed12bbbc67a27f68d697fcf64197aaff627b09e45b909a` |

All digests were recomputed before analysis and match [restored text](restored-client-text.md) and [image data](client-image-data.md). The REA windows `0x012b0000`+64 KiB (`ab51f131…`) and `0x01820000`+32 KiB (`382c4c51…`) are exact slices of the pinned text.

Addresses are virtual addresses in the restored image. Within a captured region, file offset is VA minus that capture's base; original packed-executable offsets are not interchangeable with restored-image offsets. Object offsets such as `+0x22` are bytes from the start of the in-memory model or bone object, not file-layout offsets. Bone indices are zero-based, matching the diagnostics.

Method: Capstone 5.0.9 (`pip show`; the module reports `5.0.7` as its version string) under Python 3.10.12, linear decoding from asserted boundaries. A decode must land on the stated end. This checks alignment within the asserted span; it does not independently establish every entry, caller boundary or reachable path. REA/Ghidra pseudocode was used as a map and is labeled "decompiler" below. No client code was executed for this issue and no runtime state was observed.

## Model reader `0x012b3812`

| Claim | Evidence | Status |
| --- | --- | --- |
| Body `0x012b3812..0x012b4485`, 989 instructions, ends `ret 0xc`; object pointer in ECX | Linear decode lands exactly; count equals the REA dossier | Confirmed |
| The body runs only when the third argument is 1; three inspected call candidates (`0x00cd5636`, `0x0182033c`, `0x01820472`) pass 1 at the decoded call sites | Manual call-site decode; the last two follow issue #21's entry candidates `0x018202b4` and `0x018203e0` | Confirmed |
| Version byte branches `0x0c`, `0x0e`, `0x0f` select decoders | Decompiler only; the decoder bodies were not traced here | Decompiler |
| Counts at model `+0x22` bones, `+0x24` meshes, `+0x26` actions (signed 16-bit); bone array pointer at `+0x2c`; action array at `+0x30` with 16-byte stride and key count at `+8` | Field uses in the reader and pose builders | Confirmed |
| Bone array is `new(max(count,1) * 0x8c)` at `0x012b3c79..0x012b3c9c` with no constructor or clear | No other write to the array precedes the bone loop in the decoded body | Confirmed |

Bone loop `0x012b4225..0x012b4441`, per record `i` (bone = `[model+0x2c] + i*0x8c`):

| Step | Instructions | Observation |
| --- | --- | --- |
| Dummy byte | `0x012b425b`, `0x012b425d` | One stream byte is stored at bone `+0x22`; stream advances by one |
| Dummy test | `0x012b426a..0x012b4270` | Nonzero jumps to `0x012b443c`, the loop increment. Nothing else is read or written for that record |
| Name | `0x012b4276..0x012b4282` | 32-byte copy to bone `+0x00` |
| Parent | `0x012b429c`, `0x012b429f` | Raw 16-bit copy to bone `+0x20`; stream advances `0x22` in total |
| Tracks | `0x012b42ae..0x012b442e` | `+0x24` = 12-byte entry per action. Each entry receives position (12×keys), rotation (12×keys) and a 16×keys array filled by `0x00d00724` per key |

The parent value is never compared with -1, the bone count, its own index or another record's dummy byte in the reader body. A dummy record's name, parent and track pointer are not written by the reader.

Allocation chain: `0x0191bab9` → `0x0191ba7b` (allocation retry loop calling `0x01983110`) → `0x019a4da0`, which calls through IAT slot `0x01a7c5c8` with arguments `(heap, 0, size)`. The flags argument is 0, so the caller requests no zero fill. In the Wine capture the slot holds `0x7bc275e0`, inside the range where Wine maps its ntdll. Reading this as `HeapAlloc`/`RtlAllocateHeap` is an inference; the import name is encrypted in the packed file. The selected reader leaves those dummy fields uninitialized; their actual allocator/prior contents were not observed. No pose path below reads them.

After loading, `0x012b4456`/`0x012b445b` call `0x012b2df3` with argument 0. With a nonzero argument that routine reclassifies every record as dummy exactly when its name begins with `D`,`u` (`0x012b2e3a`, `0x012b2e4c`, stores at `0x012b2e54`/`0x012b2e5d`). The BMD path disables this rule, so the file's dummy byte stands. The rule is enabled by construction path `0x010a792f`, which fills bones from a fixed table at `0x01f7bb90`, not from a BMD file. `0x012b2df3` then calls `0x012b47fd` (485 instructions). That routine writes only byte `+0x28` of every bone, including dummies, from a per-index global table at `0x075a9d58`. It does not touch `+0x20` or `+0x22`.

The sibling reader `0x012b2e81..0x012b3812` (815 instructions, no decryption branch, no raw direct-call candidate found) has the same bone loop (`0x012b35c7..0x012b37e3`).

## Pose builders

`0x012b5064` (704 instructions, `ret 0x20`, 314 raw direct-call candidates) and `0x012bcffb` (317 instructions, `ret 0x10`, one raw call candidate at `0x009ab512`, action-0 track only) iterate bones `0..count-1`:

| Step | `0x012b5064` | `0x012bcffb` | Observation |
| --- | --- | --- | --- |
| Dummy skip | `0x012b5217..0x012b521f` | `0x012bd035..0x012bd03d` | Nonzero dummy byte jumps to the loop increment; slot `i` is not written |
| Root | `0x012b5786..0x012b578d`, `0x012b5881..0x012b5895` | `0x012bd2a8..0x012bd2af`, `0x012bd313..0x012bd324` | Parent -1 composes global matrix `0x078965ac` (scaled in some branches) into `out[i]` |
| Child | `0x012b589f..0x012b58bc` | `0x012bd32e..0x012bd348` | `concat(out + parent*0x30, local, out + i*0x30)`; parent is sign-extended, with no range, order or dummy check |

`out` is the first stack argument. It appears only in these three address computations in `0x012b5064`. Concatenation `0x00cff83e` (726 instructions) reads only its first two arguments and stores 12 floats through its third (one 3×4 matrix). The arithmetic itself was not compared.

A raw E8 target search finds 314 call candidates for `0x012b5064`. A separate raw PUSH search finds 300 candidates followed by a matching call in a short straight-line decode, using immediate `0x06fce398`, the candidate base of a shared output buffer. These are heuristic counts: starts may be embedded in another instruction or data, and complete caller boundaries, reachability and argument provenance have not been established. The lookahead now stops at returns, branches, interrupts and explicit stop/trap instructions; that refinement preserves the 300-candidate count in this pinned text. That address is in the third section beyond its raw data, which a standard loader zero-fills. The packer's effect on it was not checked. Routines `0x00966ea5`, `0x012b5bde`, `0x012b8d1d` and `0x012bb35a` also receive addresses in that buffer as pushed arguments. Their uses were not traced, and no routine that clears or initializes the buffer was found among these call patterns.

## Consequence for the 66 rejected edges

The diagnostics give 66 direct edges across 13 files. Every edge has `parent = child - 1` and the parent is a dummy record. Under the confirmed flow, each child:

* is not rejected and is not skipped;
* is not reattached to the root;
* composes `out[parent]`, a slot that the same call never writes for this model.

The prior contents of that slot are unknown. Possible sources include initialization, earlier pose output or another untraced writer; these are examples, not an exhaustive classification. Descendants can inherit dependence on that unknown state. The flow is modeled, without arithmetic, by `scripts/model_hierarchy_flow.py`.

This identifies the selected loops' dependency mechanism, not a value. No runtime capture has shown these slots during a render of the affected models. A zero-matrix outcome would collapse the subtree; a stale outcome would depend on draw history. Neither was observed.

## Validation implications

The strict reader rejects these edges; the selected client read/pose instructions do not reject them. The pose result depends on caller-buffer state, so neither "treat the dummy as root" nor "use identity" is justified by this evidence. Other whole-client acceptance behavior remains unverified. Changing behavior responsibly requires one of:

1. Keep rejecting, as now.
2. Accept the records structurally with a per-bone marker for "parent slot not written by the client pose loop," and refuse pose or geometry export for marked subtrees.
3. Capture the runtime buffer while these models render and reproduce that state.

No reader change is made. Option 2 could expose the supported structural observation while keeping pose/export unsupported; it would not itself reproduce rendering.

## Corrected attempts and tool limits

* A first consumer filter required both parent and dummy fields within 70 instructions of a stride use. It found only the two readers. Widening to stride sites indexed from model `+0x2c` found both pose builders.
* `0x010a792f` first looked like a consumer. Its full decode shows a table-driven constructor.
* The concat store detector first looked three instructions ahead and found none; the real distance is four. The tool was corrected, not the claim.
* A synthetic test showed the first `decode_range` truncated its input at the end address and reported a straddling instruction as undecodable. It now decodes past the end and reports an overrun.
* The stride scan finds `imul`, `mov` and `add/sub` immediates only. Stride computed through `lea`/shift chains would be missed. Prologue backtracking is limited to 8 KiB, so large or frameless functions get no candidate start.

## Unresolved

* Actual contents of `out[parent]` when these 13 models render, and which call sites render them.
* Whether vertices or normals bound to dummy records read unwritten slots in the skinning consumer (candidate `0x012b5bde`).
* Complete parent arrays for the 13 files, which would count affected descendants. This needs the decoded models; the private installation was outside this session's granted folders.
* Version-branch decoders, rotation conversion `0x00d00724`, concatenation arithmetic, the heap import identity and packer treatment of the buffer section.

## Reproduction

The commands require the private captures. The scan and report directories must be new paths; raw outputs stay ignored under `evidence/claude-model-hierarchy/`.

```sh
python3 scripts/model_hierarchy_verify.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --output evidence/claude-model-hierarchy/verify-report.json
python3 scripts/model_hierarchy_scan.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --output evidence/claude-model-hierarchy/stride-sites.json
MU_RECOVERY_INTEGRATION=1 python3 -m unittest tests.test_model_hierarchy
```

`model_hierarchy_verify.py` checks the listed instructions of both readers, `0x012b2df3`, `0x012b47fd`, both pose builders and the allocator chain. It also checks six whole-body decodes, argument-use and store counts, raw call-candidate and straight-line buffer-push-candidate counts and the heap slot value, and exits nonzero on any mismatch. The arguments at the three reader call sites and the `0x010a792f` constructor were decoded manually and are not in the script. The v2 report explicitly marks call-search confidence as unverified. Synthetic regressions demonstrate an E8 match inside a MOV immediate and require PUSH lookahead to stop before returns and other control transfers. The local scan reported 438 stride sites. A source-only clone runs the synthetic tests and skips the private check.

# Model-loading call path and v12 decoder

CLIENT-LOADER-001 / issue #21 follows model filename strings into a concrete
client call path and reconstructs one decoder. The authored C matches the
captured routine in 4,048 synthetic cases and every one of 180 installed v12
payloads. It does not reconstruct the complete loader or establish gameplay.

## Source identities and bounded REA evidence

The target executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The restored text is 23,572,480 bytes at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The separately captured image data has SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
All are Wine compatibility captures, not native Windows observations.

REA 6.5.0 with Ghidra 12.1.4 analyzes bounded raw windows and explicit function
seeds. Its generic GCC profile does not recover original Microsoft C++ types
or reliable signatures for every call. Seed names are authored labels, not
recovered original symbols. Ghidra body ranges below are observed analysis
results, not proof of complete original source boundaries.

| Entry | Observed body | Evidence ID | Interpretation and limit |
|---|---|---|---|
| `0x018202b4` | 300 bytes through `0x018203df` | `ev_172bf818729f34478b92fe02041d08774762552573b7b4d1f16f1890e5792920` | Candidate filename formatter/caller; seeded from a string reference and prologue, flow reaches a return |
| `0x012b3812` | 3,187 bytes through `0x012b4484` | `ev_b7c3916cb27a5373a7036c8cc69c7130450ada4c1c9347936f06a742e6a61789` | Direct call target with file-like reads, version dispatch and mesh/action/bone-layout copying; complete behavior unverified |
| `0x0098c5f2` | 194 bytes through `0x0098c6b3` | `ev_abf4e01a55fd6b6d1f4811ab7f532ecf28e1521caa0c200984c1b3f0f3dd8c90` | Observed v12 rolling decoder; reconstructed and instruction-compared |

The decoder body SHA-256 is
`d848bd43bfc35dcd14883313057e2c9dec83fa85fc771064f3118d54fb4f999f`.
Its full body is leaf code with no external call or data dependency. The format
constant is embedded in instructions and matches the already documented public
v12 constant in `model-recovery/SOURCES.md`.

## Observed static call chain

The first candidate references the BMD filename-format data at `0x01aef904`
and calls `0x012b3812` at instruction `0x0182033c`, passing a filename buffer,
another argument and flag 1 with a register-held object pointer. This is a
static call-site observation, not evidence that the live game invoked it.

The callee reads a version byte at file-buffer offset 3. Its version-12 branch
calls `0x0098c5f2` twice: at `0x012b393d` with destination zero to query length,
and at `0x012b3979` with an allocated output. Each caller removes twelve bytes
of stack arguments afterward. The routine also has separate version-14 calls
to `0x016ced37` and version-15 setup/decode calls to `0x0091a6c0` and
`0x0091a730`. Those helpers have not been reconstructed by this milestone.

Subsequent code copies a 32-byte model name, reads the three 16-bit counts and
copies mesh arrays with the known 16/20/8-byte element layouts. This supports
the model-loading interpretation of this call path. It does not establish
original class names, full validation rules, allocation-failure behavior,
exception handling, rendering or dummy-parent semantics. The strict reader's
17 rejections remain unchanged.

## Reconstructed decoder behavior

The logical API is `mu_bmd12_decode(destination, source, length)`. Length and
return are signed 32-bit values. A null destination returns length without
reading source. A nonpositive nonquery length also leaves caller spans alone.
A positive call processes bytes in increasing order, starting feedback at 94.
Each output byte is the keyed XOR input minus feedback modulo 256. After the
store, the routine rereads that source byte and adds 61 modulo 256 for the next
feedback value. The key index cycles through sixteen positions.

The order matters for aliasing. For synthetic input bytes 0 and 1, disjoint
output is 115 and 53, while in-place output is 115 and 194. A destination one
byte ahead can also overwrite an upcoming input byte. The C implementation
preserves both effects. It does not promise envelope validation, allocation,
capacity checking, status flags or behavior for inaccessible pointers.

## Decisive comparisons

Unicorn 2.1.4 executes the actual 194 captured bytes, with no helper substitutes.
An authored return address ends execution. Isolated nonexecutable source/stack
mappings, a step budget and memory hooks bound the execution. The checks compare
the entire arena, signed return, caller return address, stack cleanup, saved
registers, direction flag and exact two source reads/one output write per byte.
No unexpected memory accesses occur in successful comparisons.

- 4,048 synthetic cases cover three patterns, fourteen positive lengths through
  1,024, four source alignments, twelve displacements from -1,024 through 4,096,
  both DF states, null-destination signed-length queries including INT32 limits,
  and nonpositive nonquery calls with an inaccessible source sentinel.
- All 180 pinned installed v12 payloads, totaling 3,176,971 encrypted bytes,
  match the captured instructions, authored C and existing Python reader with
  disjoint buffers. Every installed input is hash-checked against the pinned
  complete corpus manifest. This is direct decoder comparison, not merely a
  successful structural parse.
- A deliberately wrong implementation reads feedback before the output store.
  It fails 312 synthetic overlap cases. Its return, ABI and access checks still
  pass, so output comparisons detect the semantic mistake.

Finite comparison coverage is not an all-input proof. Nonempty huge signed
lengths, address wrap, code/stack aliasing, memory faults, concurrent writes and
native Windows execution remain unverified. Registers used as scratch and
condition/status flags are not exposed as part of the C API.

## Local artifacts and next action

Raw REA dossiers/windows remain in `evidence/model-loader-first/`,
`evidence/model-loader-callee/` and `evidence/model-codec/`. The last directory
also has synthetic/corpus comparison reports, deliberately wrong source/library
and its failed comparison report. These are ignored and absent from a fresh
GitHub clone. The [module README](../../reconstructed/model-codec/README.md)
explains how to supply private inputs and rerun comparisons.

Next trace and validate the version-14 or version-15 helpers, or reconstruct a
bounded plaintext loader path with explicit external dependencies. Establish
actual hierarchy handling before interpreting negative bone values or dummy
parents. The client object layout is still a partial map, not recovered types.

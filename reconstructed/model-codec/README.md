# Client-linked BMD codecs

`mu_bmd12_decode` is authored C for the rolling decoder called by the selected
client model-loading path. It matches captured instructions in 4,048 synthetic
cases and all 180 pinned installed v12 payloads. This is a decoder component,
not a complete model loader or playable client.

The logical name is ours. The original entry is `0x0098c5f2`, with a 194-byte
observed body. The [finding](../../docs/research/client-model-loader.md) records
caller evidence, captured-code identity, ABI checks, coverage and limitations.

## Contract

```c
int32_t mu_bmd12_decode(void *destination, const void *source, int32_t length);
```

The return is always the signed 32-bit input length. A null destination queries
the length without accessing source. A nonpositive length also accesses neither
caller span. For a positive nonquery call, both pointers must cover that many
accessible bytes with no address wrapping or aliasing of executing code or the
call stack. Unaligned and overlapping spans are supported.

The function writes one byte, then rereads that source position for feedback.
In-place output therefore differs from the ordinary disjoint decoder. Moving
feedback ahead of the store breaks 312 synthetic comparisons. Do not add
`restrict`, copy the input first, or replace the operation with `memmove`.

It allocates nothing and does not validate a BMD envelope, available capacity,
model structure, file path or encryption version. The strict checked reader in
`model-recovery/` remains the interface for untrusted files. No source parser
acceptance was relaxed. Exceptional pointers, concurrent modification, original
status/exception flags and native Windows equivalence remain unverified.

## Build and compare

```sh
make -C reconstructed/model-codec
python3 -m unittest discover -s reconstructed/model-codec -p 'test_*.py' -v
```

Seven portable tests use authored bytes, analytic expected values and the
published inverse encoding. The eighth is an explicit private integration
check. The validator requires the pinned full restored-text capture before
loading the optional emulator. Supply your own private evidence and use:

```sh
./tools/python/bin/python scripts/validate_model_codec.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --game-root /path/to/matching/installation \
  --output /new/local/comparison.json
```

Omit `--game-root` for synthetic instruction comparison only. Corpus comparison
also requires the exact ignored `model-recovery/verified-v14/manifest.json`,
whose digest is pinned by the validator. Every selected model hash and file
identity is checked. Both comparisons execute the actual decoder body without
substituting any of its operations. Raw code, payloads and reports stay local.

## v15 key setup

`client_lea.h` exposes `mu_client_lea_setup`, a byte-defined 772-byte LEA context
for 16/24/32-byte keys. It preserves unused context bytes and accepts unaligned,
disjoint key/context spans. Null pointers and unsupported sizes are no-ops.
It matches 1,320 actual captured-instruction cases, including both DF states.
A reversed-key-order negative control fails all 1,248 valid cases.

Five portable tests cover public encryption vectors, no-op gates and context
layout/guards. A sixth explicitly skips private comparison unless integration
is requested. Read [the finding](../../docs/research/client-lea-key.md) for exact
identities, span requirements and the reproduction command. Key/context alias behavior remains outside the
setup contract.

## v15 ECB decoder

`mu_client_lea_decode` consumes a valid recovered setup context and complete
16-byte blocks. It snapshots groups of eight, four and one block, preserving
the observed data-overlap effects between groups. Context must be disjoint from
data. Null/zero/unaligned-length gates are no-ops. No envelope checks or arbitrary
context/round-count contract are implied.

[The decoder finding](../../docs/research/client-lea-decode.md) records 12,960
valid original-code guest comparisons, 46 no-op checks, 1,152 scalar instruction
comparisons and 4,094 wrong-batch differences. Authored C also matches the
independent reader on all 11,583 installed v15 payloads; that corpus result does
not execute original instructions. Five portable decoder tests plus three
relocation fixtures run by default. The private scalar/corpus test requires the
pinned text, installation, manifest and rejected-model diagnostics. Original
AVX execution uses the separate opt-in x86 guest tool; normal CI only cross-builds
that tool on Linux. Full-loader, rendering and native Windows claims remain open.

## Bone-track loop

`bone_tracks.h` exposes `mu_bone_tracks_read`, authored C for the bone loop
`0x012b4225..0x012b4441` in reader `0x012b3812`. Per non-dummy bone it stores
the name, the raw parent and a track array with 12 bytes per action. Each track
entry points to position, Euler-rotation and quaternion arrays of 12/12/16 bytes
per key. Each quaternion comes from record-math `mu_rotation_quaternion`.
Client records hold 32-bit pointers, so the API works on a byte view of one
32-bit client address window, with an allocator callback that receives the
client's operator-new request sizes in original order. It rereads counts and
pointers where the client does. A null allocation or an access outside the
window returns a status; those statuses are authored conventions, not client
behavior.

The [finding](../../docs/research/client-bone-tracks.md) records the layouts,
allocation behavior and the instruction comparison. The actual loop, memcpy,
operator new/malloc and rotation/trig code all run. 342 synthetic comparisons
and all 11,962 installed v12/v14/v15 models the readers accept match the
captured instructions. A zero-size-allocation-eliding control differs in 57
cases. `libbonetracks` links `../record-math/record_math.c` with contraction
disabled. Seven portable tests run by default; the private instruction check
needs `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`.

## Pose builder

`pose_builder.h` exposes `mu_pose_build`, authored C for the pose builder
`0x012b5064..0x012b58cb` (thiscall on the model object, eight stack arguments).
Per non-dummy bone it takes the quaternion and position keys from the
bone-track arrays for (prior action, prior frame) and (current action, integer
current frame). It interpolates with the current frame's fraction: slerp for
quaternions unless they compare equal within 0.001, linear for positions. It
writes the quaternion to a per-bone global table and composes the resulting
3x4 matrix with the root-matrix global or the parent's output slot. Frames
outside the key range reset to key 0 while keeping the fraction. Bone 0 can lock
its x/y position to the current action's first key. A special bone rebuilds
its quaternions from Euler angles adjusted by head angles. The API takes a set of
client address regions so the two globals stay at their client addresses
(`MU_POSE_BONE_QUATERNIONS`, `MU_POSE_ROOT_MATRIX`). An out-of-range access
returns a status; that is an authored convention.

The [finding](../../docs/research/client-pose-builder.md) records the inputs,
layouts and instruction comparison. The actual builder and all its client callees
run, seeded by the actual bone-track loop. Synthetic, direct-helper and installed
v12/v14/v15 cases match. Lerp and modulo-wrap controls fail. `libposebuilder`
links the builder, the bone-track loop and record-math with contraction
disabled. Eight portable tests run by default; the private instruction check
needs `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`.

## Model transform and animation tick

`skinning.h` exposes `mu_model_transform`, authored C for the model transform
`0x012b5bde..0x012b678d`. This is the client's CPU skinning: thiscall on the
model, twelve stack arguments. Each vertex is transformed by one bone matrix,
with no blending. A bone-scale global that is not exactly 1.0 selects a
rotate-scale-translate path, and a nonzero vertex scale prescales positions.
Translating applies the body scale and then adds the body origin. Normals are
rotated only. With the model's lighting flag, a clamped Lambert term against
fixed light directions goes to the light array and to a secondary global table.
The bounding box comes from the vertex bounds or from the arguments.
`mu_animation_tick` reconstructs the tick `0x012b4dd3`. It advances the frame,
sets the prior frame and action when the integer frame changes, and then wraps,
shifts or clamps.

The [finding](../../docs/research/client-skinning.md) records the inputs,
layouts, caller classification and the mesh draw's static GL order. Both routines
run against the actual instructions, together with the record-math vector
helpers. Installed models are chained through the actual bone-track loop and pose
builder. Synthetic and all installed v12/v14/v15 calls match, and four negative
controls fail. `libskinning` links the transform, the pose builder, the bone-track
loop and record-math with contraction disabled. Eleven portable tests run by
default; the private check needs `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`.

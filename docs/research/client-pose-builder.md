# Pose builder at 0x012b5064

CLIENT-POSE-BUILD-001 / issue #46 adds authored C for the pose builder
`0x012b5064..0x012b58cb` and its four direct math helpers. Unicorn executes the
actual builder with every client function it reaches and no stubs. The cases
are seeded by first running the actual bone-track loop
(`0x012b4225..0x012b4441`, [finding](client-bone-tracks.md)) on the same
model, so the builder reads that loop's real position, Euler and quaternion
arrays. The authored source matches 483 synthetic builder calls, 1,822 direct
helper calls and 47,833 calls on all 11,962 installed
v12/v14/v15 models the readers accept. Two negative controls fail: lerp in place of slerp, and a
modulo frame wrap. Live animation state, the renderer's use of the output and
native Windows behavior remain unverified.

## Identity

| Input | Bytes | SHA-256 |
|---|---:|---|
| `main.exe` (target identity) | | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | 4 | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |

Pinned bodies (start, exclusive end, instruction count from a Capstone linear
decode that lands exactly on the end, SHA-256 of the captured bytes):

| Body | Range | Instr. | SHA-256 |
|---|---|---:|---|
| Pose builder, `ret 0x20` | `0x012b5064..0x012b58ce` | 704 | `11a830ee49191265f3d7175caf1f9c11c45327ebd277562d30fd0e0671527d94` |
| Quaternion compare | `0x00cfec33..0x00cfec8d` | 33 | `6722b79afebb674465292e284a785c14c56f21307d69585b0d86998bd9b4dd9e` |
| Slerp | `0x00d00ca4..0x00d0104f` | 267 | `24c2020d5c829119c23ef5640567db8da50f33962fa09e959f4ab9f965127d0f` |
| Quaternion to matrix | `0x00d008bf..0x00d00ca4` | 316 | `5de131c3e991bde117771227db8f1c61e4b81bed3e9f37fb0d3831360e5bb713` |
| Angles to matrix | `0x00cff32a..0x00cff5b4` | 200 | `70ff218049521f6f14b62347ffb6bf937a8964023320f359aa1f1042dc075451` |
| Vector element accessor, `ret 4` | `0x00cfc922..0x00cfc936` | 9 | `0518ccd07aae2d4de135e2ab9c0b1c22e7898200e3c42fd1db23a397871043b5` |
| Vector data accessor | `0x00cfc94a..0x00cfc956` | 7 | `25992882b0f4cb017f9114855550dd8181349a42644f0517cc755246d09e132a` |
| fabs wrappers / CRT fabs | `0x0098a647`, `0x0098a6d2`, `0x01983660` | 9/14/11 | see validator |
| acos wrappers / CRT dispatch | `0x0099d513`, `0x0099d6d5`, `0x0198ae30` | 9/14/15 | see validator |
| sin / cos wrappers | `0x009681bd`, `0x009fa223` | 14/14 | see validator |
| Composition (PR #34), rotation (PR #38) | `0x00cff83e`, `0x00d00724` | 726/113 | as in those findings |

The validator also requires exactly these direct calls in the builder:
`0x00cfc922` at `0x012b50c8`, `0x012b50e6`, `0x012b5103`, `0x012b5824`,
`0x012b5846` and `0x012b5868`; rotation `0x00d00724` at `0x012b53c9` and
`0x012b53d8`; compare at `0x012b54fc`; slerp at `0x012b5526`; quaternion to
matrix at `0x012b55b5`; `0x00cfc94a` at `0x012b57ad`; angles to matrix at
`0x012b57b3`; composition `0x00cff83e` at `0x012b5895` and `0x012b58bc`. It
checks nine second-section constants: binary32 1.0 (`0x01a7dd48`), 57.29578
(`0x01a85c38`) and 0.017453292 (`0x01a7fd6c`), and binary64 0.001, 1e-8,
binary32 pi widened, 2.0, 1.0 and 0.5. Method: Capstone 5.0.9 (module string
`5.0.7`) and Unicorn 2.1.4. A small constant-folding listing was used to read
the index arithmetic; no REA run was needed. The pseudocode below restates the
observed instructions and was checked by execution.

## Calling convention and inputs

The builder is thiscall: ECX is the model object and eight 32-bit stack
arguments are popped by `ret 0x20`. It preserves EBX, ESI, EDI and EBP. Names
below are investigator labels.

| Argument | Use |
|---|---|
| `[esp+4]` output | client address of 0x30-byte row-major 3x4 matrices, one per bone index |
| `[esp+8]` frame | binary32 current frame; integer part and fraction both used |
| `[esp+0xc]` prior frame | binary32, truncated to an integer key |
| `[esp+0x10]` prior action | low 16 bits; the builder writes 0 into this slot's low half when it is out of range |
| `[esp+0x14]` angles | three binary32 body angles in degrees, copied to model `+0x84` |
| `[esp+0x18]` head angles | two binary32 values in degrees, used only by the special bone |
| `[esp+0x1c]` keep root | low byte; nonzero keeps the current root matrix global |
| `[esp+0x20]` translate | low byte; scales and translates a rebuilt root matrix |

Model fields, in addition to the loader layout (`+0x22` bones, `+0x26` actions,
`+0x2c` bones array, `+0x30` actions array):

| Offset | Field | Access |
|---|---|---|
| `+0x60` | int32 special ("head") bone index | read |
| `+0x74` | binary32 root scale | read when translating |
| `+0x78..+0x83` | three binary32 root translations, raw copies | read when translating |
| `+0x84..+0x8f` | three binary32 body angles | written from the argument, read by angles-to-matrix |
| `+0x90` | binary32 height added to the locked root z | read |
| `+0xa8` | u16 current action | read; reset to 0 when >= action count |
| `+0xac` | binary32 current frame | written, then reread |
| `+0xb4` | int16 integer current frame | written, clamped, reread |
| action `+0xa` | u8 lock-positions flag (written by the action loop `0x012b4149`) | read for bone 0 |

Two globals in the uncaptured third image section are used:
`0x075a90d8 + 16*i`, a per-bone quaternion table, and `0x078965ac`, a single
3x4 root matrix. The table's next neighbor, `0x075a9d58`, is the per-bone byte
table of the [hierarchy finding](model-hierarchy.md). A 200-entry capacity is
an inference from that 3,200-byte distance; the builder does not bound the
index.

## Observed operation

```
if (int16)model[+0x26] <= 0: return
if (u16)prior_action >= actions: low16(prior_action) = 0
if (u16)model[+0xa8] >= actions: model[+0xa8] = 0
model[+0x84..] = angles[0..2]                       # raw dwords, in order
model[+0xac] = frame
model[+0xb4] = (int16)cvttss2si(frame)
t  = model[+0xac] - (float)(int16)model[+0xb4]       # binary32; before clamps
t1 = 1.0f - t
pf = cvttss2si(prior_frame)
if actions > 0:                                      # reread
    if pf < 0: pf = 0
    if (int16)model[+0xb4] < 0: model[+0xb4] = 0
    if pf >= keys[prior_action]: pf = 0
    if (int16)model[+0xb4] >= keys[model[+0xa8]]: model[+0xb4] = 0
for i = 0; i < (int16)model[+0x22]; i++:             # reread every iteration
    bone = model[+0x2c] + i*0x8c
    if (int8)bone[+0x22]: continue                   # dummy: slots untouched
    e1 = bone[+0x24] + prior_action*12               # prior track entry
    e2 = bone[+0x24] + model[+0xa8]*12               # current track entry
    cf = (int16)model[+0xb4]                         # reread at each use
    if i == (int32)model[+0x60]:
        A1 = e1.euler[pf]; A2 = e2.euler[cf]
        hx = head[0] / 57.29578f; hy = head[1] / 57.29578f
        A1.x -= hx; A2.x -= hx; A1.z -= hy; A2.z -= hy
        q1 = rotation(A1); q2 = rotation(A2)          # 0x00d00724
    else:
        q1 = e1.quat[pf]; q2 = e2.quat[cf]            # raw copies
    Q = table + 16*i
    if compare(q1, q2) == 0: slerp(q1, q2, t, Q) else Q = q1
    M = quaternion_matrix(Q)                         # rotation part only
    P1 = e1.pos[pf]; P2 = e2.pos[cf]
    if i == 0 and (lock[prior_action] or lock[model[+0xa8]]):
        M.x = e2.pos[0].x; M.y = e2.pos[0].y          # raw, key 0
        M.z = (P1.z*t1 + P2.z*t) + model[+0x90]
    else:
        M.r = P1.r*t1 + P2.r*t  for r = x, y, z
    if (int16)bone[+0x20] == -1:
        if !keep_root:
            root = angle_matrix(model[+0x84])        # global 0x078965ac
            if translate:
                root[r][c] *= model[+0x74] for r, c < 3
                root[r][3] = model[+0x78 + 4r]        # raw
        concat(root, M, output + i*0x30)
    else:
        concat(output + parent*0x30, M, output + i*0x30)
```

Field reads, rereads and the order of writes follow the instructions; the
authored C keeps them. All binary32 operations are scalar SSE (`MULSS`,
`ADDSS`, `SUBSS`, `DIVSS`), each rounded separately.

### Interpolation scheme

* The builder interpolates between two arbitrary keys: q1/p1 from (prior
  action, prior frame) and q2/p2 from (current action, integer current frame),
  with factor t, the current frame's fraction. It does not step to "frame+1"
  itself; the caller's choice of prior frame and action is not traced.
* t is computed before any clamp. A frame at or beyond the key count resets the
  key to 0 but keeps its fraction, e.g. frame 4.25 with four keys blends prior
  with key 0 at t = 0.25. There is no modulo wrap and no clamp to the last key.
  Negative frames truncate toward zero, so frame -0.25 gives key 0 and t = -0.25.
  Prior frames outside 0..keys-1 also reset to 0.
* The int16 store wraps large frames. Frame 32768.5 stores -32768, which then
  resets to key 0, while t is 65536.5.
* Quaternions: slerp unless compare finds all four components within 0.001,
  then q1 is copied. Positions: always linear, `p1*(1-t) + p2*t`. No
  quaternion is normalized, before or after interpolation.
* Zero-key actions: the clamps force key 0, so the builder reads 12 or 16 bytes
  from the loader's 1-byte blocks, i.e. uninitialized heap bytes. The
  characterization case stops on that undefined read.

### Hierarchy walk

Bones run in index order. A root (`parent == -1`) composes with the root-matrix
global. Every other bone composes with `output + parent*0x30` as it is at that
moment. A parent that is dummy, later in the array, the bone itself or out of
range is not checked. The composition then reads prior caller contents. Locked
root positions apply only to bone index 0. Bone 0 being dummy disables the lock.
The root matrix is rebuilt for every root bone unless keep root is set.

### Helpers

* Compare `0x00cfec33(a, b)`: for each component the binary32 difference goes
  through the client fabs chain and is compared as binary64 with `> 0.001`.
  A NaN difference counts as equal. binary32 0.001 itself differs.
* Slerp `0x00d00ca4(p, q, t, out)`: binary32 sums a = Σ(p−q)², b = Σ(p+q)²; if
  a > b the components of q are negated in place, with sign-bit XOR. cosom is
  the binary32 dot product. If `1 + cosom > 1e-8` and `1 − cosom > 1e-8`
  (binary64), it computes omega = acos(cosom) and sinom = sin(omega), with
  scales sin((1−t)·omega)/sinom and sin(t·omega)/sinom. If only the first test
  holds, the scales are 1−t and t. Otherwise, with q nearly opposite p, out =
  (−p1, p0, −p3, p2) and its first three components blend with sin((1−t)·π/2)
  and sin(t·π/2), using binary32 π widened. Each trig result is rounded to binary32.
* Quaternion to matrix `0x00d008bf(q, m)`: nine binary64 expressions of
  widened components, each rounded once, e.g. m00 = (1 − (2y)y) − (2z)z;
  written column by column; column 3 untouched.
* Angles to matrix `0x00cff32a(a, m)`: each degree angle times binary32
  0.017453292, sin/cos of a2, a1, a0 rounded to binary32; Rz(a2)·Ry(a1)·Rx(a0)
  with binary32 products; translations set to +0.

## Authored source

`mu_pose_build(memory, model, &arguments, &globals)` in
`reconstructed/model-codec/pose_builder.{c,h}` reproduces the builder over a
set of flat little-endian views of 32-bit client address ranges, so the two
globals can stay at their client addresses. It writes the clamped prior action
back into `arguments`. The helpers are in record-math as
`mu_quaternion_compare`, `mu_quaternion_slerp[_using]`, `mu_quaternion_matrix`
and `mu_angle_matrix[_using]`. Composition and rotation reuse
`mu_pose_concat` and `mu_rotation_quaternion`. sin, cos and acos come from the
host libm, the same substitution as [the rotation finding](client-rotation.md).
An access outside every region returns `MU_POSE_OUTSIDE_MEMORY`; that is not a
client behavior. `libposebuilder` links the builder, the bone-track loop and
record-math.

## Comparison method

`scripts/validate_pose_builder.py` reuses the bone-track validator's pinned
inputs, its synthetic and installed case builders, and its emulator. For each
case it first runs the actual bone-track loop and requires a clean pass. It
also requires the authored bone-track C to give the same window. That window
and its defined-byte mask seed the builder call. A second Unicorn instance maps
the full text, the full second section, only the four flag bytes, the stack,
the case window and the two global regions. It calls `0x012b5064` from a
sentinel return address with x87 `0x027f`, MXCSR `0x1f80` and poisoned XMM.

Modeled, stated explicitly:

* The quaternion table and root matrix, uncaptured. Both start undefined. A
  keep-root case supplies a declared synthetic root matrix.
* Caller memory: declared finite matrices across the output buffer and
  1 KiB margins (the "prior pose"); the angle vectors; model fields `+0x60`,
  `+0x74..+0x83`, `+0x90`, `+0xa8`; action lock bytes. Installed models use
  their parsed lock flags.

Nothing in the client is stubbed and the builder reaches no import. A read of an
undefined byte, of any byte outside the flag in its page, of an unmapped
address, or of caller stack outside the eight arguments stops a case. The only
permitted argument write is the prior-action low half. A pass requires:

* return to the sentinel with ESP + 0x24;
* EBX, ESI, EDI and EBP preserved; DF clear;
* FPCW and MXCSR control unchanged; x87 TOP balanced;
* byte-identical window, quaternion table region (64 KiB) and root region
  (4 KiB) from the authored C;
* the same prior-action slot, with other argument slots unchanged;
* agreement with an independent Python model.

Reads of output bytes not written earlier in the same call are counted as
prior-pose reads.

The four helpers are also called directly (cdecl) with the same boundaries and
compared with the C and the Python model, including the in-place negation of q.

## Results

Direct helper calls, all matching: slerp 910 (745 spherical, 164 linear,
1 opposite, 388 with q negated), compare 304, quaternion to matrix 302, angles
to matrix 306.

Synthetic builder calls, 483, all matching, over 2,102 bone evaluations:

| Group | Calls |
|---|---:|
| No actions (early return; nothing written) | 1 |
| Frame boundaries: 20 frames (0, fractions, keys−1, keys, beyond, negative, 32767.5, 1e-30) × 6 prior frames | 120 |
| Same-action consecutive keys | 15 |
| Action clamps, junk upper argument bits, current action 0x8000/0xffff | 30 |
| Keep-root/translate low-byte flags | 16 |
| Lock flags on prior/current action; dummy bone 0 | 16 |
| Special bone, head angles, bone 0 with lock, out-of-range index | 18 |
| Dummy, forward, self, −2 and later-index parents | 3 |
| 48-bone chain; 31-bone binary tree with two actions | 5 |
| Euler angles 2π apart (q negated), compare threshold around 0.001 | 41 |
| Injected non-loader quaternions: linear and opposite slerp branches | 33 |
| Zero-key actions with declared block contents | 2 |
| Angles argument aliasing model `+0x84` | 1 |
| int16 frame wrap (t = 65536.5, equal quaternions) | 2 |
| Random layouts (1-4 actions, 1-13 bones, dummies, locks, flags) | 180 |

Every builder branch was reached, including the special-bone Euler path (103),
locked root position (55), root scale/translate (142), each frame and action
clamp, the dummy skip (208) and all three slerp branches (spherical 1,421,
linear 25, opposite 12). Prior-pose reads occur in 72 calls: all three
dummy/forward/self-parent calls and 69 random layouts with a dummy parent.

Installed models are decoded and parsed by the existing readers, as in the
bone-track comparison. Each compared model gets up to four calls from
deterministic per-file parameters: same action, two-action blend, frame at or
past the end, and an exact integer frame (equal quaternions, copy path). Body
and head angles, special bone, flags, scale, translation and height are random.

| Version | Files | Compared | Calls | Matches | Bone evaluations |
|---|---:|---:|---:|---:|---:|
| v12 | 180 | 180 | 708 | 708 | 2,128 |
| v14 | 216 | 216 | 864 | 864 | 6,004 |
| v15 | 11,583 | 11,566 | 46,261 | 46,261 | 785,615 |

Bone evaluations count bones per call, dummies included. The 17 v15 files the
strict reader rejects were not run, as in the bone-track comparison. Five
models without actions take the early return. No compared model has a zero-key
action or more than 200 bones (the maximum is exactly 200). No installed call read a prior output
slot: every parent precedes its child and is non-dummy in the accepted files.
The installed calls exercise slerp 96,538 times spherically and 796 times
linearly. The linear calls fit keys whose quaternions are near negatives, as
with Euler keys a full turn apart (inference; not classified per call). They also reach the copy path
645,994 times, the special bone 23,321 times, the locked root 622 times and the
frame resets 12,036 (prior) and 5,952 (current) times; there are no failures.
The full run took 4 min 3 s on four niced workers. Report
`comparison-v12-v14-v15.json`, SHA-256
`d93ceb8e33ce9e268c68f4d37fe69cc378f0251ce48e6bcf9faa6b9ae0de0615`, corpus
digest `de62cb0f…edba4`, authored library `2be7f84e…4372`.

Trig substitution. At each return of the client's binary64 sin, cos and acos
helpers the harness reads ST0 and compares it with host libm on the same argument:

| Helper | Calls (synthetic + helpers + installed) | binary64 differs | binary32 differs | Max ULPs |
|---|---:|---:|---:|---:|
| acos | 1,421 + 745 + 96,538 | 188 + 108 + 5,919 | 0 | 1 |
| sin | 6,675 + 3,155 + 636,570 | 149 + 113 + 3,522 | 0 | 1 |
| cos | 2,388 + 918 + 346,956 | 15 + 29 + 1,025 | 0 | 1 |

All agree after binary32 rounding, which is the only form the builder uses.
As in the rotation finding this is shown only for the tested arguments on this
host; no midpoint scan was run for acos.

Negative controls (Python variants, required to differ): component-wise lerp of
the quaternions without the compare differs in 364 of 483 synthetic calls; a
modulo frame wrap differs in 60. The portable suite repeats both against the
authored C. A mutation that compared the fabs result in binary32 instead of
binary64 failed three direct compare cases (not kept).

Characterization (never counted as matches):

| Input | Emulator | Authored C |
|---|---|---|
| Zero-key action, block contents undefined | stops at the undefined read by `0x012b547d` (q2 from a 1-byte block) | completes, reading the same bytes |
| Frame 40000.25 (t = 65536.25) | sin argument beyond the SSE2 domain; x87 fallback stops at uncaptured `0x0bdcfbc8` | completes with libm (not claimed) |
| Parent index 0x7fff | unmapped read at `0x00cff860` in composition | `MU_POSE_OUTSIDE_MEMORY` |

## Unresolved

* Live state: the caller's prior frame/action choice, the previous contents of
  the output buffer and root matrix, live FP state and the real values of the
  model fields the loader does not write. The builder's callers (314 raw
  call candidates) are not traced.
* Renderer use of the output matrices and of the quaternion table.
* The quaternion table capacity and what lies past it; models with more than
  200 bones write past `0x075a9d58` if that inference holds.
* Uninitialized heap bytes read for zero-key actions; NaN/infinity propagation
  and NaN payloads (the comparisons stay finite; arm64 and x86 differ in default
  NaN); trig arguments beyond the SSE2 domain; the client trig algorithms.
* The second builder `0x012bcffb`, the 17 reader-rejected v15 files and native
  Windows behavior.

## Reproduce

```sh
make -C reconstructed/model-codec
./tools/python/bin/python scripts/validate_pose_builder.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --flag evidence/trig-state-15/captures/late/math-dispatch-flag.bin \
  --feature evidence/x86-math-capture-09/cpu-features.bin \
  --game-root "$MU_GAME_ROOT" --versions 12,14,15 --workers 4 \
  --output /new/local/pose-builder.json
```

Portable tests: eight builder checks in `reconstructed/model-codec/test_pose_builder.py`
(slerp result, frame reset with kept fraction, action clamps and argument slot,
dummy slots and prior-slot composition, locked root, Python-model agreement with
both negative controls, outside-memory status, pinned-text refusal) and four
helper checks in `reconstructed/record-math/test_pose_helpers.py`. The ninth
builder check is private: with `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`
it runs the validator on the synthetic cases and installed v12/v14 models, and
fails if inputs are missing. `MU_CLIENT_TEXT`, `MU_IMAGE_DATA`, `MU_TRIG_FLAG`
and `MU_MATH_DATA` override the input paths. The full report, its log, the
listings and test logs are ignored under `evidence/client-pose-builder/` in
the pose-builder worktree.

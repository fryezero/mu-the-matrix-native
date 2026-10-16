# BMD bone-track loop at 0x012b4225..0x012b4441

CLIENT-BONE-TRACK-001 / issue #40 adds authored C for the bone loop inside model
reader `0x012b3812`, including its per-action track section
`0x012b42ae..0x012b4441`. Unicorn executes the actual loop with the client's
memcpy, its operator new/malloc chain, rotation helper `0x00d00724` and the
actual trigonometric helpers, with no stubs for client code. The authored source
matches 342 synthetic cases and every installed v12, v14 and v15 model the
existing readers accept: 180 v12, 216 v14 and 11,566 v15 files, with 4,759,146 rotation calls. A negative control fails as required.
Original allocation failure, live FP state, rendering and native Windows
behavior remain unverified.

## Identity

| Input | Bytes | SHA-256 |
|---|---:|---|
| `main.exe` (target identity) | | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | 4 | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |
| memcpy feature word `0x01cf6618` (math capture09, value `0x2f`) | 4 | `bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9` |

The validator pins these captured bodies (start, exclusive end, SHA-256):

| Body | Range | SHA-256 |
|---|---|---|
| Bone loop, 190 instructions | `0x012b4225..0x012b4441` (540 bytes) | `f64d0af94eadadc0a2b603d02d64afe9894a5d43f1a8842baf4f6fdeb95d835c` |
| memcpy, 429 instructions | `0x0194c200..0x0194c774` | `a54559a3343e0eba7db605526a5e3605108e176e3fbc590a2439578fb4df3936` |
| operator new thunk | `0x0191bab9..0x0191bac2` | `8bb78a0e58a9fce635c1116508eb5fc00f0a0b92d2d08abd06f1dc6c97b3de4c` |
| new retry loop | `0x0191ba7b..0x0191ba9c` | `6e821d9b924a3ea12912c009fff2838c20afcff60ec472f3e5702e60528b4a84` |
| malloc thunk | `0x01983110..0x0198311b` | `8b641bf9120fd530c5eb92f525a94c7d6676eb4346c08f12cde44f35ab45b9d4` |
| malloc | `0x019a4da0..0x019a4df1` | `8f5fc5d10bcd43802516fcb240b671f03663a02f68e100c1dd4f396d82f4a204` |
| Rotation helper | `0x00d00724..0x00d008bf` | `1d585a53f706aed8dd37de105b739b739905065deb41350a02fe83d9153e53a2` |

Method: Capstone 5.0.9 (module string `5.0.7`) linear decode, which must land
exactly on `0x012b4441`. The validator also requires exactly these direct calls
in the loop. memcpy is called at `0x012b4282`, `0x012b43cf` and `0x012b43f0`.
`0x0191bab9` is called at `0x012b42be`, `0x012b4345`, `0x012b4376` and
`0x012b43a8`. `0x00d00724` is called at `0x012b442e`. Unicorn 2.1.4 executes
every instruction. No REA run was needed. The pseudocode below restates the
observed instructions and was checked by execution.

## Observed operation

The loop runs inside the reader's frame. It takes three frame inputs,
`[ebp-0x14]` model object, `[ebp-0x18]` decoded stream base and `[ebp-0x10]`
signed stream offset. The emulator's frame hooks show that it reads no other
caller slot before writing it. Three `AND [slot], 0` instructions read old
values whose result is discarded. The loop writes `[ebp-0x10]` (final offset)
and the scratch slots `-0x20`, `-0x24`, `-0x2c`, `-0x34`, `-0x38`, `-0x3c`,
`-0x44` and `-0x114..-0x120`.

```
for i = 0; i < (int16)model[+0x22]; i++:            # reread every iteration
    bone = model[+0x2c] + i*0x8c                     # reread every iteration
    bone[+0x22] = stream[off++]                      # dummy byte, stored first
    if (int8)bone[+0x22] != 0: continue              # tested from the record
    memcpy(bone+0x00, stream+off, 32); off += 32     # name
    bone[+0x20] = (u16)stream[off]; off += 2         # parent, raw
    bone[+0x24] = new(sat((u32)(int16)model[+0x26] * 12))
    for a = 0; a < (int16)model[+0x26]; a++:         # reread every iteration
        e      = bone[+0x24] + a*12
        copied = (int16)actions[a].keys * 12          # first read, signed IMUL
        keys   = (int16)actions[a].keys               # second read
        e[+0] = new(sat(sat(keys*3)*4))               # positions
        e[+4] = new(sat(sat(keys*3)*4))               # Euler rotations
        e[+8] = new(sat(sat(keys*4)*4))               # quaternions
        memcpy(e[+0], stream+off, copied); off += copied
        memcpy(e[+4], stream+off, copied); off += copied
        for k = 0; k < keys; k++:
            rotation(e[+4] + k*12, e[+8] + k*16)      # 0x00d00724(input, output)
```

`actions` is `model[+0x30]`, a 16-byte-stride array with the int16 key count at
`+8`. `sat` is the `MUL` / `CMOVB -1` pair, an unsigned 32-bit product saturated
to `0xffffffff` on carry. `e[+8]` and `e[+4]` are reread for every key.

### Output layouts

| Record | Offset | Field | Written by this loop |
|---|---|---|---|
| bone, stride `0x8c` | `+0x00` | 32-byte name, raw | non-dummy only |
| | `+0x20` | int16 parent, raw (no range check) | non-dummy only |
| | `+0x22` | int8 dummy flag (any nonzero means dummy) | always |
| | `+0x23` | not written | never |
| | `+0x24` | u32 pointer to the track array | non-dummy only |
| | `+0x28..+0x8b` | not written here | never |
| track array, stride 12 per action | `+0` | positions, `keys` x 3 binary32 | yes |
| | `+4` | Euler angles a0,a1,a2, `keys` x 3 binary32 | yes |
| | `+8` | quaternions x,y,z,w, `keys` x 4 binary32 | yes |

Positions and rotations are copied bitwise from the stream. The emulator copies
NaN, infinity and subnormal patterns unchanged. Each quaternion is
`mu_rotation_quaternion` of the matching rotation, read back from the newly
copied heap array rather than the stream. Byte `+0x28` is written later by
`0x012b47fd` ([hierarchy finding](model-hierarchy.md)).

### Allocation behavior

Pre-allocated by earlier reader code: the model object, the action array
(`max(actions,1)*16` bytes, keys at `+8` written by the action loop
`0x012b4149..0x012b4220`) and the bone array (`max(bones,1)*0x8c` bytes,
uninitialized). The loop allocates everything else through `0x0191bab9`.
Per non-dummy bone it makes `1 + 3*actions` calls, in the order shown, all
before the corresponding copies.

The allocator chain is MSVC-style operator new and malloc. `0x0191ba7b` loops on
malloc `0x019a4da0`. malloc rejects requests above `0xffffffe0` and maps 0 to 1.
It then calls the IAT slot `0x01a7c5c8` with `(heap handle [0x0bdcfc10], 0,
size)`. The slot value `0x7bc275e0` is in Wine's ntdll range. The HeapAlloc
reading is an inference. Flags 0 means no zero fill. On a null result, malloc
consults `0x019a3360` and `0x0199c4c0` (new-mode and new-handler state). The
loop never checks for a null pointer. The emulator confirms that it reads no
allocated byte before writing it. Zero actions or zero keys still allocate, as
1-byte HeapAlloc blocks. Each block keeps its uninitialized contents and is
stored as a valid pointer.

Bones and actions with negative counts run zero iterations. A negative key
count, or a negative action count on a non-dummy bone, saturates the request to
`0xffffffff`. malloc then refuses it.

The loop has no bounds check against the decoded stream length, and none on
parent values, dummy flags or counts.

## Authored source

`mu_bone_tracks_read(image, model, stream, &offset, allocate, context)` in
`reconstructed/model-codec/bone_tracks.c` reproduces the loop over a flat
little-endian view of one 32-bit client address window, because the client
records hold 32-bit pointers. It rereads every field the original rereads and
uses memmove semantics for the copies. It calls the allocator callback with the
same operator-new request sizes, in the same order. Quaternions come from
`mu_rotation_quaternion` (record-math, PR #38). That function uses host libm in
place of the client trig helpers; its domain is described in
[the rotation finding](client-rotation.md). A null allocator result returns
`MU_BONE_TRACKS_ALLOCATION_FAILED`. An access outside the image returns
`MU_BONE_TRACKS_OUTSIDE_IMAGE`. Neither status is a client behavior.

## Comparison method

`scripts/validate_bone_tracks.py` maps the full text, the full second section,
and four partially captured pages. The flag, the captured feature word and two
synthetic globals are readable only at their exact bytes. Everything else is
unmapped. It starts at `0x012b4225` inside a synthetic reader frame
(EBP-0x470, x87 `0x027f`, MXCSR `0x1f80`, poisoned XMM) and stops at
`0x012b4441`.

Modeled boundaries, stated explicitly:

* HeapAlloc import. An authored two-instruction stub at `0x7bc275e0` returns a
  deterministic, 16-byte-aligned bump allocation filled with poison bytes. Its
  hook requires return address `0x019a4ddb`, the heap token and flags 0. The
  authored-C callback applies malloc's observed adjustments to the same
  allocator. The test then compares the two size logs.
* Heap handle `0x0bdcfc10` (uncaptured). A synthetic token readable only by the
  malloc instruction at `0x019a4dcf`, and checked when it reaches the import.
* memcpy feature word `0x0bdcb284` (uncaptured). memcpy reads bit 1 to select
  `rep movsb` for copies of at least 128 bytes, and bit 0 to select its SSE2
  path. Synthetic cases run under values 0, 1 and 2. Installed models cycle
  through them by file index. The captured word `0x01cf6618` (bit 1 set)
  selects the 32..127-byte SSE2 path.

Window bytes carry a defined-byte mask: model fields, action-entry fields and
the stream are defined, and every write defines bytes. A read of an undefined
byte stops the case. The one exception is a memcpy read inside the 16-byte
aligned envelope of its current source span, which is counted. No synthetic
case triggers one. In installed data, memcpy's `palignr` path (synthetic
feature value 1) loads aligned blocks up to 12 bytes past the end of the final
track copy, which is the end of the decoded payload. This happened in 4 of 396
v12/v14 files under value 1 (`Data/Object113/Object119.bmd`, `Object121`,
`Object122`, `Object67`) and once in the full corpus run. The values are unused,
as the window comparison shows. The real client therefore reads past its decoded
buffer within the same 16-byte block. A pass requires all of the following:

* arrival at `0x012b4441`;
* ESP/EBP restored and EBX/ESI/EDI preserved;
* DF clear;
* FPCW and MXCSR control unchanged and the x87 stack balanced;
* only declared frame inputs read and only declared frame scratch written;
* a byte-identical whole window from authored C;
* the same final offset;
* the same allocation sizes;
* agreement with an independent Python model of the loop.

## Results

Synthetic, 114 cases x 3 synthetic feature values = 342 comparisons, all
matching:

| Category | Cases |
|---|---:|
| Zero bones, zero actions, zero keys, zero/nonzero keys mixed, all dummy (flags 1, `0x80`, `0xff`) | 5 |
| Mixed dummy flags 1/2/`0x7f`; raw parents -1, 0, 5, `0x7fff`, -32768, -2; full 32-byte name | 10 |
| Key counts 1..300 at five stream alignments, random prefixes (memcpy size thresholds 32/128) | 45 |
| 2,000 keys; 11 actions x 4 bones; 60 bones with dummies | 3 |
| Random layouts (0-4 actions, 0-11 keys, 0-7 bones, random flags/parents/alignments) | 40 |
| Edge angles (±0, subnormal, π multiples, 65536, 180223) with raw NaN/inf/subnormal positions | 1 |
| Negative bone count; bone count below record count | 2 |
| Overlap: bone array over unread stream (5 offsets, no actions); track data overwritten (2); action array inside a bone name | 8 |

Those comparisons perform 5,376 allocations, 19,221 rotations and 3,810 memcpy calls.
All eight memcpy paths are reached: small tail, 32..127 SSE2, `rep movsb`,
coaligned SSE2, `palignr`, dword forward, dword with unaligned source, and
backward (overlap). Exact counts are in the local report.

Installed models are decoded and parsed by `model-recovery/bmd_encrypted.py`.
The decoded payload digest must equal the reader's. Each model's stream is its
decoded payload. The start offset is the reader's first bone offset, and the
model object carries the reader's counts and key counts. The test also checks
the output against the reader: dummy flags, parents and bitwise positions and
rotations must agree, and the final offset must equal the reader's parsed end.

| Version | Files | Compared | Matches | Keys (rotation calls) |
|---|---:|---:|---:|---:|
| v12 | 180 | 180 | 180 | 3,802 |
| v14 | 216 | 216 | 216 | 15,562 |
| v15 | 11,583 | 11,566 | 11,566 | 4,739,782 |

The 17 v15 files rejected by the strict reader are listed in the report and were not run. The largest quaternion difference from an independent
double-precision Hamilton product is 1.59e-7. Altogether 11,962 installed models use 1,624,365
allocations and 1,144,869 memcpy calls. The full run took 2 min 17 s on nine workers.

Negative control: a Python variant that skips allocation for zero-byte requests
and stores a null pointer differs in 57 of 342 synthetic comparisons and is
required to differ. The portable suite repeats this against the authored C.

Characterization (never counted as matches):

| Input | Emulator | Authored C |
|---|---|---|
| Negative key count | After the first allocation, malloc refuses `0xffffffff` and stops at an unmapped TLS/errno read (`0x0191d647` reads address 0) | status 1, requests `[12, 0xffffffff]`, same window |
| Negative action count | Same stop before any HeapAlloc | status 1, same window |
| HeapAlloc returns null on the 2nd call | Stops at uncaptured `0x0bdcf8f0` read by `0x019a3360` (new-mode state) | status 1, same window |
| Rotation angle 1e6 | Enters the x87 trig fallback, which stops at uncaptured `0x0bdcfbc8` | completes with libm (not claimed) |

## Unresolved

* Client allocation failure: the new-handler/new-mode state and the bad_alloc
  throw are uncaptured. The C failure status is an authored convention.
* Actual HeapAlloc block placement and contents, and the real heap handle.
  Blocks are uninitialized, so 1-byte blocks for empty arrays hold unknown bytes.
* The real value of `0x0bdcb284`. All three memcpy selections give equal
  results on the tested cases.
* Stream over-read: the loop trusts counts. Truncated or inconsistent data reads
  past the decoded buffer. The authored C stops at the image bound instead.
* Angles outside the SSE2 trig domain, live caller FP state, the client SSE2
  sine/cosine algorithms (libm is substituted) and native Windows behavior.
* The 17 v15 files the strict reader rejects were not run through the loop.
  Neither was the sibling plaintext reader `0x012b2e81` (bone loop
  `0x012b35c7..0x012b37e3`, used for v10).
* Pose-builder use of these arrays (`0x012b5064`, `0x012bcffb`) is not covered.

## Reproduce

```sh
make -C reconstructed/model-codec
./tools/python/bin/python scripts/validate_bone_tracks.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --flag evidence/trig-state-15/captures/late/math-dispatch-flag.bin \
  --feature evidence/x86-math-capture-09/cpu-features.bin \
  --game-root "$MU_GAME_ROOT" --versions 12,14,15 --workers 9 \
  --output /new/local/bone-tracks.json
```

Seven portable tests check the layout, the allocation order, signed counts,
failure statuses, the convention, the Python-model agreement and the negative
control. An eighth is private: with `MU_RECOVERY_INTEGRATION=1` and
`MU_GAME_ROOT` set, it runs the validator on the synthetic cases and on
installed v12/v14 models. Integration fails if those inputs are missing.
`MU_CLIENT_TEXT`, `MU_IMAGE_DATA`, `MU_TRIG_FLAG` and `MU_MATH_DATA` override
the input paths. The full v15 report and log are kept, ignored, under
`evidence/client-bone-tracks/` in the bone-tracks worktree.

# Rotation conversion at 0x00d00724

CLIENT-ROTATION-001 / issue #37 adds authored C for the selected hierarchy
rotation helper. The actual client body, its two float wrappers and the actual
trigonometric helpers execute under emulation without stubs. The authored
source matches 8,012 controlled synthetic cases bitwise under flag value 1,
x87 control `0x027f` and MXCSR `0x1f80`. Live animation inputs, native Windows
FP state and exceptional-value behavior remain unverified.

## Identity and source link

Original executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Restored text at `0x00401000`, 23,572,480 bytes, has SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The helper spans `0x00d00724..0x00d008be` inclusive, 411 bytes, capture offset
`0x008ff724`, body SHA-256
`1d585a53f706aed8dd37de105b739b739905065deb41350a02fe83d9153e53a2`.
REA evidence `ev_ab1d111d96e988e1db29bd7973e3c4018cb25b075d45fea18250bb52da7eb593`
is described in [the dispatch-state finding](client-trig-state.md).

The verified second image section (base `0x01a7c000`, 2,557,764 bytes, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`) supplies
the binary64 scale 0.5 at `0x01a7de98` and the trig tables. The four-byte flag
at `0x0bdd1cc8` has digest
`67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` and value 1.

The validator linearly decodes four bounded caller ranges and confirms that
`0x012b442e` (BMD bone-track loop), `0x012b37d0` (sibling reader loop),
`0x012b53c9`, `0x012b53d8` (pose builder `0x012b5064`) and `0x012bd130`
(builder `0x012bcffb`) are direct calls to this helper. A raw E8 search also
finds `0x010a80a8`, whose surrounding function was not decoded; it remains a
candidate. Every decoded caller pushes output then input pointers and pops
both after return, consistent with cdecl.

## Observed operation

Observation from Capstone and the instruction comparison: the helper takes
two stack arguments, input then output. It reads input float 2, then 1, then 0.
Each is widened with CVTSS2SD, multiplied by the captured binary64 0.5 and
narrowed with CVTSD2SS. For each half angle h it calls `0x009681bd` and then
`0x009fa223`. Those 31-byte wrappers widen h to binary64, call `0x01985700`
or `0x0198c4d0`, and FSTP the x87 return to binary32. Zero input gives zero
and one from those helpers, so they are sine and cosine respectively.

With s[i], c[i] for input index i, the four MULSS chains and stores are:

| Offset | Value, each product rounded to binary32 left to right |
|---|---|
| 0 | s0·c1·c2 − c0·s1·s2 |
| 4 | c0·s1·c2 + s0·c1·s2 |
| 8 | c0·c1·s2 − s0·s1·c2 |
| 12 | c0·c1·c2 + s0·s1·s2 |

This is the x,y,z,w quaternion of R = Rz(a2)·Ry(a1)·Rx(a0), the common ZYX
Euler convention. The angle units and whether the original authors called it
a quaternion are inferences; analytic portable tests confirm the convention
against an independent double-precision Hamilton product. All three input
reads precede the first store, so in-place conversion is equivalent.

## Trigonometric dispatch observed under emulation

Both trig entries jump to the x87 fallback (`0x019997cf` FSIN,
`0x019996df` FCOS) when the flag is zero, when MXCSR & `0x7f80` differs from
`0x1f80`, or when x87 control & `0x7f` differs from `0x7f`. Otherwise they jump to SSE2
paths `0x019a72f8`/`0x019acd58`. x87 precision/rounding control and MXCSR DAZ/FZ bits
are not part of that test. The SSE2 entries handle binary64 arguments whose sign-cleared high
16 bits are in `0x3030..0x40f5`; zero/tiny arguments take a short path and
larger values jump to the x87 fallback. Because the helper halves its
binary32 inputs, the SSE2 domain is |angle| < 180,224.

Every compared case stayed on SSE2 paths: 20,916 main-path calls each for sine
and cosine and 3,120 zero-path calls each. The SSE2 tiny path is unreachable
from binary32 halves other than zero. Two dispatch probes with MXCSR RZ
(`0x7f80`) or x87 control `0x027e` entered the FSIN fallback, which then reads
uncaptured `0x0bdcfbc8`; both stopped as required. Reads during compared cases
touched 291 distinct data addresses from `0x01a7de98` up to `0x01bc2290`,
all inside the verified second section.

## Authored source

`mu_rotation_quaternion(angles, quaternion)` in `reconstructed/record-math/`
reproduces the half-angle rounding, call order, binary32 products and store
order. Contraction is disabled and intermediates use volatile binary32 storage.
Sine and cosine come from the host libm, rounded to binary32. This is a
substitute for the client helpers, not a reconstruction of their algorithm.
`mu_rotation_quaternion_using` accepts caller sine/cosine callbacks invoked in
the original order sin(h2), cos(h2), sin(h1), cos(h1), sin(h0), cos(h0).

## Comparison method

`scripts/validate_rotation.py` pins the text, second section and flag digests,
the body digest, flag value 1 and the 0.5 scale. Unicorn 2.1.4 maps the whole
text, the whole second section and only the flag page. It starts at
`0x00d00724` with x87 control `0x027f` (PC53, RNE, masked), empty x87 stack,
MXCSR `0x1f80` and signaling-NaN patterns in every XMM register.

Memory hooks allow reads only of pinned text, the captured section bytes, the
four flag bytes, the 12 input bytes and stack bytes already written in the
same case or holding the return address/arguments. Any other read stops the
case, and unmapped reads fault. Writes are limited to the frame below the
initial stack and the 16 output bytes. A passing case also requires return to
the synthetic caller, ESP+4, preserved EBX/ESI/EDI/EBP, clear DF, unchanged
MXCSR control and x87 control, balanced x87 TOP, exactly three input reads and
six flag reads, four ordered four-byte output stores and an identical 8 KiB arena.

## Results

Report `comparison-02.json` covers 8,036 attempts. 8,012 SSE2-domain cases match
with no mismatches and no stops:

| Category | Cases |
|---|---|
| Product of 14 edge values per axis (±0, 2^-149, 2^-148, 1e-20, 0.1, ±1, π/2, π, 2π, −100, 65536, largest SSE2-domain value) | 2,744 |
| Each of 32 edge values in each axis, others random in [−π, π] | 96 |
| Uniform [−π, π] / [−4π, 4π] | 1,500 / 1,000 |
| Log-uniform magnitude 2^-40..2^17.4, random sign | 1,500 |
| Random finite bit patterns below the SSE2 limit | 500 |
| Host-midpoint trig candidates, both signs, each axis | 672 |

Additional sweeps, all matching:

* 2,816 alias/alignment cases with output displaced −16..+16 bytes, including
  in-place and odd overlaps, at four input alignments.
* 256 state variants: x87 PC64 `0x037f`, PC24 `0x007f`, zeroed XMM registers
  and preset MXCSR status bits. Outputs are unchanged, consistent with the
  dispatch ignoring precision control and SSE2 code storing exact binary64.

The trig substitution is characterized separately. The client's six binary64
returns per case were read from ST0 after each helper call. Composing them through
`mu_rotation_quaternion_using` matches every case. Against macOS arm64 libm,
47,354 of 48,072 binary64 results are identical and 718 differ by one ULP
(332 sine, 386 cosine). All 48,072 agree after binary32 rounding.

Two such results can differ after binary32 rounding only near a binary32
rounding midpoint. `scripts/scan_trig_midpoints.c` scanned every positive
binary32 argument below 90,112. It found 112 host results within 64 binary64
ULPs of a midpoint, input SHA-256
`726aff70ca69f6730e0a01097dd36e7addc9e60b330141bec2ddfe82f42fc9fa`. Each was
run as ±2h in every axis. All 1,344 nonzero trig calls agree after rounding,
including cos(2^-12), whose true value lies just above a midpoint. The scan is
host-libm-specific; another libm would need its own scan.

Negative controls: passing reversed axis order to the authored function changes
7,547 of 8,012 results. A Python variant using the client's binary32 trig values but
binary64 products with one final rounding differs in 3,460 cases. Per-product
binary32 rounding is therefore observable.

Outside the SSE2 domain, 24 characterization attempts are never counted as
matches. Values ±180,224, 1e6, −1e10, the maximum binary32 value and ±inf in
any axis enter the x87 fallback. Each stops at the uncaptured read of
`0x0bdcfbc8`. NaN in any axis returns through the fallback without such a read.
The emulator and authored C both produce `0x7fc00000` in all four outputs.
That NaN result depends on emulated x87 behavior and is not claimed.

## Failed hypotheses and limits

The first full run aborted because the harness treated every returned trig
result as finite. NaN inputs return through the x87 fallback. The corrected
harness reports out-of-domain attempts separately. Unicorn reported zero MXCSR
status after every case even though the SSE2 code is inexact, so status flags
are neither compared nor used as a domain oracle, consistent with
[pose composition](pose-concat.md).

Equality of the libm-based function is demonstrated only on the tested inputs
and this host. The client SSE2 sine/cosine algorithms and tables are not
reconstructed. Their binary64 results are not correctly rounded and differ from
macOS libm by up to one observed ULP. An exhaustive comparison over all binary32
inputs was not run. Inputs beyond the SSE2 domain, non-finite values, other
MXCSR/x87 modes, exception flags, the zero-flag path and real FSIN/FCOS
precision remain unverified. So do the caller's live FP state, animation
data and native Windows behavior.

## Reproduce

```sh
make -C reconstructed/record-math
clang -O2 -std=c11 -ffp-contract=off scripts/scan_trig_midpoints.c -lm -o /tmp/scan
/tmp/scan 64 > /new/local/midpoints.txt
./tools/python/bin/python scripts/validate_rotation.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --flag evidence/trig-state-15/captures/late/math-dispatch-flag.bin \
  --midpoints /new/local/midpoints.txt --output /new/local/rotation.json
```

Portable tests run five analytic checks and skip the private one explicitly.
With `MU_RECOVERY_INTEGRATION=1` the private test builds the scanner and runs
the full validator. `MU_CLIENT_TEXT`, `MU_IMAGE_DATA` and `MU_TRIG_FLAG`
override input paths. Reports, scanner output, failed-hypothesis notes and
test logs are ignored under `evidence/client-rotation/`. Source-only clones
contain none of them.

# Hierarchy pose composition

CLIENT-POSE-MATH-001 / issue #33 adds authored `mu_pose_concat` for the selected
hierarchy's 3x4 transform composition. It matches captured instructions in
5,176 finite-domain synthetic cases under controlled binary32 RNE state.
Original live pose-buffer values and rendering remain unknown.

## Identity and caller link

The target executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Restored text at `0x00401000`, length 23,572,480, has SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The helper starts at `0x00cff83e`, ends inclusively at `0x00cfff3b`, and spans
1,790 bytes. Its capture offset is `0x008fe83e`, not a packed-file offset.
Its SHA-256 is
`c358cd6e89029b912c7297f31c049c8383a5aa85bf6400ee77c6e033c01bcb7c`.

[Hierarchy analysis](model-hierarchy.md) established the parent/output dependency.
The new validator decodes from the two selected consumer entries and confirms
calls at `0x012b5895`, `0x012b58bc` and `0x012bd348` target this helper. This
is bounded static caller evidence, not raw call-search totals or live execution.
The older finding's arithmetic-unverified limitation is narrowed only by the
controlled comparisons here. Unknown prior dummy-slot contents remain unknown.

REA 6.5.0/Ghidra 12.1.4 analyzed an 8,192-byte raw x86 window at `0x00cff000`
seeded at the helper entry. Evidence ID is
`ev_c007f0000330b153029fc30bba8df396db0e9c06962ce79573b1b66f4e35e6fb`.
Capstone decodes 726 instructions with no calls or branches before the return.
The arithmetic is 36 MULSS and 27 ADDSS operations, with twelve scalar stores.
The generic pseudocode's arithmetic was checked through actual instructions.

## Observed operation and contract

The three caller-stack arguments are parent, local, output. Each is a row-major
3-by-4 transform with twelve little-endian binary32 values. For output row r
and column c, the helper computes parent[r,0]*local[0,c], adds
parent[r,1]*local[1,c], then adds parent[r,2]*local[2,c]. Column three also adds
parent[r,3]. Each product and addition rounds to binary32 before the next one.
It writes fields in row-major order and rereads inputs for later fields.

The C function reuses the record-math byte load/store helpers. Volatile float
intermediates and `-ffp-contract=off` preserve separate rounding. It requires
RNE, masked exceptions and finite normal/zero inputs and intermediates with
no underflow/overflow. Accessible, nonwrapping 48-byte spans can be unaligned
and overlap, but cannot alias executing code or the call stack. There is no
null-pointer no-op or capacity check. No original return value is inferred.

Output aliasing parent or local can change later calculations. A conventional
matrix implementation that snapshots both inputs is not equivalent on those
cases. In-place composition is therefore deliberately sequential.

## Checks and the floating-point boundary

Unicorn 2.1.4 runs the actual 1,790-byte body without substitutes. MXCSR starts
at `0x1f80`, RNE with exceptions masked and DAZ/FTZ disabled. Host storage/RNE
checks must pass. All 5,176 supported cases match the entire 8 KiB caller arena,
return address, stack cleanup, saved registers, DF and unchanged MXCSR control
bits. Hooks check exactly 75 caller data reads and twelve ordered four-byte
stores, bounded source/output spans and stack accesses. Both DF states and all
four word alignments are covered. Overlap displacements are whole words;
disjoint/overlapping spans can have unaligned absolute addresses.

Thirteen patterns include zeros, signed constants, fractions, cancellation and
eight reproducible random patterns. Five parent/local displacements, ten
output displacements, four alignments and both DF states produce 5,200 attempts.
Twenty-four attempts leave the stated domain. Each arithmetic result is checked
for non-finite/subnormal values; nonzero products rounded to zero are also
excluded. These attempts are recorded separately, not passing comparisons.

The first comparison relied on emulator exception status to detect domain
violations. Sixteen cases differed in NaN representation after alias-driven
overflow, although status flags did not report it. That failed hypothesis is
preserved in `comparison-01.json` and `comparison-debug.json`. Direct
intermediate-value checks identify all 24 out-of-domain attempts, including
cases whose final bytes happened to match. Emulator status alone is not a
reliable domain oracle. NaN payloads, exception/status behavior and traps are
not claimed equivalent.

A separately compiled wrong implementation snapshots both inputs. It fails
2,464 supported comparisons. Analytic portable tests check identity,
noncommuting translation, intermediate binary32 rounding and an in-place result
with hand-calculated sequential values. The full existing cofactor/inverse
regression suite also passes. No strict model acceptance changed.

## Reproduction and next work

```sh
make -C reconstructed/record-math
./tools/python/bin/python scripts/validate_pose_concat.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --output /new/local/pose-comparison.json
```

Supply the pinned restored text and optional emulator dependencies. Portable
tests run four authored cases and explicitly skip the private fifth. Requested
integration fails on missing/mismatched inputs. The validator executes only
controlled synthetic buffers, never actual live bone outputs.

Ignored `evidence/pose-concat/` contains the REA window/dossier, red tests,
failed first hypothesis, corrected `comparison-02.json`, separately compiled
`wrong-snapshot.c`/report and full test logs. The standalone validator also
checks the selected hierarchy CALL instructions. Source-only clones contain
none of these raw inputs or generated reports.

Next validate rotation helper `0x00d00724` or bounded model record
loading/allocation. The static hierarchy finding and this arithmetic result do
not establish the initial/prior buffer values, runtime animation state,
rendering, original FP state or native Windows equivalence.

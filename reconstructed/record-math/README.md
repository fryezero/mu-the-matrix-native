# Reconstructed record arithmetic

Authored C operations for the observed cofactor helper and 4-by-4 record
operation. Names are investigator choices, not original symbols or classes.

`mu_record_cofactor(source, row, column)` evaluates a signed minor for indices
0..3. `mu_record_inverse(destination, source)` computes all cofactors, accumulates
a scalar with explicit binary32 stores, then writes transposed scaled cofactors
or takes the observed zero-scalar fallback. Records contain 64 bytes of
little-endian IEEE binary32 values in row-major order. Byte access permits valid
unaligned and overlapping buffers.

The fallback constructs a public mathematical identity, then reads and negates
source translation fields. In-place and partial overlaps therefore differ from
a version that snapshots source translation first. The private validator checks
the public identity construction against the captured template.

## Comparison scope

The reference uses an empty x87 stack, PC53, round-to-nearest and masked
exceptions, control word `0x027f`. C uses staged binary64 products and explicit
binary32 rounding; contraction is disabled. Callers provide valid 64-byte spans,
the stated FP environment and no concurrent access. The basic environment
predicate checks storage, evaluation method and rounding; it does not verify
trap masks or flush/denormal modes.

Tests cover finite synthetic records, selected scales and zero/degenerate/alias
cases. NaN payloads, infinities, unmasked traps, FP flags, general underflow,
other rounding modes and actual Windows/game invocation remain unverified.
The inverse API is logically void: the original EAX scratch value depends on
the branch and is not claimed as an original return contract.

## Build and compare

The top-level `make test` builds portable synthetic tests. Install the full
optional analysis dependencies for private instruction comparison:

```sh
./tools/python/bin/python scripts/validate_record_math.py \
  --capture /absolute/path/to/client-text.bin \
  --math-data /absolute/path/to/math-capture-09 \
  --library reconstructed/record-math/librecord_math.dylib
```

Use `.so` on Linux. `MU_CLIENT_TEXT` and `MU_MATH_DATA` override local integration
paths. Full text and selected data/manifest identities are checked before use.
Actual wrapper/helper bytes execute in Unicorn without arithmetic stubs; the
FP initialization and return store are authored harness instructions. All 1,680
cofactor and 1,050 inverse cases match. Full arena guards and original stack,
register, control-state and bounded-access checks accompany the comparison.
See [the finding](../../docs/research/record-math.md) for provenance and limits.

## Hierarchy pose composition

`mu_pose_concat(parent, local, output)` composes twelve-field 3x4 transforms
using separate binary32 products/additions and row-major sequential stores.
It reuses byte-defined storage access for unaligned spans. Inputs/output may
overlap; copying both inputs first would change 2,464 synthetic results.

The [pose finding](../../docs/research/pose-concat.md) records 5,176 actual
instruction matches under controlled RNE normal/zero arithmetic, plus 24
explicitly out-of-domain attempts. Four analytic portable tests and one private
instruction check extend this module. No original live pose/FP state or rendering
is inferred. Existing cofactor/inverse binary64 contracts remain unchanged.

## Rotation conversion

`mu_rotation_quaternion(angles, quaternion)` mirrors the client helper at
`0x00d00724`. It halves three binary32 angles, takes binary32-rounded sine and
cosine, and writes the x,y,z,w quaternion of Rz(a2)·Ry(a1)·Rx(a0) with separately
rounded binary32 products. All inputs are read before the ordered stores, so
in-place spans are valid. Trigonometry uses the host libm as a substitute for
the client SSE2 helpers. `mu_rotation_quaternion_using` takes caller sine/cosine
callbacks, invoked in the original order.

The [rotation finding](../../docs/research/client-rotation.md) records 8,012
bitwise matches against the actual client body and trig helpers. These cases use
flag 1, x87 `0x027f` and MXCSR `0x1f80`, without stubs. It also covers 2,816
alias/alignment cases, 256 FP-state variants and host-midpoint trig candidates.
Results outside the SSE2 domain and non-finite values remain unverified. Five
analytic portable tests and one private instruction check cover this entry.

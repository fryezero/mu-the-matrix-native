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

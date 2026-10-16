# Controlled reconstruction of record arithmetic

Observed 2026-10-15 for main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Restored-text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Scoped capture09 supplies the verified zero bias and identity template;
[the data finding](client-math-data.md) records digests and Wine limitations.

| Observed range | Bytes | SHA-256 |
| --- | ---: | --- |
| Cofactor `0x00401240..0x004013c3` | 388 | `3953e0e96ca8d44c44aafc7ba04cda9741268dd4076b7378d2726e79ba0c392e` |
| Record operation `0x004013d0..0x004014dd` | 270 | `478df4df0c19b0eb211a0f955c1c1ed7be2f0a268959aa563539e0e270502524` |

REA 6.5.0 / Ghidra 12.1.4 helper dossier:
`ev_5af8081d62a9556960e039094d888d0743d424b9a7b05124db9bd5be50bb7d00`.
The wrapper dossier remains
`ev_486f89fae4379bc3801cf0754db5c1d7861fda2329ec676b92c9afe1fb6bd31b`.
Both use the pinned first 64 KiB and four-seed profile in the window-map finding,
raw x86 load base `0x00401000`, 2 GiB heap and disabled analyzers. Generic GCC
calling conventions remain incomplete. Instructions and emulation establish
the tested logical inputs; generated pseudocode stays local.

## Ordered behavior

The helper excludes a selected row/column, evaluates six ordered triple products,
rounds its accumulator to binary32 after each addition/subtraction and applies
checkerboard sign. The wrapper stores all sixteen cofactors, accumulates a scalar
from the first input row with float rounding, then uses a float-rounded reciprocal
for transposed scaled output. C preserves product order, intermediate stores and
signed zeros, with staged binary64 products and disabled contraction.

For scalar zero, the original copies the template, then reads and negates source
fields at offsets `0x30..0x38`. In-place or partial overlaps can alter those source
fields before they are read. The C implementation preserves these effects.
This is consistent with cofactor-based 4-by-4 inversion with an unusual fallback;
original names, class, callers and subsystem remain unknown.

## Independent comparison

The validator pins the complete text plus every selected data file and manifest
identity. Actual wrapper/helper instructions run with captured globals, without
arithmetic stubs. An authored FNINIT/FLDCW/JMP prologue establishes an empty x87
stack, PC53, RNE and masked exceptions, control word `0x027f`. An authored result
store rounds the helper's already-float x87 return. The public identity
construction is checked against captured data before native C comparison.
The actual original process FP state was not captured. The native basic
environment check does not validate every FP property.

There are 105 synthetic records: identity/diagonal/permutation fixtures,
zero/singular inputs, selected powers of two and a near-singular input,
64 seeded rational records and 32 finite full-mantissa records. All sixteen
removed-row/column pairs yield 1,680 helper comparisons. Ten destination
displacements and varying source alignments yield 1,050 wrapper comparisons,
including in-place, partial overlaps and disjoint unaligned buffers.
All match byte for byte. Full 4 KiB arena guards, returned control flow, stack
cleanup, callee-saved registers, helper-entry counts, unchanged control word and
bounded code/data accesses are checked. Thirty wrapper cases take fallback and
1,020 take reciprocal scaling. No unexpected accesses occur.

The helper returns a float-rounded x87 value and removes twelve argument bytes.
The wrapper removes eight; observed EAX is destination in fallback and destination
plus 48 otherwise. Its authored logical API is void and infers no stable return
contract from this scratch register. An unused incoming ECX context is not given
a fabricated class type.

A plausible native version that snapshots translation first fails 16 alias cases.
A separate PC24 reference experiment differs in 1,471 comparisons: precision
mode is material. That experiment is outside the supported model. No claim covers
all NaN/Inf, underflow/denormal, trap, FP-status, rounding or concurrency behavior.
Controlled emulation is not native Windows or actual game-invocation proof.

## Records and continuation

Ignored evidence: `evidence/record-math-equivalence.json`,
`evidence/record-math-wrong-snapshot-result.json`,
`evidence/record-math-pc24-diagnostic.json`, `evidence/rea-record-cofactor.json`
and original capture09 directories. Authored source/synthetic tests are under
`reconstructed/record-math/`; the repeatable validator is
`scripts/validate_record_math.py`. A clone supplies matching private inputs.

Next recover genuine caller/type context or relevant original FP state before
widening the behavior model. These are editable tested components, not a
recovered game loop or complete client.

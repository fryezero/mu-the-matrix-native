# Adjacent 64-byte clear routine

Observed 2026-10-15 for main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The verified Wine text capture is 23,572,480 bytes at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
See [capture limits](restored-client-text.md) and [the adjacent copy](client-copy64.md).

## Wrapper and helper

The wrapper at `0x00401020..0x0040102d` is 14 bytes, SHA-256
`a258ffbdd85880bc768fc3d2af6309c2743c6447f2bc19fc6115434595917d79`.
It calls the internal helper at `0x0194cd00` with the ECX destination, byte zero
and length 64. It returns the helper's EAX destination, with no stack arguments
consumed at its own boundary. The relevant helper range is
`0x0194cd00..0x0194ce59`, SHA-256
`9930d1c9fefcb3dc3f336202236a1c2eec2e1414822cdd0d4666ca6c1304e776`.

For length 64, the helper reads bit 1 at `0x01cf6618`. That global lies outside
the captured text and its actual runtime value is unknown. The validator
explicitly supplies both zero and two as synthetic feature words, rather than
claiming either was observed. The clear path avoids the helper's larger-count
branches, including another feature global. Instruction and memory hooks show
no reads outside the selected feature word, stack and destination in these cases.

Bit 1 clear reaches the scalar path at `0x0194ce05`; bit 1 set reaches the SSE
path at `0x0194cdc7`. Both clear exactly 64 bytes and return the destination.
Both preserve the tested callee-saved registers and the input DF state. The
wrapper and helper execute from the original captured bytes, with no helper
stub or instruction patch. Only the synthetic inputs/state are supplied.

REA 6.5.0 / Ghidra 12.1.4 decompiled the wrapper from the same verified 4 KiB
prefix, using an added explicit seed at `0x00401020`. Evidence ID
`ev_945e936d6437010deb8e9d6ea07fd85097c00cd48388b188e703481966180709`.
The original two seeds, 2 GiB heap and disabled analyzer profile were retained.
A first attempt used the wrong seed-column order and was rejected; it is kept
as failed evidence. The corrected raw import still uses the generic GCC profile;
calling conventions and returns come from instructions/emulation, not inferred
pseudocode types. Its prefix excludes the actual helper body, which was separately
inspected with Capstone 5.0.9 and executed with Unicorn 2.1.4.

## Comparison and context search

The authored `mu_clear64` uses an exact 64-byte zero fill and returns its pointer.
All 768 comparisons match across three synthetic patterns, 64 destination
alignments, both feature states and both DF states. Each comparison checks the
complete 4 KiB arena, pointer return, x86 stack cleanup, callee-saved registers,
DF preservation and executed helper paths. A deliberately incorrect 65-byte
clear is detected in 768 cases by the same full-arena comparison.

The earlier direct-call scan found no E8-relative calls to the first copy,
clear or length entries in the captured section. This follow-up scanned every
byte position for their exact little-endian absolute addresses in both the
restored section and the pinned original executable. No matches occurred.
This bounded unsuccessful search leaves indirect references, other modules,
inlining and unused compiled routines unresolved. The nearby layout remains
consistent with a mathematical record; no original class or game subsystem is
identified. Further context needs a larger function/data-reference map or
validated companion-module evidence.

Ignored local evidence:

- `evidence/rea-client-clear64.json`: successful REA record/pseudocode.
- `evidence/rea-client-clear64-bad-seed.json`: rejected initial seed format.
- `evidence/clear64-equivalence.json`: checked instructions, branches and results.
- `evidence/clear64-wrong-65-result.json`: negative-control results.
- `evidence/clear64-reference-scan.json`: input hashes and exact-address scan.

The comparison is against captured instructions with explicit synthetic state.
It does not establish native Windows behavior, original process feature settings,
fault/concurrency semantics or actual invocation by the game. Original bytes and
generated pseudocode remain ignored. The next useful step is a broader bounded
function map to prioritize arithmetic and genuine subsystem entry points.

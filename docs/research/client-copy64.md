# First reconstructed behavior from restored client code

Observed 2026-10-15. Exact executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The source capture is the 23,572,480-byte Wine region at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Its capture08 identity and limitations are in [the runtime finding](restored-client-text.md).

## REA and calling convention

REA 6.5.0 / Ghidra 12.1.4 decompiled `0x00401000` from the verified 4,096-byte
prefix, SHA-256 `12862e9cdd93ac2586988694fc4c08066361de7bf31048442bb8cf7ea57a096d`.
Evidence ID `ev_24927ad2923966a8c00f6b9c78059b8bf860bd1e73e6b20fb662cdb778c8ba3b`.
The raw-x86 load base was `0x00401000`, with the same two explicit function seeds,
2 GiB heap and disabled analyzers recorded in the runtime finding.

REA's generic GCC compiler profile leaves the destination ECX input implicit
and reports a void return. The instructions instead place the destination in
EAX and return with four bytes of argument cleanup. Capstone 5.0.9 inspection
and Unicorn 2.1.4 execution establish those register/stack observations. This
resembles a one-argument x86 member function, but no original class name or type
is recovered. Seed names are investigator assertions.

The selected function spans `0x00401000..0x00401015`, 22 bytes, SHA-256
`54396a6b24bf4ce529617c72471631a0e8f8156f25f08b4ae118ebe37f29956e`.
It preserves ESI/EDI, obtains the source from the stack and transfers sixteen
32-bit words using the direction flag. The authored C implementation explicitly
models forward transfers with DF clear. It does not model DF-set traversal,
faults, address wrapping, segmentation or concurrent access.

## Nearby map and unresolved context

The following inclusive ranges were decoded in the captured prefix. They are
observations and candidate roles, not recovered original symbols.

| Range | Observed behavior | Remaining uncertainty |
| --- | --- | --- |
| `0x00401000..0x00401015` | Sixteen-word forward copy, destination in ECX/EAX | Original type and callers unknown |
| `0x00401020..0x0040102d` | Calls `0x0194cd00` with destination, zero byte and length 64 | Clear operation validated on both feature-bit paths; actual feature value unknown |
| `0x00401030..0x0040105b` | Three-component squares/sum and call to `0x01999870` | x87 precision, control word, exceptions and original type |
| `0x00401060..0x0040108c` | Similar operation at object offsets `0x10..0x18` | Same limits |
| `0x00401090..0x004010bc` | Similar operation at offsets `0x20..0x28` | Same limits |
| `0x004010c0..0x00401125` | Supplied scalar divided by the first computed length; three components scaled | Nonfinite/zero/rounding cases unvalidated |
| `0x00401130..0x00401198` | Similar scaling at offsets `0x10..0x18` | Same limits |
| `0x004011a0..0x00401208` | Similar scaling at offsets `0x20..0x28` | Same limits |
| `0x00401210..0x00401213` | Float load at offset `0x30` | Original field meaning unknown |
| `0x00401220..0x00401223` | Float load at offset `0x34` | Original field meaning unknown |
| `0x00401230..0x00401233` | Float load at offset `0x38` | Original field meaning unknown |

The observed layout is consistent with a 64-byte mathematical record, possibly
a matrix. That is an inference. The caller at `0x004013ee` calls a separate
index/arithmetic helper at `0x00401240`; its presence gives local arithmetic
context without establishing any game subsystem. A full byte-position scan of
the restored section found no direct E8-relative calls to `0x00401000`,
`0x00401020` or `0x00401030`. This does not exclude indirect calls, inlining,
other modules or unexecuted code. No imported OS function occurs inside the
selected copy routine. Within these eleven mapped routines, the two observed outgoing callees are internal
addresses; the earlier bounded REA import does not contain their bodies.

## Behavior comparison

The validator first checks the complete capture's length/digest, then executes
the actual captured copy instructions under Unicorn x86-32. Each isolated run
has a flat mapped arena and stack, a clear DF, a return sentinel and an instruction
budget. The host runs the authored compiled C function on the same synthetic
arena. The complete 4,096-byte memory result, destination return, x86 EIP/ESP and
callee-saved EBX/EBP/ESI/EDI are checked.

All 393 cases match. Three patterns cover every destination displacement from
-64 through +64, with three source alignments; six additional cases use disjoint
unaligned spans. Tests include equal pointers, both overlap directions and
sub-word overlaps. Replacing the authored implementation with a deliberately
incorrect `memmove` wrapper produces 158 mismatches, confirming that the check
detects a plausible but wrong replacement. This comparison proves only the
stated input/environment subset against captured instructions, not native
Windows or gameplay equivalence.

Ignored evidence on the original lab workstation:

- `evidence/rea-client-copy64.json`: complete REA record and generated pseudocode.
- `evidence/cap002-copy64-equivalence.json`: successful private comparison summary.
- `evidence/cap002-wrong-memmove-result.json`: negative-control mismatches.
- `evidence/x86-capture-text-08/`: original validated capture and manifest.

The repository contains authored source, synthetic tests and this reviewed
finding. A fresh clone must supply private bytes to repeat instruction comparison.
The [adjacent clear operation](client-clear64.md) is now compared on both helper paths.
Caller/type context remains unresolved before expanding into x87 arithmetic. Keep the unresolved startup localhost connection
separate from these component results.

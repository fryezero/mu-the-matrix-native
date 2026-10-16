# Client-linked v15 ECB decoder

CLIENT-LEA-DECODE-001 / issue #31 adds authored portable C for the ECB wrapper
and its eight/four/single-block behavior. Actual captured code matches 12,960
valid guest cases and 46 no-op cases. A separate scalar instruction comparison
passes 1,152 cases. This is a decoder component, not a recovered model loader.

## Input identity and bounded analysis

The target executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Restored text starts at VA `0x00401000`, length 23,572,480 and SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The [observed dispatch](model-dispatch.md) connects entry `0x0091a730` to wrapper
`0x0092be30`. [Key setup](client-lea-key.md) defines its context.

| Body | Inclusive end | Bytes | Captured-body SHA-256 |
|---|---|---|---|
| eight blocks `0x00927060` | `0x009282a4` | 4,677 | `ccc0ee915849c68077c607526892a398731c53f81635c9ac780c401f6aa26239` |
| four blocks `0x00929370` | `0x0092a42f` | 4,288 | `6fa51533865332b415f88ecde322aea8e9778f7dbcfbe116a7112b70d8f747ce` |
| wrapper `0x0092be30` | `0x0092bef5` | 198 | `a45a3d2a04babe7b627edd1473e63893dbc592eb4f3292387e9528e427b4dc37` |
| one block `0x0093bb20` | `0x0093c225` | 1,798 | `f37b056688cef339f0f1e857fb421d2e04ad3062a3ba3162fc23d80ba02e26a1` |

Capture offsets are VA minus `0x00401000`; these are not packed-file offsets.
The bodies decode to 870/815/74/509 instructions respectively. Branches target
instruction boundaries inside each body. Only the wrapper has calls, and they
target the three helpers. There are no absolute or segmented memory operands.
The static validator checks these properties before comparison. Its authored
miniature fixtures reject unbounded transfers, invalid instruction boundaries,
absolute/segmented reads and incomplete decode.

REA 6.5.0/Ghidra 12.1.4 produced bounded dossiers for the wrapper and AVX helpers.
The eight/four-block dossiers use a 28,672-byte window at `0x00926000`, seeded
with both entries, with the same two disabled analyzers as earlier recovery.
Evidence IDs are:

- wrapper `ev_6d66b208948d94526d1010311f5088eec5490d1a692540833c2dfe25bac123d5`;
- eight blocks `ev_aec823a2ca9708c438f9efd7e02ac5ad04f18f89b4eb880b03be4ce476af659b`;
- four blocks `ev_3777c37fd6b3e0b11a42cda650bf32d61be8ba604c0470931e4832a499963b09`.

The selected BMD caller writes the same 32-byte public format constant already
used by `model-recovery/bmd_encrypted.py`. Instructions at `0x012b3aca..0x012b3adc`
pass size 32, the local key and a separate local context, call setup at
`0x012b3ad7`, then remove twelve argument bytes. The validator checks that
bounded path from the model-read entry. It is static evidence, not a live call.

## Contract and batch ordering

`mu_client_lea_decode(destination, source, uint32_length, context)` returns no
specified value. Null context, null source/destination, zero length and lengths
not divisible by sixteen cause no caller-buffer access. Valid contexts are
those produced by the recovered setup for 16/24/32-byte keys. Context must be
readable and disjoint from input/output. Caller spans must cover the length,
be accessible, not wrap, and not alias executing code or the call stack.
Unaligned input/output and overlapping data spans are supported.

The wrapper processes groups of eight blocks, then four, then individual
blocks. Helpers load each entire group before writing any decoded output.
The portable source snapshots only the current group. An earlier group's
output can therefore change input for a later group when spans overlap.
A whole-input snapshot or always-single-block loop would change this behavior.
Helper ABI uses ECX for destination, EDX for source and a caller-stack context.
The wrapper uses four ordinary caller-stack arguments and caller cleanup.

Arbitrary context contents/round counts, context-data aliasing, fault/status
flags and concurrent modification are outside the authored contract. It does
not allocate, validate capacity or parse an envelope. Strict model acceptance
is unchanged.

## Actual-code comparisons and limits

Unicorn 2.1.4 runs the wrapper/scalar path but refuses an AVX instruction at
`0x009293d9` or `0x009270af` for four/eight blocks. The failed probe is retained.
No substitute instruction handler was added. Its scalar comparator covers
lengths 16/32/48, all supported keys, overlap, alignment and both DF states.
All 1,152 cases match complete arena bytes, caller return, saved registers,
stack cleanup and DF. Hooks bound data/context reads, output writes and stack
access. This result does not execute AVX batches.

The separate PE32 comparator runs in QEMU 11.1.2 TCG, Debian x86-64 Linux and
Wine 8.0 with outbound networking blocked. A first attempt to map the original
whole-text address conflicted with the standalone runner's allocations. The
corrected runner copies only the four pinned bodies into a shared relocated
window. Relative transfers stay valid; the static properties above support
relocation. Other window pages are inaccessible. No algorithm is stubbed.
The executable used in the final run has SHA-256
`02f7ede8cd18059b101f3b7fe91ececcc2d297fe25f230e3340d1a7b17bd866d`.

All 12,960 valid cases and 46 no-op cases pass. They cover three synthetic key
patterns, all three sizes, four context/data word alignments, fifteen lengths
from 16 to 512, twelve displacements and both DF states. The context is read-only;
inaccessible pages surround the arena. Every arena byte is compared. The
assembly bridge records saved integer registers, stack cleanup and DF and
restores its own state. A deliberately bad callee fails its bridge check.
An always-single-block negative control differs in 4,094 valid cases. Wrong
input is refused with exit 2 before captured code can execute. The guest shut
down cleanly afterward.

The guest comparison has no instruction trace or inside-arena read trace.
Page guards and full arena comparison cannot prove that every read stays in
its logical input span. Those limits are explicit in its report; the scalar
hook result supplies that narrower evidence only. Relocated compatibility
execution does not prove original process state, live invocation, native
Windows equivalence, every input value or whole-loader behavior.

## Installed payload coverage and continuation

Separately, authored host C matches the independent native asset reader on
all 11,583 pinned v15 encrypted payloads, totaling 655,268,704 bytes. This
includes the seventeen structurally rejected models. Each input hash, size,
file identity, envelope and block alignment is checked; manifest and rejection
diagnostics are also pinned. This corpus comparison executes authored C and
the independent reader, not original captured instructions. It does not make
any rejected model acceptable or establish runtime model/hierarchy behavior.

[Guest instructions](../../runtime-linux/lea-compare/README.md) describe the
cross-build and original-code run. For scalar plus installed-payload checking:

```sh
./tools/python/bin/python scripts/validate_client_lea_decode.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --game-root /path/to/matching/installation \
  --output /new/local/lea-decode-report.json
```

Omit `--game-root` for scalar/static checks alone. Corpus mode additionally
requires the exact ignored model manifest and rejection diagnostics, with
optional `--manifest`/`--diagnostics` paths. Build the independent native reader
first. Missing requested inputs are errors. Portable tests use public vectors
and authored bytes; the guest is a separate opt-in verification, never a CI
claim about original client execution.

Raw inputs, failed probes and reports stay ignored under
`evidence/client-lea-key/`, `evidence/client-lea-resolved/` and
`evidence/client-lea-decode/`. Final reports are `guest-comparison-14.txt`,
`scalar-comparison-02.json` and `corpus-comparison-01.json`. A source-only clone
contains none of this private evidence. Next recover bounded model allocation,
version routing and record loading, or validate the hierarchy's actual matrix
concatenation. Complete loading and rendering remain unresolved.

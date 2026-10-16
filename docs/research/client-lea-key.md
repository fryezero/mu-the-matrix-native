# Client-linked v15 key context

CLIENT-LEA-KEY-001 / issue #29 reconstructs the key setup at the observed v15
jump target `0x0092a430`. Authored C matches the actual captured instructions
in 1,320 synthetic cases. This recovers context initialization, not ECB
payload decryption or a complete model loader.

## Identity and source link

The exact original executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The restored text starts at VA `0x00401000`, has 23,572,480 bytes and digest
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The selected setup body is `0x0092a430..0x0092bd5d`, inclusive, 6,446 bytes.
Its offset within the text capture is `0x00529430`, not an offset in the packed
original file. Its SHA-256 is
`027959c97d01690e622312ae0c16e269a7b95cb30d3af160486349219a28b0da`.

[The BMD call-path finding](client-model-loader.md) traces the v15 branch to
setup entry `0x0091a6c0`, with a 32-byte key. [The dispatch capture](model-dispatch.md)
resolves that entry's jump slot `0x01d04e14` to this body. This is static caller
context plus an observed compatibility-environment binding. No live model-load
invocation or native Windows binding was captured.

REA 6.5.0 with Ghidra 12.1.4 produced a seeded bounded dossier, evidence ID
`ev_df7a2e68fc50fb733641d7bda86be57ae7c4ec92b59fed2b5aaff9bd8dc6ca4e`.
Capstone decodes 1,468 contiguous instructions through the final return, with
no CALL instruction. The raw window uses x86 at base `0x0092a000`, length
16,384. Tool settings match the bounded decode work described in the dispatch
finding. Generated pseudocode remains an analysis aid, not source proof.

## Observed behavior and authored contract

`mu_client_lea_setup(context, key, key_bytes)` uses three caller-stack arguments
and leaves argument cleanup to its caller. It has no specified return value.
A null context, null key or size other than 16/24/32 causes no caller-buffer
access. Supported inputs write little-endian words into a byte-defined context:

| Key bytes | Forward round keys | Round count at byte 768 | Untouched context interval |
|---|---|---|---|
| 16 | 144 words, bytes 0..575 | 24 | bytes 576..767 |
| 24 | 168 words, bytes 0..671 | 28 | bytes 672..767 |
| 32 | 192 words, bytes 0..767 | 32 | none |

The observed layout agrees with the public LEA key schedule. The compact C
implementation uses explicit byte loads/stores, unsigned 32-bit arithmetic
and defined rotations. It assumes accessible, nonwrapping, disjoint key and
context spans that do not alias executing code or the call stack. It permits
unaligned pointers. It does not introduce an original struct name or require
native word alignment.

The original unrolled code interleaves reading later key words with writing
context words. The compact C snapshots the disjoint key first. Key/context
aliasing is outside this contract; no equivalence for such overlap is claimed.
Original arithmetic/status flags, fault paths, concurrent modification and
exception behavior remain unverified.

## Comparisons

The validator checks the full pinned text before importing Unicorn 2.1.4 or
loading the authored library. It executes only the actual selected body, with
no algorithm/helper substitutes. There are 416 valid cases for each key size
and 72 null/unsupported no-op cases, totaling 1,320. Valid cases use thirteen
synthetic key patterns, all sixteen key/context word-alignment pairs and both
DF states. Patterns include zero, all bits set, alternating bits, increasing
and decreasing bytes, and eight reproducible pseudorandom keys.

Every case compares the entire 8 KiB caller arena and verifies return to the
caller, stack cleanup, callee-saved registers and unchanged DF. Memory hooks
require each key word to be read exactly once and each active context word,
plus round count, to be written exactly once. Caller accesses outside those
spans fail. Stack accesses are bounded to eight bytes below entry through the
three arguments. Execution must stay in the selected body. Unused context
bytes and external guards remain unchanged. All 1,320 comparisons pass.

A separately compiled wrong implementation reverses the round-key order after
setup. It fails all 1,248 valid instruction comparisons. The validator also
records that negative-control difference. This distinguishes the observed
forward context from a plausible reversed decrypt-context convention.

Portable checks consume the context through independent encryption equations
and five [public Crypto++ LEA vectors](https://github.com/weidai11/cryptopp/blob/master/TestVectors/lea.txt),
covering every supported key size. The existing fixture records the public
source-file digest. Additional analytic first-round checks and alignment/tail
checks use authored bytes. Cipher arithmetic/constants are public facts; no
third-party source implementation or game payload is included.

These are bounded synthetic key-setup comparisons. No installed v15 payload
was decrypted by this recovered component. The existing independent v15
reader's corpus result is separate evidence.

## Reproduce and continue

```sh
make -C reconstructed/model-codec
./tools/python/bin/python scripts/validate_client_lea_key.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --output /new/local/lea-key-comparison.json
```

Supply the pinned private restored-text capture and optional analysis
dependencies from `tools/requirements-lock.txt`. A source-only clone runs five
portable tests and explicitly skips the sixth private check. Requested
integration fails on missing/mismatched inputs. The public header documents
the caller's span requirements.

Ignored evidence is `evidence/client-lea-resolved/rea-key.json` and
`evidence/client-lea-key/`. The latter contains the initial probe, red test log,
`comparison-01.json`, `wrong-order.c`, `wrong-order-comparison.json` and complete
portable/private test logs. A fresh GitHub clone contains none of those inputs
or outputs.

Next recover the resolved ECB wrapper `0x0092be30` and actual eight/four/single
block targets `0x00927060`, `0x00929370`, `0x0093bb20`. Establish helper ABI,
round-count handling and batch read/write ordering before choosing overlap
semantics. The observed setup context alone does not establish any of them.

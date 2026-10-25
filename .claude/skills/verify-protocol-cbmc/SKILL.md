---
name: verify-protocol-cbmc
description: "Prove, with the CBMC bounded model checker, that the native client's network protocol layer (native/core/mu_protocol.c: C1..C4 framing, the receive dechunker, the packet builder and XorData) stays inside its buffers and frames server bytes correctly for every input up to a stated bound. Use after any change to native/core/mu_protocol.c, mu_protocol.h, native/tools/mu_proto.c, or code that feeds recv() bytes into mu_recv_push/mu_recv_drain or builds packets with mu_packet_*; also when a reviewer asks whether a framing or buffer bug is possible."
---

# Formal verification of the network protocol layer

The receive side of `native/core/mu_protocol.c` takes bytes from a game server
and cuts them into frames; the send side builds packets into a fixed object.
Tests (`native/tests/test_protocol.py`, 1,000 random streams) and the Unicorn
comparison against the client's own instructions (`scripts/validate_protocol.py`,
300 streams) check the cases someone wrote down. This skill checks **every**
byte stream, chunking and length up to the bounds below, including the ones
nobody thought of, by running CBMC on the real C source with a few small
harnesses. Nothing here touches the client, a server, or the network.

Read this file cold: it tells you whether your change touches verified code,
how to run the check, how to read a failure, and how to keep the verification
true to the code.

## Does my change touch verified code?

Yes if you edited anything in these ranges of `native/core/mu_protocol.c` at the
sync commit below, or the constants `MU_PACKET_CAP`, `MU_PACKET_OBJ`,
`MU_RECV_CAP`, `MU_SEND_XOR_KEY` or the `mu_frame_info`/`mu_packet`/`mu_recv`
layouts in `mu_protocol.h`. Then run the check before and after.

| Function (lines at the sync commit) | Harness | Property |
|---|---|---|
| `mu_frame_header_len` 14–26, `mu_frame_parse` 28–64 | `frame_parse.c` | P1 |
| `mu_recv_init` 151–154, `mu_recv_drain` 166–192 (+ `mu_frame_parse`) | `recv_drain.c` | R1, R2 |
| `mu_recv_push` 156–164 | `recv_push.c` | R3 |
| `mu_packet_begin` 114–134, `mu_packet_add` 97–112 (plain path), `mu_packet_finish` 136–149, `mu_packet_len` 92–95, `packet_set_size` 86–90 | `packet_begin.c`, `packet_build.c`, `packet_add.c` | S1 |
| `mu_send_xor_encode` 68–73, `mu_send_xor_decode` 75–84 | `xor_inverse.c`, `xor_window.c`, `xor_upper.c` | S2 |

Not covered: `mu_serial_next` 194–199 (a byte counter; it is never called from
the harnesses), `native/tools/mu_proto.c` (the CLI around this module), and
anything in the "What this does not prove" section.

**Sync commit: `024e9496fe8a0335a2a6419772ac6efdf8a00a3f`** (branch
`claude/pstack-verify-skills`, 2026-10-24). At that commit the harnesses
describe the code and every property holds. Move this hash forward only after
you have reread the covered functions at the new commit, confirmed the
harnesses still describe them (same guards, same loop shapes, same layouts),
and `run.sh` passes. If the code changed in a verified range and nobody did
that, the verification is stale: say so, and run
`/pstack:maintain-formal-verification-skill`.

## The properties, in one sentence each

Each property names the harm it rules out. "Any" means any value the bound
allows; CBMC explores all of them at once, it does not sample.

- **P1 — the parser never reads past what has arrived, and classifies every
  buffer by the C1..C4 rule.** `mu_frame_parse(buf, avail)` touches no byte at
  or past `avail`; with fewer than 3 bytes it answers need-more; a head outside
  C1..C4 or a zero size is bad; a declared size beyond `avail` is need-more; a
  complete frame is ok with the declared total size, the 2- or 3-byte header
  length and the C3/C4 encrypted flag. Harm otherwise: the receiver hands the
  dispatcher bytes that have not arrived, or reads stale ring contents.
  Bound: 0..24 bytes, any contents (the buffer is allocated at exactly `avail`
  bytes so the bounds check is the proof).

- **R1 — the receiver stays inside its ring.** Over one `mu_recv_drain`,
  nothing reads or writes outside the 0x2000-byte ring or the bytes handed in,
  and no loop runs past the bound. This is CBMC's own bounds, pointer,
  overflow, conversion and unwinding checks on the product code. Harm
  otherwise: memory corruption from a malformed server stream.
  Bound: 0..12 buffered bytes, any contents.

- **R2 — frames are exact consecutive slices of the stream.** Every frame the
  callback receives starts where the previous one ended (from the ring's
  front), has at least one byte, is byte-identical to the buffered bytes, is cut
  only while 3 or more bytes are buffered, has a C1..C4 head and is exactly its
  declared size; afterwards the leftover is the unconsumed tail moved to the
  front unchanged with no complete frame left in it, or the ring is empty
  because a non-MU head or a zero size was met at a frame start. Harm
  otherwise: stale, torn or repeated frames reach the dispatcher.
  Bound: 0..12 buffered bytes, any contents.

- **R3 — a push appends or refuses, never overflows.** `mu_recv_push` refuses
  (returns -1) exactly when buffered + new bytes would exceed 0x2000, and then
  changes neither the length nor any byte; otherwise it appends the bytes after
  the buffered ones, leaves the buffered ones alone and grows the length by the
  count. Harm otherwise: a server burst overwrites memory after the ring (the
  client instead logs "Receive Packet Buffer Overflow" and stops).
  Bound: any buffered length 0..0x2000 with any ring contents, a push of
  0..0x40 bytes.

  R2 over one drain plus R3 covers any server stream in any chunking: a drain
  consumes a prefix of what is buffered and keeps the rest at the front, a push
  appends after it, so the next drain sees exactly the unconsumed stream. (A
  harness stating this directly over several pushes was tried and does not
  finish on either CBMC backend, even at 6 bytes in 2 pushes.)

- **S1 — the packet builder stays inside its object and keeps an honest size
  word.** From any head, opcode and prior contents, `mu_packet_begin` clears
  the overflow flag and lays down exactly head, size placeholder (one byte for
  C1/C3, two for C2/C4, none otherwise) and opcode with the rest of the body
  area zero, and `mu_packet_finish` returns that body length and writes it
  into the head's size field (`packet_begin.c`). With one plain
  `mu_packet_add` of 0..20 bytes between them, everything stays inside the
  0x145c-byte object, the bytes land after the body, the size word equals the
  body length and the size field and opcode are right (`packet_build.c`). From
  **any** size word (0..0xffff) and any object contents, one plain add refuses
  exactly when the body would pass 0x145a, then changes only the overflow
  flag; otherwise it appends after the body, advances the size word and
  touches nothing else (`packet_add.c`). Because that starting size word is
  unconstrained, `packet_add.c` is the inductive step for any number of adds.
  Harm otherwise: a long chat, trade or mail message overruns the packet
  object, or every frame carries a wrong length or a stale overflow flag.
  Bound: one add of 0..20 bytes per harness.

  An **encoded** add differs from a plain one only by the call
  `mu_send_xor_encode(obj, cur, cur+len)` after the copy. S1 proves
  `cur + len <= 0x145a`; S2 below proves that call then touches only
  `obj[cur+2 .. cur+len+2)`, which is inside the object. The harnesses do not
  run the encoded path through `mu_packet_add` itself because CBMC does not
  finish on writes through a pointer into a struct member at a symbolic index.

- **S2 — XorData decode inverts encode, and encode touches only its range.**
  On a size word plus 0..22 body bytes, for any `start <= end`, decode after
  encode restores every byte, encode follows the chain rule
  `obj[i+2] ^= obj[i+1] ^ key[i & 31]` at every index of the range (chaining on
  the byte it just wrote, or the size word's high byte at i == 0), and encode
  changes nothing outside `[start+2, end+2)` (`xor_inverse.c`, `xor_window.c`
  on a 64-byte window). On the **full** packet range, for any `start` with
  `start + len <= 0x145a` and `len <= 20`, encode touches no byte at or past
  `end+2` (`xor_upper.c`: the object is allocated at exactly `start+len+2`
  bytes). Harm otherwise: frames the server cannot decode, or writes past the
  appended bytes.
  Unverified: that encode leaves bytes *below* `start+2` alone when the range
  sits past the 64-byte window (the loop's index arithmetic does not depend on
  where the range sits, but that is an argument, not a proof).

## Run it

```sh
brew install cbmc z3            # once; CBMC 6.11.0 and z3 5.1.0 were used
.claude/skills/verify-protocol-cbmc/run.sh
```

Expected output: one `[PASS]` line per harness with its properties, seconds and
CBMC's `0 of N failed`, then `RESULT: all properties hold ...`. Exit status 0.
Measured on an Apple-silicon Mac at the sync commit, each harness alone:
frame_parse 0 s, recv_drain 58 s, recv_push 17 s, packet_begin 1 s,
packet_build 2 s, packet_add 4 s, xor_inverse 16 s, xor_window 50 s,
xor_upper 29 s; the whole run takes 3 to 4 minutes, longer when another
solver shares the machine. Each run is capped by `VERIFY_TIMEOUT` (default
600 s); a `[TIME]` line means the solver did not finish, not that the property
failed. Logs land in `$TMPDIR/verify-protocol-cbmc/` (`VERIFY_LOGDIR`
overrides).

Other modes: `run.sh --list` (the harness table), `run.sh --only NAME`,
`run.sh --trace NAME` (one harness with the counterexample trace),
`run.sh --mutants` (below).

## Reading a failure

A `[FAIL]` line is followed by the failed CBMC properties, for example:

```
[FAIL]  recv_drain    R1,R2    41s  2 of 560 failed (3 iterations)
        [cb.assertion.3] line 44 R2: frame lies inside the buffered bytes: FAILURE
        [mu_recv_drain.pointer_dereference.5] line 174 dereference failure: pointer outside object bounds in buf[...]: FAILURE
        -> R2 (harness assertion) failed
        -> R1 (CBMC memory-safety or unwinding check) failed
```

Property names starting with a harness function (`main`, `cb`, `check_add`)
are the R/S/P assertions written in the harness, in plain words. Names starting
with a product function (`mu_recv_drain`, `mu_frame_parse`, ...) are CBMC's
own checks on the product code: `array_bounds`, `pointer_dereference`,
`pointer_arithmetic`, `overflow`, `conversion`, `unwind`. Then:

1. `run.sh --trace NAME` prints the counterexample: the concrete inputs CBMC
   found and every assignment up to the violated line. Read it as a short
   story in the code's words: "the ring held `c2 00 01` (a C2 frame declaring
   size 1); drain parsed it as complete; the callback got 1 byte; `off`
   advanced by 1; ..." — write that story in the review or issue, not the raw
   trace.
2. Decide whether it is a **real bug** or a **modeling error**:
   - Real bug: the trace's inputs are something a server or caller can
     actually produce, and the violated statement is a promise the header
     makes (a guard, a size rule, a bounds guarantee). Report it with the
     story. Do not weaken the assertion or shrink the bound to make it pass;
     do not change the product code unless the user asked for a fix.
   - Modeling error: the inputs are ruled out by a caller contract the harness
     failed to assume (then add the `__CPROVER_assume` and say which contract
     it encodes), or the assertion misstates the documented rule (compare with
     `docs/research/client-net-protocol.md` and `mu_protocol.h`), or a known
     checker artifact, of which there is exactly one today: the descending loop
     in `mu_send_xor_decode` (`for (i = end; i-- > start;)`) wraps `i` to
     `SIZE_MAX` at loop exit when `start` is 0. That is defined in C and the
     value is never used, so `xor_inverse` runs without
     `--unsigned-overflow-check`; every other harness keeps it.
3. A `[TIME]` or `[ERROR]` line is neither pass nor fail. Rerun with a larger
   `VERIFY_TIMEOUT`, or look at the log for a CBMC "Invariant check failed"
   (a CBMC crash, see the tool notes below).

## What this does not prove

- Only the stated bounds: streams of up to 12 buffered bytes per drain, pushes
  of up to 0x40 bytes, 24 bytes to the parser, adds of up to 20 bytes, XorData
  round trips of up to 22 bytes. A pass says nothing about a 300-byte frame
  except through the argument that the code's loops do not depend on the size
  beyond those indices. Raising a bound is a one-line change in
  `harness/common.h` (and `--unwind` in `run.sh`); solver time grows quickly
  (recv_drain: 16 s at 8 bytes, 58 s at 12, over 7 minutes at 16).
- The C3/C4 payload cipher (the client's CryptoModule) is a documented boundary
  in the finding and is not in this module.
- Real sockets, the callers that feed `recv()` results in, the dispatcher
  behind the callback, and `nRecv`'s behaviour in the original client. The
  bit-exact agreement with the client's instructions is a separate check,
  `scripts/validate_protocol.py`, and stays so.
- `mu_recv_push` with a count larger than the ring: the harness bounds `n` to
  0x40, so the guard `r->len + n > MU_RECV_CAP` is proven only for counts a
  `recv()` into a sane buffer can return. For `n` within 0x2000 of `SIZE_MAX`
  the sum would wrap and the guard would pass; no caller passes such a count.
- Frames whose declared size is 1 or 2 (shorter than their own header) are
  delivered as 1 or 2 bytes. The client does the same (it rejects only
  `size <= 0`), so the harness accepts it; what the dispatcher makes of such a
  frame is out of scope.
- Memory and library modeling: the harnesses substitute byte-loop models for
  `memcpy`/`memmove` with C-standard semantics (see `harness/common.h`;
  `memset` is CBMC's own); the product is compiled unchanged, with the system
  preprocessor through CBMC.

## Keeping it true to the code

When a change in a verified range is intended:

1. Reread the function and the harness that covers it (table above). The
   harness comments name the guard or rule each assertion encodes.
2. If the *contract* changed (a new cap, a new head byte, a different size
   rule), change the assertion to state the new contract and the matching
   `spec_*` helper in `common.h`, then update the sentence in this file. If
   only the implementation changed, nothing in the harness should move.
3. Run `run.sh`, then `run.sh --mutants`. A planted mistake that is no longer
   caught means the harness drifted from the code: fix the harness or the
   mutant's `sed` pattern (a `[STALE]` line means the pattern no longer
   matches the source; update it to the new text).
4. Update the line numbers in the table and move the sync commit.

Layout: `harness/common.h` includes the product source (`MU_PROTOCOL_SOURCE`
defaults to `native/core/mu_protocol.c` four directories up; `run.sh` points
it at a mutated copy), defines the bounds (`PARSE_MAX`, `STREAM_MAX`,
`ADD_MAX`, `XOR_MAX`, `PUSH_N_MAX`), the `spec_*` statement of the C1..C4 rule
written independently of the product, and the library models. One `main` per
harness file. `run.sh`'s table gives each harness its backend (`sat` is CBMC's
built-in solver, `z3` is `--smt2`), unwinding depth and check set.

### Planted mistakes (`run.sh --mutants`)

Each mutant is a `sed` edit applied to a temporary copy of the product source;
the real file is never touched. The property that guards it must fail
(`[CAUGHT]`); `[MISSED]` fails the run.

| Mutant | Edit | Must fail |
|---|---|---|
| parse-size-unchecked | drop `if (size > avail) return NEED_MORE` in `mu_frame_parse` | P1, R1/R2 |
| parse-two-bytes | `avail < 3u` → `avail < 2u` | P1 |
| drain-overlap | `off += info.size` → `off += info.size - 1u` in `mu_recv_drain` | R1/R2 |
| push-no-guard | drop `if (r->len + n > MU_RECV_CAP) return -1` | R3 |
| add-no-guard | drop the `0x145a` guard block in `mu_packet_add` | S1 (`packet_add`) |
| add-size-off-by-one | the add advances the size word by `len + 1` | S1 (`packet_add`, `packet_build`) |
| begin-keeps-overflow | drop `p->overflow = 0u` in `mu_packet_begin` | S1 (`packet_begin`, `packet_build`) |
| begin-no-head | drop the head-byte add in `mu_packet_begin` | S1 (`packet_begin`) |
| finish-wrong-byte | C1/C3 size field takes the high byte instead of the low byte | S1 (`packet_begin`, `packet_build`) |
| encode-one-too-far | encode loop `i < end` → `i <= end` | S2 (`xor_upper`, `xor_window`) |
| decode-ascending | decode walks ascending instead of descending | S2 (`xor_inverse`) |

The whole mutant run takes about 5 minutes. The `run.sh` table says per
harness whether a mutant run uses `--stop-on-fail` (the z3 harnesses: one
counterexample is enough and comes fast) or a full solve (the SAT harnesses).
The `begin-keeps-overflow` mutant exists because an earlier version of the
library model let it pass: it modeled `memset` with `__CPROVER_array_set` on
the member pointer, which CBMC applied to the whole struct, clearing the flag
for the code. Keep models narrower than the code they stand in for, and keep a
mutant for every statement a model could silently absorb.

### Tool notes

- Why CBMC: the question is whether the C itself behaves for every input up to
  a bound (memory safety, framing invariants), so a checker that runs on the
  real source beats a hand model of it. It installs with one `brew` command.
- Why two backends: z3 (`--smt2`) is needed where an index into the
  0x2000-byte ring or the 0x145c-byte packet object ranges over the whole
  object (`recv_drain`, `recv_push`, `packet_add`); CBMC's SAT encoding does
  not finish there. CBMC's own SAT solver is needed for `packet_begin` and
  `packet_build`: z3 proves the real code in seconds but could not build a
  counterexample for any planted mistake in 300 s (the body offsets flow
  through memory and model construction stalls), while SAT refutes each in 1
  to 3 s. The parser and XorData harnesses are small plain arrays, fastest on
  SAT. The table in `run.sh` records the choice per harness; do not change a
  backend without rerunning `--mutants`.
- Do not use `--arrays-uf-always`. On this code it both aborted CBMC
  ("unexpected array expression: member with 'struct'") and, in a probe, let a
  read through a pointer at a symbolic offset into a struct member disagree
  with the array's contents. Every result in this skill avoids that flag.
- Why `recv_drain.c` views its receiver through a byte array (and the others
  do not): the drain reads the ring through `&r->buf[off]` at a symbolic
  `off`; on a byte array that is a plain index for the solver. The push and
  packet harnesses, which only *write* at symbolic offsets through
  `memcpy`, are faster as struct objects with the redirecting copy model.
  Each harness header says which layout it uses; `-DHARNESS_STRUCT` and
  `-DHARNESS_PLAIN_COPY` switch them.

## Related

- `/pstack:maintain-formal-verification-skill` brings this verification back
  in line after commits that touched the covered code without rechecking.
- `docs/research/client-net-protocol.md`: the finding this module implements,
  with the client addresses of each routine.
- `native/tests/test_protocol.py`, `scripts/validate_protocol.py`: the tests
  and the Unicorn comparison this skill complements.
- A close second target for the same technique: `reconstructed/boot/decoder.c`
  (`mu_decode_block`, the startup decompressor), a back-reference decoder
  whose output-bounds guards would suit the same harness shape.

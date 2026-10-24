# Protocol CLI

`mu-proto` composes and reads MU packets with the reconstructed framing (heads C1/C2 plaintext, C3/C4
CryptoModule payload; one- or two-byte size field) and the client's send obfuscation (XorData). It touches
no socket: it only runs `native/core/mu_protocol.c` on the hex you give it. The same module has a formal
bounded check in `.claude/skills/verify-protocol-cbmc`.

## Sub-features

- `proto-build` compose a frame from head, opcode and payload, optionally obfuscated.
- `proto-parse` classify a frame: head, size, header length, payload offset, status.
- `proto-dechunk` split a byte stream into frames like the receive loop, keeping a partial tail.
- `proto-xor` XorData encode and its exact inverse.

## How to get to it (user POV)

- `mu-proto build C1|C2|C3|C4 OPCODE PAYLOAD [--xor]`
- `mu-proto parse FRAME`
- `mu-proto dechunk STREAM`
- `mu-proto xor-encode OBJECT`, `mu-proto xor-decode OBJECT` (OBJECT = 2-byte little-endian size word + body)
- `mu-proto` with no arguments prints the usage.

## Driving it with run-tool.sh

Preconditions:

- `RUN` from `new-run.sh`, `V` set (no root or GL needed).

- **Build.** Run `$V/run-tool.sh "$RUN" proto-build mu-proto build C1 F1 010203`. Exit 0, stdout `frame: c106f1010203`
  (head C1, total size 6, opcode F1, payload 01 02 03).
- **Parse.** Run `$V/run-tool.sh "$RUN" proto-parse mu-proto parse c106f1010203`. Exit 0, stdout
  `head=c1 size=6 header_len=2 payload_off=2 encrypted=0 status=OK` and `payload: f1010203`.
- **Partial frame.** Run `$V/run-tool.sh "$RUN" proto-partial mu-proto parse c110f1`. Exit 0, `size=16 ... status=NEED_MORE`.
- **Bad head.** Run `$V/run-tool.sh "$RUN" proto-bad mu-proto parse 00010203`. Exit 1, stdout `status: BAD (head 00)`.
- **Dechunk.** Run `$V/run-tool.sh "$RUN" proto-dechunk mu-proto dechunk c106f1010203c2000700aabbcc`. Exit 0, two
  `frame head=.. size=..` lines (c1 size 6, c2 size 7) and `frames=2 leftover=0`. With `c106f1010203c110aa` the
  result is `frames=1 leftover=3` (the C1 frame of size 16 is incomplete and stays buffered).
- **Obfuscation round trip.** Run `$V/run-tool.sh "$RUN" proto-xor-enc mu-proto xor-encode 0400c100f101`; the last
  word of stdout is the encoded body (`6a7b47b8` at the sync commit). Run
  `$V/run-tool.sh "$RUN" proto-xor-dec mu-proto xor-decode 04006a7b47b8`; stdout `body: c100f101`.
- **Proof.** The seven `.stdout` and `.exit` files.

## Gotchas

- Arguments are hex (whitespace, `:` and `,` allowed inside); an odd nibble count or a non-hex character is
  rejected.
- `parse` exits 1 for a BAD head but 0 for NEED_MORE; `dechunk` stops at a bad head and resets, as the client
  does.
- The XOR object starts with the two size bytes; feeding a bare body shifts the key chain and the round trip
  no longer restores the input.
- C3/C4 payload encryption (the CryptoModule) is a documented boundary: `build C3 ...` frames carry the
  plaintext payload with the C3 head only.

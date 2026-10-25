# NET-LINK-001 handoff: transport, links, connections

Lane: transport-core. Branch `claude/session-core` (from `origin/claude/architect-native-port`, the design PR #161).
Plan row: `docs/design/native-port/plan.md` section B. Contract: `docs/design/native-port/sketch/native/net/`; `mu_transport.h`, `mu_link.h` and `mu_conn.h` were moved to `native/net/` (removed from `sketch/`); `dispatch.def`, `ignore.def` and `mu_crypto.h` stay (other lanes' files).

## What changed

- `native/net/mu_transport.h` (public): the byte medium. `mu_transport_sockets` (product),
  `mu_transport_replay` (stub, see open items), `mu_transport_poll` / `_flush` / `_free`, endpoint parsing
  and the loopback test (`mu_endpoint_parse`, `mu_endpoint_is_loopback`), transport counters.
- `native/net/mu_link.h` (private to net/session/fixture): `mu_transport_ops`, the loopback hook
  `mu_transport_wrap` (the fixture implements the ops in-process; FIXTURE-001 uses it), the link calls,
  and the client lock API.
- `native/net/transport.c`: the wrapper and the link calls. `transport_sockets.c`: nonblocking BSD
  sockets, kqueue on macOS (EVFILT_READ per link, a one-shot EVFILT_WRITE while connecting), poll(2) on
  other hosts so the portable build stays Linux-clean; the endpoint allowlist is checked on the
  configured host text before any name lookup or connect(2); 64 KiB inbound buffer per link with
  backpressure; outbound queue drained by flush (partial sends stay queued). `transport_lock.c`: the
  client lock. `transport_replay.c`: the replay stub.
- `native/net/mu_conn.h`, `conn.c`: `mu_net` (connections, serials, the crypto pointer), the per-connection
  read step `mu_conn_pull`, the verified dechunker (`mu_recv_push` / `mu_recv_drain`), the decode hook
  (`n->decode`, C1/C2 pass-through `mu_net_decode_plain`), `mu_net_next`, and `mu_net_send` (Send
  `0x00d51d4f`: WriteSize, then the raw send or the C3/C4 wrap by Send's first argument).
- `native/Makefile`: `core/mu_protocol.c` added to `CORE_SRC` (no code change in it); a NET-LINK-001 block
  building `build/libmunet.{dylib,so}` (net + protocol, for ctypes).
- `.claude/skills/verify-protocol-cbmc/`: one new harness `harness/link_pull.c` (properties L1, L2 on the
  link -> dechunker step), its row in `run.sh`, two planted mistakes on `conn.c` (`run.sh` gained a
  fourth mutant field naming the edited source), and the SKILL.md table, property text and timings.
- `native/tests/test_transport.py`: 11 portable tests.

### The client lock

- Always: refusal while a process whose name or any argument's basename (after `/` or `\`) is `main.exe`
  or `MuTheMatrix.exe` runs (`proc_listallpids` + `KERN_PROCARGS2` on macOS, `/proc/*/cmdline` on Linux;
  the way mu-mac-tools finds the client with `pgrep -f`), then the per-user single-instance lock:
  `flock(LOCK_EX|LOCK_NB)` on `MU_CLIENT_LOCK_PATH`, default
  `$HOME/Library/Application Support/MuTheMatrixNative/client.lock` (macOS) or
  `$HOME/.mu-the-matrix-native.lock`; the file then holds `mu-native pid N`. flock locks belong to the open
  file description, so a second transport in the same process is refused too, and the kernel releases
  the lock if the process dies. `mu_transport_free` releases it.
- `MU_AGENT=1`: in addition, `$MU_GAME_LOCK_DIR/owner` must exist and its first line equal `MU_LOCK_ID`
  (mu-autologin.sh's check). No lock path is compiled in: `MU_AGENT=1` without `MU_GAME_LOCK_DIR` is
  `MU_TRANSPORT_ERROR`. The transport never creates or removes the game lock.
- The holder's owner line (or the matching process) is copied into `error`.
- `MU_CLIENT_PROCESS_NAMES` (comma list) replaces the two process names; the tests use a random name so
  the owner's own running game cannot decide them.

## Checks actually run

- `native/tests/test_transport.py` (portable, ctypes on `build/libmunet`): **11/11 pass** - allowlist refusal
  before connect (refused peer never sees a connection; `connects_attempted == 0`), a connection that does not
  widen the allowlist (only `mu_net_allow` does), partial reads (a
  4-frame stream sent one byte at a time comes out as the same 4 frames), partial writes (8 MiB queued
  against a peer that does not read: pending > 0 across flushes, then all bytes arrive in order), the
  0x2000 guard (a C2 frame declaring 0x3000: no frame, `MU_DECODE_OVERFLOW`, sticky), frames before the
  guard delivered, lock held -> `MU_TRANSPORT_LOCKED` with the owner line and released on free, a lock
  held by another process (Python `fcntl.flock`) refused, the game-lock owner check (no dir, not held,
  foreign `MU_LOCK_ID`, missing `MU_LOCK_ID`, matching id; the owner file is left in place), a stand-in
  process with argv[0] `C:\MuTheMatrix\<name>` refused (and the default names include `main.exe` and
  `MuTheMatrix.exe`). Every peer is a socket the test opens on 127.0.0.1; every lock is in a temp dir.
- `verify-protocol-cbmc` (`.claude/skills/verify-protocol-cbmc/run.sh`, CBMC 6.11.0, z3 5.1.0), after the
  `CORE_SRC` change: **10/10 harnesses PASS** - the 9 existing `mu_protocol.c` harnesses unchanged
  (frame_parse 0 of 566, recv_drain 0 of 545, recv_push 0 of 470, packet_begin 0 of 460, packet_build
  0 of 471, packet_add 0 of 475, xor_inverse 0 of 443, xor_window 0 of 474, xor_upper 0 of 455 failed)
  plus the new `link_pull` (0 of 1091 failed, 37 s). `run.sh --mutants`: **13/13 planted mistakes caught**
  (the 11 existing ones in 18 harness runs as before, plus `pull-no-guard` and `pull-room-plus-one` on
  `conn.c`, both caught by `link_pull`). The final rerun on the committed tree is in the PR description.
- `make test` and `scripts/audit_repository.py`: see the PR description (run once on the whole branch).

## Artifacts

- CBMC logs: `$TMPDIR/verify-protocol-cbmc/` by default; this run used the session scratchpad
  (`.../scratchpad/cbmc-logs`), not committed.
- Built: `native/build/libmunet.dylib` (ignored).

## Deviations from the sketch

1. `mu_conn.h` does not include `mu_crypto.h` (the crypto lane's file): `struct mu_crypto` is forward-declared.
   The decode stage and the send wrap are function pointers in `mu_net` (`decode`, default
   `mu_net_decode_plain`; `wrap`, default NULL) instead of a `mu_decode` symbol here, so NET-DECODE-001's
   `decode.c` plugs in without a duplicate symbol: it defines its `mu_decode` (and the wrap) with the
   `mu_decode_fn` / `mu_wrap_fn` signatures and sets them in `mu_net_init` (a one-line change in `conn.c`).
2. `mu_frame.bytes` holds `MU_RECV_CAP` (0x2000) bytes, not `MU_PACKET_OBJ`: the dechunker can cut any frame
   that fits its ring; the client's packet queue capacity (0x01291777) is NET-DISPATCH-001's to recover.
   Bytes past a frame's length are zeroed (deterministic reads by handlers of short frames).
3. `mu_decode_status` gained `MU_DECODE_OVERFLOW` (the 0x2000 guard). `MU_DECODE_BAD` is a frame shorter than
   its header plus the opcode byte (journaled, not applied; what the client does with one is open).
4. The client stops receiving on the guard (it logs and returns without recv); the session (SESSION-CORE-001)
   closes with `MU_CLOSE_RECEIVE_OVERFLOW`, the sketch's reason.
5. Additions not in the sketch: `mu_transport_counters`, `mu_endpoint_parse`, `mu_endpoint_is_loopback`,
   `mu_transport_impl`, the ops `counters` hook, `mu_endpoint_equal`, the client-lock functions (in
   `mu_link.h`: no private header of my own is in the lane's owned paths), `mu_net_create/_destroy` (ctypes),
   `mu_net_state`, and `mu_conn_pull` as a public step (the CBMC harness drives it). `mu_conn` keeps the
   ring as its first member (the harness indexes it from the object's start) and a queue of the frames one
   drain cut (`pend`), so `mu_net_next` hands them out one at a time through the verified `mu_recv_drain`.
6. kqueue only where it exists (macOS, FreeBSD); poll(2) elsewhere.
7. The process refusal and the per-user lock apply in both modes; `MU_AGENT=1` adds the game-lock check.
8. `mu_net_connect` opens without allowing: the sketch's "allow + open" would let any endpoint the session
   connects to through. The transport is created with the configured connect server allowed; an endpoint the
   session learns from the service is added explicitly with the new `mu_net_allow` (F4 03, a room's chat
   server). Tested: a connection to an endpoint nobody allowed is `MU_LINK_REFUSED`.

## Static reading used here (evidence for NET-DECODE-001)

Target: restored main.exe first section, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`
(capture09, base `0x00401000`). Method: Capstone disassembly (`scratchpad/dis.py`, not committed). Observation:
- Send `0x00d51d4f(a, b)`: WriteSize `0x00d51c1f`, a one-byte routine `0x00d51d86` (`ret`), then
  `0x00d51e87(body, size, a, b)`, whose first instruction jumps into the protection (`jmp 0x10b46cb0`); the
  body after it: `cmp [ebp+0x10], 0` at `0x00d51e97` - when Send's first argument is 0 the bytes go to the raw
  sender `0x00d52159` as built; otherwise a copy gets a random byte appended, its head becomes C2 when the
  second argument is non-zero, the send serial `[0x06fca01d]` is stored and incremented, and Encrypt
  `0x018df500` on `g_enc 0x06fce2fc` runs; a result under 0x100 bytes with the second argument 0 becomes a C3
  frame (`0x00d51f85`), else the C4 path.
- Receive `0x01290792`: `cmp [this+0x4014], 0x2000; jl` at `0x0129079e`/`0x012907a8`, else the overflow log
  (`0x01206598`) and return; recv into `this+0x2014+len` for `0x2000 - len` bytes (`0x012907c3..0x012907ee`).
Inference: Send's first argument selects the encrypted (C3/C4) path; the second promotes to the 2-byte size.
Unresolved: the random byte's role, the displaced first instruction of `0x00d51e87`, and what the serial and
the channel `[0x1cf1008]` are per connection (NET-DECODE-001).

## Open items

- `mu_transport_replay` is a clean stub: it returns NULL with "replay transport not implemented (NET-LINK-001
  stub)" and never aborts. It needs a recording (CAPTURE-KIT-001) and the journal's FRAME records (the journal
  format exists since SESSION-CORE-001: FRAME records carry the connection and the dechunked bytes; outbound
  records carry the built frame). The divergence-report evidence of the plan row is therefore not done.
- C3/C4: inbound C3/C4 frames are `MU_DECODE_CRYPTO` (journaled as undecodable); `Send(1, ..)` is refused
  with `MU_SEND_NEEDS_CRYPTO` and nothing is written. Both wait for NET-CRYPTO-001 / NET-DECODE-001.
- The 64 KiB inbound buffer and the blocking `getaddrinfo` in open are choices, not client facts.

## Next step

NET-DECODE-001 (crypto lane) installs `mu_decode` and the wrap through `n->decode` / `n->wrap`, and moves
`link_pull`'s neighbours (a CBMC bounds harness on `mu_decode`) next to it.

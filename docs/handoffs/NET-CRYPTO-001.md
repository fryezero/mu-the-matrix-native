# NET-CRYPTO-001 handoff: the C3/C4 CryptoModule over Crypto++

Lane: crypto. Branch: `claude/net-crypto` (from `origin/claude/architect-native-port`, builds on #161).

## What changed

Reconstructed the client's C3/C4 payload cipher (the "CryptoModule") as a native library over
Crypto++, verified against the client's own instructions. This closes the boundary the earlier
network finding left open (17 ciphers and the key string were known; the keyschedule, hash
selection, counters and rekeying were not).

New / edited files (lane-owned):

- `native/net/mu_crypto.h`, `native/net/crypto.cpp` — the C ABI module (`libmucrypto`). Keeps the
  client's two maps (`g_enc`/`g_dec`) in one `mu_crypto`; ctor seeding, CreateCtx/Remove, SetKey
  (hash selection, cipher choice, interval), Encrypt/Decrypt per channel with rekeying; caller-owned
  buffers, explicit lengths; plus a cipher-holder layer and `mu_crypto_block` for KATs.
- `native/Makefile` — a `NET-CRYPTO-001` block (own block, commented): `libmucrypto` and the
  `crypto-mutants/libmucrypto_m%` mutation targets. `CORE_SRC` untouched (another lane owns it).
- `scripts/validate_crypto.py` — Unicorn comparison of the client's ctor, CreateCtx/Remove/getters,
  SetKey, factory, Encrypt and Decrypt against the module; six families, per-call buffer and
  full-context comparison, coverage gates, 14 planted mistakes (`-DMU_CRYPTO_MUTATION=k`).
- `native/tests/test_crypto.py` — portable (CI) KATs for all 17 cases, round trips, rekey-boundary
  round trips through the full module.
- `tests/test_crypto_private.py` — gates the Unicorn comparison on `MU_RECOVERY_INTEGRATION`.
- `docs/research/client-crypto.md` — the finding. Pointer added to the CryptoModule section of
  `docs/research/client-net-protocol.md`.

## Checks run

- `make -C native build/libmucrypto.dylib` — builds clean (`-Wall -Wextra -Werror -Wconversion`).
- `python -m unittest discover -s native/tests -p 'test_crypto.py'` — 15 portable tests pass.
- `make test PYTHON=tools/python/bin/python` (the main checkout's interpreter) — exit 0,
  1188 tests, 0 failures; private suites (including `test_crypto_private`) skip explicitly without
  `MU_RECOVERY_INTEGRATION`.
- `scripts/audit_repository.py` on the staged tree — 0 rejected.
- Public header compiles as C11 (`-Wall -Wextra -Werror`).
- Private: `scripts/validate_crypto.py --mutations` under Unicorn over the pinned captures
  (default seed 20261025, scale 4, 151 s). Result: 1,073 cases, 15,834 compared calls, 0
  mismatches (ctor 2, open 240, set_key 548, factory 148, encrypt 68, decrypt 67 cases). All 17
  factory cases are reached in set_key, factory, encrypt and decrypt, and all 11 selector values
  in set_key. Rekeys happen at intervals 8, `0x20` and `0x800` in both directions. All 14
  planted mistakes are caught, and no coverage problem is reported.
- `tests/test_crypto_private.py` (scale 2, mutations) passed in 133 s with
  `MU_RECOVERY_INTEGRATION=1`. The worktree has no `evidence/`, so I set `MU_CLIENT_TEXT`,
  `MU_IMAGE_DATA` and `MU_CPU_FEATURES` to the main checkout's captures.
- First-probe cross-check: the module's encrypt of the seed-keyed socket channel reproduces the
  client's output byte for byte.

## Artifacts

- `verify-runs/net-crypto-001/validate_crypto.json` and `.log` in the worktree (ignored, not
  committed): the final report. It pins SHA-256 digests of the allowlisted code ranges and the
  routine bodies, and lists the seeded globals, per-family coverage and the mutation results.

## Deviations from the sketch

- `mu_crypto_run` (the sketch's single in-place `buf`/`cap`/`out_len` form) is kept, and
  `mu_crypto_call` (separate `dst`/`src`, the client's own argument shape) was added as the
  primary entry; `run` wraps `call`. The validator and NET-DECODE-001 want the client's two-buffer
  shape and the exact return value, which `run` alone hides.
- Added `mu_crypto_set_key` returning a `mu_crypto_choice` (hash, cipher, sub-cipher, interval,
  key-length, key) as the sketch asked, plus inspection calls (`mu_crypto_view_channel`,
  `mu_crypto_channels`, the getters `cipher_index`/`enc_count`/`dec_count`) and a cipher-holder
  layer (`mu_crypto_cipher_*`, `mu_crypto_block`) the sketch did not name — needed so the validator
  and the portable KATs can compare per-context state and single blocks.
- Added a native-only refusal `MU_CRYPTO_OUTSIDE` (`-2`) for inputs where the client would overrun
  its own `0x1000`-byte stack buffers (Encrypt output > 0x1000, Decrypt input > 0x1000 with a
  recovered length still in 1..0x1000). In range the module equals the client exactly; this only
  refuses to reproduce an out-of-bounds write.
- `mu_crypto_new_server_side` is literally `mu_crypto_new` (the cipher is symmetric in its state,
  so the mirror end is the same object construction); documented in the header.

## Open items

- `native/net/crypto.cpp` is its own `libmucrypto` target and is NOT in `CORE_SRC`; whoever wires
  the net library into the session/transport build (transport-core lane) will link it.
- The portable KATs anchor DES-EDE2 and DES-XEX3 structurally on the DES case and 3-Way/RC5/GOST/
  SAFER on reference implementations in the test; if Crypto++'s published TestData files are added
  to the tree later, those could replace the in-test references.

## For NET-DECODE-001

- The two Decrypt calls (C3 `0x01222223`, C4 `0x01222266`) sit in the receive stage
  `0x012220fd`, not in `0x01221b94` as the plan says; `0x01221b94` is a separate function called
  from `0x01224496`. The send wrap (entry `0x00d51e87`) calls Encrypt as a size query, then for C3
  or C4. Use `mu_crypto_call(c, MU_CRYPTO_DEC or MU_CRYPTO_ENC, channel, dst, cap, src, len)` for
  the client's exact return value, or `mu_crypto_run`.
- The channel is the socket object's address, as a signed `int`: `0x06fca2d8` for the global
  socket, or other socket objects (the current-socket pointer `0x01cf1008`, the per-connection
  list). Any `int` works for the module; which socket is open in which phase is NET-DECODE-001's.
- Still NET-DECODE-001's: where the serial goes (`g_byPacketSerialSend` `0x06fca01d`,
  `g_byPacketSerialRecv` `0x06fca01e`) and the `Decrypt error` check; the random byte stored after
  the frame at `0x00d51edb`; the C1 `0x4D` packet built at `0x0122227f` when Decrypt fails.
- An empty payload encrypts to the pad byte alone, which the receiver's Decrypt rejects
  (recovered length 0) after the sender has already counted it. The two ends then fall out of
  step. Real frames always carry at least serial and opcode, so this cannot happen on the wire,
  but the fixture must not send empty C3 bodies.
- Blocked (BP), not analysed: whether code outside `main.exe` re-keys a channel (the hooked
  connect, close, send and receive sites, and the uncalled SetKeyChannel). Test once recordings
  exist: decrypt recorded C3/C4 frames with this model (LIVE-COMPARE-001).

## Next step

NET-DECODE-001 (the next milestone in this lane). Reconstruct the receive stage `0x012220fd`
(C1/C2 pass-through, C3/C4 through `mu_crypto_call` on the DEC map, the serial check) and the
send wrap entered at `0x00d51e87`, as Unicorn families with planted mistakes plus the CBMC
harness the plan names.

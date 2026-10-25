# Client C3/C4 CryptoModule: full reconstruction over Crypto++

NET-CRYPTO-001 reconstructs the game client's own C3/C4 payload cipher (the "CryptoModule")
as a native library over Crypto++, verified against the client's actual instructions. The
earlier network finding ([client-net-protocol.md](client-net-protocol.md)) identified the 17
ciphers and the key string by emulation but left the keyschedule, hash selection, counters and
rekeying as a documented boundary; this finding closes that boundary.

The work is offline: no server was contacted and no live client state was read. The `ws2_32`
calls and `IGC.dll` remain untouched (see [the boundary](#protection-boundary-and-key-origin)).

## Evidence

Virtual addresses are in the pinned `main.exe` (SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`). Behaviour was observed by
running the client's own routines under Unicorn over:

| Capture | SHA-256 | Base |
| --- | --- | --- |
| Restored first section | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` | `0x00401000` |
| Verified second image section | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` | `0x01a7c000` |
| CPU feature word (`0x01cf6618`) | `bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9` | — |

The third image section (RTTI type names for the cipher and hash classes) was read from the
offline guest capture `evidence/x86-guest-sec3-25/main-01ced000.bin` (base `0x01ced000`); it is
observation of class identity only and is not needed to run the routines.

"Verified" below means the authored module was compared byte for byte against the client's
instructions under Unicorn (`scripts/validate_crypto.py`); "observed" means read from a run but
not yet in a comparison family; "static" means read from the disassembly only.

## Objects and addresses (verified)

Two module objects: the encrypt map `g_enc` (`0x06fce2fc`) and the decrypt map `g_dec`
(`0x06fce31c`). Each is a `std::map<int, context*>` (MSVC red-black tree) plus a `std::string`
holding the key string `98135003732920532106543021784355` (32 bytes). Both are constructed by
the one constructor `0x018df200`, called at process start from `0x008dd4b9` (g_enc) and
`0x008dd4d3` (g_dec); the string is assigned at `0x018df261`.

| Routine | Address | Role |
| --- | --- | --- |
| Constructor | `0x018df200` | empty map + seed string (both maps) |
| CreateCtx | `0x018df700` | (re)create a channel's context, seed-keyed |
| Remove | `0x018df3f0` | destroy a channel's context |
| SetKeyChannel | `0x018df5c0` → SetKey `0x018ea8d0` | re-key a channel |
| Encrypt | `0x018df500` | encrypt on `g_enc` |
| Decrypt | `0x018df460` | decrypt on `g_dec` |
| GetCipherIndex / GetDecCount / GetEncCount | `0x018df610` / `0x018df660` / `0x018df6b0` | getters (no in-image callers) |
| Factory | `0x018ea540` | build one of 17 Crypto++ block ciphers |
| Rekey | `0x018df9c0` → SetKey | re-key a context from its state table |
| Update | `0x018dfed0` | record plaintext bytes into the state table |
| Hash table | `0x018eaf30` (10 entries) | hash selection in SetKey |
| Factory jump tables | `0x018ea884` (index), `0x018ea8ac` (index-9 sub) | — |

In-image users (static):

* the send wrap entered at `0x00d51e87` calls `Encrypt` on `g_enc` three times
  (`0x00d51f66` size query with `dst = NULL`, `0x00d51fb9` C3, `0x00d52037` C4);
* the receive stage `0x012220fd` calls `Decrypt` on `g_dec` (`0x01222223` C3, `0x01222266` C4);
* socket connect `0x01290490` calls `CreateCtx` on `g_enc` (`0x012905bb`) and `g_dec`
  (`0x012905c8`); the socket close routines `0x01290350` and `0x01290447` call `Remove` on
  `g_enc` (`0x0129041d`, `0x01290466`) and `g_dec` (`0x0129042a`, `0x01290473`).

At the `g_enc` CreateCtx and Remove sites the instruction before the call is a `jmp` out of
`main.exe` followed by the leftover bytes `e2 fc 06`. Those are the tail of
`push [ebp-4]; mov ecx, 0x06fce2fc` (`ff 75 fc b9 fc e2 fc 06`) whose first five bytes the
`jmp` overwrote. That reading is an inference from the leftover bytes, not an execution. The
same pattern sits at the send-wrap entry `0x00d51e87` and the receive-stage entry `0x012220fd`.
`SetKeyChannel` `0x018df5c0` and the three getters have no caller in the restored text.

## The context record (0x98 bytes, verified)

CreateCtx `0x018df700` allocates `0x98` bytes (`operator new`) and sets:

| Offset | Field | CreateCtx value |
| --- | --- | --- |
| `+0x00` | channel integer | the argument |
| `+0x04` | encrypt packet counter | **1** |
| `+0x08` | decrypt packet counter | **1** |
| `+0x0c..+0x8b` | 128-byte state table | filled with `0x63` (`memset`, `0x018df7e3`) |
| `+0x8c` | unused word | 0 (never read) |
| `+0x90` | cipher holder (`cipher*`) | set by SetKey |
| `+0x94` | cipher index | set by SetKey |

Then SetKey `0x018ea8d0` is called with the key string to key `+0x90`. CreateCtx destroys any
existing context for the channel first (`0x018df763`: the holder's `operator delete` of `0x98`
bytes), so a re-create starts counters at 1 again.

## SetKey: hash selection and cipher choice (verified)

`SetKey(this=holder, key, key_len)`:

1. Zero a `0x800`-byte digest buffer (`0x018ea924`).
2. Compute a selector byte (`0x018ea92c`): with `key_len < 10`, the selector is `key[0]`. With
   `key_len >= 10` it is `((key[0] ^ key[1]) < (key[2] % 3) ? 1 : 0) | key[3]) ^ key[4]` — a
   `setl` of the comparison OR'd with `key[3]` then XOR'd with `key[4]`.
3. `selector % 11` (`0x018ea965`) indexes the 10-entry hash table `0x018eaf30`. The entries are
   the hash classes below; `dec eax` before the `cmp eax, 9` makes selector `0` fall through to
   the default handler `0x018eae48`, and table slot index `1` (selector `2`) is also the default
   (its table entry `0x018eae48`). So selectors 0 and 2 share the default.
4. The chosen hash digests the key. The cipher index is `digest[j] % 10` for a hash-specific
   byte `j` (below), stored at the context's `+0x94` (`0x018ea9e6`).
5. The factory `0x018ea540(index, digest_buffer, digest_size)` builds the cipher from the
   **zero-filled digest buffer** (so cipher key bytes past the digest size are zero).

Selector → hash → digest byte `j` → factory key length (all verified against the client):

| `selector % 11` | Hash (RTTI) | digest byte `j` | key length |
| --- | --- | --- | --- |
| 0, 2 (default) | MD5 (`CryptoPP::Weak1::MD5`) | 9 | 16 |
| 1 | SHA-256 | 0 | 32 |
| 3 | SHA-512 | 1 | 64 |
| 4 | SHA-384 | 2 | 48 |
| 5 | MD4 (`Weak1::MD4`) | 3 | 16 |
| 6 | MD5 | 4 | 16 |
| 7 | RIPEMD-160 | 5 | 20 |
| 8 | RIPEMD-320 | 6 | 40 |
| 9 | RIPEMD-128 | 7 | 16 |
| 10 | RIPEMD-256 | 8 | 32 |

The seed string `98135003732920532106543021784355` (used for the first key of every context)
is `key_len 32 >= 10`; its selector resolves to the default MD5 entry, whose digest's byte 9 is
`0xef`, `% 10 = 9` → factory index 9, and `digest[0] & 7 = 4` → sub-cipher DES-XEX3. So every
freshly created context starts on **DES-XEX3** until the first server-driven re-key.

## The factory: 17 ciphers (verified)

`factory(index, key, key_len)`: `index % 10` selects a class through `0x018ea884`; index 9
selects a sub-cipher from `key[0] & 7` through `0x018ea8ac`. Each class is a Crypto++
`ConcreteCipher<T, interval>` whose `+0x04` carries its rekey interval (written by the class's
own SetKey). The 17 cases, confirmed by RTTI type names (`.?AV?$ConcreteCipher@V<T>@CryptoPP@@`)
and by known-answer / reference tests through the C ABI:

| Case | Index·sub | Cipher | Key bytes | Block | Rekey interval |
| ---: | --- | --- | ---: | ---: | ---: |
| 0 | 0 | TEA | 16 | 8 | 0x800 |
| 1 | 1 | 3-Way | 12 | 12 | 0x800 |
| 2 | 2 | CAST-128 | 16 | 8 | 0x800 |
| 3 | 3 | GOST | 32 | 8 | 0x800 |
| 4 | 4 | RC5 | 16 | 8 | 0x800 |
| 5 | 5 | RC6 | 16 | 16 | 0x800 |
| 6 | 6 | MARS | 16 | 16 | 0x800 |
| 7 | 7 | IDEA | 16 | 8 | 0x800 |
| 8 | 8 | GOST | 32 | 8 | 0x800 |
| 9 | 9·0 | Twofish | 16 | 16 | 8 |
| 10 | 9·1 | DES | 8 | 8 | 8 |
| 11 | 9·2 | DES-EDE2 | 16 | 8 | 8 |
| 12 | 9·3 | DES-EDE3 | 24 | 8 | 0x20 |
| 13 | 9·4 | DES-XEX3 | 24 | 8 | 8 |
| 14 | 9·5 | SKIPJACK | 10 | 8 | 0x20 |
| 15 | 9·6 | SAFER-K | 16 | 8 | 8 |
| 16 | 9·7 | SAFER-SK | 16 | 8 | 0x20 |

Indices 3 and 8 are both plain GOST (two jump-table slots). Each class keys itself with its
fixed key length (the `push` before the SetKey call in each wrapper constructor) regardless of
the length the factory was given, with Crypto++'s default rounds (`g_nullNameValuePairs`,
`0x01d04e70`, initialised by `0x008dfa20`). The intervals are the template argument of each
`ConcreteCipher` (8, 0x20 or 0x800), read from wrapper `+0x04`.

## Encrypt / Decrypt and rekeying (verified)

`Encrypt(channel, dst, src, len)` looks up the channel's context in `g_enc` (`-1` if none),
then runs the class Encrypt (vtable slot 2):

* `pad = (block - len % block) % block` (0 when already aligned); output length `= len + 1 + pad`.
* The `len` source bytes are copied into a zero-filled block-aligned buffer; the cipher runs in
  **ECB** over the whole buffer (the final, all-zero block is computed and discarded); the last
  output byte (`out - 1`) is set to the pad count.
* `dst == NULL` is a size query: it returns the output length and changes nothing.

`Decrypt(channel, dst, src, len)` (requires `dst != NULL`, else `-1`) runs the class Decrypt
(slot 3): `-1` unless `len % block == 1`; the recovered length is `n = len - src[len-1] - 1`; a
size query (unusual) returns `n`; with a destination it requires `1 <= n <= 0x1000` (else `-1`),
runs ECB over the blocks covering `n` bytes and copies `n` bytes out. An empty plaintext encrypts
to a single pad byte and then decrypts to `n = 0`, which the client rejects (`-1`).

After a successful call the direction's counter steps (`Update` then the counter): the plaintext
(the `src` of Encrypt, the recovered `dst` of Decrypt) is recorded by Update `0x018dfed0` — for
`n > 8` (signed) the first 8 bytes, for `0 < n <= 8` the first byte, each as `state[b & 0x7f] = b`;
then if the counter **equals the interval** the context is re-keyed with `SetKey(state, 128)`
(Rekey `0x018df9c0`) and the counter restarts at **1**, otherwise the counter is incremented.
Because both ends record the same plaintext, their 128-byte state tables stay identical and they
re-key to the same cipher in step.

### Channel integers (static)

The channel key is the address of a socket object (the `CWsctlc` class constructed at
`0x012900cd`), used as a signed `int`:

* connect and close pass the socket's own `this` (`[ebp-4]`);
* the send wrap passes `[0x01cf1008]`, the current-socket pointer. It holds the global socket
  `0x06fca2d8`, and some senders swap in another socket object for one send and restore it
  (for example `0x009cc57b` .. `0x009cc58f`);
* the receive stage passes its first argument: the global socket `0x06fca2d8` (call at
  `0x0120effd`) or a socket object taken from a per-connection list (call at `0x011f12f6`).

So the channels are `0x06fca2d8` plus the addresses of any other socket objects the client
creates. The value only selects a map entry: no channel is special-cased, and the cipher output
does not depend on the number. Which connection is open in which phase (login, game, the
connect-to-game hop) belongs to NET-DECODE-001.

## Protection boundary and key origin

Inside `main.exe`, all key material the CryptoModule uses is internal. The first key of every
context is the constant seed string `98135003732920532106543021784355`. After that the key is
the context's own 128-byte state table: seeded `0x63`, then changed by the recorded plaintext.
No in-image path takes a key byte from received data. The packet serials
`g_byPacketSerialSend` (`0x06fca01d`) and `g_byPacketSerialRecv` (`0x06fca01e`) are frame
bytes, not cipher keys (their semantics belong to NET-DECODE-001). The cipher is bundled
Crypto++ game code, and its reconstruction is not blocked.

**Unresolved and blocked (BP):** whether code outside `main.exe` changes channel keys. The four
outbound `jmp` sites listed above lead outside the image (to `IGC.dll` addresses, as in the
frame-loop finding). `SetKeyChannel` and the getters have no in-image caller. Following those
jumps would mean analysing `IGC.dll`, which is out of scope, so this was not done. A test that
avoids that boundary: once recordings exist (CAPTURE-KIT-001), decrypt recorded C3/C4 frames
with this `main.exe`-only model. Frames that do not decrypt to a valid serial and opcode would
show that keys come from elsewhere.

## The native module

`native/net/mu_crypto.h` and `native/net/crypto.cpp` build `native/build/libmucrypto` over
Crypto++ (already a repository dependency). The C ABI keeps the client's two maps in one
`mu_crypto`, with caller-owned buffers and explicit lengths; `mu_crypto_new_server_side` is the
same constructor named for the fixture's mirror end (the cipher is symmetric in its state, so the
server's ENC map mirrors the client's DEC map). A native refusal `MU_CRYPTO_OUTSIDE` (`-2`)
marks the inputs where the client would overrun its own `0x1000`-byte stack buffers; every
in-range result equals the client's.

## Verification

`scripts/validate_crypto.py` (private, Unicorn) runs the client's ctor, CreateCtx/Remove/getters,
SetKey, factory, Encrypt and Decrypt against the module over seeded keys, channels, lengths and
rekey boundaries, comparing the return value, the whole destination buffer, every context
(map order, channel, counters, the 128-byte state, the cipher index, class and interval) and the
factory calls SetKey made. Allowlisted code regions and the entered routine bodies are pinned by
SHA-256 in the JSON report. Execution outside the allowlist, an undefined read, or a use after
free stops a case.

* Default run (seed 20261025, scale 4, 151 s): 1,073 cases, 15,834 compared calls, 0 mismatches.

  | Family | Cases | Calls |
  | --- | ---: | ---: |
  | ctor | 2 | 2 |
  | open | 240 | 1,895 |
  | set_key | 548 | 701 |
  | factory | 148 | 1,036 |
  | encrypt | 68 | 7,061 |
  | decrypt | 67 | 5,139 |

* The set_key, factory, encrypt and decrypt families each reach all 17 factory cases. SetKey
  reaches all 11 selector values, so every entry of the 10-entry hash table plus the default.
  Rekeys happen at every interval in both directions: encrypt 46 at 8, 7 at `0x20` and 2 at
  `0x800`; decrypt 48, 5 and 1.
* Selector 1 (SHA-256) cannot reach Twofish, DES-EDE2, DES-XEX3 or SAFER-K. Its cipher index and
  its index-9 sub-cipher both come from `digest[0]`. `digest[0] % 10 == 9` makes the byte odd,
  so only the odd sub-ciphers can follow. The validator skips these four selector/case pairs
  because they cannot occur.
* 14 planted mistakes (`-DMU_CRYPTO_MUTATION=k`) are each caught: selector comparison, `% 11`,
  the RIPEMD-128/256 table swap, the default digest byte, the index-9 sub-cipher byte, the
  SKIPJACK interval, the empty-block pad rule, the Update count and mask, the rekey counter
  reset, the Decrypt length rule, the Decrypt record source, and the CreateCtx counter start.

Portable tests (`native/tests/test_crypto.py`, CI, no client bytes) check all 17 cases through
the C ABI against published single-block vectors (TEA, 3-Way, CAST-128, RC6, MARS, IDEA, Twofish,
DES, DES-EDE3, SKIPJACK), independent reference implementations (RC5, GOST, SAFER-K, SAFER-SK)
and structural builders over the verified DES case (DES-EDE2, DES-XEX3), plus encrypt/decrypt
round trips over every length and full-module round trips across rekey boundaries.
`tests/test_crypto_private.py` gates the Unicorn comparison on `MU_RECOVERY_INTEGRATION`.

## Unresolved / handoff to NET-DECODE-001

* Which connection (login or game) is open in which phase, and the serial semantics across the
  connect-to-game hop, belong to NET-DECODE-001. The CryptoModule accepts any `int` channel, and
  in `main.exe` it reads no key material from received data. NET-DECODE-001 can call
  `mu_crypto_call` or `mu_crypto_run` directly for the C3/C4 steps. See the pointer added to
  [client-net-protocol.md](client-net-protocol.md#c3--c4-cryptomodule-verified-structure-boundary-for-reconstruction).
* The send wrap (entry `0x00d51e87`) and the receive stage `0x012220fd` were read only far
  enough to confirm the Encrypt/Decrypt call shapes and the C3/C4 head and length handling. Their
  full framing is NET-DECODE-001's to reconstruct: where the serial goes, the random byte stored
  after the frame at `0x00d51edb`, and the C1 `0x4D` packet built at `0x0122227f` when Decrypt
  fails. The plan names `0x01221b94` as the decode stage, but the two Decrypt calls are inside
  `0x012220fd`; `0x01221b94` is a separate function called from `0x01224496`.
* Whether code outside `main.exe` re-keys a channel is blocked by the protection boundary (see
  above).

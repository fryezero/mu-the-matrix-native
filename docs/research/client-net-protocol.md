# Client network protocol: framing, send obfuscation and the receive dispatcher

NATIVE-NET-001 recovers the game client's own network protocol layer from
`main.exe` so a native client can later talk to the owner's Mu The Matrix
server. The work is offline: no server was contacted, no live traffic captured,
and the running game and bottles were not touched. The `ws2_32` calls
(`socket`, `connect`, `send`, `recv`, `closesocket`, `WSAStartup`,
`WSAAsyncSelect`) are platform boundaries; everything described here is the
client's own code around them.

Evidence is the restored first section (SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, imported at
`0x00401000`) and the verified second image section (SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, VA
`0x01a7c000`) of the pinned `main.exe` (SHA-256
`3cf91f3c…5527a`). Addresses are virtual addresses in that image. "Verified"
means the authored C or a model was compared against the client's actual
instructions under Unicorn; "static" means read from the disassembly only.

## Scope and the protection boundary

The socket class, framing and the client's send obfuscation are plain game code
and are reconstructed and verified here. The heavier C3/C4 payload cipher is a
bundled Crypto++-style library (the "CryptoModule"); it is **documented as a
boundary and not reconstructed** in the C module. No `IGC.dll`, `RGS.dll` or
packer code is touched, and nothing here impersonates the launcher session or
bypasses a server check — it is protocol documentation only.

## Socket class (static)

The client wraps a Winsock client socket in a class constructed at
`0x012900cd`. Field layout, read statically:

| Offset | Meaning |
|---|---|
| `+0x00` | owner window handle |
| `+0x04` | "is server socket" flag |
| `+0x0c` | `SOCKET` handle |
| `+0x10` | send buffer, `0x2000` bytes |
| `+0x2010` | pending send length |
| `+0x2014` | receive buffer, `0x2000` bytes |
| `+0x4014` | receive length |
| `+0x4020` | packet-queue object |

Methods: Winsock init `0x012901d0` (requests `WSAStartup` 2.2), create
`0x012902a7` (`socket(AF_INET, SOCK_STREAM, 0)`), close `0x01290350`, connect
`0x01290490` (resolves with `inet_addr`/`gethostbyname`, `connect`, then
`WSAAsyncSelect` message `0x23`), buffered send `0x012905d4`, the `FD_WRITE`
drain `0x012906d4`, and the receive reader `0x01290792`. A second standalone
sender lives at `0x00d52159`.

## Framing: C1 / C2 / C3 / C4 (verified)

MU frames begin with a head byte and a length field:

| Head | Size field | Header bytes | Payload |
|---|---|---|---|
| `0xC1` | `buf[1]` (1 byte) | 2 | plaintext |
| `0xC2` | `buf[1..2]` big-endian (2 bytes) | 3 | plaintext |
| `0xC3` | `buf[1]` (1 byte) | 2 | CryptoModule |
| `0xC4` | `buf[1..2]` big-endian (2 bytes) | 3 | CryptoModule |

The size field is the **total** frame length, header included. The receive
reader `0x01290792` appends `recv()` bytes to `+0x4014`, then, while at least 3
bytes are buffered, reads the head, computes the size by the rule above, and —
when the whole frame is present — hands `size` bytes to the packet queue
(`0x01291777`); a frame larger than the buffer waits for more, and a head that
is not `0xC1..0xC4` resets the receive length to 0. This exact loop is
reproduced by `mu_recv_drain` / `mu_frame_parse` and verified against the
client's instructions over 300 synthetic multi-frame streams (0 mismatches).

## Packet builder and send obfuscation (verified)

The outbound packet object is `0x1460` bytes: a 2-byte little-endian length word
then up to `0x145a` body bytes. The builder:

* **Init** `0x00d52133` clears it; **Begin** `0x00d51baf` lays down the head
  byte, reserves the size field (1 byte for C1/C3, 2 for C2/C4) and appends the
  opcode byte.
* **AddData** `0x00d51c9b` appends body bytes and, when its encode flag is set,
  runs the send obfuscation over exactly the appended range.
* **WriteSize** `0x00d51c1f` patches the size field with the final body length;
  **Send** `0x00d51d4f` finalizes and calls the raw sender.

The send obfuscation is **XorData** `0x00d52055`, a chained XOR with a 32-byte
key held as immediates at `0x00d5205e`:

```
ab 11 cd fe 18 23 c5 a3 ca 33 c1 cc 66 67 21 f3
32 12 15 35 29 ff fe 1d 44 ef cd 41 26 3c 4e 4d
```

For `i` in `[start, end)`: `body[i] ^= body[i-1] ^ key[i & 31]`, with
`body[-1]` taken from the length word's high byte at `i == start`. Each body
byte chains onto the previous already-encoded byte; the inverse walks the range
high-to-low. The builder and this XOR are reproduced by `mu_packet_*` and
`mu_send_xor_*` and verified against the client over 500 synthetic
multi-chunk builds (0 mismatches). A separate `send` path (`0x00d51c9b`
encoded then a `C3`/`C4` wrap at `0x00d51e8c`) adds the serial and the
CryptoModule for encrypted packets.

Packet serial counters: `g_byPacketSerialSend` at `0x06fca01d` and
`g_byPacketSerialRecv` at `0x06fca01e` are single bytes that post-increment per
packet; the receive path logs `Decrypt error : g_byPacketSerialRecv(…)` when the
serial it recovers does not match.

## C3 / C4 CryptoModule (verified structure, boundary for reconstruction)

Encrypted payloads go through a `std::map<int, context*>` keyed by a channel
integer, with two instances: an encrypt map `g_enc` (`0x06fce2fc`) and a decrypt
map `g_dec` (`0x06fce31c`). Each is seeded from the key string
`98135003732920532106543021784355` (constructor `0x018df200`). A context is
`0x98` bytes: the key, per-direction packet counters, a `0x63`-filled 128-byte
table, and a cipher holder. `SetKey` (`0x018ea8d0`) hashes the key — the hash is
selected from a 10-entry table at `0x018eaf30` (MD4 / SHA-512 / RIPEMD-128/160/
320 and others) — to pick a cipher and derive a rekey interval; `Encrypt`
(`0x018df500`) / `Decrypt` (`0x018df460`) look up the channel context and run the
block cipher, rekeying every interval.

Running the client's `factory` `0x018ea540` and `Encrypt`/`Decrypt` under
Unicorn and matching single blocks against Crypto++ (bit-exact known-answer
tests) identifies the 17 ciphers it can instantiate:

| Index | Cipher | Key bytes | Block |
|---|---|---|---|
| 0 | TEA | 16 | 8 |
| 1 | 3-Way | 12 | 12 |
| 2 | CAST-128 | 16 | 8 |
| 3, 8 | GOST | 32 | 8 |
| 4 | RC5 | 16 | 8 |
| 5 | RC6 | 16 | 16 |
| 6 | MARS | 16 | 16 |
| 7 | IDEA | 16 | 8 |
| 9·0 | Twofish | 16 | 16 |
| 9·1 | DES | 8 | 8 |
| 9·2 | DES-EDE2 | 16 | 8 |
| 9·3 | DES-EDE3 | 24 | 8 |
| 9·4 | DES-XEX3 | 24 | 8 |
| 9·5 | SKIPJACK | 10 | 8 |
| 9·6 | SAFER-K | 16 | 8 |
| 9·7 | SAFER-SK | 16 | 8 |

(Index 9's sub-cipher is `key[0] & 7`.) This is recorded for completeness; the
keyed block-cipher selection is a large, library-specific keyschedule and is
**not** reimplemented in the native module. A native client would reproduce it by
driving the same primitives (Crypto++ is already a repository dependency), which
is left as the next step.

## Receive dispatcher (static)

A decode/decrypt stage at `0x01221b94` splits the queued bytes (C1/C2 direct,
C3/C4 through `g_dec` + serial check) and calls the main dispatcher
`0x01287ead(opcode, packet, length, encrypted)`, which indexes a 254-entry
jump table at `0x0128e59d`. Representative early entries, read statically:

* `0xF1` → sub-dispatch `0x0128b24d` by `packet[3]`: `01` login result, `02`
  game-server move, `03` client-close; `0xF3` is also handled near here.
* `0xF4` → `0x012883f0` by `packet[4]`: `03` **ReceiveServerConnect**
  (`0x0127ea69`, copies a 15-byte address at `packet[4]` and the port at
  `packet[0x14]`), `05` server-list item, `06` the server-list receive
  (`0x0127ec2f`), driving the list parser `0x010721d4` whose entry struct holds
  a server id, name and a load/percent byte.

The first login and server-list opcodes and their packet offsets are recorded
here as a static map; they are not reproduced in C in this milestone.

## Deliverables and verification

* C module `native/core/mu_protocol.{c,h}`: C1–C4 framing parse, the send XOR
  (encode + exact inverse), the faithful packet builder (Begin/AddData/
  WriteSize), the receive dechunker and the serial counter. Self-contained, no
  Crypto++ or client bytes.
* CLI `native/build/mu-proto`: `build`, `parse`, `dechunk`, `xor-encode`,
  `xor-decode` over synthetic packets.
* Portable tests `native/tests/test_protocol.py`: framing rules, builder vs an
  independent model (2000 cases), XOR round-trip and rule (2000 cases), dechunk
  vs model (1000 cases), partial-frame buffering, bad-head reset and CLI round
  trips.
* Verification `scripts/validate_protocol.py` (private, Unicorn): the authored C
  equals the client's `AddData`/`XorData` (`0x00d51c9b` / `0x00d52055`, 500
  cases) and `nRecv` (`0x01290792`, 300 cases) byte for byte. Pinned routine
  digests: `0xd51c9b` `c78a5451…`, `0xd52055` `c63549d8…`, `0x1290792`
  `27347565…`.

### Unresolved

* The C3/C4 keyed block-cipher selection is identified but not reimplemented in
  C; the receive dispatcher and login/server-list packet bodies are mapped
  statically but not reconstructed. These are the next steps toward a native
  client that can complete a handshake.

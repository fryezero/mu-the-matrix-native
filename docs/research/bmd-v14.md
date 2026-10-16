# BMD version 14 envelope research

Investigated 2026-10-15. Scope is the exact installed corpus associated with
`main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
No target executable was run for this investigation.

## Result

The pinned public `ModulusDecrypt` implementation, built without changes to its
source files against Crypto++ 8.9.0, decrypts all 216 installed version-14 files.
Every resulting body passes this project's existing strict v10 layout parser
with complete consumption and without permitting padding. This is a local
format result. It does not establish original rendering or gameplay behavior.
The private, per-file result and digest record is
`evidence/v14-source/oracle-decrypt-manifest.json`.

The source lead is [MuClientTools16 at commit
90c78cf](https://github.com/VDraven/MuClientTools16/tree/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad).
It explicitly routes BMD version `0x0e` to
[`ModulusDecrypt`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/BMD_SMD.cpp#L227-L249).
The routine is a layered block-cipher envelope. Its name does not imply that
this path uses the separate MU network SimpleModulus scheme.

## Envelope algorithm established from source

All offsets in the following description are relative to the envelope after
the eight-byte BMD header. Let `N` be the envelope length and `D = N - 34`.

| Envelope bytes | Meaning |
| --- | --- |
| `0` | Inner cipher selector, masked with `7` |
| `1` | Outer cipher selector, masked with `7` |
| `2..33` | Inner key material, recovered after removing outer layers |
| `34..N-1` | Model body |

Initialize the outer cipher with the published 32-byte format constant
`webzen#@!01webzen#@!01webzen#@!0`. This is an asset-format constant, not an
account credential. Let `B = 1024 - (1024 % outer_block_bytes)`.

Apply these outer decryptions in order:

1. If `D > 4*B`, decrypt `B` bytes at `2 + floor(D/2)`.
2. If `D > B`, decrypt `B` bytes at `N-B`, then `B` bytes at `2`.
3. Read the inner key from bytes `2..33`.
4. Initialize the inner cipher. Decrypt `D - (D % inner_block_bytes)` bytes
   starting at `34`. Keep any remaining body bytes unchanged.
5. Remove the first 34 bytes.

The source processes independent blocks without chaining, IV, or padding.
The decrypt order reverses the encrypt order. These conclusions follow from
[`MuCrypto.cpp` lines 74-115 and 168-247](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.cpp#L74-L247)
and [`MuCrypto.h` lines 6 and 32-68](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.h#L6-L68).

## Cipher defaults are part of the format

The upstream initializer receives a nominal length of 32 but ignores that
argument. It passes each cipher's `DEFAULT_KEYLENGTH` to `SetKey`. Using a
32-byte key for every cipher changes the result or fails initialization.
The wrapper invokes `ProcessBlock` for each block, without overriding default
round counts. See the pinned
[`ConcreteCipher` implementation](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.h#L25-L71).

The selector mapping comes from
[`InitModulusCrypto`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.cpp#L74-L115).
The following defaults were checked in both the bundled headers and the pinned
Crypto++ 8.9.0 headers linked in the table.

| Selector | Crypto++ class | Key bytes actually consumed | Block bytes | Default rounds where explicit | Outer window `B` |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | [TEA](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/tea.h#L16) | 16 | 8 | 32 | 1024 |
| 1 | [ThreeWay](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/3way.h#L16) | 12 | 12 | 11 | 1020 |
| 2 | [CAST128](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/cast.h#L25) | 16 | 8 | Cipher default | 1024 |
| 3 | [RC5](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/rc5.h#L16) | 16 | 8 | 16 | 1024 |
| 4 | [RC6](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/rc6.h#L17) | 16 | 16 | 20 | 1024 |
| 5 | [MARS](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/mars.h#L17) | 16 | 16 | Cipher default | 1024 |
| 6 | [IDEA](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/idea.h#L16) | 16 | 8 | 8 | 1024 |
| 7 | [GOST](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/gost.h#L16) | 32 | 8 | Cipher default | 1024 |

TEA is the fixed eight-byte-block `TEA` class, not `BTEA`, `XTEA`, or an XXTEA
variant. GOST uses Crypto++'s fixed S-box table and little-endian key loading.
A generic implementation exposing arbitrary GOST parameter sets is not a
verified substitute. See
[`tea.h` class declarations](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/tea.h#L16-L127)
and [`gost.cpp` lines 7-39](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/gost.cpp#L7-L39).

## Exact installed header observations

A read-only scan identified 216 distinct filesystem identities with `BMD` and
version 14. Every four-byte little-endian length at file offset 4 equals
`file_bytes - 8`, including the 34-byte envelope prefix. Body sizes range from
378 to 430,376 bytes. The scan records source-relative paths, SHA-256, lengths,
selectors and window relationships in the ignored
`evidence/v14-source/corpus-headers.json`, SHA-256
`23a423bfeee6428f6255c112de0658f8ce60ee5a43865a8fa32aaf23b4df983e`.

| Masked selector | Inner count | Outer count |
| ---: | ---: | ---: |
| 0 | 34 | 15 |
| 1 | 46 | 26 |
| 2 | 38 | 24 |
| 3 | 15 | 38 |
| 4 | 16 | 43 |
| 5 | 24 | 18 |
| 6 | 18 | 27 |
| 7 | 25 | 25 |

Raw inner selectors 8, 9 and 10 occur 24, 26 and 19 times. The source's `& 7`
therefore matters in real inputs. All raw outer selectors are within 0..7.
There are 187 middle-window cases, 24 head/tail-only cases and five inner-only
cases. Sixteen files have overlapping head and tail windows. Decrypting the
head before the tail would not reverse their encryption.

Three sample identities, with no copied asset bytes:

| Source-relative path | File bytes | SHA-256 |
| --- | ---: | --- |
| `Data/Effect/htrackt2.bmd` | 4,972 | `fefa39f950dd5b40ce42bcd765d3a4c0e090d44dd7dce051827054afa3a2b74b` |
| `Data/Item/flag_india.bmd` | 19,311 | `25307a009958d62b4bd1e99d5f1acf97a9db854e69508d1b650e1014c0867995` |
| `Data/Item/MLbattlescroll.bmd` | 21,941 | `160bd1166eaa10f631b250b302dcff7ddd63ea380f61fa572a666b9561bd38f0` |

## Bounds and portability issues in the reference

These are implementation recommendations, based on the cited source and the
observed inputs.

- Require the complete eight-byte BMD header and at least 34 envelope bytes
  before subtracting sizes or indexing selectors. Check every requested window
  against the copied buffer before cipher operations.
- Decode the outer file length explicitly as little-endian `u32`. The reference
  casts to host `size_t*`, which is unsuitable for a 64-bit portable reader.
- Keep strict equality between the declared envelope length and actual bytes
  for this installed corpus. The reference encryptor writes the plaintext
  length, while its decryptor only performs a minimum-size comparison and then
  decrypts the whole remaining buffer. That source-produced length variant
  differs from every installed v14 header inspected here. Do not accept it
  accidentally. See
  [`BMD_SMD.cpp` lines 201-208 and 242-249](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/BMD_SMD.cpp#L201-L249).
- Use strict `>` threshold comparisons. Preserve the source's order even when
  windows overlap. The overlap condition is `B < D < 2*B-32`.
- Call block processing only for complete blocks. Treat an aligned prefix of
  length zero as a successful no-op; the reference returns `-1` for zero bytes
  but its caller ignores that return.
- Keep exceptions and C++ ownership inside the native boundary. Use per-call
  cipher objects rather than a shared mutable global instance. The reference
  destructor does not release its final `m_cipher`; avoid copying that lifetime
  behavior. See
  [`MuCrypto.h` lines 74-98](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/Core/MuCrypto.h#L74-L98).
- Validate complete model records after decryption. The envelope does not
  authenticate the decoded data. Neither readable names nor successful cipher
  operations prove a valid model.

## Dependency recommendation and actual verification

Use Crypto++ for the eight cipher implementations, with an independently
written bounded envelope wrapper. The original source bundles Crypto++ 5.6.5,
identified by
[`CRYPTOPP_VERSION 565`](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/_src_/3rdParty/cryptopp/config.h#L66).
The dependency audited here is Crypto++ 8.9.0, official source commit
[`843d74c7`](https://github.com/weidai11/cryptopp/tree/843d74c7c97f9e19a615b8ff3c0ca06599ca501b).
The named cipher defaults match across the two inspected header sets.

Crypto++'s release README lists Apple Clang, GCC and Visual Studio support.
Its makefile has separate Darwin dylib and Unix shared-library targets.
This makes it a reasonable dependency for macOS, Linux and Windows, but is not
proof of this project's wrapper on all three platforms. Actual research checks
used the installed Homebrew Crypto++ 8.9.0 on this Mac. See
[compiler support](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/Readme.txt#L91-L101)
and [native library targets](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/GNUmakefile#L1492-L1520).

The ignored oracle executable is `evidence/v14-source/upstream-oracle`.
`MuCrypto.cpp` and `MuCrypto.h` are unchanged pinned downloads. A forced include
supplies fixed-width Windows typedefs and standard C++ headers. The local
runner accepts `encrypt SEED INPUT OUTPUT` or `decrypt INPUT OUTPUT`, with
raw envelope inputs and outputs. It does not load or execute game code.

The research verified:

- 216 private input decryptions, followed by complete strict model parsing.
- 832 synthetic oracle encrypt/decrypt round trips, all 64 selector pairs and
  13 lengths per pair, including 1020-byte ThreeWay thresholds and overlaps.
- 91 reviewed portable oracle vectors in
  [`model-recovery/fixtures/modulus-v14-vectors.json`](../../model-recovery/fixtures/modulus-v14-vectors.json).
  These cover all 64 pairs using the authored triangle fixture, window
  thresholds, overlaps, large bodies and masked selector aliases. Every stored
  vector also decrypts through the original source to its expected hash.

The synthetic plaintexts contain authored triangle geometry or a defined byte
pattern. No original asset bytes appear in the reviewed vectors. Seeds describe
this Mac's C library `rand` sequence; stored ciphertext is the portable expected
value. The project implementation must compare against those stored bytes,
rather than regenerate expected ciphertext through its own encryptor.

## License requirements

The reference code is MIT, copyright 2021 VD. Retain its copyright and permission
notice if copying substantial code. This research used it only as a separately
acquired local oracle and recommends an independently authored wrapper. The
reviewed vector file records its origin. See the pinned
[MuClientTools16 license](https://github.com/VDraven/MuClientTools16/blob/90c78cf5876ec43be69f26e2956d3ffbdc26c5ad/LICENSE#L1-L21).

Crypto++ states that individual files are public domain and licenses the
compilation under Boost Software License 1.0. Its `License.txt` also contains a
separate CRYPTOGAMS notice for identified 32-bit ARM assembly files. Preserve
applicable upstream notices when vendoring or distributing the dependency;
using the project MIT license must not conceal that dependency's provenance.
See the pinned
[Crypto++ license](https://github.com/weidai11/cryptopp/blob/843d74c7c97f9e19a615b8ff3c0ca06599ca501b/License.txt#L1-L84).

Game assets retain their original ownership and remain outside the repository.
The source-derived format constant and public cryptographic algorithms do not
assign a license to decrypted assets.

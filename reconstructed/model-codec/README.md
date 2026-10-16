# Client-linked BMD codecs

`mu_bmd12_decode` is authored C for the rolling decoder called by the selected
client model-loading path. It matches captured instructions in 4,048 synthetic
cases and all 180 pinned installed v12 payloads. This is a decoder component,
not a complete model loader or playable client.

The logical name is ours. The original entry is `0x0098c5f2`, with a 194-byte
observed body. The [finding](../../docs/research/client-model-loader.md) records
caller evidence, captured-code identity, ABI checks, coverage and limitations.

## Contract

```c
int32_t mu_bmd12_decode(void *destination, const void *source, int32_t length);
```

The return is always the signed 32-bit input length. A null destination queries
the length without accessing source. A nonpositive length also accesses neither
caller span. For a positive nonquery call, both pointers must cover that many
accessible bytes with no address wrapping or aliasing of executing code or the
call stack. Unaligned and overlapping spans are supported.

The function writes one byte, then rereads that source position for feedback.
In-place output therefore differs from the ordinary disjoint decoder. Moving
feedback ahead of the store breaks 312 synthetic comparisons. Do not add
`restrict`, copy the input first, or replace the operation with `memmove`.

It allocates nothing and does not validate a BMD envelope, available capacity,
model structure, file path or encryption version. The strict checked reader in
`model-recovery/` remains the interface for untrusted files. No source parser
acceptance was relaxed. Exceptional pointers, concurrent modification, original
status/exception flags and native Windows equivalence remain unverified.

## Build and compare

```sh
make -C reconstructed/model-codec
python3 -m unittest discover -s reconstructed/model-codec -p 'test_*.py' -v
```

Seven portable tests use authored bytes, analytic expected values and the
published inverse encoding. The eighth is an explicit private integration
check. The validator requires the pinned full restored-text capture before
loading the optional emulator. Supply your own private evidence and use:

```sh
./tools/python/bin/python scripts/validate_model_codec.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --game-root /path/to/matching/installation \
  --output /new/local/comparison.json
```

Omit `--game-root` for synthetic instruction comparison only. Corpus comparison
also requires the exact ignored `model-recovery/verified-v14/manifest.json`,
whose digest is pinned by the validator. Every selected model hash and file
identity is checked. Both comparisons execute the actual decoder body without
substituting any of its operations. Raw code, payloads and reports stay local.

## v15 key setup

`client_lea.h` exposes `mu_client_lea_setup`, a byte-defined 772-byte LEA context
for 16/24/32-byte keys. It preserves unused context bytes and accepts unaligned,
disjoint key/context spans. Null pointers and unsupported sizes are no-ops.
It matches 1,320 actual captured-instruction cases, including both DF states.
A reversed-key-order negative control fails all 1,248 valid cases.

Five portable tests cover public encryption vectors, no-op gates and context
layout/guards. A sixth explicitly skips private comparison unless integration
is requested. Read [the finding](../../docs/research/client-lea-key.md) for exact
identities, span requirements and the reproduction command. The ECB payload
decoder and key/context alias behavior remain outside this component's claim.

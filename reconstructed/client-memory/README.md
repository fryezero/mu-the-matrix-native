# Reconstructed client memory operations

`mu_copy64_forward_words(destination, source)` models the observed routine at
`0x00401000` for valid flat-memory spans and a clear x86 direction flag. It copies
sixteen four-byte words in increasing address order and returns the destination.
Both spans must contain 64 accessible bytes. Unaligned and overlapping spans
are permitted. No null checks, address wrapping, faults, atomicity or concurrent
access behavior is modeled.

The per-word read precedes its write. When the destination starts four bytes
after the source, the first source word repeats sixteen times. `memmove` would
preserve the original 64 bytes and therefore produces a different result.
Small local `memcpy` operations preserve each four-byte transfer without C
alignment or aliasing assumptions.

Build with `make -C reconstructed/client-memory` or the top-level `make test`.
The portable tests use synthetic buffers. One private comparison is opt-in:

```sh
MU_RECOVERY_INTEGRATION=1 make test PYTHON=./tools/python/bin/python
```

That full command also requires the older private inputs described in
[setup](../../docs/setup.md). To run this comparison alone, supply the pinned
restored first section and the built library:

```sh
./tools/python/bin/python scripts/validate_client_copy.py \
  --capture /absolute/path/to/client-text.bin \
  --library reconstructed/client-memory/libclient_memory.dylib
```

Use `.so` on Linux. `MU_CLIENT_TEXT` can override the integration test's default
local capture path. The emulator is an optional analysis dependency pinned in
`tools/requirements-lock.txt`; portable checks do not need it. Requested private
checks fail if the capture, its digest or the emulator is missing.

The comparison executes captured instructions under Unicorn and the authored C
library on the host. It checks all 4,096 arena bytes, pointer returns, x86 stack
cleanup and preserved registers across 393 synthetic cases. These are bounded
instruction-equivalence checks, not execution in the original game or proof of
a known class layout. [The finding](../../docs/research/client-copy64.md) records
provenance, REA limitations and the nearby function map.

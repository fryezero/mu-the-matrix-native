# Executable recovery status

Target is the exact installed Mu The Matrix client selected by the user, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
An older MU client is not an accepted substitute.

## Verified recovered component

`reconstructed/boot/decoder.c` is an independently written, bounded C
implementation of the decoder starting at virtual address `0x0e64605d`.
Its API is new and does not pretend to reproduce the original calling convention.
The compiler builds it with C11 and strict warnings. Five test methods pass,
including all four original compressed blocks, exact input consumption, output
length, and SHA-256 matches against independently decoded results. Invalid
backreferences, truncation, overlapping backward copying, and output capacity
are checked. A sanitizer-loaded Python test was attempted but the platform
refused loading its sanitizer runtime; the passing suite uses an ordinary
compiled library and does not claim sanitizer coverage.

```
make -C reconstructed/boot
./tools/python/bin/python -m unittest discover -s reconstructed/boot -p 'test_*.py' -v
```

The CLI `reconstructed/boot/recover-block INPUT OFFSET NEW_OUTPUT` decodes one
block and refuses to overwrite a destination. The complete first-layer recovery
is implemented by `scripts/loader_recover.py`. It validates the exact input digest,
then emits chunk identities and address mappings in
`evidence/loader-recovery/recovery.json`.

Four chunks, each 10,496,000 bytes, reconstruct the complete 41,984,000-byte
`.themida` reservation. Reconstructed region SHA-256:
`e42182c0b148ffc94fa6b9077fe81bebd471ef6ac9f30c682218259afea1bc31`.
Its observed next entry is VA `0x0be5f280`, offset `0x23280` from base `0x0be3c000`.
This region is protector/initializer material, not an independently runnable PE
or recovered gameplay source.

The independent upstream aPLib decoder comparison is recorded by
`scripts/loader_validate.py` and the saved loader evidence. Its exact pinned
upstream reference is retained in that verification output.

## REA and Ghidra

Ghidra 12.1.4 and OpenJDK 21 were installed locally through Homebrew. The configured
REA doctor succeeded. Startup code was extracted byte-for-byte with original file
offsets in `boot-code-provenance.json`. REA produced pseudocode for it in
`evidence/rea-boot-decompile.json`, evidence ID
`ev_40cefd09c26df63624c70576f9de73bb8bbc457dd37f6c0d1536a60c2755d701`.
Ghidra merged caller/stub boundaries in this result. The C decoder was reconstructed
from instructions and tested; the generated pseudocode itself is not a buildable
or validated source replacement.

Whole recovered-region default analysis exhausted a 2 GiB Java heap. A changed
profile used 4 GiB and disabled `x86 Constant Reference Analyzer` and
`Scalar Operand References`. That profile completed and is explicitly preserved
in its REA records. Decompilation at the recovered entry and its immediate
initializer gives short call wrappers with unresolved obfuscated control flow;
it does not expose gameplay. Successful records:

- `evidence/rea-protector-decompile-tuned.json`, ID
  `ev_c8e093664abd9d769d4f8debaa47990ea6ce677362d9da3ddb8caaf50f5a8b63`.
- `evidence/rea-protector-initializer-decompile.json`, ID
  `ev_03b9ccfe442e9d4efd7227f5d3bd81e5db1727eeb3ef249225d235c9ebebdb18`.

`REA_GHIDRA_SEED_FILE` explicitly asserts the recovered entry as a function.
That assertion is derived from loader arithmetic, not a discovered source name.

## Earlier bounded CPU emulation

`scripts/loader_emulate.py` uses Unicorn with an explicit synthetic CPU/memory
context. The PE sections and independently recovered protector region are mapped;
this does not establish the real Windows process state. No Windows API behavior,
network access, filesystem I/O by emulated instructions, or production account
login was supplied.

The first attempt stopped before RDTSC. Later hypotheses supplied two deterministic
timestamp inputs. An earlier unresolved-IAT run wandered into zero data; that run
is not evidence of decrypted code. The final corrected run replaces IAT slots
with STOP-only traps and halts at `kernel32.dll!GetModuleHandleA`, whose argument
is the decrypted string `kernel32.dll`. It does not invent a loaded module handle.

The corrected run records 1,015,078 instructions, 25,910 basic blocks, and 140
written pages, all in `.themida`. Only 3,316 bytes differ in the reconstructed
protector overlay. Original gameplay code was not decrypted. Exact assumptions,
stop cause, page identities and overlay provenance are under
`evidence/loader-recovery/emulation-04/`. These are controlled emulation
observations, not execution of the complete program under Windows.

## Isolated startup checks

A separate CrossOver bottle named `MuMatrixRecovery` was created from the
`win10_64` template. The game directory was copied using filesystem cloning to
`runtime/client`; the original installed executable was not patched or replaced.

- WineDbg launch of the analysis copy produced
  `rosetta error: invalid gdt selector index 6`.
- A direct launch in the same fresh bottle, without WineDbg, produced the same
  diagnostic before any gameplay or login was observed.
- An attempted native LLDB attach returned `attach failed: lost connection`.
  No native memory dump was obtained.
- Only the newly created bottle's wineserver was terminated to stop these tests.
  The user's original bottle was not shut down.

Logs are `runtime/winedbg.typescript` and `runtime/direct-startup.log`.
The fresh bottle does not duplicate every configuration or dependency in the
original bottle. These failures therefore establish the tested configurations,
not that the game can never run in CrossOver or that the exact cause is known.
No game-account login was performed. Network traffic was not captured, so no
claim is made that startup attempted zero network operations.

The later win10/win32 finding changes the CrossOver boundary. The exact client
gets beyond this observed stop in a 32-bit bottle; the launcher needs .NET 4.8,
builtin WIC/GDI+, WPF software rendering and its default skin. Native WIC breaks
image encoding, and the copied custom `Template.design` had to be disabled (no
longer with the mscoree proxy v3, see
[`research/mac-launcher-skin.md`](research/mac-launcher-skin.md)). Read
[`research/mac-crossover-32bit.md`](research/mac-crossover-32bit.md) for the
authored isolated setup, real test results, static selector-0x33 candidates and
the unresolved fault-path inference. This does not demonstrate gameplay.

## Current blocker

The 64-bit CrossOver failure above is a configuration-specific historical result.
The full x86 guest captures below already restore client code, and the newer
32-bit CrossOver route can initialize the original launcher. Native Windows
equivalence, full gameplay and the reconstructed client remain open. Captured
instructions still require function/type recovery, authored implementation,
compilation and behavior checks. There is no verified playable source rebuild.

## Mac-only runtime recovery

Full x86 QEMU TCG with Debian/Wine now runs the exact copied client beyond the Rosetta stop. Later captures restore the first executable region at `0x00401000`, 23,572,480 bytes, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`. An early capture exactly matches the still-packed on-disk mapping; later captures agree on the restored digest. REA/Ghidra successfully decompiled a bounded arithmetic routine from a verified 4 KiB prefix. [The restored-code report](research/restored-client-text.md) records addresses, hashes, profiles and limitations. [The runtime guide](../runtime-linux/README.md) explains the tested environment and scoped capture tool.

The wider Windows-API capture remains incomplete. The isolated Wine environment showed no demonstrated login/gameplay and an unresolved localhost connection. Restored bytes and generated pseudocode are not a buildable source client or proven gameplay equivalence. All payloads and decompiler records remain private.

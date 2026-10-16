# Current status

Updated 2026-10-15. Target: the exact installed Mu The Matrix version, not an older MU substitute. Later goal: native macOS gameplay after source reconstruction and behavior validation.

## Working components

- Startup decompressor reconstructed in C and independently compared against all four original compressed blocks. The 41,984,000-byte result still contains protector code.
- REA/Ghidra native inspection configured; startup and immediate protector wrappers decompile with explicit control-flow limitations.
- Images: 19,703 decoded from 19,707 wrapper candidates. One remaining candidate is editable mesh text, three are inconsistent terrain images.
- Models: 12,663 parsed from 12,754 unique BMD-extension files. V10: 701/701; v12: 180/180; v14: 216/216; v15: 11,566/11,583. Seventeen v15 inputs are rejected and 74 other/table envelopes remain unsupported.
- 370 JSON effect descriptions parse; all 92 distinct texture references exist in the inspected installation.
- Windows capture helper cross-compiles. SHA-256 known-vector and own-process read smoke tests pass under Wine. Native Windows capture is unverified. A Mac-only QEMU/Linux Wine experiment now yields a repeatable restored client-text region.
- First authored behavior from restored client code: 64-byte copy and clear operations, matching captured instructions in 393 and 768 synthetic cases. [Finding and limits](research/client-copy64.md).

## Executable recovery boundary

Earlier bounded Unicorn emulation stopped at `GetModuleHandleA("kernel32.dll")` without restoring the first client section. Full x86 QEMU/Linux Wine now restores that section at `0x00401000`, with matching late-capture hashes across runs. REA/Ghidra successfully decompiled one routine from a verified 4 KiB prefix. [The report](research/restored-client-text.md) distinguishes readable code, inferred arithmetic and unverified behavior.

CrossOver remains unable to start the original. No Windows PC is currently available. The active runtime is an isolated Linux compatibility environment with outbound networking blocked. No login/gameplay has been demonstrated; initialization logs contain an unresolved localhost connection. Native Windows equivalence is unverified.

## Checks

The repository discovers 93 tests. The portable run passes 86 and explicitly
skips seven private-input checks. The opt-in local integration run passes all 93.
A fresh 92-file source-only checkout also passes 86 tests with seven explicit skips.
The v14 reader matches an independent upstream oracle on all 216 installed
files and 91 authored synthetic vectors. The complete corpus scan reports
12,663 parsed, 17 rejected and 74 unsupported files. Three selected v14 models
export as JSON and OBJ. The copy reconstruction matches captured x86 in all
393 synthetic cases; the wrong memmove control fails 158 cases.
[PR #8](https://github.com/fryezero/mu-the-matrix-recovery/pull/8) passed macOS/Linux
CI before merging, at the commit recorded in the evidence index.

The corpus totals above come from complete local scans, not from CI. Raw scan
manifests and original inputs are intentionally ignored. `docs/evidence-index.json`
is the shared summary and identity index.

## Still unfinished

Protected gameplay functions and types, faithful initialization capture, networking semantics, rendering equivalence, a client build from recovered source, and the eventual macOS port. A Windows memory capture does not by itself solve these tasks.

## Repository publication

The private [GitHub repository](https://github.com/fryezero/mu-the-matrix-recovery)
contains 91 reviewed source/documentation files on main. Model PR #4, runtime
PR #6 and [client-copy PR #8](https://github.com/fryezero/mu-the-matrix-recovery/pull/8)
are merged. No game executable, asset pack or memory capture was uploaded.
The initial 58-file publication was independently downloaded and compared with
the lab snapshot; later changes are tracked through Git and checked in CI.
[Clear PR #10](https://github.com/fryezero/mu-the-matrix-recovery/pull/10) is merged after passing macOS/Linux CI. The [bounded 64 KiB map](research/client-window-map.md) now distinguishes 803 candidates and unresolved references, with a separate REA comparison. Original types and complete boundaries remain open.

## Runtime route without a Windows PC

The owner has no Windows PC available for the foreseeable future. The active experiment uses QEMU full x86-64 TCG, Debian amd64 and Linux Wine to avoid Rosetta. The guest boots, software OpenGL and both Windows bitness probes work, and the exact copied client restores readable code. The scoped Linux capture tool and boundary tests are implemented. [The research note](research/mac-runtime.md) records the approach and limitations. Compatibility-environment evidence must remain distinct from native Windows behavior.

The bounded map is merged through PR #13 after passing macOS/Linux CI. Selected image-data acquisition continues under issue #12.

Selected math data is now captured with exact identity and restored-text checks before/after reading. The scalar is positive zero, the template equals a standard identity matrix, and the observed feature bit selects SSE. [Evidence and limits](research/client-math-data.md).

The fixed math-data scope is merged through PR #14 after passing macOS/Linux CI. Selected arithmetic reconstruction continues under issue #15.

Authored cofactor/record-operation source matches 1,680 helper and 1,050 wrapper comparisons under explicit PC53/RNE state, including aliasing. [Arithmetic evidence and limits](research/record-math.md).

Record arithmetic is merged through PR #16 after passing macOS/Linux CI. Issue #17 begins case-specific diagnosis of the 17 rejected v15 models without changing acceptance.

Model issue #17 locates each rejected v15 field, including 13 dummy-parent cases. Native and Python decoding agree for all 17. Acceptance remains strict; see [the case report](research/model-edge.md).

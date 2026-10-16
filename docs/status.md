# Current status

Updated 2026-10-15. Target: the exact installed Mu The Matrix version, not an older MU substitute. Later goal: native macOS gameplay after source reconstruction and behavior validation.

## Working components

- Startup decompressor reconstructed in C and independently compared against all four original compressed blocks. The 41,984,000-byte result still contains protector code.
- REA/Ghidra native inspection configured; startup and immediate protector wrappers decompile with explicit control-flow limitations.
- Images: 19,703 decoded from 19,707 wrapper candidates. One remaining candidate is editable mesh text, three are inconsistent terrain images.
- Models: 12,447 parsed from 12,754 unique BMD-extension files. V10: 701/701; v12: 180/180; v15: 11,566/11,583. Seventeen v15 inputs are rejected. V14's 216 files and 74 other/table envelopes remain unsupported.
- 370 JSON effect descriptions parse; all 92 distinct texture references exist in the inspected installation.
- Windows capture helper cross-compiles. SHA-256 known-vector and own-process read smoke tests pass under Wine. Native Windows capture is unverified.

## Executable recovery boundary

Bounded CPU emulation reaches `GetModuleHandleA("kernel32.dll")` after 1,015,078 instructions. Written image pages are confined to protector memory. No gameplay region has been demonstrated as recovered. Synthetic CPU inputs and STOP-only import traps are recorded in the private evidence.

Both a debugger start and a direct start of an isolated copy fail in a fresh CrossOver bottle with `invalid gdt selector index 6`. The user confirmed the original also does not start in CrossOver and is normally played on Windows. No account login was performed during investigation.

## Checks

The repository now discovers 40 tests. The portable run passes 37 and explicitly
skips three private-input checks. The opt-in local integration run passes all 40.
A staged source-only checkout, containing no game files or raw evidence, also
passes the portable suite with the same three skips. The Windows helper builds
with strict compiler warnings. These checks were run on the original Mac; the
GitHub macOS/Linux CI workflow is supplied for remote verification.

The corpus totals above come from complete local scans, not from CI. Raw scan
manifests and original inputs are intentionally ignored. `docs/evidence-index.json`
is the shared summary and identity index.

## Still unfinished

Protected gameplay functions and types, faithful initialization capture, networking semantics, rendering equivalence, a client build from recovered source, and the eventual macOS port. A Windows memory capture does not by itself solve these tasks.

## Repository publication

The private [GitHub repository](https://github.com/fryezero/mu-the-matrix-recovery) contains 58 reviewed source/documentation files. Its downloaded archive matched the local source snapshot exactly. [CI passed on macOS and Linux](https://github.com/fryezero/mu-the-matrix-recovery/actions/runs/38826951964); the evidence index records the tested commit. No game executable, asset pack or memory capture was uploaded.

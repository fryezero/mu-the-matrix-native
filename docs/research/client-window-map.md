# Bounded restored-code navigation map

Observed 2026-10-15 for main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Input is the verified first-section capture, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Only its first 65,536 bytes, VA `0x00401000..0x00410fff`, were selected.
Window SHA-256 `a6522c311c2dab67135f05210f195859ae5e0a15a0b890401f3889fc54d9fc7f`.
This map supports navigation. It does not establish original symbols, complete
function boundaries, types, execution coverage or gameplay semantics.

## Authored map and reproduction

`scripts/map_client_window.py` verifies the entire captured-section digest before
selecting a window of at most 256 KiB. Its decoder is Capstone 5.0.9. Explicit
seeds, aligned entries after two INT3 bytes and decoded local call targets remain
separate origin labels. All are candidates. Code paths stop at other candidate
entries, so shared tails and valid continuation may be omitted. Decoded calls
have possible fallthrough; no-return behavior remains unknown.

```sh
./tools/python/bin/python scripts/map_client_window.py \
  --capture /absolute/path/to/client-text.bin \
  --seed 0x401000 --seed 0x401020 --seed 0x401030 \
  --output evidence/NEW-window-map.json
```

The default window is 64 KiB, with 1,024 candidate and 4,096 instruction-per-candidate
budgets. Output must be new. `--no-padding` restricts discovery to seeds and
reachable decoded calls. Reports preserve local/outside/indirect transfers,
unmodeled operand forms, invalid/truncated instructions, traps, conflicting
instruction decodes, candidate boundaries, window exits and budget limits.
Absolute memory operands, segmented offsets and address expressions are distinct;
none establishes pointed-to values or an original import/type.

This run produced 803 candidates. Origin labels overlap: three explicit seeds,
795 padding candidates and 99 decoded local call targets. There are 1,167 unique
call sites: 352 direct local, 410 direct outside the window and 405 indirect.
The map contains 351 absolute memory operands, whose values are not captured
by this window. No candidate/instruction budget was exhausted and no conflicting
decodes were observed in this run; one traversal reaches the window edge.
These counts are navigation observations, not a source-recovery percentage.

## REA comparison and selected routine

REA 6.5.0 / Ghidra 12.1.4 inspected the same window with the three explicit seeds,
2 GiB heap, raw x86 load base `0x00401000`, generic GCC compiler profile and the
previously documented disabled analyzers. Seed-file SHA-256
`1cbc3adbd57859a89f2a2be30d1bdc862acdbca8b85c05d3e97255dc19e4e583`.
Procedure-inventory evidence ID
`ev_3a3b7f26c4be6c7c51c56ede1d53b5acbc121ffe3b7b5a181e43950601600a7d`.
It contains 31 function-manager entries; 29 also occur in the authored map.
The authored method misses `0x00403920` and `0x0040cb00`. Neither inventory is
complete or a ground-truth count. Keep these omissions when refining seeds.

For the selected candidate at `0x004013d0`, an additional explicit function seed
was added for a separate REA dossier. Its name `observed_record_operation` is
an investigator assertion. The four-seed file SHA-256 is
`21ff602a834275b9062c74f938599f32f5763279598763fa478d345b0bb9d42e`.
Evidence ID
`ev_486f89fae4379bc3801cf0754db5c1d7861fda2329ec676b92c9afe1fb6bd31b`.
Both tools describe the 270-byte region `0x004013d0..0x004014dd`; the authored
map decodes 100 instructions, one local call at `0x004013ee` to `0x00401240`
and four local branch sites. No issue or candidate-boundary stop occurs there.

Instructions and pseudocode show a 4-by-4 loop calling the index/arithmetic
helper, a scalar accumulation from the input's first four components, a zero
comparison, reciprocal scaling and transposed output placement. One branch
copies a 64-byte global template and negates components at offsets `0x30..0x38`.
This is consistent with a cofactor-based 4-by-4 inversion/transform operation,
but its original symbol and game subsystem remain unknown. The raw import's
calling convention is incomplete; generated C is not a validated replacement.

The selected routine references a double at `0x01a7dd40` and a template address
`0x01cf3b00`, outside the captured text. Their runtime values are unknown. x87
rounding/exception behavior and overlapping input/output effects also need
validation. Acquire those selected image-data ranges with source/process identity
before reconstructing this behavior; do not guess zero/identity constants.

## Local records and checks

`evidence/client-map-64k/` retains the raw window, seed files, REA inventories,
selected dossier, versioned maps and comparisons. These files remain ignored.
`candidate-map-v5.json` is the current checked map. Earlier private versions
precede loop-edge and absolute-memory-operand handling; they are preserved.
The authored synthetic tests cover bounds, budgets, local/external/indirect/far
transfers, loops, overlapping paths, segmented references and rejected input.
Capstone is part of the portable dependency set; Unicorn and game bytes are not
needed for these tests. The next task is a scoped image-data capture and a
validated implementation of a nontrivial record operation.

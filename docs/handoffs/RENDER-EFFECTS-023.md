# RENDER-EFFECTS-023

Implementation checkpoint, not PR-ready. Branch `codex/render-effects-023`, base main `825c37b7`, after #354
merged. #355 remains pending and will be incorporated before final checks. Offline/static only; no live client,
launcher, installed app, server-state work, protection analysis or memory writes.

Scope: world bitmap slots for `0x7f7a` and `0x80ba`; the 19 remaining mace particle pairs in
`reconstructed/particles/item_mace_kinds.inc`; 12 other bitmap slots for those particles; direct OBJECT point
following for `0x7ffb/0`, `0x85fc/1,/2`; per-item OBJECT keys in `mu-render character`. RENDER-ITEMS-002W keeps
the blend-light input and body-fit work. Existing EFFECTS-022 consumers are unchanged.

The source/include, native point adapter, bitmap table, viewer caller, synthetic host and new validator are
implemented. The generator/table point comparisons for #355's newly admitted maces, affected checks, final
mutants, renders and census remain pending. No ready-prs entry has been written.

## Checkpoint evidence

- Baseline build: root `nice -n 10 make -j4`, 30.21 s; render targets, 4.40 s. Implementation build: 11.09 s.
- Small original sample on the implementation: 11,414 comparisons, zero mismatches, 7.335 s. Create/move/render
  each 3,800; 14 static original loader mappings. The full sample and compiled mutants have not run yet.
- Synthetic native tests: viewer registry and no-asset generation tests pass. The loaded-bitmap host initially
  used an empty draw target and crashed on the first loaded quad; it now uses the real raster target. The failed
  loader test passes alone, 1 test in 1.927 s, with all 19 particle draws and distinct file/filter/wrap checks.
- Baseline, Lorencia 128,124, 61 consecutive draws at default and clock 123456: the two older maces create 72
  particles, zero refused, last frame 33 particles and 10 sprites drawn; `0x0f2a` has 488 accepted sprite requests
  and 154 refused particles, with zero particles and zero sprites drawn. The missing texture requests are
  counted separately from kind refusals.
- One baseline default-draw tour sweep is captured: October 22, 28 PNGs and 28 dumps; DATA-ACQ-002, 64 PNGs
  and 64 dumps. Their hashes and normalized reports are local; bulk tour outputs are already removed.
- Viewer baseline, 16 frames starting counter 3: owned-spark fixture 160 effects / 6 refused; `0x0f2a` fixture
  128 / 40. Native before/after images do not establish original-client pixel equivalence.

All test/tool commands run from the repository root. Builds use at most four jobs, runners at most two,
heavy commands nice 10. Shared `tools/python`, `evidence` and `input` are symlinked and not staged.

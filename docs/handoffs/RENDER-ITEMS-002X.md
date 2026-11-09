# RENDER-ITEMS-002X

Implementation checkpoint, not ready for steward. Branch `codex/render-items-002x`, from `54a53e1a`, after
prerequisite PR #360 reported MERGED. Codex, GPT-6.1 Sol; no subagents. Offline/static only. The installed
Native Preview and Wine apps are untouched. No full gate in the lane.

## Result

Bodies **1,404 -> 1,424 of 1,674**, leaving **250**. Skins stay 17/17; links stay eighteen targets/twenty-four types.
Both complete tables reproduce from pinned instruction extraction. Recipe rows 1,385 -> 1,405; `item_bodies.h`
is 482,415 bytes, below 512 KiB. Survey membership changes for exactly twenty types; nine shape totals change,
complete shapes 600 -> 609 of 798. Raw shapes, classifications and stopped states are unchanged.

Fourteen types also pass their complete owned pre-program comparison. Final affected suites, private rows,
mutants and the single final default-draw identity sweep are pending.

Read-program types: `0x0b29`, `0x0b52`, `0x0f1e`, `0x174a`, `0x2301`, `0x2302`, `0x23a8`, `0x23a9`,
`0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`. They need extended probes, correct nested-range
random attribution and, except the two swords, carried model fields. Existing binary32 scalar/products retain
exact draw words. The seven other candidates remain rejected.

No-glow types: `0x232c..0x2330` and `0x26f5`. They bypass the ordinary level-glow helper chain, including
fixture records with kind B `0x26/0x5b`. Their new validator checks both random states and those records.

## Checks so far

- Baseline root build: pass, 28.71 s; world target: pass, 4.06 s.
- Baseline default tours: 46 maps, 92 PNGs, 92 dumps and 46 reports hashed once, 62.18 s. Images removed.
- Read-program screen: 21 candidates; 14 pass 292 independent body states each, 353.33 s.
- Owned program screen: all fourteen pass 64 states each, 896 total, 6.58 s. Ordered draw/request/refusal streams
  and exact random consumption agree. Counts are harness requests, not native particle-pool creations.
- No-glow screen: 23 candidates; six pass 292 independent body states each, 50.60 s.
- Consecutive-helper experiments: no admissions, 120.71 / 168.11 s. Prototype removed.

The largest-group screen adds no body: twelve types in four groups, 210.20 s including a stale-phase exception;
the corrected two-type tail completes in 13.16 s. A portable regression fails before the phase reset and passes
after it, 0.10 / 0.08 s. The rejected helper-group prototype is absent from the source.

Additional implementation checks:

- Complete table extraction: pass, 868.00 s.
- Root build after table generation: pass, 9.23 s.
- C-to-C against saved prerequisite main library: 216,448 states, 213,888 identical; exactly the intended twenty
  types change, 128 states each, 6.10 s.
- Targeted portable modules: 18 tests, 16 passed and two private skips, 0.17 s.
- Full survey: 1,691 types / 798 shapes, 67.17 s. The old export's hand-maintained membership list omitted the
  named and no-glow lists. It now uses `gen.ALL_TYPES`; a portable test compares the exported membership with
  native `mu_rc_item_special` over all 1,691 types. Three tests pass, one private skip, 0.10 s. Re-export uses the
  saved raw survey, without a second instruction survey.

## Limits

Affected portable/native checks, private validators, mutants and the one final byte-identity sweep are pending. The checkpoint is not a readiness claim. No comparison was relaxed.
The later groups retain unresolved input/model state and effect/matrix work. Existing pose/bone/record/buff,
selected-item, process-random and process-counter limits remain. No new particle consumer is claimed.

## Next groups

Finish the largest-group screen, generate tables, validate the six record-aware no-glow bodies and all item rows
selected by the test budget, then complete docs, push, append ready-prs once and clean up.

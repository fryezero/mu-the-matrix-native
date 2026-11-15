# RENDER-ITEMS-002Z

Branch `codex/render-items-002z` from main `b7dfd2ed`. GPT-6.1 Sol, no subagents.
Offline/static only. Research is part 40 of `docs/research/client-render-items.md`.
The merge steward owns the full gate and merge.

## WIP

This is a checkpoint, not PR-ready. The verified baseline remains 1,465 of 1,674 bodies.

Done:

- Read the task/common briefs, current resume, 002Y handoff and part 38, ranked gaps and lane ownership.
- Added a narrow reader for the complete signed 6,000-tick colour cycle at
  `0x0175f2e6..0x0175f469`, checking both branch targets, vector setters and the wave multiply.
  Scalar kind 10 retains signed truncation/remainder and binary32 arithmetic. No cap or tolerance changes.
- `0x0b51` probe fit passes. An initial 80-case-per-family preflight, including the full 64 directed
  clocks and 64 complete owned streams, passes for it and the six prior later read types.
  The owner table was regenerated. Full cycle/forcing-record comparisons and compiled mutants remain.
- Thirty helper-count candidates refuse the simple no-glow hypothesis. Thirteen early complete
  bodies fit a separate pre-glow, pre-tail reference and pass 292 independent states each:
  `0x23f3`, `0x23fc`, `0x24f7`, `0x24f8`, `0x271a`, `0x2725`, `0x27b8..0x27bb`,
  `0x289f`, `0x28b0`, `0x28d7`. Full forcing-record comparisons and compiled mutants remain.
- The original `0x27b8..0x27bb` gate is at `0x0176f367..0x0176f37e`; its draw ends with
  the jump from `0x0176f589` to the epilogue at `0x017e6304`. The new direct recipe path
  preserves entry model fields and omits the glow/tail chain.
- Other-body screening proceeds in descending census shape size. The largest shield and armour
  groups still refuse. `0x1710` and `0x10fd` remain excluded.
- Added focused validators for the cycle and early bodies, plus portable admission/entry-state checks.
  Their final runs are still pending. Existing registry rows are unchanged; new rows are appended.
- Body-table source formatting is compacted without changing values, preserving the 512-KiB audit cap.

Left:

- Finish the other-body screen, including any independent-state failures and refusal reasons.
- Full pinned body-table regeneration, classifier export, C-to-C admission delta and static refusal ledger.
- Root build, affected portable/private validators, changed-row mutants once, 8d reduced,
  genuine-main default identity with explicit world builds and both binary hashes.
- Final research/status/plan/roadmap updates, audit, latest-main integration, PR and ready entry.

Next step: inspect the local screen logs, reconcile admitted lists, regenerate once, then run the finish checks.
Local resumable inputs and logs are in
`~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002z/`. They contain no new live input.
No installed app, original-client process, service, protection or character-power work is involved.

Checkpoint update, before full regeneration:

- The five-state count census, including option/ancient states, reproduces the exact forty historical
  helper-count candidates. All fourteen early-body candidates are in that group, including `0x2493`.
  Proposed admissions are therefore one read body plus fourteen helper-count bodies. If finish checks
  pass, the total is 1,480/1,674, leaving 26 helper-count and 168 other bodies, 194 total.
- Exact-white probes exposed the whole-body versus mesh final entry on `0x23f3/0x23fc/0x2493`.
  The checked branch is `0x01775e43..0x0177608b`; all three light channels must equal one.
  A separate phase-5 recipe handles that branch. The existing plain field distinguishes early
  bodies, so no table-struct field or external ABI changes are needed.
- Corrected light preflight passes all twelve light vectors on all fourteen candidates.
  Portable renderchar suite: 131 tests, 102 passed and 29 private skips, 1.32 s.
- Early-body preflight: 280 sampled bodies, 7,168 forcing-record states, 2,016 directed lights and
  896 independent frame counters, zero mismatches, 9.15 s. No mutants have run yet.
- The standard other-body screen covers all multi-type shapes and additional singletons without a fit.
  The broader early-body screen tests 118 clean candidates, adds only `0x2493`, and rejects the rest,
  488.39 s. `0x23f4` and `0x2701` retain independent-state failures. The two paused standard-screen
  segments are iteration diagnostics, not a completed full body comparison.
- A 194-row refusal ledger records historical groups, source addresses and specific reasons in
  `docs/research/item-body-refusals-002z.tsv`. No denominator is replaced by a diagnostic count.

Next: full pinned body generation, then finish checks. Proposed counts remain provisional until those pass.

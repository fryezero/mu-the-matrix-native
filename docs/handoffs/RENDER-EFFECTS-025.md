# RENDER-EFFECTS-025

## WIP checkpoint

Branch `codex/render-effects-025`, base main `ff8e0543`. Offline/static only. No live client,
installed app, launcher, network, server-state, protection-module work or memory writes.
No subagents. Research part 37 is planned, subject to checking main before the final push.

Done:
- Traced Hammer14's `up01` lookup and sprite helper. The loader copies the authored name,
  the lookup returns -1 for `up01 `, and the sprite helper still reads `BoneTransform - 0x30`.
  Added an explicit optional host transform for that separate record. Names stay exact;
  other negative and out-of-range bones retain their refusals.
- The native default supplies a separate zero record. Fixtures may supply all twelve words
  or NULL to retain the refusal. This ports the operation on explicit native state. It does
  not establish identity with the original process bookkeeping occupying that address.
- Ported clouds/28 create/move/render. The initial sample caught the missing alpha multiplier.
- Expanded the scene census to 96 admitted programs in twelve eight-wearer batches. The two
  remaining particle pairs are `0x8109/7` from `0x1313`/`0x1317`, and `0x810a/9` from `0x1319`.
  Added both consumers. They account for 12 unsupported requests in the bounded 16-draw fixture.
- Captured main's default 46-view sweep once, plus eight maces, closer Ferea and the Lorencia
  demo at clocks 0/123456. Local outputs are lane-owned under `native/{scratch,renders}/render-effects-025`
  in the shared tools directory. No proprietary inputs or rendered images are staged.

Checks so far:
- Baseline root build 42.73 s, explicit render targets 5.19 s.
- Implementation builds 12.50, 10.80 and 14.95 s after the initial aggregate initializer repair.
- First focused final-scope sample: 2,001 comparisons, zero mismatches, 8.406 s script.
  This is 600 create, 600 move, 600 render, 200 complete Hammer14 request streams and one native host.
- Initial two native module tests passed in 10.881 s, before adding the two bow pairs and
  the full native draw-adapter assertion. Those additions still need their final private run.

Left:
- Finish compiled mutants, registry row and final full focused sample.
- Finish the native adapter assertion and portable fallback/negative-domain test.
- Compare native after renders and finish the 96-program refusal census.
- Run post-build affected selectors, affected portable suites/private validators, 8d reduced and 6b consumers.
- Merge latest main, write research and final handoff/status/PR body, audit, push, PR, ready line, cleanup.

The steward owns the full gate and merge. No ready-prs entry exists for this lane at this checkpoint.

Checkpoint update: the full focused proof passes 10,002 component comparisons, zero mismatches,
30.81 s script / 30.87 s command. The new registry row passes 202 comparisons and 24/24 compiled
mutants, zero stopped, 59.8 s row / 59.89 s command. The private five-module run covers 41 tests:
38 initially pass, three stale missing-name assertions are corrected and all three pass on rerun
in 0.660 s. No production code changed for those expectation repairs. The expanded 96-program
scene changes 7,389 accepted / 28 refused to 7,416 / zero; unsupported particles 12 to zero.
The denominator changes because newly admitted particle rand calls affect later gated requests.
The eight-mace run changes 5,610 / 61 to 5,671 / zero, with 61 more sprite allocations and one
more sprite submitted at the final frame. Its final PNGs remain identical; no visible gain is
claimed for those cameras. Closer Ferea creates 257 particles / zero unsupported versus 243 / 14.
The two-clock final frames change 6,623 / 6,626 pixels.

Post-build selectors retain 80 validators, including meshdraw, model_edge and movement symbol
fallbacks. The portable selector exceeds the private 40-module cap; 8d is reduced to changed
native modules plus shared consumers. The affected batches and final identity sweep are next.

Merged main ACTORS-001 as `ba6c5bfd`, then NEXT-GAPS-001 as `00e84869`. Both appended validator
rows are retained. Merged root build passes in 12.93 s; render targets in 5.35 s; manifest checks
in 1.14 s. The combined range from ff8e0543 selects 83 validators, including actor_recipes,
audio_combat and viewport_monsters beyond the original 80. The merged portable delta selects
155 work items; its native selection still exceeds the 8d cap.

The first portable batch covers 1,652 tests: 1,371 pass, 280 skip, one new ctypes fixture fails.
The fixture wrote through a pointer slice without an end index; explicit element stores repair it.
That failed test passes in 0.013 s. No production behavior changed. Batch wall 282.5 s / 347.83 s
including selection. The native host now clears its raster, supplies identity view/projection
and asserts actual fragments in addition to the existing routing and adapter assertions; it
passes in 1.570 s. The original arithmetic comparators and compiled mutation targets are unchanged.

The merged portable delta passes 1,464 tests: 1,223 pass, 241 skip, no failures/errors, 422.6 s
runner / 504.28 s command. The six-module private run passes all 45 tests in 115.188 s runner /
115.28 s command. The 83-row affected validator batch is running. Main has since landed
RENDER-ITEMS-002X as `3732f82a`; merge and delta checks follow after the current batch finishes.
Research part 36 is now occupied on main; this lane retains part 37.

Static follow-up explains Hammer14's unchanged pixels. The original `up01` call at `0x017d9a6e`
pushes scale zero at `0x017d9a54..0x017d9a58`. The native restored request also has scale zero.
The refusal and allocation counts change; its visible area does not. No positive-size replacement
or name trimming is introduced.

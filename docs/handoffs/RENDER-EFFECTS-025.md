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

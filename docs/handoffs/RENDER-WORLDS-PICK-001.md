# RENDER-WORLDS-PICK-001

Branch `claude/render-worlds-pick-001`, from main `c5b9d5ca` (#400, batch 118; #399 INNER-005 merged). Claude
Fable 5.2 lane, no subagents. Worktree `~/Documents/MTM/worktrees/render-worlds-pick-001`. Merge belongs to the
steward.

## WIP (checkpoint 2)

**Done**
- Step 1 complete in code and checks: `validate_worlds_pick` 3,000 cases (box, segment, pick) equal, 0 stops,
  23/23 compiled mutants detected (lowest 23), 343.4 s through `run_validators.py --private --cache` at this
  commit. Portable tests `reconstructed/objects/test_worlds_pick.py` (7) and the runtime host
  `native/tests/test_native_worlds_pick.py` pass.
- Base numbers taken once: base `mu-world` SHA-256
  `0b67fc1e9ec614d2c318fb51d31f1205c7f8d5fd4921aa34834b969a23519c8a` (main `c5b9d5ca`); 46-view default sweep
  ledger `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-pick-001/before-ledger.json` (79.9 s).
- Step 2 tool started: `scripts/world_inner_census.py` (abstract interpreter over the pinned text). Its probes
  reproduce the documented tables of Kanturu 37/40, Kalima, Crywolf, Trials, Aida, Remain, the tower, Barracks,
  Elbeland and Swamp of Calmness (`--probe ENTRY,WORLD`).

**Left**
- Census: run every routine (RenderObjectVisual's own world cases, the chain hooks, the 48 class visuals), add the
  native status (producer constants in the sources, consumer oracles, a mu-world probe per row), write the CSV and
  the summary.
- Research doc `docs/research/client-worlds-pick.md`; step 3 if time remains; after sweep, affected checks,
  status lines, PR.

**Next step**
- Extend `world_inner_census.py` `main` with the routine list and the CSV writer; then the status oracles.

# SESSION-COMBAT-001

Bounded plaintext combat migration implemented in `codex/session-combat-001`.
The interrupted checkpoint was reviewed and corrected before release. [Finding and evidence](../research/client-combat.md#9-session-combat-001-2026-10-28).

- Session combat state, frame handlers and intents; combat renders results; local combat/item kill observers removed.
- Fixture owns synthetic damage/death/reward/respawn rules. Attack/move use plain in-process frames; encrypted casts remain journaled unsent.
- Only F3 and C5 static seed rows added after the scoped reverse lookups. No other routing recovery or table export.
- New body/builder comparison: 6,000 cases, zero mismatches, 6/6 compiled mutants caught.
- Existing families: 25,200 combat and 33,000 effects/voice cases, zero mismatches, 32/32 mutants caught.
- `combat-fight.scn` runs in VERIFY-SESSION; attack/action/damage/die/16/20/A4, zero unbound/undecodable.

Local artifacts: `~/Documents/MTM/mu-mac-tools/native/scratch/session-combat-001/`.
Final release verification on `2b36422`, with latest main `b223709` integrated:

- `bash scripts/local-macos-ci.sh`: passed; 1,458 tests run, 177 explicit skips; viewer/readers build and repository audit pass, 1,342 staged files, zero rejected.
- VERIFY-SESSION: 7/7 scenarios, 50 expectations, 53 inbound frames, zero unbound/undecodable. The combat scenario has seven inbound frames and ten expectations; its two unsent requests are intentional.
- Private session test: 5/5 pass, including 240 instruction cases and six mutants. Registered validator runner: one pass, no failures/errors/skips.
- New 6,000 + existing 25,200 + effects/voice 33,000 comparisons total 64,200, zero mismatches; six compiled mutants and 32 existing modeled negative controls all caught.
- No existing golden/render hash pins changed. Combat timing/RNG, unsent-cast kills, synthetic drop and unknown remote-HP presentation changes are recorded in the finding. Pinned text/data hashes are unchanged.

Release evidence: `release-audio-ci.log`, `resume-combat-wire.json`, `resume-combat.json`, `resume-skillfx.json`, `resume-session-private.log`, `resume-manifest/`, plus the local CI fixture reports under this worktree's ignored `verify-runs/` before cleanup. A durable copy of the final fixture report is retained in the scratch directory. Untracked evidence/Python symlinks account for the fixture runner's dirty flag; no tracked source changes were pending during this gate.

Manual scope/standards review corrected incomplete fixture die frames, unknown HP sentinel conversion, reset-test coverage and the seed-only fixture include boundary. The first full gate's three findings are closed in the final passing gate. No hosted workflow or live client was run.

Remaining: NET-DECODE-001 for actual wire construction/encrypted requests and experience acceptance;
SESSION-SKILL-001 for broader cast/skill integration; SESSION-ITEMS-001 for ground ownership/pickup;
the separate remote HP-update route, special-world body services and live comparison. No live game, crypto or keyed-transform reconstruction.

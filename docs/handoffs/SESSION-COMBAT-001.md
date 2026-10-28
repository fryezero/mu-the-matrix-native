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
The local macOS gate and final suite counts are recorded below after verification.

Remaining: NET-DECODE-001 for actual wire construction/encrypted requests and experience acceptance;
SESSION-SKILL-001 for broader cast/skill integration; SESSION-ITEMS-001 for ground ownership/pickup;
special-world body services and live comparison. No live game, crypto or keyed-transform reconstruction.

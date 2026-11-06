# Offline join vitals and the toxic HP orb

APP-POLISH-003 changes the offline preview's join data and HUD input. No maximum-vital formula is ported.
The progression fallback introduced by APP-POLISH-002 is removed. The session's maxima now go directly to
setHPMP, including zero when a fixture does not supply them. A world without a session leaves the layer's
existing values alone. No damage, regeneration, stat-allocation or combat algorithm changes.

## Recorded join data

The source is the retained 2026-10-22 MTM-1 read of FryeZEN2, already documented in
[client-progression sections 1 and 7](client-progression.md). This lane reread the local dump, without
starting the original client. `scratch/progress/live/dk1-192dac80.bin` under the native tools directory is
12,288 bytes, SHA-256 `188ed9d02ee7c6e1a281c6e7959b2f477b987cafe1e7dbb1b2972ebe0e434402`.
It starts at CharacterMachine `0x192dac80`. CharacterAttribute begins eight bytes later. The global
`0x01d1df1c` points to CharacterAttribute; `[0x01d1df18] + 8` gives the same record.

Observed class `+0x187` is 1, level `+0` is 1, and the five stats at `+0x18a` are 28,20,25,10,0.
The eight int32 values at attribute `+0x68..+0x84` are 1100,200,1100,200,52,52,25,25, in order
HP, MP, HP max, MP max, SD, SD max, AG, AG max. These are server-supplied values observed in the client,
not a derivation from the demo progression formula. The existing progress fixture supplies the matching
baseline stats. The recorded master-level word is irrelevant to this non-third-class hero.

`fixture/hero_join.h` supplies those four full resources only for the existing class-1, level-1 world
session. Actors, characters and skill-only world fixture creation all use it. The dev-only seed writes
current, ordinary maximum and third-class maximum slots once at join. No frame handler changes.
The preview's default combat fixture HP input becomes 1100, so its existing initial placement answer
and damage model agree with that join. Explicit standalone `--hero-hp` input still overrides the default.
The underlying combat default and all damage/RNG/respawn rules are unchanged.

This does not establish values for other classes or levels. The synthetic character-selection list's
level/name is separate from the existing world session's level-1 seed; this lane does not reconcile that
older split. Nor does it complete CharacterInfo ownership or replace progression's demo server formulas.

## Original toxic-state selection and movie behaviour

Original instructions use `pins.TEXT` and `pins.DATA`, with the requested `pins.SECTION3` also hash-checked.
See [client-app-polish2](client-app-polish2.md) for the getters, property names and viewport addresses.

- At `0x00c71798`, push state `0x37`; `0x00c7179f` calls membership query `0x00c54ea8` with ECX
  `0x01d1df54`. If absent, `0x00c717ab` pushes `0x136`, queried at `0x00c717b5`.
- Either present takes `0x00c717c7`, writing 1 to `[ebp-0x14]`; neither takes `0x00c717c1`, writing 0.
  `0x00c717ce..d1` copies the byte to the vital cache object. The cache equality/copy at
  `0x00c718a3/c1` includes that byte, so changing only the toxic flag must refresh the movie.
- `0x00c718f5` writes `isToxic`; `0x00c719d6` invokes `setHPMP` with the full object.
- Static reading of the existing local `Frame.Main.setHPMP` decompilation: true selects the HP bitmap
  `guege_hp_green-nopack`; false selects `guege_hp-nopack`. The MP/SD/AG bars receive only their values.
  The main movie's provenance hashes are unchanged from APP-POLISH-002.

The expanded `validate_app_polish2` enters at `0x00c71798`, executing this selection and the intact body.
Membership and GFx calls are recording boundaries. The native comparison compiles the production
`toxic_state`, seed, hero getter, vitality adapter and GFx layer. It compares the actual outgoing Invoke
object, with repeated vital values and state-only transitions, ordinary/third classes, both flags,
neither flag and neighbouring non-toxic states. Each original case also verifies cache suppression.
Portable tests cover join data, refusal to extrapolate, absent maxima, precedence, idle stability,
state-only changes and restoration of the red orb. Fourteen compiled mutants target eight vital mappings,
session disconnection, demo animation, each state ID, the outgoing flag and cache invalidation.

The session has no replicated buff-list state. `mu_gfx_hero.is_toxic` is the display input for that future
adapter; today `--gfx-open buffs=55` or `buffs=310` exercises it through the existing demo-buff path.
This does not inflict poison, change stats, create a timer or implement a state packet. Poison application,
expiration and the future session-buff adapter remain open.

The patched updater entry `0x00c71772 → 0x10b14930` remains opaque and untouched. IGC.dll, RGS.dll, packer,
Hash Protection, network/login/dispatch and live-client access are outside this lane.

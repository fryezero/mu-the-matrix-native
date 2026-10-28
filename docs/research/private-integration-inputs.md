# Private integration inputs, INTEGRATION-GREEN-001

Target `main.exe`: SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Offline checks only. The installed app's Native Data `setup.json` identifies the game root; no original client
or launcher was started, stopped or read live. Captures and generated manifests stay local and ignored.

## Effects input scope

Verified by reading both validators: the previous loader verified all 54,525,952 bytes of capture-04, then
passed only its first `0x12a00` bytes to `Machine` or `TreeMachine`. Those are the initialized section-3
range `[0x01ced000, 0x01cffa00)`, 76,288 bytes. This includes the frame-step constant at `0x01cf103c`
and initialized C++/CRT data. The existing emulation supplies later section-3 storage as zeroed pages,
records undefined reads and explicitly sets the epoch, locale pointer and math-dispatch flag. That behavior
and every compared routine remain unchanged.

The old analysis directory still holds capture-04. Its whole-file digest is exactly
`0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f`.
Its first 76,288 bytes match the range digest already recorded in [client-effects.md](client-effects.md):
`299d83842841fa2cdb619c42fa25d42c228971c9261d526c5743102092729f32`.
Both effects validators now verify that range through `pins.EFFECTS_INIT` before mapping it. They accept
either the old capture or an exact range-only file starting at `0x01ced000`. Reports name the initialized
range digest and length, without claiming verification of an unused runtime tail.

This is a scope change from the old whole-file pin to its previously documented initialized-range pin,
with no replacement client bytes. `pins.SECTION3` retains the original whole-file pin for objects/movement.
The 2026-10-24 guest read `x86-guest-sec3-25` has whole digest
`e011c60f9d63d4d36453f0e8e3d12b9c141f584a8659e3850667d8c2c7bb5b9e` and initialized-range digest
`17918e3236e0175d9b41af3a2595e4a8e51869f7daa96c9430a76c7070502ba5`.
It differs in 384 bytes inside that range and remains rejected. No equivalence to that runtime state is claimed.

Synthetic tests reject a changed initialized byte, truncated range and missing file, while allowing arbitrary
unused tails. The private effects and tree comparisons use the extracted, hash-verified range file.

## Model corpus manifest provenance

Old pin: `fffcbad941e9bad394489382e79ad6d9d2e9f405847975de0eff113babd366ff`.
New pin: `27afde534d6b2d2af7fd4e551a9c3217416329089b2a3652c9f396a3f09884e0`.

The original `verified-v14/manifest.json` was located in the older analysis directory and compared directly
with a fresh strict scan of the app's installed game. All 12,754 relative paths and their order agree.
Every recorded source size/hash and decoded-payload hash agrees. There are exactly 20 differing records:

- Three v14 records have `json`/`obj` export annotations in the old manifest. The selected assets were
  `Data/Item/flag_class04.bmd`, `Data/Object113/Object07.bmd`, `Data/Object113/Object97.bmd`. The old summary
  counts three exports of each kind; the new scan has zero.
- The 17 rejected v15 records have more precise `error` strings after commit `30bea61`, which added the
  offending bone, vertex, corner and layout offsets. Rejection status and input identity did not change.

No timestamp, ordering, installation-file or accepted-model difference accounts for this drift. The only
changed top-level fields are `summary` and `files`. Counts remain 12,663 parsed, 17 rejected, 74 unsupported;
versions remain 701 v10, 180 v12, 216 v14 and 11,583 v15. The rejected-file diagnostics retain their original
`ba945b166c52e068a4ed12bbbc67a27f68d697fcf64197aaff627b09e45b909a` pin. Validators still verify each
installed payload against its source digest, with rejected v15 identities coming from those diagnostics.

Reproduce with the current documented scanner and no export selections or `--client-layout`:

```sh
make -C model-recovery
./tools/python/bin/python model-recovery/recover_models.py \
  --root "$MU_GAME_ROOT" --output "$NEW_SCAN_DIRECTORY" --validate-all
export MU_V14_MANIFEST="$NEW_SCAN_DIRECTORY/manifest.json"
```

The scanner exits 1 because the complete corpus includes the 17 explicit rejections and 74 unsupported
formats. Inspect its manifest rather than treating this expected scan status as a decoder-test failure.
Two independent runs on 2026-10-27 produced the new exact digest. The scanner records no absolute root or timestamps.
The scanner file SHA-256 was `748a79dab2c776222e92a684d45f032e3586ee1df42334264f3e28896d4816cd`.
See [the task handoff](../handoffs/INTEGRATION-GREEN-001.md) for actual test counts and local report locations.

## Native checks and environment isolation

The app's legacy Native Data directory has `setup.json` but no current manifest. Passing its lang/object/audio
paths as ambient environment made native tools correctly refuse that set, including unrelated synthetic tests.
The portable gate runs without those private export variables. The native private suite uses only the installation
and pinned captures; optional export consumers run separately against existing explicit research exports under
the snapshot scratch root. No app folder, manifest guard or original game file is changed.

The optional installed Lorencia-fire test exposed a separate stale expectation: it required exactly 17 loaded
particle bitmaps. The current `mu_particles.c` bank has 49 effect entries plus the two world rain textures, 51 total,
including later helper, terrain, Icarus and world-warp additions. The run loaded all 51. The test now requires exactly
51 successful loads and retains its creation, unsupported-count and drawn-particle assertions. This updates a
coverage count to the expanded bank; it does not accept a missing bitmap or change production rendering.

## Clean build ordering

The clean build at main `8eac05c` failed compiling `mu_combat.c` before `session_intents.h` existed.
A stale generated header also omitted the new combat intents. Later main already adds a combat-specific
dependency. This lane covers the transitive core consumers as well. Core facades now depend on the session
and layout generation stamps and session headers, as world/session objects already do. The fresh-target
regression checks generator ordering for combat, NPC and player consumers. This changes build dependencies
only. It does not change handlers, routing, fixture policy or instruction-comparison expectations.

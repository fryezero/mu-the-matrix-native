# Other players: viewport, equipment, moves and removal (NATIVE-PLAYERS-001)

This finding answers how the pinned client handles the other characters a server puts around the hero: how a remote
player is created from the player viewport, how its class and equipment bytes become the part and weapon slots the
world render draws, how the server's move packets are replayed through the hero's own path follower, how it dies and
disappears, and how its name plate and personal store show. It joins that to the native world as a clearly labelled
local demo (there is no server in this project).

Labels:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case
  (`scripts/validate_players.py`);
- **static**: a reading of the decoded instructions that was not executed;
- **inferred**: a reading of bytes that a protection patch partly destroyed;
- **demo**: native inputs or choices that stand in for the server.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_players.py` refuses other inputs and records the SHA-256 (first 16 hex digits) of the bodies it
runs. The body of ChangeCharacterExt is pinned with an explicit end (`0x0137c276`) because its two patched sites jump
out of the restored text.

## Short answers

- **Packets.** The receive dispatcher's table `0x0128e59d` (NATIVE-NET-001) routes opcode `0x12` to the player
  viewport `0x0122d413`, `0x13` to the monster viewport `0x0122c426`, `0x14` to the viewport destroy `0x01232986`,
  `0x17` to the die packet `0x01234585`, `0x1f` to `0x0122e633` and `0x45` to the equipment change `0x0122f1b6` (both
  create through the same routines), `0x3d` to the move packet `0x0126568e` and `0x3f` (sub-codes at `packet[3]`) to the
  personal store handlers (`2` open `0x0122e4da`, `3` `0x01233b83`, `6` `0x0127ef18`). The classic `0xd4` walk opcode
  is not in this table.
- **Creation.** Each viewport record (`0x44 + 8 × buffs` bytes) names a key (bit 15: the character appeared here),
  a tile, a packet class byte, 18 equipment bytes, a 10-character name, the target tile, direction and PK level,
  pets, the ride item, a server word and flags. CreateCharacter `0x0137f6c2` reuses the live slot with that key or
  takes the first free one of 400; the character create `0x0137d8a1` writes the defaults (scale 0.9, PK 3, guild
  -1, Player action 1, move speed 10, every part -1, ...). The class byte is `0x0139ca62` of the packet byte (the
  nibbles swap: packet `0x10` is class `0x01`).
- **Equipment → slots.** ChangeCharacterExt `0x0137b68c` decodes the 18 bytes: weapons (byte 0/1 with the high
  nibble of bytes 0xb/0xc, `0xfff` none), the five body parts (9-bit codes spread over bytes 2..4, 8 and 0xc..0xe;
  `0x1ff` means the class's default part `0x3700 + 0x50 × slot + skin`), the 3-bit level codes of byte 5..7
  (`0x01395741`: 0, 3, 5, 7, 9, 11, 13, 15), the excellent bits of byte 9 and the ancient bits of byte 0xa, the wing
  through the switch `0x0137c7df` (an 8-bit index from bytes 4, 8 and 0xf → 102 item types; some read the level from
  byte 0x11), the group-13 helper (pet) of byte 4 and the ride state of bytes 0xf/0x10. It also drives the helper
  effects and the mount manager. The slot layout is the one the world render reads (NATIVE-RENDERCHAR-001): type
  word, level +2, option (excellent) +3, ext (ancient) +4.
- **Movement.** The move packet `0x0126568e` stores the direction (byte 7 high nibble) and the target tile, then
  PathFinding2 (mode 2, or 4 in worlds `0x52..0x5a`; 4 again on failure) from the current tile; without a path the
  character is set onto the target. Every logic step MoveCharacters runs `0x013b852a` for every character but the
  hero: with Movement set, SetPlayerWalk (unless the character's skill belongs to group 7), MovePath(c, 1), on
  arrival Movement = 0, SetPlayerStop and the angle `(direction - 1) × 45`, then MoveCharacterPosition; without
  Movement and a target that differs from the tile, a new path (or the teleport). Dead characters are left alone.
- **Removal.** The destroy packet lists keys (bit 15 cleared); DeleteCharacter `0x0137c457` clears the live byte,
  calls removeInfo (hudPlayerName) unless the world is one of `0x009dacb8`'s, releases helpers, buffs and effects.
  The die packet sets the dead counter; from 15 on SetPlayerDie's Player branch takes action `0x142`/`0x144..0x147`,
  the fade `0x013a5ea1` sinks and removes the character (NATIVE-COMBAT-001/002).
- **Plates and stores.** addInfo runs at the end of the viewport record (kind 1: the PK colour, the guild line,
  party HP bars; NATIVE-NAMES-001). A personal store is `setStore({isOpen: true, store: GlobalText[0x450], id:
  "<font color='PK colour'>name</font>", title})` on the player's clip (`0x00c84731`, the entry byte `+0xa0` = 1;
  this names the writer NATIVE-NAMES-001 had not found), `setStore({isOpen: false})` on close (`0x00c848fa`), also
  called by the destroy handler.

## Routines

| Routine | Address | Status |
|---|---|---|
| player viewport (opcode 0x12) | `0x0122d413` | static (record layout, creation effects) |
| CreateCharacter | `0x0137f6c2` | static |
| character create (defaults) | `0x0137d8a1` | static (the constant stores; world-specific tails not read) |
| packet class byte → class byte | `0x0139ca62` | verified (256 values) |
| ChangeCharacterExt | `0x0137b68c` | verified (helper codes 0, 0x20, 0x40, 0x60, 0x80; 0xa0 inferred) |
| wing switch | `0x0137c7df` | verified (every index 0..0x66, with and without the level nibble) |
| item level code | `0x01395741` | verified (256 values) |
| class tier / skin index | `0x0139cb8a`, `0x0139d6a2` | verified (256 values) |
| ride state | `0x0129dc91` | verified |
| move packet (opcode 0x3d) | `0x0126568e` | verified (model `0x7d9` and the hero's auto-move list static) |
| MoveCharacters' remote step | `0x013b852a` | verified (dead model `0x7a7` static) |
| MoveCharacters' loop (attribute bit 2 marks, frustum byte, the per-character calls) | `0x0137a7ce`, `0x0137a716` | static |
| viewport destroy (opcode 0x14) / DeleteCharacter | `0x01232986` / `0x0137c457` | static |
| equipment change (opcode 0x45), the "object" viewport (0x1f) | `0x0122f1b6`, `0x0122e633` | static (same decoder) |
| store open / close | `0x0122e4da` / `0x01233b83`; `0x00c84731` / `0x00c848fa` | static |

### The viewport record (static)

| Offset | Field |
|---|---|
| +0 | key, big endian; bit 15 = created in place (no walk-in: position = (tile + 0.5) × 100, effect `0x7f85` for others) |
| +2, +3 | tile |
| +4 | packet class byte; `(b & 7) == 1` with an existing character keeps its guild fields |
| +5..+0x16 | the 18 equipment bytes (ChangeCharacterExt); byte 0x15's bits 5..7 are a pose state (2..4: the sitting / ride actions `0x172..0x17f`, `0x179/0x17a` by sex and the ride buffs `0x59/0x5a/0x72`; 1: a sub-handler `0x01219985`) |
| +0x18 | name, 10 characters ("webzen" names are skipped) |
| +0x22, +0x23 | target tile |
| +0x24 | direction (high nibble; the angle is `(d - 1) × 45`) and PK level (low nibble) |
| +0x25 | elemental attribute |
| +0x26..+0x2e | three pet item codes (big-endian word + level byte; kind-0xc items only) |
| +0x2f | pet index; +0x30 ride item (big endian); +0x32 a class-nibble-4 byte |
| +0x3e | server word (the server name when the server flag is set) |
| +0x40 | bit 0 stunned, bits 1..6 → `c + 0x3230`, bit 7 transformed |
| +0x41, +0x42 | muun item index (table `0x06fbc870`) and level → slot 9 |
| +0x43 | buff count; +0x44 + 8 i: buff type word and value |

After the fields: no path for a created character; otherwise PathFinding2 to the target (mode 2 / 4 / teleport);
world `0x18..0x1d`/`0x24` effect `0x7f79`; name; the buffs through `0x0128723b`; world `0x1e` → `0x00d8b3e3`;
addInfo for others; the server name; class nibble 8 → effect `0x64b`.

### ChangeCharacterExt (verified)

In the client's order, for a Player-model character:

1. weapons from bytes 0/1 and the high nibbles of bytes 0xb/0xc (`0xfff` clears the slot and its option/ext bytes);
2. the wing switch (index `((e4 & 0xc) << 4) | ((e8 & 7) << 3) | ((e15 & 0x1c) >> 2)`; 0 and > 0x66 → none);
3. with the fourth argument 0: `0x00c9ea70(o)` and the helper effect off; else the object's live byte cleared;
4. the helper: `e4 & 3` (3 = none); for 0..2 the type is `0x24e6 + v` and, for 0 outside scene 6 or without a pet
   item, the effect `0x24e6`; the codes `e15 & 0xe0` = 0x20 / 0x40 / 0x60 / 0x80 give the helpers `0x24e6 + 0x40 /
   0x41 / 0x7b / 0x43` with a model effect `0x1a00 + w`;
5. the mount manager: reset and set with the helper type and the ride state (transformed: -1 and `0x00b9b476`);
6. the hero-only option block (static), `0x009ebf04(c)`;
7. `c + 0x16` from byte 0xb bit 1 (kept when 1..3, else 4 / 0), `c + 0x31dc` = 0x10 / 0xf from bit 3;
8. the levels, the five parts (code `0x1ff` → the class part), the option and ext bits, `c + 0x15` = byte 0xa bit 0;
9. `0x009dadf1(c)` when `c + 0xe` is 0, `0x01394f6f(c)`, and for the hero outside scene 5 `0x01394870(c)`.

**The patched sites.** Five bytes at `0x0137b8c9` (after the compares with 0x20, 0x40 and 0x80) and five at
`0x0137b901` (the switch default) are protection patches that jump outside the restored text. The surviving bytes
after them (`74 1d` = `je 0x0137b924` where `push 0x50` lies, `eb 2b` = `jmp 0x0137b934`) fit `cmp byte [ebp-0x28],
0xa0; je` for the default and `cmp eax, 0xa0; je 0x0137b8dd` for the first site. The C therefore maps 0xa0 to the
helper `0x50`; this is **inferred**, not executed. The validator models the first site as "no match" and keeps the
codes 0xa0..0xe0 out of its domain.

## Validation

`scripts/validate_players.py` runs the routines in Unicorn (`scripts/client_ui_machine.py`) and compares each result
with `reconstructed/players/libremoteplayers` on the same synthetic CHARACTER record, equipment bytes, packets and
host answers. Modelled explicitly: the key → character lookup, the effects, the mount manager, the hero state
getter, the skill table and the movement services (PathFinding2 with a scripted answer and path, MovePath,
MoveCharacterPosition, SetPlayerWalk/Stop, SetAction), each recorded with its arguments and compared in order; the
vector accessors, the world predicate and the field getters run as client code. Any other executed block stops the
case.

Private run (`--cases 1000 --negative 60`, about three minutes), report `evidence/native-players/report-01.json`:

| Section | Cases | Result |
|---|---|---|
| class byte, item level, class skin | 256 values each | 0 mismatches |
| wing switch + ride state | 1,000 (every index twice, then random) | 0 mismatches |
| ChangeCharacterExt: slots, bytes, engine calls | 1,000 (random equipment, scenes 2/5/6, both argument forms) | 0 mismatches |
| move packet: fields, path calls | 1,000 (hero echoes, unknown keys, dead, mode-4 worlds, teleports) | 0 mismatches |
| remote step: fields, calls | 1,000 (moving, standing, arrivals, kept actions, skill group 7) | 0 mismatches |
| negative controls | 7 planted mistakes (class bit, option bit, level code, wing level, move target, world mode, direction) | 7 detected |

Portable: `reconstructed/players/test_remote_players.py` (worked examples) and `native/tests/test_native_players.py`
(mu-walk on the synthetic world: viewport creation in range, plates of kind 1 with the party bar, move packets and
the route's tiles with the walk/stand actions, the die packet → SetPlayerDie action → fade → removal → respawn, the
store, walking into and out of the demo range, `--no-players`, determinism). Private: Lorencia with the demo players
(Item.bmd parts) and the Unicorn run.

## Native integration

- `reconstructed/players` is the platform-neutral decoder and movement logic; `native/core/mu_world_players`
  runs it in the session: a **demo server** (`native/world/lorencia-demo-players.txt`, labelled) encodes each
  player into the viewport byte layout (the inverse of the decoder, with the packet class byte found by inverting
  `0x0139ca62`), sends move packets when a player stands (its route), the die, store and destroy packets, and keeps a
  viewport range around the hero (default 12 tiles, `--player-range`). The client side then runs the reconstructed
  routines: CreateCharacter and the defaults, the record's fields, ChangeCharacterExt, the part files (class parts of
  the Player loader for `0x1ff`, Item.bmd's folder/file for item types through NATIVE-DATA-002, armour textures from
  Data/Player as NATIVE-ITEMS-001), MoveCharacters' remote step over the world's path finder (NATIVE-PATH-001),
  MovePath, CharacterMoveSpeed and MoveCharacterPosition (NATIVE-WORLD-001), SetPlayerWalk's run counter and walk
  action (NATIVE-PATH-002; the armed walk/stand poses are the static table of NATIVE-ACTOR-001), the Player model's
  animation step with the loader's play speeds, the dead counter, SetPlayerDie's action and the fade.
- The parts draw through RenderObjDraw's passes (`mu_renderchar_draw_item`: the level glow, excellent and ancient
  passes; the EnchantEffect colours of the Lang tables with `MU_LANG_DIR`, else a blue viewer colour), with the
  character light (terrain light + 0.2) and the fade's alpha. As in the NATIVE-RENDERCHAR-001 sheets, +9 and
  higher sets are chrome-white at town scale.
- The plates: each created player is a hudPlayerName character of kind 1 (PK colour by level, the guild line
  through the demo guild table, a party member's HP bar); removeInfo at destroy and after the fade; the store box
  through `mu_names_set_store` (the real movie's `setStore` through the GFx layer with `--gfx`, a stand-in box in
  the software path).
- `mu-world --players FILE [--no-players] [--player-range N]`, `mu-client --players FILE` (world_embed), reports
  `players_frame` per frame and a `players` summary.

Renders stay local under `~/Documents/mu-mac-tools/native/renders/players/`: `gl1/` and `lorencia-players.mp4` (the
demo in Lorencia with the town objects, 1,000 frames), `lorencia-players-town.png`, `lorencia-players-store.png`,
`soft1/` (the software path).

## Limits and next steps

- The viewport record, the creation effects, the destroy path and the store packets are static readings; the pose
  state (sitting / ride actions) and the pets are decoded but not animated; the helper (pet / mount) models and the
  mount pose are not drawn (the helper pass `0x01378d9c` is not reconstructed); the muun slot is decoded only.
- Hovering (setTopMovie) covers monsters only; player selection, trade and party requests are out of scope.
- The hero's own move echo (the auto-move list) and the special models `0x7d9` / `0x7a7` / `0x81e` / `0x93f` are
  static branches of the verified routines.
- The demo server's choices (routes, ranges, deaths, stores, guild names, HP) are not server behaviour.
- Next: the equipment change packet `0x45` end to end (it reuses the decoder), the helper models, a live capture of a
  crowded town for a side-by-side of the plates and the chrome sets.

# Monster and NPC session viewport

VIEWPORT-MONSTER-001, 2026-10-27. Plaintext loopback fixture only. No original client or live service used.

## Record handler

**Static routing evidence.** `client-remote-players.md` identifies opcode `0x13` with handler
`0x0122c426`. Only that seed row was added. No dispatch-table traversal or generator was used.
The scoped static reading covered `0x0122c426..0x0122d413` in pinned restored text capture09,
SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The data capture is run10, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

The C2 packet has count at +4, capped at 75. Records start at +5. A record consumes
`28 + 8 * buff_count` bytes, with the buff count at +26 and a maximum of 56.
Key bytes are big endian; bit 15 is the creation flag, bit 14 is also separately tested but remains
part of the masked key. The class uses only the low two bits of byte 2 and byte 3. Byte 2 also
contains the +0x34 flag and OBJECT +0x43 value. Tiles, targets, direction, elemental byte, four
OBJECT words, level, HP and buff records follow. HP uses byte indices 18,20,19,21 and 22,24,23,25,
respectively, in descending significance. These are not conventional big-endian dword reads.

**Verified bounded handler.** `scripts/validate_viewport_monsters.py` runs the original entry through
return for 1,000 records and compares authored C fields, CreateMonster arguments, buff calls and
record advancement. The fields include nine model-angle families, direction nibbles, both placement
path calls and teleport fallback, level and HP, flags, targets and OBJECT words. Three short-length
parser refusals per case add 3,000 authored boundary checks. Eight separately compiled C mistakes
are caught: class mask, HP byte order, angle factor, fallback target, stride, buff offset, creation
model and slot level. There are zero mismatches.

The model factory is an explicit host returning a synthetic CHARACTER with the requested tile and
one of nine model indices. Model-table angle override returns false. Engine singleton, name-plate,
creation visual and buff implementation calls are hosts, not equality claims. Elemental attachment
map processing, event-world branches, alternate-object classes accepted by `0x00d034b0`, and the
full creation/effect behavior remain outside this comparison. Their parsed fields are retained in
session metadata; retaining them does not claim native execution of those branches.

## Creation

**Verified bounded creation fields.** The new C creation adapter is compared for 963 classes against
original CreateMonster processor/generic execution through the existing `validate_actors` machine.
Model, nonzero equipment writes, equipment levels, class byte, key/class identity and initial tiles
match. The original CreateCharacter call is an explicit host; the existing player milestone's
verified default prefix is reused. Default scale and model action/effect tables continue through
`mu_actor`, unchanged. The 61 extraction failures are listed in the private report, not filled with
another MU version's data. Existing separately extracted effect classes, including 873, retain their
prior NATIVE-WORLD-002 evidence status.

This comparison inherits `client-actors.md`'s world-0/rand-0 assumptions, four declining processor
hosts and direct generic entry. It does not execute or analyse the intervening protection jump.
The native `kind = 2` discriminator distinguishes this feed from players; it is native policy,
not a recovered classification of every NPC. Missing class rows are ignored, rather than asserted
recovered. Player-model NPC rendering retains the existing 229/257 support boundary.

## Session and presentation

Players, monsters and NPCs use the same 400-slot CharactersClient table, keys, revisions, lease and
existing movement/destroy routes. A complete variable-length batch is checked before mutation.
Monster packet fields and buffs absent from the current CHARACTER projection live in replicated
per-slot metadata; the existing projection and reconstructed players/helpers implementations are
unchanged. Overflow is ignored; identity lookup reuses a key before choosing the first free slot.

The fixture `monsters` behavior owns placement parsing, its RNG, idle timers and wander targets.
It emits C2 13 creation and C1 3d movement. Actors load models from session records and step inside
the single characters lease at tick 21. The reserved actors tick-20 hook no longer steps records.
When cache identities change, the actors part rebuilds its model/effect cache from the records,
including GL texture teardown/reload. Cache rebuilding restarts presentation animation/effects.
The legacy actor cache remains capped at 32; session storage supports 400. Generic full-viewport
rendering remains open, as the previous player milestone also documents for its eight-model cache.

Unmigrated combat still mutates presentation motion. Its sink/respawn position is committed through
a motion lease before the next pump, and its wander pause is observed by the fixture. This bridge
must disappear with SESSION-COMBAT-001, together with that milestone's local damage/kill policies.
No replicated HP or death field is written by this bridge.

## Checks and artifacts

- Synthetic NATIVE-WORLD-002 world: 120 frames with wandering class 3, Smith 251 and effect class 873.
  All 120 SHA-256 frame hashes equal the pre-change `54ae63f` baseline. All 120 repeat unchanged.
  Models, scales, labels, movement/arrival totals, light and effect count also match.
- The discovered `monsters-viewport.scn` uses four frames for two creations, a move and a destroy.
  It has zero unbound/undecodable frames. Mixed player/monster and malformed-batch tests inspect records.
- Existing players/helpers/actors instruction families are rerun unchanged; final counts and local
  gate results are in the milestone handoff.

Local logs and reports: `~/Documents/MTM/mu-mac-tools/native/scratch/viewport-monster-001/`.
Synthetic renders: `~/Documents/MTM/mu-mac-tools/native/renders/viewport-monster-001/`.
Only source, synthetic scenarios and reviewed summaries are committed.
